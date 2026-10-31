from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fsrs import ReviewLog

from app.models.fsrs_review import ReviewHistory
from app.services.fsrs_service import FSRSService


class ReviewHistoryService:
    """
    Manages immutable audit records for spaced repetition reviews.
    Guarantees strict idempotency and preserves exact before/after memory metrics.
    """

    @classmethod
    def get_by_idempotency_key(
        cls,
        db: Session,
        idempotency_key: str,
    ) -> Optional[ReviewHistory]:
        """Retrieves existing review record by unique idempotency key."""
        return db.query(ReviewHistory).filter(
            ReviewHistory.idempotency_key == idempotency_key
        ).first()

    @classmethod
    def record_review(
        cls,
        db: Session,
        student_id: int,
        concept_id: int,
        idempotency_key: str,
        rating: int,
        answer_correctness: bool,
        previous_due_at_utc: Optional[datetime],
        next_due_at_utc: datetime,
        previous_stability: Optional[float],
        updated_stability: float,
        previous_difficulty: Optional[float],
        updated_difficulty: float,
        retrievability_before: Optional[float],
        review_log: ReviewLog,
        question_id: Optional[int] = None,
        response_id: Optional[int] = None,
        evidence_id: Optional[str] = None,
    ) -> Tuple[ReviewHistory, bool]:
        """
        Inserts an immutable review record. If idempotency key already exists,
        returns the existing record without creating duplicate entries.
        Returns: (review_history_record, is_duplicate)
        """
        existing = cls.get_by_idempotency_key(db, idempotency_key)
        if existing:
            return existing, True

        now_utc = datetime.now(timezone.utc)
        log_json = FSRSService.review_log_to_dict(review_log)

        history = ReviewHistory(
            student_id=student_id,
            concept_id=concept_id,
            question_id=question_id,
            response_id=response_id,
            evidence_id=evidence_id,
            idempotency_key=idempotency_key,
            rating=rating,
            answer_correctness=answer_correctness,
            previous_due_at_utc=previous_due_at_utc,
            next_due_at_utc=next_due_at_utc,
            previous_stability=previous_stability,
            updated_stability=updated_stability,
            previous_difficulty=previous_difficulty,
            updated_difficulty=updated_difficulty,
            retrievability_before=retrievability_before,
            review_timestamp_utc=review_log.review_datetime if review_log.review_datetime else now_utc,
            review_log_json=log_json,
        )

        db.add(history)
        db.flush()
        return history, False

    @classmethod
    def get_student_history(
        cls,
        db: Session,
        student_id: int,
        concept_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ReviewHistory]:
        """Queries review history for a student with optional concept filtering."""
        query = db.query(ReviewHistory).filter(ReviewHistory.student_id == student_id)
        if concept_id is not None:
            query = query.filter(ReviewHistory.concept_id == concept_id)

        return query.order_by(ReviewHistory.review_timestamp_utc.desc()).offset(offset).limit(limit).all()
