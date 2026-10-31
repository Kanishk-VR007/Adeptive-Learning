import json
import logging
import time
from typing import Any, Dict, Optional
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from sqlalchemy.orm import Session

from app.agents import (
    AdaptiveActionType,
    AdaptiveLearningAgent,
    AnswerEvaluationAgent,
    ConceptSelectionAgent,
    LearningContextAgent,
    LearnerModelingAgent,
    QuestionGenerationAgent,
    StudentFeedbackAgent,
    LearningState,
)
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.service import get_gpu_execution_manager
from app.core.config import settings
from app.db.session import SessionLocal
from app.graph.conditional_routes import route_after_evaluation, route_after_adaptive
from app.models.assessment import LearnerResponse, Question, LearningSession

logger = logging.getLogger(__name__)


def _get_db(config: Optional[RunnableConfig]) -> Session:
    """Extracts DB session from config or returns a new session."""
    if config and "configurable" in config and "db" in config["configurable"]:
        return config["configurable"]["db"]
    return SessionLocal()


def _get_execution_manager(config: Optional[RunnableConfig]) -> GPUExecutionManager:
    """Extracts GPUExecutionManager from config or returns default singleton."""
    if config and "configurable" in config and "execution_manager" in config["configurable"]:
        return config["configurable"]["execution_manager"]
    return get_gpu_execution_manager()


# ==========================================
# GRAPH NODE DEFINITIONS
# ==========================================

