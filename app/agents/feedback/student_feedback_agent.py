import json
import logging
from typing import Any, Dict, Optional
from pydantic import ValidationError

from app.agents.state.learning_state import LearningState, StudentFeedbackOutput
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.providers.base import LLMResponse
from app.ai.schemas import ChatMessage, InferenceOptions
from app.core.config import settings

logger = logging.getLogger(__name__)


class StudentFeedbackAgent:
    """
    Agent 8: Student Feedback Agent.
    Executes Llama 3.2 via GPUExecutionManager.execute_llama() to generate
    warm, encouraging feedback, Socratic hints, and clear next-step guidance.
    Enforces deterministic display_mastery from BKT engine and validated adaptive actions.
    """

    SYSTEM_PROMPT = """You are an expert, encouraging personal tutor for an adaptive exam-prep system.
Your role is to formulate warm, constructive pedagogical feedback and Socratic hints for a student.

Guidelines:
1. Always maintain a growth mindset, supportive tone, and clear explanations.
2. If the student made an error, acknowledge their effort and provide a Socratic hint that guides them toward the correct concept without simply giving away the complete final answer.
3. If they mastered the concept, celebrate their success and encourage them as they advance.
4. If clarification is needed, clearly and politely ask what part was confusing or ask them to show their reasoning steps.
5. Formulate your output strictly as a JSON object with the following schema:
{
  "feedback": "Encouraging explanation of the concept and evaluation",
  "socratic_hint": "Gentle guiding hint or question (or null if fully correct)",
  "next_question": "The next question or follow-up prompt to present to the student",
  "adaptive_action": "ACTION_NAME",
  "display_mastery": 0.50
}
"""

    @classmethod
    async def run(
        cls,
        state: LearningState,
        execution_manager: GPUExecutionManager,
    ) -> Dict[str, Any]:
        trace = list(state.get("node_execution_trace", []))
        trace.append("student_feedback")

        metrics_acc = dict(state.get("metrics", {}))
        student_name = state.get("student_name") or "Student"
        eval_result = state.get("evaluation_result", {}) or {}
        misc_analysis = state.get("misconception_analysis", {}) or {}
        adaptive_action = state.get("adaptive_action") or "TARGETED_PRACTICE"
        
        # Deterministic mastery from state (updated_mastery or current_mastery)
        deterministic_mastery = state.get("updated_mastery")
        if deterministic_mastery is None:
            deterministic_mastery = state.get("current_mastery", 0.20)
        deterministic_mastery = round(float(deterministic_mastery), 4)

        next_q_data = state.get("validated_next_question") or state.get("generated_question") or {}
        next_question_text = next_q_data.get("question") if isinstance(next_q_data, dict) else None

        # Build context for Llama
        user_prompt_data = {
            "student_name": student_name,
            "concept": state.get("current_concept_name") or f"Concept #{state.get('current_concept_id')}",
            "is_correct": eval_result.get("is_correct", False),
            "answer_type": eval_result.get("answer_type", "incorrect"),
            "reasoning_summary": eval_result.get("reasoning_summary", ""),
            "misconception_detected": misc_analysis.get("detected", False),
            "misconception_category": misc_analysis.get("category", "none"),
            "misconception_description": misc_analysis.get("description", ""),
            "adaptive_action": adaptive_action,
            "next_concept": state.get("candidate_next_concept_name") or f"Concept #{state.get('candidate_next_concept_id')}",
            "next_question_text": next_question_text,
            "deterministic_mastery": deterministic_mastery,
        }

        user_prompt = (
            f"Please generate the student feedback JSON for the following learning turn data:\n"
            f"{json.dumps(user_prompt_data, indent=2)}\n\n"
            f"Remember: Output ONLY valid JSON."
        )

        messages = [
            ChatMessage(role="system", content=cls.SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_prompt),
        ]
        opts = InferenceOptions(
            temperature=settings.OLLAMA_TEMPERATURE,
            max_tokens=settings.OLLAMA_MAX_TOKENS,
            context_length=settings.OLLAMA_CONTEXT_LENGTH,
            format_json=True,
        )

        async def formatting_task() -> LLMResponse:
            if hasattr(execution_manager.llama, "generate_chat"):
                return await execution_manager.llama.generate_chat(messages=messages, options=opts)
            elif hasattr(execution_manager.llama, "generate"):
                return await execution_manager.llama.generate(
                    prompt=user_prompt,
                    system_prompt=cls.SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=600,
                    format="json",
                )
            raise AttributeError("Llama provider has neither generate_chat nor generate method")

        try:
            gpu_res = await execution_manager.execute_llama(
                formatting_task=formatting_task,
                context_length=settings.OLLAMA_CONTEXT_LENGTH,
            )
            llm_response: LLMResponse = gpu_res.get("result")
            for k, v in gpu_res.get("metrics", {}).items():
                metrics_acc[k] = v

            raw_text = (llm_response.content or "").strip()
            # Clean possible markdown fences
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

            parsed_data = json.loads(raw_text)
            
            # Enforce deterministic integrity over model hallucination:
            parsed_data["adaptive_action"] = adaptive_action
            parsed_data["display_mastery"] = deterministic_mastery
            if next_question_text and not parsed_data.get("next_question"):
                parsed_data["next_question"] = next_question_text

            feedback_output = StudentFeedbackOutput(**parsed_data)
            feedback_dict = feedback_output.model_dump()

        except Exception as e:
            logger.warning(f"Llama feedback generation encountered error: {e}. Falling back to deterministic feedback template.")
            feedback_dict = cls._generate_fallback_feedback(
                eval_result=eval_result,
                adaptive_action=adaptive_action,
                next_question_text=next_question_text,
                display_mastery=deterministic_mastery,
                student_name=student_name,
            )

        return {
            "student_feedback": feedback_dict,
            "node_execution_trace": trace,
            "metrics": metrics_acc,
        }

    @classmethod
    def _generate_fallback_feedback(
        cls,
        eval_result: Dict[str, Any],
        adaptive_action: str,
        next_question_text: Optional[str],
        display_mastery: float,
        student_name: str,
    ) -> Dict[str, Any]:
        is_correct = eval_result.get("is_correct", False)
        reasoning = eval_result.get("reasoning_summary", "")

        if is_correct:
            fb = f"Excellent work, {student_name}! You demonstrated a solid grasp of this concept. {reasoning}"
            hint = None
        else:
            fb = f"Good effort, {student_name}. Let's look closer at where the reasoning can be sharpened. {reasoning}"
            hint = "Review the core definition and examine the relationship between the key variables."

        return {
            "feedback": fb,
            "socratic_hint": hint,
            "next_question": next_question_text or "Ready for the next practice question?",
            "adaptive_action": adaptive_action,
            "display_mastery": display_mastery,
        }
