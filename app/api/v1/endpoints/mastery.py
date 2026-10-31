from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_any_authenticated_user, require_teacher
from app.models.user import User
from app.schemas.learner_mastery import SubjectMasterySummary
from app.services.mastery_service import MasteryService

router = APIRouter(prefix="/mastery", tags=["Learner Mastery (BKT)"])


@router.get(
    "/me/subject/{subject_id}",
    response_model=SubjectMasterySummary,
    summary="Get current student's concept mastery breakdown for a subject"
)
def get_my_subject_mastery(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """
    Retrieve personalized concept mastery probabilities, counts of mastered concepts,
    and progress status across the specified subject curriculum.
    """
    return MasteryService.get_user_subject_mastery(
        db=db,
        user_id=current_user.id,
        subject_id=subject_id
    )


@router.get(
    "/user/{user_id}/subject/{subject_id}",
    response_model=SubjectMasterySummary,
    summary="Get specific student's mastery report (Teacher only)"
)
def get_student_subject_mastery(
    user_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """
    Retrieve detailed concept mastery diagnostics for a specific student.
    Restricted to teachers.
    """
    return MasteryService.get_user_subject_mastery(
        db=db,
        user_id=user_id,
        subject_id=subject_id
    )
