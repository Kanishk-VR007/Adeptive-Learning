import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.deps import require_role
from app.schemas.diagnostic import (
    DiagnosticStartRequest,
    DiagnosticSessionResponse,
    DiagnosticSubmissionRequest,
    DiagnosticResultResponse,
)
from app.services.diagnostic_service import DiagnosticService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostic", tags=["Diagnostic Assessment"])


@router.post("/start", response_model=DiagnosticSessionResponse, status_code=status.HTTP_201_CREATED)
def start_diagnostic_assessment(
    req: DiagnosticStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
):
    """
    Initializes a diagnostic assessment session covering prerequisite concepts for a subject.
    Returns questions without exposing solutions.
    """
    try:
        return DiagnosticService.start_diagnostic(
            db=db, student_id=current_user.id, subject_id=req.subject_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/submit", response_model=DiagnosticResultResponse, status_code=status.HTTP_200_OK)
def submit_diagnostic_answers(
    submission: DiagnosticSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
):
    """
    Evaluates diagnostic responses, updates BKT knowledge estimates with empirical evidence,
    detects prerequisite gaps, and returns a personalized initial learning path.
    """
    try:
        return DiagnosticService.submit_diagnostic(
            db=db, student_id=current_user.id, submission=submission
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
