from datetime import datetime, timezone
import zoneinfo
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from fsrs import Card, Rating, ReviewLog

from app.models.fsrs_review import ConceptReviewState, ReviewPreferences
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.syllabus import Concept
from app.services.fsrs_service import FSRSService


class ReviewStateService:
    """
    Manages the lifecycle, enrollment, restoration, and persistence of
    concept-level FSRS memory cards for each student-concept pair.
    """

    @classmethod
    def get_review_state(
        cls,
        db: Session,
        student_id: int,
        concept_id: int,
    ) -> Optional[ConceptReviewState]:
        """Retrieves existing concept review state for a student."""
        return db.query(ConceptReviewState).filter(
            ConceptReviewState.student_id == student_id,
            ConceptReviewState.concept_id == concept_id,
        ).first()

    @classmethod
    def restore_card(cls, state: ConceptReviewState) -> Card:
        """
        Restores an official FSRS Card instance from stored JSON / dict payload.
        Ensures complete official state fidelity without manual approximations.
        """
        card_dict = state.fsrs_card_json
        if isinstance(card_dict, str):
            return FSRSService.card_from_json(card_dict)
        return FSRSService.card_from_dict(card_dict)

    @classmethod
    def is_concept_eligible_for_enrollment(
        cls,
        db: Session,
        student_id: int,
        concept_id: int,
    ) -> Tuple[bool, str]:
        """
        Validates enrollment criteria:
        1. Concept must exist.
        2. Student must not already have an active card for this concept.
        3. Valid learner-model evidence or mastery record exists (meaningful activity completed).
        """
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            return False, f"Concept with ID {concept_id} not found."

        existing_state = cls.get_review_state(db, student_id, concept_id)
        if existing_state:
            return False, f"Concept '{concept.name}' is already enrolled in spaced repetition."

        # Check evidence: does LearnerMastery or LearningHistory exist?
        has_mastery = db.query(LearnerMastery).filter(
            LearnerMastery.student_id == student_id,
            LearnerMastery.concept_id == concept_id,
        ).first()

        has_history = db.query(LearningHistory).filter(
            LearningHistory.student_id == student_id,
            LearningHistory.concept_id == concept_id,
        ).first()

        if not has_mastery and not has_history:
            return False, "Concept requires prior learning activity before spaced repetition enrollment."

        return True, "Concept is eligible for spaced repetition enrollment."

    @classmethod
    def check_daily_enrollment_limit(
        cls,
        db: Session,
        student_id: int,
    ) -> Tuple[bool, int, int]:
        """
        Verifies if student has exceeded their daily new concept enrollment limit
        according to their local timezone calendar date.
        Returns (is_under_limit, enrolled_today_count, daily_limit).
        """
        pref = db.query(ReviewPreferences).filter(
            ReviewPreferences.student_id == student_id
        ).first()

        limit = pref.daily_new_concept_limit if pref else 5
        tz_name = pref.timezone_name if pref else "UTC"

        try:
            tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        now_local = datetime.now(timezone.utc).astimezone(tz)
        start_of_today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_today_utc = start_of_today_local.astimezone(timezone.utc)

        enrolled_today_count = db.query(func.count(ConceptReviewState.id)).filter(
            ConceptReviewState.student_id == student_id,
            ConceptReviewState.enrolled_at_utc >= start_of_today_utc,
        ).scalar() or 0

        return enrolled_today_count < limit, enrolled_today_count, limit

    @classmethod
    def enroll_concept(
        cls,
        db: Session,
        student_id: int,
        concept_id: int,
        ignore_daily_limit: bool = False,
    ) -> ConceptReviewState:
        """
        Enrolls a concept into spaced repetition for a student.
        Initializes an official FSRS Card and persists the record.
        """
        # 1. Check existing state
        existing_state = cls.get_review_state(db, student_id, concept_id)
        if existing_state:
            return existing_state

        # 2. Check concept existence
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID {concept_id} does not exist.",
            )

        # 3. Check daily limit
        if not ignore_daily_limit:
            under_limit, current_count, limit = cls.check_daily_enrollment_limit(db, student_id)
            if not under_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Daily new concept enrollment limit reached ({current_count}/{limit}).",
                )

        now_utc = datetime.now(timezone.utc)
        card = FSRSService.create_new_card()

        state_rec = ConceptReviewState(
            student_id=student_id,
            concept_id=concept_id,
            fsrs_card_json=FSRSService.card_to_dict(card),
            fsrs_library_version="6.3.2",
            due_at_utc=card.due,
            state=card.state.value,
            stability=card.stability if card.stability is not None else 0.0,
            difficulty=card.difficulty if card.difficulty is not None else 0.0,
            last_review_at_utc=None,
            total_reviews=0,
            lapses=0,
            enrolled_at_utc=now_utc,
            updated_at_utc=now_utc,
        )

        db.add(state_rec)
        db.commit()
        db.refresh(state_rec)
        return state_rec

    @classmethod
    def update_card_state(
        cls,
        db: Session,
        review_state: ConceptReviewState,
        updated_card: Card,
        rating: int,
        log: ReviewLog,
    ) -> ConceptReviewState:
        """
        Applies review results to the ConceptReviewState record.
        Persists updated stability, difficulty, state, due date, review count, and lapses.
        """
        now_utc = datetime.now(timezone.utc)

        review_state.fsrs_card_json = FSRSService.card_to_dict(updated_card)
        review_state.due_at_utc = updated_card.due
        review_state.state = updated_card.state.value
        review_state.stability = float(updated_card.stability) if updated_card.stability is not None else 0.0
        review_state.difficulty = float(updated_card.difficulty) if updated_card.difficulty is not None else 0.0
        review_state.last_review_at_utc = log.review_datetime if log.review_datetime is not None else now_utc
        review_state.total_reviews += 1

        if rating == Rating.Again.value:
            review_state.lapses += 1

        review_state.updated_at_utc = now_utc
        db.flush()
        return review_state
