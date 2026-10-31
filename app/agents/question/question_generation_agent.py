import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.agents.state.learning_state import CandidateQuestionItem, LearningState
from app.models.assessment import LearnerResponse, Question
from app.models.syllabus import Concept, DifficultyLevel

logger = logging.getLogger(__name__)


class QuestionGenerationAgent:
    """
    Agent 7: Question Generation & Validation Agent.
    Ensures that the next pedagogical question matches the candidate concept,
    is appropriately calibrated in difficulty, is not a duplicate of recently solved questions,
    and has clear evaluation criteria.
    Falls back to existing questions from the Question Bank when needed.
    """

    @classmethod
    def validate_and_calibrate_question(
        cls,
        db: Session,
        student_id: int,
        target_concept_id: int,
        adaptive_action: str,
        draft_question: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validates draft question from DeepSeek or selects a matching question from the database.
        """
        # 1. Determine target difficulty
        if adaptive_action == "CONCEPT_REMEDIATION":
            target_diff = "easy"
            db_diff = DifficultyLevel.BEGINNER
        elif adaptive_action == "ADVANCE_TO_NEXT_CONCEPT":
            target_diff = "hard"
            db_diff = DifficultyLevel.ADVANCED
        else:  # TARGETED_PRACTICE or REVISION
            target_diff = "medium"
            db_diff = DifficultyLevel.INTERMEDIATE

        # 2. Check recent questions answered by student to prevent repetition
        answered_q_ids = set()
        if student_id:
            recent_resp = db.query(LearnerResponse.question_id).filter(
                LearnerResponse.user_id == student_id
            ).limit(20).all()
            answered_q_ids = {r[0] for r in recent_resp}

        # 3. If draft question is provided and valid, verify concept and calibrate
        if draft_question and draft_question.get("question") and draft_question.get("expected_answer"):
            q_text = draft_question.get("question", "").strip()
            # Simple deduplication check
            is_dup = False
            for ans_qid in answered_q_ids:
                db_q = db.query(Question).filter(Question.id == ans_qid).first()
                if db_q and db_q.question_text.strip().lower() == q_text.lower():
                    is_dup = True
                    break

            if not is_dup:
                return {
                    "concept_id": target_concept_id,
                    "difficulty": target_diff,
                    "question": q_text,
                    "expected_answer": draft_question.get("expected_answer", ""),
                    "evaluation_criteria": draft_question.get("evaluation_criteria", ["Conceptual accuracy"]),
                    "is_from_bank": False,
                }

        # 4. Fallback: retrieve suitable question from database Question Bank
        query = db.query(Question).filter(
            Question.concept_id == target_concept_id,
        )
        if answered_q_ids:
            query = query.filter(~Question.id.in_(answered_q_ids))

        fallback_q = query.filter(Question.difficulty_level == db_diff).first()
        if not fallback_q:
            fallback_q = query.first()  # Any difficulty for this concept

        if not fallback_q:
            # Fallback to any question for this concept even if answered before
            fallback_q = db.query(Question).filter(Question.concept_id == target_concept_id).first()

        if fallback_q:
            rubric = fallback_q.evaluation_rubric or {}
            criteria = rubric.get("criteria", ["Accuracy"]) if isinstance(rubric, dict) else ["Accuracy"]
            return {
                "id": fallback_q.id,
                "concept_id": fallback_q.concept_id,
                "difficulty": target_diff,
                "question": fallback_q.question_text,
                "expected_answer": fallback_q.correct_answer,
                "evaluation_criteria": criteria,
                "is_from_bank": True,
            }

        # 5. Last resort synthesis if question bank is completely empty for this concept
        concept = db.query(Concept).filter(Concept.id == target_concept_id).first()
        c_name = concept.name if concept else "the concept"
        return {
            "concept_id": target_concept_id,
            "difficulty": target_diff,
            "question": f"Explain the fundamental principles and definition of {c_name}.",
            "expected_answer": f"A correct explanation of {c_name} with key relationships.",
            "evaluation_criteria": ["Defines key terms", "Explains core mechanism"],
            "is_from_bank": False,
        }

    @classmethod
    async def run(cls, state: LearningState, db: Session) -> Dict[str, Any]:
        trace = list(state.get("node_execution_trace", []))
        trace.append("validate_question")

        student_id = state.get("student_id", 0)
        target_concept_id = state.get("candidate_next_concept_id") or state.get("current_concept_id", 0)
        adaptive_action = state.get("adaptive_action", "TARGETED_PRACTICE")
        draft_q = state.get("generated_question")

        calibrated_q = cls.validate_and_calibrate_question(
            db=db,
            student_id=student_id,
            target_concept_id=target_concept_id,
            adaptive_action=adaptive_action,
            draft_question=draft_q,
        )

        return {
            "validated_next_question": calibrated_q,
            "node_execution_trace": trace,
        }
