import json
import logging
import re
from typing import Any, Dict, List, Optional
from app.agents.state.learning_state import (
    CandidateQuestionItem,
    DeepSeekAnalysisOutput,
    EvaluationItem,
    LearningState,
    MisconceptionItem,
)
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.providers.base import BaseLLMProvider, LLMResponse
from app.ai.schemas import ChatMessage, InferenceOptions
from app.core.config import settings
from app.models.assessment import Question
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def clean_think_tags(text: str) -> str:
    """Removes internal <think>...</think> chain-of-thought tokens from DeepSeek-R1."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()


def extract_json_payload(text: str) -> Dict[str, Any]:
    """
    Extracts valid JSON dictionary from LLM response text.
    Handles raw JSON, markdown fences, embedded blocks, and malformed text.
    """
    clean_text = clean_think_tags(text)

    # 1. Direct parse
    try:
        return json.loads(clean_text)
    except Exception:
        pass

    # 2. Markdown fenced block
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass

    # 3. Outer curly braces
    start = clean_text.find("{")
    end = clean_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = clean_text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass
        # Try unclosed brace repair
        try:
            repaired = candidate.rstrip() + '}'
            return json.loads(repaired)
        except Exception:
            pass

    # 4. Fallback for malformed / non-JSON LLM responses (Phase 7 requirement)
    lower = clean_text.lower()
    is_correct = "is_correct\": true" in lower or (
        "correct" in lower and "not correct" not in lower and "incorrect" not in lower
    )
    return {
        "evaluation": {
            "is_correct": is_correct,
            "answer_type": "correct" if is_correct else "partially_correct",
            "reasoning_summary": clean_text[:300].strip() or "Evaluated based on conceptual alignment.",
            "confidence": 0.85 if is_correct else 0.70,
        },
        "misconception": {
            "detected": not is_correct,
            "category": "conceptual_misconception" if not is_correct else "none",
            "description": None if is_correct else clean_text[:200].strip(),
        },
        "candidate_question": None,
    }


class AnswerEvaluationAgent:
    """
    Agent 3: Answer Evaluation Agent (DeepSeek-R1 via LM Studio).
    Evaluates conceptual correctness, identifies partial correctness, calculation vs conceptual errors.
    Also coordinates with Misconception Detection (Agent 4) and Question Generation (Agent 7)
    in a unified single DeepSeek inference pass.
    """

    @classmethod
    def evaluate_objective_answer(
        cls,
        student_answer: str,
        expected_answer: str,
        question_type: str = "MCQ"
    ) -> Optional[EvaluationItem]:
        """
        Deterministic validation for MCQ and simple numeric answers.
        Returns EvaluationItem if deterministically resolvable, else None for LLM evaluation.
        """
        s_clean = student_answer.strip().lower()
        e_clean = expected_answer.strip().lower()

        if question_type.upper() in ("MCQ", "MULTIPLE_CHOICE"):
            # Check exact match or single letter match
            if s_clean == e_clean:
                return EvaluationItem(
                    is_correct=True,
                    answer_type="correct",
                    reasoning_summary="Selected option matches the correct answer key exactly.",
                    confidence=1.0
                )
            # If both are single letters and differ
            if len(s_clean) == 1 and len(e_clean) == 1 and s_clean != e_clean:
                return EvaluationItem(
                    is_correct=False,
                    answer_type="incorrect",
                    reasoning_summary=f"Selected option '{student_answer.strip()}' does not match correct option '{expected_answer.strip()}'.",
                    confidence=1.0
                )

        if question_type.upper() == "NUMERIC":
            try:
                s_val = float(s_clean)
                e_val = float(e_clean)
                if abs(s_val - e_val) < 1e-5:
                    return EvaluationItem(
                        is_correct=True,
                        answer_type="correct",
                        reasoning_summary=f"Numerical value {s_val} matches expected value {e_val}.",
                        confidence=1.0
                    )
            except ValueError:
                pass

        return None

    @classmethod
    async def run(
        cls,
        state: LearningState,
        execution_manager: GPUExecutionManager,
        deepseek_provider: Optional[BaseLLMProvider] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        trace = list(state.get("node_execution_trace", []))
        trace.append("deepseek_evaluation")

        context = state.get("relevant_learning_context", {}) or {}
        student_answer = state.get("student_answer", "").strip()
        expected_answer = context.get("expected_answer", "")
        question_text = context.get("question_text", "")
        concept_name = state.get("current_concept_name") or context.get("concept_name", "Concept")
        candidate_concept_name = state.get("candidate_next_concept_name") or concept_name
        candidate_concept_id = state.get("candidate_next_concept_id") or state.get("current_concept_id")
        evaluation_rubric = context.get("evaluation_criteria", {})
        question_type = context.get("question_type", "OPEN_ENDED")

        # Fallback to database lookup if context was not pre-loaded
        if (not expected_answer or not question_text) and db and state.get("question_id"):
            q_db = db.query(Question).filter(Question.id == state["question_id"]).first()
            if q_db:
                expected_answer = q_db.correct_answer
                question_text = q_db.question_text
                question_type = q_db.question_type.value if hasattr(q_db.question_type, "value") else str(q_db.question_type)
                evaluation_rubric = q_db.evaluation_rubric or {}

        # Check for blank or ambiguous input immediately
        if not student_answer:
            return {
                "evaluation_result": {
                    "is_correct": False,
                    "answer_type": "ambiguous",
                    "reasoning_summary": "The student submitted an empty response.",
                    "confidence": 0.0,
                },
                "misconception_analysis": {
                    "detected": False,
                    "concept_id": state.get("current_concept_id"),
                    "category": "unclear_response",
                    "description": "No response provided.",
                },
                "evaluation_confidence": 0.0,
                "is_uncertain_evaluation": True,
                "clarification_prompt": "Your answer was blank. Please provide your explanation or working.",
                "node_execution_trace": trace,
            }

        # Check deterministic pre-check for objective questions
        deterministic_eval = cls.evaluate_objective_answer(student_answer, expected_answer, question_type)
        if deterministic_eval is not None and question_type.upper() in ("MCQ", "MULTIPLE_CHOICE", "NUMERIC"):
            eval_dict = deterministic_eval.model_dump()
            misc_dict = {
                "detected": not deterministic_eval.is_correct,
                "concept_id": state.get("current_concept_id"),
                "category": "calculation_error" if not deterministic_eval.is_correct else "none",
                "description": deterministic_eval.reasoning_summary if not deterministic_eval.is_correct else None,
            }
            return {
                "evaluation_result": eval_dict,
                "misconception_analysis": misc_dict,
                "reasoning_summary": deterministic_eval.reasoning_summary,
                "evaluation_confidence": deterministic_eval.confidence,
                "is_uncertain_evaluation": False,
                "clarification_prompt": None,
                "generated_question": None,
                "node_execution_trace": trace,
            }

        system_prompt = (
            "You are an expert AI pedagogical tutor evaluating a student's answer. "
            "Analyze the student's reasoning, evaluate conceptual correctness, identify any conceptual "
            "misunderstandings or calculation errors, and draft a calibrated follow-up question "
            "for the candidate next concept.\n\n"
            "You MUST output valid JSON strictly matching this structure:\n"
            "{\n"
            '  "evaluation": {\n'
            '    "is_correct": true,\n'
            '    "answer_type": "correct",\n'
            '    "reasoning_summary": "Evidence-based concise explanation of student reasoning",\n'
            '    "confidence": 0.95\n'
            "  },\n"
            '  "misconception": {\n'
            '    "detected": false,\n'
            '    "concept_id": "CONCEPT_ID",\n'
            '    "category": "none",\n'
            '    "description": "Description of misconception or gap if detected, else null"\n'
            "  },\n"
            '  "candidate_question": {\n'
            f'    "concept_id": "{candidate_concept_id}",\n'
            '    "difficulty": "medium",\n'
            '    "question": "Clear follow-up question text",\n'
            '    "expected_answer": "Reference answer",\n'
            '    "evaluation_criteria": ["Criteria 1", "Criteria 2"]\n'
            "  }\n"
            "}\n\n"
            "Allowed answer_type values: 'correct', 'partially_correct', 'incorrect', 'ambiguous'.\n"
            "Allowed misconception category values: 'conceptual_misconception', 'calculation_error', "
            "'incorrect_formula_application', 'incomplete_understanding', 'careless_mistake', "
            "'incorrect_prerequisite_knowledge', 'unclear_response', 'none'.\n"
            "Do NOT invent a misconception if the student understood the concept. "
            "Do NOT include internal reasoning or <think> tags in your output. "
            "CRITICAL: Start your response directly with { and end with }. Return ONLY valid raw JSON."
        )

        user_content = (
            f"Concept: {concept_name}\n"
            f"Question: {question_text}\n"
            f"Expected Answer: {expected_answer}\n"
            f"Rubric / Criteria: {evaluation_rubric}\n"
            f"Candidate Next Concept: {candidate_concept_name} (ID: {candidate_concept_id})\n"
            f"Student's Answer: {student_answer}\n"
        )
        if deterministic_eval:
            user_content += f"\nNote: Objective answer check indicates is_correct={deterministic_eval.is_correct}."

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_content),
        ]
        options = InferenceOptions(
            temperature=settings.LMSTUDIO_TEMPERATURE,
            max_tokens=settings.LMSTUDIO_MAX_TOKENS,
            context_length=settings.LMSTUDIO_CONTEXT_LENGTH,
        )

        provider = deepseek_provider or getattr(execution_manager, "deepseek", None)

        async def reasoning_task():
            res = await provider.generate_chat(messages=messages, options=options)
            raw_text = res.content
            parsed = extract_json_payload(raw_text)
            if not isinstance(parsed, dict):
                parsed = {}
            if parsed.get("misconception") is None:
                parsed["misconception"] = {"detected": False, "category": "none", "description": None}
            return DeepSeekAnalysisOutput.model_validate(parsed)

        try:
            exec_res = await execution_manager.execute_deepseek(
                reasoning_task=reasoning_task,
                context_length=settings.LMSTUDIO_CONTEXT_LENGTH,
            )

            raw_res = exec_res["result"]
            metrics = exec_res.get("metrics", {})

            if isinstance(raw_res, DeepSeekAnalysisOutput):
                analysis = raw_res
            elif isinstance(raw_res, LLMResponse):
                p = extract_json_payload(raw_res.content)
                if isinstance(p, dict) and p.get("misconception") is None:
                    p["misconception"] = {"detected": False, "category": "none", "description": None}
                analysis = DeepSeekAnalysisOutput.model_validate(p)
            elif isinstance(raw_res, dict):
                if raw_res.get("misconception") is None:
                    raw_res["misconception"] = {"detected": False, "category": "none", "description": None}
                analysis = DeepSeekAnalysisOutput.model_validate(raw_res)
            else:
                analysis = DeepSeekAnalysisOutput.model_validate(raw_res)

            # Deterministic override if objective check was decisive
            if deterministic_eval is not None:
                analysis.evaluation.is_correct = deterministic_eval.is_correct
                if deterministic_eval.is_correct and analysis.evaluation.answer_type != "correct":
                    analysis.evaluation.answer_type = "correct"
                elif not deterministic_eval.is_correct and analysis.evaluation.answer_type == "correct":
                    analysis.evaluation.answer_type = "incorrect"

            eval_dict = analysis.evaluation.model_dump()
            misc_dict = analysis.misconception.model_dump()
            q_dict = analysis.candidate_question.model_dump() if analysis.candidate_question else None

            confidence = analysis.evaluation.confidence
            is_uncertain = (
                confidence < settings.EVALUATION_CONFIDENCE_THRESHOLD
                or analysis.evaluation.answer_type == "ambiguous"
                or misc_dict.get("category") == "unclear_response"
            )

            clarification_msg = None
            if is_uncertain:
                clarification_msg = (
                    "Your answer could not be evaluated with sufficient confidence. "
                    "Could you please explain your steps or clarify your reasoning?"
                )

            current_metrics = dict(state.get("metrics", {}))
            current_metrics.update(metrics)

            return {
                "evaluation_result": eval_dict,
                "misconception_analysis": misc_dict,
                "reasoning_summary": analysis.evaluation.reasoning_summary,
                "evaluation_confidence": confidence,
                "is_uncertain_evaluation": is_uncertain,
                "clarification_prompt": clarification_msg,
                "generated_question": q_dict,
                "metrics": current_metrics,
                "node_execution_trace": trace,
            }

        except Exception as e:
            logger.error(f"DeepSeek evaluation error: {e}", exc_info=True)
            # Safe degradation fallback if model fails
            return {
                "execution_status": "error",
                "error_code": "DEEPSEEK_EVALUATION_FAILED",
                "error_message": f"DeepSeek evaluation failed: {str(e)}",
                "is_uncertain_evaluation": True,
                "node_execution_trace": trace,
            }
