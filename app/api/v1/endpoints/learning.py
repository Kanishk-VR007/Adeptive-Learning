import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_any_authenticated_user
from app.models.user import User
from app.schemas.learning import (
    GraphStatusResponse,
    LearningTurnRequest,
    LearningTurnResponse,
    LearningTurnStatusResponse,
    SessionHistoryResponse,
)
from app.services.learning_orchestration_service import LearningOrchestrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning", tags=["Agentic AI Tutor (LangGraph)"])


@router.post(
    "/turns",
    response_model=LearningTurnResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit student response and execute adaptive learning turn",
)
async def submit_learning_turn(
    payload: LearningTurnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Submits a student's answer for evaluation, executes the sequential LangGraph pipeline:
    1. Learning Context retrieval
    2. Concept Selection
    3. DeepSeek reasoning (Evaluation, Misconception analysis, Question drafting)
    4. Deterministic BKT mastery update
    5. Adaptive pedagogical decision
    6. Question calibration/validation
    7. Llama student-facing feedback generation
    8. Database persistence
    """
    return await LearningOrchestrationService.execute_turn(
        db=db,
        current_user=current_user,
        payload=payload,
    )


@router.get(
    "/turns/{run_id}",
    response_model=LearningTurnStatusResponse,
    summary="Retrieve execution status of a learning turn",
)
def get_learning_turn_status(
    run_id: str,
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Returns the current execution status, execution trace, and any errors for an authorized run.
    """
    return LearningOrchestrationService.get_run_status(
        run_id=run_id,
        current_user=current_user,
    )


@router.get(
    "/turns/{run_id}/result",
    response_model=LearningTurnResponse,
    summary="Retrieve validated result of a learning turn",
)
def get_learning_turn_result(
    run_id: str,
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Returns the complete validated result of a learning turn, ensuring cross-student isolation.
    """
    return LearningOrchestrationService.get_run_result(
        run_id=run_id,
        current_user=current_user,
    )


@router.get(
    "/sessions/{session_id}/history",
    response_model=SessionHistoryResponse,
    summary="Retrieve authorized learning session history",
)
def get_session_history(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Returns the complete question response history and feedback for a given learning session.
    Only the session owner or instructors/admins may view.
    """
    return LearningOrchestrationService.get_session_history(
        session_id=session_id,
        current_user=current_user,
        db=db,
    )


@router.get(
    "/graph/status",
    response_model=GraphStatusResponse,
    summary="Retrieve LangGraph and GPU execution status",
)
def get_graph_health_status(
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Provides an authorized health and architecture status endpoint for LangGraph nodes,
    checkpointer type, and active GPU state machine.
    """
    return LearningOrchestrationService.get_graph_status()