async def validate_submission(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    trace = list(state.get("node_execution_trace", []))
    trace.append("validate_submission")

    student_id = state.get("student_id")
    question_id = state.get("question_id")
    student_answer = state.get("student_answer")

    if not student_id or not question_id or student_answer is None or str(student_answer).strip() == "":
        return {
            "execution_status": "error",
            "error_code": "VALIDATION_ERROR",
            "error_message": "student_id, question_id, and non-empty student_answer are required",
            "node_execution_trace": trace,
        }

    db = _get_db(config)
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        return {
            "execution_status": "error",
            "error_code": "QUESTION_NOT_FOUND",
            "error_message": f"Question with id #{question_id} does not exist",
            "node_execution_trace": trace,
        }

    return {
        "concept_id": q.concept_id,
        "current_concept_id": q.concept_id,
        "execution_status": "in_progress",
        "node_execution_trace": trace,
    }


async def load_learning_context(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    if state.get("error_code"):
        trace = list(state.get("node_execution_trace", []))
        trace.append("load_learning_context")
        return {"node_execution_trace": trace}

    db = _get_db(config)
    return await LearningContextAgent.run(state=state, db=db)


async def select_candidate_concept(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    if state.get("error_code"):
        trace = list(state.get("node_execution_trace", []))
        trace.append("select_candidate_concept")
        return {"node_execution_trace": trace}

    db = _get_db(config)
    return await ConceptSelectionAgent.run(state=state, db=db)


async def deepseek_evaluation(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    if state.get("error_code"):
        trace = list(state.get("node_execution_trace", []))
        trace.append("deepseek_evaluation")
        return {"node_execution_trace": trace}

    db = _get_db(config)
    exec_mgr = _get_execution_manager(config)
    return await AnswerEvaluationAgent.run(state=state, execution_manager=exec_mgr, db=db)


async def validate_evaluation_output(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    trace = list(state.get("node_execution_trace", []))
    trace.append("validate_evaluation_output")

    if state.get("error_code"):
        return {"node_execution_trace": trace}

    conf = state.get("evaluation_confidence", 1.0)
    eval_res = state.get("evaluation_result", {}) or {}
    is_uncertain = (
        state.get("is_uncertain_evaluation", False)
        or conf < settings.EVALUATION_CONFIDENCE_THRESHOLD
        or eval_res.get("answer_type") == "ambiguous"
    )

    return {
        "is_uncertain_evaluation": is_uncertain,
        "node_execution_trace": trace,
    }


async def request_clarification(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    trace = list(state.get("node_execution_trace", []))
    trace.append("request_clarification")

    return {
        "adaptive_action": AdaptiveActionType.CLARIFICATION_REQUIRED,
        "clarification_prompt": "Your explanation was a bit ambiguous or incomplete. Could you explain your reasoning step-by-step?",
        "adaptive_reasoning": "Confidence was below pedagogical threshold. Preserving current mastery and prompting for clarification.",
        "node_execution_trace": trace,
    }


async def update_bkt_mastery(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    if state.get("error_code"):
        trace = list(state.get("node_execution_trace", []))
        trace.append("update_bkt_mastery")
        return {"node_execution_trace": trace}

    db = _get_db(config)
    return await LearnerModelingAgent.run(state=state, db=db)


async def adaptive_decision(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    if state.get("error_code"):
        trace = list(state.get("node_execution_trace", []))
        trace.append("adaptive_decision")
        return {"node_execution_trace": trace}

    db = _get_db(config)
    return await AdaptiveLearningAgent.run(state=state, db=db)


async def remediation_node(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    trace = list(state.get("node_execution_trace", []))
    trace.append("remediation_node")
    return {"node_execution_trace": trace}


async def targeted_practice_node(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    trace = list(state.get("node_execution_trace", []))
    trace.append("targeted_practice_node")
    return {"node_execution_trace": trace}


async def advance_concept_node(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    trace = list(state.get("node_execution_trace", []))
    trace.append("advance_concept_node")
    return {"node_execution_trace": trace}


async def revision_node(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    trace = list(state.get("node_execution_trace", []))
    trace.append("revision_node")

    db = _get_db(config)
    student_id = state.get("student_id")
    concept_id = state.get("current_concept_id") or state.get("concept_id")

    res: Dict[str, Any] = {"node_execution_trace": trace}
    if student_id and concept_id:
        from app.services.review_state_service import ReviewStateService
        from app.services.fsrs_configuration_service import FSRSConfigurationService
        from app.services.fsrs_service import FSRSService

        review_state = ReviewStateService.get_review_state(db, student_id, concept_id)
        if review_state:
            scheduler = FSRSConfigurationService.get_scheduler_for_student(db, student_id)
            card = ReviewStateService.restore_card(review_state)
            r = FSRSService.get_retrievability(scheduler, card)
            res["fsrs_retrievability"] = r
            res["fsrs_next_due_utc"] = review_state.due_at_utc.isoformat()

    return res


async def validate_question(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    if state.get("error_code"):
        trace = list(state.get("node_execution_trace", []))
        trace.append("validate_question")
        return {"node_execution_trace": trace}

    db = _get_db(config)
    return await QuestionGenerationAgent.run(state=state, db=db)


async def student_feedback(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    if state.get("error_code"):
        trace = list(state.get("node_execution_trace", []))
        trace.append("student_feedback")
        return {"node_execution_trace": trace}

    exec_mgr = _get_execution_manager(config)
    return await StudentFeedbackAgent.run(state=state, execution_manager=exec_mgr)


async def persist_outcome(state: LearningState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    trace = list(state.get("node_execution_trace", []))
    trace.append("persist_outcome")

    if state.get("error_code"):
        return {
            "execution_status": "error",
            "node_execution_trace": trace,
        }

    db = _get_db(config)
    student_id = state.get("student_id")
    question_id = state.get("question_id")
    session_id = state.get("session_id")
    student_answer = state.get("student_answer", "")
    eval_result = state.get("evaluation_result", {}) or {}
    feedback = state.get("student_feedback", {}) or {}

    response_id = state.get("response_id")
    if not response_id and student_id and question_id:
        # Check if already persisted
        existing = db.query(LearnerResponse).filter(
            LearnerResponse.user_id == student_id,
            LearnerResponse.question_id == question_id,
            LearnerResponse.response_text == student_answer,
        ).order_by(LearnerResponse.id.desc()).first()

        valid_session_id = None
        if session_id:
            sess = db.query(LearningSession).filter(LearningSession.id == session_id).first()
            if sess:
                valid_session_id = sess.id

        if existing:
            response_id = existing.id
        else:
            try:
                new_resp = LearnerResponse(
                    session_id=valid_session_id,
                    user_id=student_id,
                    question_id=question_id,
                    response_text=str(student_answer),
                    is_correct=bool(eval_result.get("is_correct", False)),
                    confidence_score=float(state.get("evaluation_confidence", 1.0)),
                    ai_feedback=json.dumps(feedback) if feedback else None,
                )
                db.add(new_resp)
                db.commit()
                db.refresh(new_resp)
                response_id = new_resp.id
            except Exception as e:
                logger.warning(f"Failed to persist LearnerResponse: {e}")
                db.rollback()

    fsrs_due_iso = None
    fsrs_r = None

    # Handle FSRS update only when turn is explicitly SCHEDULED_REVISION
    if state.get("turn_type") == "SCHEDULED_REVISION" and state.get("review_rating"):
        try:
            from app.services.revision_service import RevisionService
            from app.schemas.fsrs_review import CompleteRevisionRequest

            cid = state.get("concept_id") or state.get("current_concept_id")
            rev_res = RevisionService.complete_revision_session(
                db=db,
                student_id=student_id,
                concept_id=cid,
                request=CompleteRevisionRequest(
                    question_id=question_id,
                    response_text=str(student_answer),
                    rating=int(state.get("review_rating")),
                    idempotency_key=state.get("idempotency_key") or f"turn_{state.get('run_id')}",
                    response_id=response_id,
                ),
            )
            fsrs_due_iso = rev_res.next_due_at_utc.isoformat()
            fsrs_r = rev_res.retrievability
        except Exception as e:
            logger.warning(f"Failed to update FSRS in scheduled revision turn: {e}")

    result_payload: Dict[str, Any] = {
        "response_id": response_id,
        "execution_status": "completed",
        "node_execution_trace": trace,
    }
    if fsrs_due_iso:
        result_payload["fsrs_next_due_utc"] = fsrs_due_iso
    if fsrs_r is not None:
        result_payload["fsrs_retrievability"] = fsrs_r

    return result_payload



def build_learning_graph() -> StateGraph:
    """
    Constructs the complete LangGraph StateGraph according to Phase 5 architecture.
    """
    builder = StateGraph(LearningState)

    # 1. Register all nodes
    builder.add_node("validate_submission", validate_submission)
    builder.add_node("load_learning_context", load_learning_context)
    builder.add_node("select_candidate_concept", select_candidate_concept)
    builder.add_node("deepseek_evaluation", deepseek_evaluation)
    builder.add_node("validate_evaluation_output", validate_evaluation_output)
    builder.add_node("request_clarification", request_clarification)
    builder.add_node("update_bkt_mastery", update_bkt_mastery)
    builder.add_node("adaptive_decision", adaptive_decision)
    builder.add_node("remediation_node", remediation_node)
    builder.add_node("targeted_practice_node", targeted_practice_node)
    builder.add_node("advance_concept_node", advance_concept_node)
    builder.add_node("revision_node", revision_node)
    builder.add_node("validate_question", validate_question)
    builder.add_node("student_feedback", student_feedback)
    builder.add_node("persist_outcome", persist_outcome)

    # 2. Sequential start edges
    builder.add_edge(START, "validate_submission")
    builder.add_edge("validate_submission", "load_learning_context")
    builder.add_edge("load_learning_context", "select_candidate_concept")
    builder.add_edge("select_candidate_concept", "deepseek_evaluation")
    builder.add_edge("deepseek_evaluation", "validate_evaluation_output")

    # 3. Conditional Edge 1: Evaluation certainty check
    builder.add_conditional_edges(
        "validate_evaluation_output",
        route_after_evaluation,
        {
            "request_clarification": "request_clarification",
            "update_bkt_mastery": "update_bkt_mastery",
        },
    )

    # Request clarification bypasses BKT and routes to student_feedback
    builder.add_edge("request_clarification", "student_feedback")

    # Validated evaluation proceeds to BKT and Adaptive decision
    builder.add_edge("update_bkt_mastery", "adaptive_decision")

    # 4. Conditional Edge 2: Adaptive action routes
    builder.add_conditional_edges(
        "adaptive_decision",
        route_after_adaptive,
        {
            "remediation_node": "remediation_node",
            "targeted_practice_node": "targeted_practice_node",
            "advance_concept_node": "advance_concept_node",
            "revision_node": "revision_node",
            "validate_question": "validate_question",
        },
    )

    # Converge action branches to validate_question
    builder.add_edge("remediation_node", "validate_question")
    builder.add_edge("targeted_practice_node", "validate_question")
    builder.add_edge("advance_concept_node", "validate_question")
    builder.add_edge("revision_node", "validate_question")

    # 5. Final sequential edges
    builder.add_edge("validate_question", "student_feedback")
    builder.add_edge("student_feedback", "persist_outcome")
    builder.add_edge("persist_outcome", END)

    return builder
