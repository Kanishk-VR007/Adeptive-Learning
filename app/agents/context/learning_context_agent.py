import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.agents.state.learning_state import LearningState
from app.models.assessment import Question
from app.models.concept_graph import ConceptPrerequisite
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.syllabus import Concept
from app.models.user import User

logger = logging.getLogger(__name__)


class LearningContextAgent:
    """
    Agent 1: Learning Context Agent (Pure Python).
    Retrieves and prepares isolated pedagogical context for the authenticated student.
    Only loads relevant recent history to prevent memory/context explosion.
    """

    @classmethod
    async def run(cls, state: LearningState, db: Session) -> Dict[str, Any]:
        trace = list(state.get("node_execution_trace", []))
        trace.append("load_learning_context")

        student_id = state.get("student_id")
        question_id = state.get("question_id")

        if not student_id:
            return {
                "execution_status": "error",
                "error_code": "UNAUTHORIZED_STUDENT",
                "error_message": "Missing authenticated student identity.",
                "node_execution_trace": trace,
            }

        try:
            # 1. Verify student exists
            student = db.query(User).filter(User.id == student_id).first()
            if not student:
                return {
                    "execution_status": "error",
                    "error_code": "STUDENT_NOT_FOUND",
                    "error_message": f"Student ID {student_id} not found.",
                    "node_execution_trace": trace,
                }

            # 2. Retrieve question
            question = db.query(Question).filter(Question.id == question_id).first()
            if not question:
                return {
                    "execution_status": "error",
                    "error_code": "QUESTION_NOT_FOUND",
                    "error_message": f"Question ID {question_id} not found.",
                    "node_execution_trace": trace,
                }

            concept_id = question.concept_id
            concept = db.query(Concept).filter(Concept.id == concept_id).first()
            if not concept:
                return {
                    "execution_status": "error",
                    "error_code": "CONCEPT_NOT_FOUND",
                    "error_message": f"Concept ID {concept_id} not found.",
                    "node_execution_trace": trace,
                }

            # 3. Retrieve prerequisites
            prereq_edges = db.query(ConceptPrerequisite.prerequisite_id).filter(
                ConceptPrerequisite.concept_id == concept_id
            ).all()
            prereq_ids = [p_id for (p_id,) in prereq_edges]
            prereq_concepts = db.query(Concept).filter(Concept.id.in_(prereq_ids)).all() if prereq_ids else []
            prereqs_info = [{"id": c.id, "name": c.name} for c in prereq_concepts]

            # 4. Retrieve current BKT mastery
            mastery_rec = db.query(LearnerMastery).filter(
                LearnerMastery.student_id == student_id,
                LearnerMastery.concept_id == concept_id
            ).first()
            current_mastery = mastery_rec.current_mastery if mastery_rec else 0.20

            # 5. Retrieve recent isolated history (last 5 records for this student and concept/subject)
            recent_history_records = (
                db.query(LearningHistory)
                .filter(
                    LearningHistory.student_id == student_id,
                    LearningHistory.concept_id == concept_id
                )
                .order_by(LearningHistory.timestamp.desc())
                .limit(5)
                .all()
            )

            history_summary = [
                {
                    "is_correct": h.is_correct,
                    "updated_mastery": round(h.updated_mastery, 4),
                    "timestamp": h.timestamp.isoformat() if h.timestamp else None
                }
                for h in recent_history_records
            ]

            context_data = {
                "question_text": question.question_text,
                "question_type": question.question_type.value if hasattr(question.question_type, "value") else str(question.question_type),
                "expected_answer": question.correct_answer,
                "evaluation_criteria": question.evaluation_rubric or {},
                "concept_name": concept.name,
                "concept_description": concept.description or "",
                "difficulty_level": question.difficulty_level.value if hasattr(question.difficulty_level, "value") else str(question.difficulty_level),
                "prerequisites": prereqs_info,
                "recent_history": history_summary,
                "recent_misconceptions": [],
                "prior_mastery": round(current_mastery, 4),
            }

            return {
                "student_name": student.full_name or f"Student #{student.id}",
                "current_concept_id": concept_id,
                "current_concept_name": concept.name,
                "current_mastery": current_mastery,
                "relevant_learning_context": context_data,
                "node_execution_trace": trace,
            }

        except Exception as e:
            logger.error(f"Error loading learning context: {e}", exc_info=True)
            return {
                "execution_status": "error",
                "error_code": "DB_CONTEXT_ERROR",
                "error_message": f"Database error during context loading: {str(e)}",
                "node_execution_trace": trace,
            }
