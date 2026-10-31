import logging
import uuid
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agents.state.learning_state import LearningState
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.service import get_gpu_execution_manager
from app.graph.learning_graph import execute_learning_turn, get_compiled_graph
from app.models.assessment import LearningSession, LearnerResponse, Question
from app.models.user import User, UserRole
from app.schemas.learning import (
    GraphStatusResponse,
    LearningTurnRequest,
    LearningTurnResponse,
    LearningTurnStatusResponse,
    SessionHistoryResponse,
    SessionHistoryTurnItem,
)

logger = logging.getLogger(__name__)

# In-memory execution store for runs: run_id -> (student_id, LearningState)
_active_runs: Dict[str, Dict[str, Any]] = {}


class LearningOrchestrationService:
    """
    Coordinates authenticated student learning turns with LangGraph,
    authorizes access to sessions and questions, ensures state isolation,
    and formats responses.
    """

    @classmethod
    async def execute_turn(
        cls,
        db: Session,
        current_user: User,
        payload: LearningTurnRequest,
        execution_manager: Optional[GPUExecutionManager] = None,
    ) -> LearningTurnResponse:
        # 1. Authorize & validate question
        question = db.query(Question).filter(Question.id == payload.question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question #{payload.question_id} not found",
            )

        # 2. Authorize session if provided
        if payload.session_id:
            session = db.query(LearningSession).filter(LearningSession.id == payload.session_id).first()
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Learning session #{payload.session_id} not found",
                )
            if session.user_id != current_user.id and current_user.role != UserRole.TEACHER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized: You do not own this learning session",
                )

        # 3. Formulate initial state
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        initial_state: LearningState = {
            "run_id": run_id,
            "session_id": payload.session_id,
            "student_id": current_user.id,
            "student_name": current_user.full_name or f"Student #{current_user.id}",
            "question_id": question.id,
            "concept_id": question.concept_id,
            "current_concept_id": question.concept_id,
            "student_answer": payload.student_answer,
            "turn_type": payload.turn_type or "NORMAL_PRACTICE",
            "review_rating": payload.review_rating,
            "idempotency_key": payload.idempotency_key,
            "node_execution_trace": [],
            "metrics": {},
            "execution_status": "in_progress",
        }


        # 4. Invoke LangGraph
        exec_mgr = execution_manager or get_gpu_execution_manager()
        final_state = await execute_learning_turn(
            initial_state=initial_state,
            db=db,
            execution_manager=exec_mgr,
        )

        # Store in run registry
        _active_runs[run_id] = {
            "student_id": current_user.id,
            "state": final_state,
        }

        return cls._state_to_response(final_state)

    @classmethod
    def get_run_status(cls, run_id: str, current_user: User) -> LearningTurnStatusResponse:
        record = _active_runs.get(run_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learning turn run #{run_id} not found",
            )

        if record["student_id"] != current_user.id and current_user.role != UserRole.TEACHER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: You do not have permission to view this run",
            )

        state = record["state"]
        return LearningTurnStatusResponse(
            run_id=run_id,
            execution_status=state.get("execution_status", "completed"),
            node_execution_trace=state.get("node_execution_trace", []),
            error_code=state.get("error_code"),
            error_message=state.get("error_message"),
        )

    @classmethod
    def get_run_result(cls, run_id: str, current_user: User) -> LearningTurnResponse:
        record = _active_runs.get(run_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learning turn run #{run_id} not found",
            )

        if record["student_id"] != current_user.id and current_user.role != UserRole.TEACHER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: You do not have permission to view this run result",
            )

        return cls._state_to_response(record["state"])

    @classmethod
    def get_session_history(cls, session_id: int, current_user: User, db: Session) -> SessionHistoryResponse:
        sess = db.query(LearningSession).filter(LearningSession.id == session_id).first()
        if not sess:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session #{session_id} not found",
            )

        if sess.user_id != current_user.id and current_user.role != UserRole.TEACHER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: Cannot view another student's learning session",
            )

        responses = db.query(LearnerResponse).filter(
            LearnerResponse.session_id == session_id
        ).order_by(LearnerResponse.submitted_at.asc()).all()

        items = [
            SessionHistoryTurnItem(
                id=r.id,
                question_id=r.question_id,
                response_text=r.response_text,
                is_correct=r.is_correct,
                confidence_score=r.confidence_score,
                time_spent_ms=r.time_spent_ms,
                ai_feedback=r.ai_feedback,
                submitted_at=r.submitted_at.isoformat() if r.submitted_at else "",
            )
            for r in responses
        ]

        return SessionHistoryResponse(
            session_id=sess.id,
            student_id=sess.user_id,
            subject_id=sess.subject_id,
            session_type=str(sess.session_type.value if hasattr(sess.session_type, "value") else sess.session_type),
            started_at=sess.started_at.isoformat() if sess.started_at else "",
            completed_at=sess.completed_at.isoformat() if sess.completed_at else None,
            responses=items,
        )

    @classmethod
    def get_graph_status(cls, execution_manager: Optional[GPUExecutionManager] = None) -> GraphStatusResponse:
        graph = get_compiled_graph()
        exec_mgr = execution_manager or get_gpu_execution_manager()
        gpu_status = exec_mgr.get_status()

        return GraphStatusResponse(
            status="healthy",
            compiled_nodes=list(graph.nodes.keys()),
            checkpointer_type="MemorySaver/SqliteSaver",
            gpu_manager_state=gpu_status.state,
            active_model=gpu_status.active_model,
            gpu_monitoring_enabled=gpu_status.monitoring_enabled,
        )

    @classmethod
    def _state_to_response(cls, state: LearningState) -> LearningTurnResponse:
        return LearningTurnResponse(
            run_id=state.get("run_id", ""),
            execution_status=state.get("execution_status", "completed"),
            student_id=state.get("student_id", 0),
            question_id=state.get("question_id", 0),
            current_concept_id=state.get("current_concept_id") or state.get("concept_id", 0),
            candidate_next_concept_id=state.get("candidate_next_concept_id"),
            current_mastery=state.get("current_mastery", 0.20) or 0.20,
            updated_mastery=state.get("updated_mastery"),
            evaluation_result=state.get("evaluation_result"),
            misconception_analysis=state.get("misconception_analysis"),
            adaptive_action=state.get("adaptive_action"),
            adaptive_reasoning=state.get("adaptive_reasoning"),
            student_feedback=state.get("student_feedback"),
            node_execution_trace=state.get("node_execution_trace", []),
            metrics=state.get("metrics", {}),
            turn_type=state.get("turn_type"),
            review_rating=state.get("review_rating"),
            fsrs_next_due_utc=state.get("fsrs_next_due_utc"),
            fsrs_retrievability=state.get("fsrs_retrievability"),
            error_code=state.get("error_code"),
            error_message=state.get("error_message"),
        )

