import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.fsrs_review import ConceptReviewState, ReviewHistory
from app.models.assessment import LearningSession, LearnerResponse
from app.models.teacher_class import ClassEnrollment
from app.core.security import verify_password, get_password_hash
from app.api.deps import get_current_user
from app.schemas.user import UserResponse, UserUpdate, PasswordChangeRequest, AccountDeletionRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users & Account"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Returns profile information for the authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    req: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates user profile information (e.g., full name)."""
    if req.full_name is not None:
        current_user.full_name = req.full_name.strip()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
def change_password(
    req: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Securely updates password after verifying current credentials."""
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password.",
        )
    current_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    logger.info(f"Password updated successfully for user {current_user.id}")
    return {"message": "Password updated successfully."}


@router.get("/me/export", status_code=status.HTTP_200_OK)
def export_user_learning_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Exports all persisted learning records, mastery estimates, and revision states
    for the authenticated student in compliance with data portability requirements.
    """
    masteries = (
        db.query(LearnerMastery)
        .filter(LearnerMastery.student_id == current_user.id)
        .all()
    )
    mastery_data = [
        {
            "concept_id": m.concept_id,
            "concept_name": m.concept.name if m.concept else None,
            "p_know": round(m.current_mastery, 4),
            "is_mastered": m.is_mastered,
            "attempts": m.total_attempts,
            "correct_attempts": m.correct_attempts,
            "last_practiced_at": m.last_attempt_at.isoformat() if m.last_attempt_at else None,
        }
        for m in masteries
    ]

    reviews = (
        db.query(ConceptReviewState)
        .filter(ConceptReviewState.student_id == current_user.id)
        .all()
    )
    review_data = [
        {
            "concept_id": r.concept_id,
            "concept_name": r.concept.name if r.concept else None,
            "stability": round(r.stability, 4),
            "difficulty": round(r.difficulty, 4),
            "reps": r.total_reviews,
            "state": str(r.state),
            "due_date": r.due_at_utc.isoformat() if r.due_at_utc else None,
        }
        for r in reviews
    ]

    history_records = (
        db.query(LearningHistory)
        .filter(LearningHistory.student_id == current_user.id)
        .order_by(LearningHistory.created_at.desc())
        .limit(100)
        .all()
    )
    history_data = [
        {
            "concept_id": h.concept_id,
            "is_correct": h.is_correct,
            "p_know_before": round(h.p_know_before, 4),
            "p_know_after": round(h.p_know_after, 4),
            "timestamp": h.created_at.isoformat(),
        }
        for h in history_records
    ]

    return {
        "user_profile": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            "created_at": current_user.created_at.isoformat(),
        },
        "mastery_records": mastery_data,
        "revision_cards": review_data,
        "recent_learning_history": history_data,
    }


@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_or_deactivate_account(
    req: AccountDeletionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deactivates or permanently deletes user account upon password confirmation.
    Cascades associated records safely when permanent=True, or soft deactivates.
    """
    if not verify_password(req.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password. Account deletion aborted.",
        )

    if req.permanent:
        # Cascade delete related data
        user_id = current_user.id
        logger.warning(f"Permanently deleting user account id={user_id} ({current_user.email})")

        db.query(LearnerResponse).filter(LearnerResponse.user_id == user_id).delete()
        db.query(LearningSession).filter(LearningSession.user_id == user_id).delete()
        db.query(LearningHistory).filter(LearningHistory.student_id == user_id).delete()
        db.query(LearnerMastery).filter(LearnerMastery.student_id == user_id).delete()
        db.query(ReviewHistory).filter(ReviewHistory.student_id == user_id).delete()
        db.query(ConceptReviewState).filter(ConceptReviewState.student_id == user_id).delete()
        db.query(ClassEnrollment).filter(ClassEnrollment.student_id == user_id).delete()

        db.delete(current_user)
        db.commit()
        return {"message": "Account and all associated learning records permanently deleted."}
    else:
        current_user.is_active = False
        db.commit()
        logger.info(f"Soft deactivated user account id={current_user.id}")
        return {"message": "Account has been deactivated. Contact support to reactivate."}
