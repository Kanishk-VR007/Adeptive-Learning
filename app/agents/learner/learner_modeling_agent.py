import logging
import uuid
from typing import Any, Dict
from sqlalchemy.orm import Session

from app.agents.state.learning_state import LearningState
from app.schemas.learner_mastery import EvidenceSubmissionRequest
from app.services.learner_model_service import LearnerModelService

logger = logging.getLogger(__name__)


class LearnerModelingAgent:
    """
    Agent 5: Learner Modeling Agent (Pure Python BKT Engine).
    Accepts validated answer evidence and executes the deterministic Bayesian Knowledge Tracing update.
    Never relies on an LLM for mastery calculations.
    Uses an idempotency key to prevent double-counting of evidence upon retries or graph recoveries.
    """

    @classmethod
    async def run(cls, state: LearningState, db: Session) -> Dict[str, Any]:
        trace = list(state.get("node_execution_trace", []))
        trace.append("update_bkt_mastery")

        student_id = state.get("student_id")
        concept_id = state.get("current_concept_id") or state.get("concept_id")
        question_id = state.get("question_id")
        eval_res = state.get("evaluation_result", {}) or {}
        is_uncertain = state.get("is_uncertain_evaluation", False)

        # 1. Protection: If answer could not be reliably evaluated, do not update mastery
        if is_uncertain or state.get("execution_status") == "error":
            logger.info("Skipping BKT update due to uncertain evaluation or error state.")
            return {
                "node_execution_trace": trace,
            }

        # 2. Extract verified correctness
        is_correct = bool(eval_res.get("is_correct", False))

        # 3. Formulate deterministic idempotency key for this learning turn
        run_id = state.get("run_id") or uuid.uuid4().hex
        evidence_id = state.get("evidence_id") or f"turn_{run_id}_{student_id}_{concept_id}_{question_id}"

        try:
            evidence_req = EvidenceSubmissionRequest(
                is_correct=is_correct,
                question_id=question_id,
                evidence_id=evidence_id,
            )

            # Record learning evidence via the deterministic BKT service
            res = LearnerModelService.record_learning_evidence(
                db=db,
                student_id=student_id,
                concept_id=concept_id,
                evidence_in=evidence_req,
            )

            logger.info(
                f"BKT updated for student {student_id}, concept {concept_id}: "
                f"previous={res.previous_mastery:.4f} -> updated={res.updated_mastery:.4f} (obs={is_correct})"
            )

            return {
                "evidence_id": evidence_id,
                "current_mastery": res.updated_mastery,
                "updated_mastery": res.updated_mastery,
                "posterior_mastery": res.posterior_mastery,
                "node_execution_trace": trace,
            }

        except Exception as e:
            logger.error(f"Error in LearnerModelingAgent: {e}", exc_info=True)
            return {
                "execution_status": "error",
                "error_code": "BKT_UPDATE_FAILED",
                "error_message": f"Learner modeling BKT update failed: {str(e)}",
                "node_execution_trace": trace,
            }
