from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_any_authenticated_user
from app.models.user import User
from app.schemas.assessment import (
    SessionCreate,
    SessionDetailResponse,
    ResponseSubmit,
    ResponseEvaluationResult,
    LearnerResponseHistoryItem
)
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/assessments", tags=["Assessment: Sessions & Evaluation"])


@router.post(
    "/sessions",
    response_model=SessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new practice or diagnostic session"
)
def start_session(
    session_in: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """
    Launch a diagnostic or adaptive practice session.
    Retrieves targeted practice questions tailored to the curriculum.
    """
    return AssessmentService.create_learning_session(
        db=db,
        user_id=current_user.id,
        session_in=session_in
    )


@router.post(
    "/submit",
    response_model=ResponseEvaluationResult,
    summary="Submit an answer for evaluation and BKT mastery update"
)
def submit_answer(
    submission: ResponseSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """
    Submit a student's answer.
    Evaluates correctness, saves response history with latency/confidence telemetry,
    and updates the concept mastery probability using Bayesian Knowledge Tracing (BKT).
    """
    return AssessmentService.evaluate_and_record_response(
        db=db,
        user_id=current_user.id,
        submit_in=submission
    )


@router.get(
    "/history",
    response_model=List[LearnerResponseHistoryItem],
    summary="Get recent response history for current learner"
)
def get_my_history(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Retrieve historical responses, accuracy scores, and feedback for the authenticated learner."""
    return AssessmentService.get_user_history(db=db, user_id=current_user.id, limit=limit)
