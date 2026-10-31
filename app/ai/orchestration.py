import json
import logging
import re
from typing import Any, Dict, Optional

from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.providers.base import BaseLLMProvider
from app.ai.schemas import (
    ChatMessage,
    DeepSeekReasoningInput,
    DeepSeekReasoningOutput,
    ExecutionTurnMetrics,
    InferenceOptions,
    LearningTurnInput,
    LearningTurnOutput,
    LlamaFormatInput,
    LlamaFormatOutput,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def _extract_json_from_llm_response(text: str) -> Dict[str, Any]:
    """
    Robust JSON extraction from LLM text output.
    Handles raw JSON, markdown codeblocks (```json ... ```), and trailing text.
    """
    clean_text = text.strip()

    # 1. Direct parse attempt
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        pass

    # 2. Markdown fenced codeblock extraction
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Outer curly braces extraction
    start = clean_text.find("{")
    end = clean_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = clean_text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 4. Fallback: Parse markdown labeled key-value sections
    extracted = {}
    label_patterns = [
        ("answer_interpretation", r"(?:answer\s*interpretation|interpretation)[\*:\s]+(.+?)(?=\n\s*[\*#\-]*\s*(?:reasoning|misconception|conceptual|recommended|diagnostic|suggested)|\Z)"),
        ("reasoning_analysis", r"(?:reasoning\s*analysis|reasoning)[\*:\s]+(.+?)(?=\n\s*[\*#\-]*\s*(?:misconception|conceptual|recommended|diagnostic|suggested)|\Z)"),
        ("identified_misconception", r"(?:identified\s*misconception|misconception)[\*:\s]+(.+?)(?=\n\s*[\*#\-]*\s*(?:conceptual|recommended|diagnostic|suggested)|\Z)"),
        ("diagnostic_explanation", r"(?:diagnostic\s*explanation|explanation)[\*:\s]+(.+?)(?=\n\s*[\*#\-]*\s*(?:recommended|suggested)|\Z)"),
        ("recommended_learning_intervention", r"(?:recommended\s*learning\s*intervention|intervention)[\*:\s]+(.+?)(?=\n\s*[\*#\-]*\s*(?:suggested)|\Z)"),
        ("suggested_follow_up_question", r"(?:suggested\s*follow[ -]?up\s*question|follow[ -]?up)[\*:\s]+(.+?)$"),
        ("friendly_feedback", r"(?:friendly\s*feedback|feedback)[\*:\s]+(.+?)(?=\n\s*[\*#\-]*\s*(?:socratic|explanation)|\Z)"),
        ("socratic_hint", r"(?:socratic\s*hint|hint)[\*:\s]+(.+?)(?=\n\s*[\*#\-]*\s*(?:explanation)|\Z)"),
        ("explanation", r"(?:explanation)[\*:\s]+(.+?)$"),
    ]

    for field, pat in label_patterns:
        m = re.search(pat, clean_text, re.IGNORECASE | re.DOTALL)
        if m:
            val = m.group(1).strip().strip("*_#`")
            if val.lower() in ("none", "null", "n/a", ""):
                extracted[field] = None
            else:
                extracted[field] = val

    # Check for conceptual_correctness boolean
    correctness_m = re.search(r"conceptual\s*correctness[\*:\s]+(true|false|yes|no|correct|incorrect)", clean_text, re.IGNORECASE)
    if correctness_m:
        val_str = correctness_m.group(1).lower()
        extracted["conceptual_correctness"] = val_str in ("true", "yes", "correct")
    elif "conceptual_correctness" not in extracted:
        # Infer from answer_interpretation or reasoning if keywords indicate correctness
        lower_text = clean_text.lower()
        if "incorrect" in lower_text or "wrong" in lower_text or "misconception" in lower_text:
            extracted["conceptual_correctness"] = False
        else:
            extracted["conceptual_correctness"] = True

    if len(extracted) >= 2:
        # Provide defaults for any missing DeepSeek fields
        if "answer_interpretation" not in extracted:
            extracted["answer_interpretation"] = clean_text[:200]
        if "reasoning_analysis" not in extracted:
            extracted["reasoning_analysis"] = clean_text
        if "diagnostic_explanation" not in extracted:
            extracted["diagnostic_explanation"] = clean_text
        if "recommended_learning_intervention" not in extracted:
            extracted["recommended_learning_intervention"] = "Proceed to next practice problem" if extracted.get("conceptual_correctness") else "Review core concept"
        return extracted

    # Final safe fallback if output has text
    if len(clean_text) > 10:
        is_correct = "incorrect" not in clean_text.lower() and "wrong" not in clean_text.lower()
        return {
            "answer_interpretation": clean_text[:200],
            "reasoning_analysis": clean_text,
            "identified_misconception": None if is_correct else "Conceptual gap detected in explanation",
            "conceptual_correctness": is_correct,
            "recommended_learning_intervention": "Proceed" if is_correct else "Review concept",
            "diagnostic_explanation": clean_text,
            "suggested_follow_up_question": None,
            "friendly_feedback": clean_text[:300],
            "explanation": clean_text,
        }

    raise ValueError(f"Could not parse valid JSON from LLM output: {text[:200]}...")


class ModelOrchestrationService:
    """
    Coordinates local LLM providers (LM Studio & Ollama) through the GPUExecutionManager.
    Executes deep pedagogical reasoning and student-facing formatting in a strictly sequential pipeline.
    """

    def __init__(
        self,
        execution_manager: GPUExecutionManager,
        deepseek_provider: BaseLLMProvider,
        llama_provider: BaseLLMProvider,
    ):
        self.execution_manager = execution_manager
        self.deepseek = deepseek_provider
        self.llama = llama_provider

    async def run_deepseek_reasoning(self, req: DeepSeekReasoningInput) -> DeepSeekReasoningOutput:
        """
        Executes DeepSeek pedagogical diagnostic reasoning.
        """
        system_prompt = (
            "You are an expert AI pedagogical tutor evaluating a student's answer. "
            "Analyze the student's reasoning carefully. Identify any conceptual misconceptions, "
            "determine conceptual correctness, provide step-by-step diagnostic reasoning, "
            "recommend an appropriate learning intervention, and draft a calibrated follow-up question. "
            "You must return your output strictly in valid JSON matching this schema:\n"
            "{\n"
            '  "answer_interpretation": "string summary of student reasoning",\n'
            '  "reasoning_analysis": "detailed step-by-step diagnostic reasoning",\n'
            '  "identified_misconception": "string describing misconception or null",\n'
            '  "conceptual_correctness": true,\n'
            '  "recommended_learning_intervention": "actionable pedagogical next step",\n'
            '  "diagnostic_explanation": "explanation of the underlying concept",\n'
            '  "suggested_follow_up_question": "calibrated follow-up probe or null"\n'
            "}"
        )

        user_content = (
            f"Concept: {req.concept_name}\n"
            f"Concept Description: {req.concept_description or 'N/A'}\n"
            f"Question: {req.question_text}\n"
            f"Expected Answer: {req.expected_answer}\n"
            f"Evaluation Criteria: {req.evaluation_criteria or 'Standard conceptual accuracy'}\n"
            f"Prior Mastery: {req.prior_mastery if req.prior_mastery is not None else 'Unknown'}\n"
            f"Relevant Learner History: {req.relevant_history or 'None'}\n"
            f"Student Answer: {req.student_answer}\n\n"
            "Evaluate the answer and output ONLY valid JSON."
        )

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_content),
        ]
        opts = InferenceOptions(
            temperature=settings.LMSTUDIO_TEMPERATURE,
            max_tokens=settings.LMSTUDIO_MAX_TOKENS,
            context_length=settings.LMSTUDIO_CONTEXT_LENGTH,
        )

        response = await self.deepseek.generate_chat(messages=messages, options=opts)
        parsed_json = _extract_json_from_llm_response(response.content)
        if not parsed_json.get("recommended_learning_intervention"):
            parsed_json["recommended_learning_intervention"] = (
                "Proceed to advanced practice" if parsed_json.get("conceptual_correctness") else "Review core concept definition"
            )
        return DeepSeekReasoningOutput(**parsed_json)

    async def run_llama_formatting(self, req: LlamaFormatInput) -> LlamaFormatOutput:
        """
        Executes Llama student-facing response formatting and Socratic hinting.
        Does NOT alter BKT values; purely formats presentation.
        """
        system_prompt = (
            "You are a supportive, warm, and highly effective Socratic tutor. "
            "Using the provided pedagogical diagnosis, formulate a friendly, encouraging student response. "
            "If the answer was incorrect, provide a gentle Socratic hint without giving away the full answer. "
            "If correct, provide positive reinforcement and suggest the next question. "
            "Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "friendly_feedback": "encouraging feedback addressing the student directly",\n'
            '  "socratic_hint": "guiding hint or question or null",\n'
            '  "formatted_next_question": "formatted next question or probe or null",\n'
            '  "explanation": "clear, student-appropriate explanation",\n'
            '  "conceptual_correctness": true\n'
            "}"
        )

        user_content = (
            f"Student: {req.student_name}\n"
            f"Concept: {req.concept_name}\n"
            f"Original Question: {req.question_text}\n"
            f"Diagnostic Reasoning: {req.reasoning.reasoning_analysis}\n"
            f"Identified Misconception: {req.reasoning.identified_misconception or 'None'}\n"
            f"Conceptual Correctness: {req.reasoning.conceptual_correctness}\n"
            f"Recommended Intervention: {req.reasoning.recommended_learning_intervention}\n"
            f"Suggested Follow-Up Question: {req.reasoning.suggested_follow_up_question or 'None'}\n\n"
            "Format the response into structured JSON."
        )

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_content),
        ]
        opts = InferenceOptions(
            temperature=settings.OLLAMA_TEMPERATURE,
            max_tokens=settings.OLLAMA_MAX_TOKENS,
            context_length=settings.OLLAMA_CONTEXT_LENGTH,
            format_json=True,
        )

        response = await self.llama.generate_chat(messages=messages, options=opts)
        parsed_json = _extract_json_from_llm_response(response.content)
        # Ensure conceptual_correctness mirrors the validated reasoning
        if "conceptual_correctness" not in parsed_json:
            parsed_json["conceptual_correctness"] = req.reasoning.conceptual_correctness
        return LlamaFormatOutput(**parsed_json)

    async def process_learning_turn(self, turn_input: LearningTurnInput) -> LearningTurnOutput:
        """
        Coordinates the complete sequential learning turn through GPUExecutionManager:
        1. Acquire GPU lock
        2. Run DeepSeek reasoning
        3. Release DeepSeek resources
        4. Run Llama formatting
        5. Release Llama resources (or prewarm)
        6. Return validated output and metrics.
        """
        logger.info(
            f"Processing learning turn for concept='{turn_input.concept_name}', "
            f"question_id={turn_input.question_id}"
        )

        reasoning_input = DeepSeekReasoningInput(
            student_answer=turn_input.student_answer,
            question_text=turn_input.question_text,
            expected_answer=turn_input.expected_answer,
            evaluation_criteria=turn_input.evaluation_criteria,
            concept_name=turn_input.concept_name,
            prior_mastery=turn_input.prior_mastery,
        )

        async def reasoning_task():
            return await self.run_deepseek_reasoning(reasoning_input)

        async def formatting_task(reasoning_output: DeepSeekReasoningOutput):
            formatting_input = LlamaFormatInput(
                reasoning=reasoning_output,
                student_name=f"Student #{turn_input.student_id}" if turn_input.student_id else "Student",
                question_text=turn_input.question_text,
                concept_name=turn_input.concept_name,
            )
            return await self.run_llama_formatting(formatting_input)

        try:
            execution_res = await self.execution_manager.execute_turn(
                reasoning_task=reasoning_task,
                formatting_task=formatting_task,
                deepseek_context_length=settings.LMSTUDIO_CONTEXT_LENGTH,
                llama_context_length=settings.OLLAMA_CONTEXT_LENGTH,
            )

            metrics_data = execution_res.get("metrics", {})
            metrics = ExecutionTurnMetrics(**metrics_data)

            return LearningTurnOutput(
                success=True,
                reasoning=execution_res.get("reasoning_result"),
                formatted_response=execution_res.get("formatting_result"),
                metrics=metrics,
                error_message=None,
            )
        except Exception as e:
            logger.error(f"Error in process_learning_turn: {e}", exc_info=True)
            return LearningTurnOutput(
                success=False,
                reasoning=None,
                formatted_response=None,
                metrics=ExecutionTurnMetrics(),
                error_message=str(e),
            )
