import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_any_authenticated_user
from app.models.user import User, UserRole
from app.schemas.fsrs_review import (
    CompleteRevisionRequest,
    CompleteRevisionResponse,
    ConceptReviewStateResponse,
    ReviewHistoryItemResponse,
    ReviewPreferencesResponse,
    ReviewPreferencesUpdate,
    RevisionQueueResponse,
    RevisionStatusEnum,
    RevisionSummaryResponse,
    StartRevisionResponse,
)
from app.services.review_history_service import ReviewHistoryService
from app.services.review_rating_service import ReviewRatingService
from app.services.revision_queue_service import RevisionQueueService
from app.services.revision_service import RevisionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/revisions", tags=["FSRS Spaced Repetition & Revision Intelligence"])


@router.get(
    "/summary",
    response_model=RevisionSummaryResponse,
    summary="Get revision summary counts for the authenticated student",
)
def get_revision_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Returns counts of concepts due today, overdue, upcoming, new, and total reviews.
    Calculates 'Due Today' strictly within the student's local calendar day timezone.
    """
    return RevisionQueueService.get_summary(db=db, student_id=current_user.id)


@router.get(
    "/queue",
    response_model=RevisionQueueResponse,
    summary="Get personalized priority-ordered revision queue",
)
def get_revision_queue(
    status: Optional[RevisionStatusEnum] = Query(None, description="Filter by status (NEW, DUE_TODAY, OVERDUE, UPCOMING, REVIEWED)"),
    subject_id: Optional[int] = Query(None, description="Filter by subject ID"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Returns the student's revision queue ordered deterministically by priority score.
    Enforces student daily display limits without modifying FSRS due timestamps.
    """
    return RevisionQueueService.get_revision_queue(
        db=db,
        student_id=current_user.id,
        status_filter=status,
        subject_id_filter=subject_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/preferences",
    response_model=ReviewPreferencesResponse,
    summary="Retrieve student review preferences",
)
def get_review_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """Retrieves target retention rate, IANA timezone, and pacing limits."""
    pref = RevisionService.get_or_create_preferences(db=db, student_id=current_user.id)
    return ReviewPreferencesResponse.model_validate(pref)


@router.patch(
    "/preferences",
    response_model=ReviewPreferencesResponse,
    summary="Update student review preferences",
)
def update_review_preferences(
    payload: ReviewPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """Updates allowed student preferences (retention 0.70-0.99, valid IANA timezone, daily limits)."""
    pref = RevisionService.update_preferences(db=db, student_id=current_user.id, obj_in=payload)
    return ReviewPreferencesResponse.model_validate(pref)


@router.get(
    "/history",
    response_model=List[ReviewHistoryItemResponse],
    summary="Retrieve review history for the authenticated student",
)
def get_review_history(
    concept_id: Optional[int] = Query(None, description="Optional concept ID filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """Returns immutable review audit history for the authenticated student."""
    records = ReviewHistoryService.get_student_history(
        db=db,
        student_id=current_user.id,
        concept_id=concept_id,
        limit=limit,
        offset=offset,
    )
    results: List[ReviewHistoryItemResponse] = []
    for r in records:
        concept_name = r.concept.name if r.concept else None
        item = ReviewHistoryItemResponse(
            id=r.id,
            concept_id=r.concept_id,
            concept_name=concept_name,
            rating=r.rating,
            rating_name=ReviewRatingService.get_rating_name(r.rating),
            answer_correctness=r.answer_correctness,
            previous_due_at_utc=r.previous_due_at_utc,
            next_due_at_utc=r.next_due_at_utc,
            previous_stability=r.previous_stability,
            updated_stability=r.updated_stability,
            previous_difficulty=r.previous_difficulty,
            updated_difficulty=r.updated_difficulty,
            retrievability_before=r.retrievability_before,
            review_timestamp_utc=r.review_timestamp_utc,
            idempotency_key=r.idempotency_key,
        )
        results.append(item)
    return results


@router.get(
    "/{concept_id}/state",
    response_model=ConceptReviewStateResponse,
    summary="Get FSRS memory state for a concept",
)
def get_concept_review_state(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Returns the student's FSRS Card state (stability, difficulty, retrievability,
    due date in UTC and local timezone, review count, lapses).
    """
    return RevisionService.get_concept_review_state(
        db=db,
        student_id=current_user.id,
        concept_id=concept_id,
    )


@router.post(
    "/{concept_id}/start",
    response_model=StartRevisionResponse,
    summary="Start an authorized revision session for a concept",
)
def start_revision_session(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Starts an authorized spaced repetition session:
    Verifies concept eligibility, provisions a retrieval question, and initializes state.
    """
    return RevisionService.start_revision_session(
        db=db,
        student_id=current_user.id,
        concept_id=concept_id,
    )


@router.post(
    "/{concept_id}/complete",
    response_model=CompleteRevisionResponse,
    summary="Complete a scheduled review with student answer and recall rating",
)
def complete_revision_session(
    concept_id: int,
    payload: CompleteRevisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user),
):
    """
    Completes a scheduled revision session:
    - Verifies answer correctness.
    - Validates self-reported recall rating against correctness policy.
    - Updates BKT knowledge mastery independently.
    - Updates official FSRS memory state (stability, difficulty, interval).
    - Preserves atomic transaction and idempotency.
    """
    return RevisionService.complete_revision_session(
        db=db,
        student_id=current_user.id,
        concept_id=concept_id,
        request=payload,
    )
