from datetime import datetime, timedelta, timezone
import zoneinfo
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.fsrs_review import ConceptReviewState, ReviewPreferences
from app.models.learner_mastery import LearnerMastery
from app.models.syllabus import Concept, Chapter, Subject
from app.schemas.fsrs_review import (
    RevisionQueueItem,
    RevisionQueueResponse,
    RevisionStatusEnum,
    RevisionSummaryResponse,
)
from app.services.fsrs_configuration_service import FSRSConfigurationService
from app.services.fsrs_service import FSRSService
from app.services.review_state_service import ReviewStateService


class RevisionQueueService:
    """
    Constructs personalized, priority-ordered revision queues.
    Respects student local calendar timezones for 'Due Today' categorization,
    applies pacing limits without mutating FSRS due dates, and computes
    retrievability alongside independent BKT mastery.
    """

    @classmethod
    def get_student_timezone(cls, db: Session, student_id: int) -> zoneinfo.ZoneInfo:
        """Resolves student's IANA timezone preference, falling back to UTC."""
        pref = db.query(ReviewPreferences).filter(
            ReviewPreferences.student_id == student_id
        ).first()
        tz_name = pref.timezone_name if pref and pref.timezone_name else "UTC"
        try:
            return zoneinfo.ZoneInfo(tz_name.strip())
        except Exception:
            return zoneinfo.ZoneInfo("UTC")

    @classmethod
    def get_local_calendar_day_bounds_utc(
        cls,
        target_tz: zoneinfo.ZoneInfo,
        reference_time_utc: Optional[datetime] = None,
    ) -> Tuple[datetime, datetime]:
        """
        Calculates UTC start and end timestamps representing the student's
        local calendar day [00:00:00, 23:59:59.999999].
        """
        ref_utc = reference_time_utc or datetime.now(timezone.utc)
        if ref_utc.tzinfo is None:
            ref_utc = ref_utc.replace(tzinfo=timezone.utc)

        local_time = ref_utc.astimezone(target_tz)
        start_of_day_local = local_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_local = start_of_day_local + timedelta(days=1)

        start_of_day_utc = start_of_day_local.astimezone(timezone.utc)
        end_of_day_utc = end_of_day_local.astimezone(timezone.utc)
        return start_of_day_utc, end_of_day_utc

    @classmethod
    def classify_status(
        cls,
        due_at_utc: datetime,
        total_reviews: int,
        start_of_today_utc: datetime,
        end_of_today_utc: datetime,
        last_review_at_utc: Optional[datetime] = None,
    ) -> RevisionStatusEnum:
        """
        Determines revision status relative to student's local calendar day:
        - total_reviews == 0 -> NEW
        - due_at_utc < start_of_today_utc -> OVERDUE
        - start_of_today_utc <= due_at_utc <= end_of_today_utc -> DUE_TODAY
        - due_at_utc > end_of_today_utc:
          - if last_review_at_utc >= start_of_today_utc -> REVIEWED
          - else -> UPCOMING
        """
        if total_reviews == 0:
            return RevisionStatusEnum.NEW

        if due_at_utc < start_of_today_utc:
            return RevisionStatusEnum.OVERDUE

        if start_of_today_utc <= due_at_utc <= end_of_today_utc:
            return RevisionStatusEnum.DUE_TODAY

        if last_review_at_utc and last_review_at_utc >= start_of_today_utc:
            return RevisionStatusEnum.REVIEWED

        return RevisionStatusEnum.UPCOMING

    @classmethod
    def compute_priority_score(
        cls,
        status: RevisionStatusEnum,
        due_at_utc: datetime,
        now_utc: datetime,
        retrievability: float,
        bkt_mastery: float,
        lapses: int,
    ) -> float:
        """
        Deterministic queue priority score (higher score = earlier in review queue):
        - OVERDUE: high base weight + overdue hours
        - DUE_TODAY: medium base weight
        - NEW: controlled introduction weight
        - Memory degradation bonus: (1.0 - retrievability) * 100
        - Mastery gap bonus: (1.0 - bkt_mastery) * 50
        - Historical lapse penalty: lapses * 15
        """
        if status == RevisionStatusEnum.OVERDUE:
            hours_overdue = max(0.0, (now_utc - due_at_utc).total_seconds() / 3600.0)
            base = 1000.0 + min(hours_overdue * 10.0, 500.0)
        elif status == RevisionStatusEnum.DUE_TODAY:
            base = 500.0
        elif status == RevisionStatusEnum.NEW:
            base = 250.0
        elif status == RevisionStatusEnum.REVIEWED:
            base = 50.0
        else:  # UPCOMING
            days_future = max(0.0, (due_at_utc - now_utc).total_seconds() / 86400.0)
            base = max(10.0, 100.0 - (days_future * 10.0))

        # Memory urgency
        retrievability_urgency = (1.0 - retrievability) * 100.0
        bkt_urgency = (1.0 - bkt_mastery) * 50.0
        lapse_urgency = min(lapses * 15.0, 150.0)

        return round(base + retrievability_urgency + bkt_urgency + lapse_urgency, 2)

    @classmethod
    def get_summary(
        cls,
        db: Session,
        student_id: int,
        reference_time_utc: Optional[datetime] = None,
    ) -> RevisionSummaryResponse:
        """
        Generates aggregate counts for due today, overdue, upcoming, new, and reviewed.
        """
        now_utc = reference_time_utc or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        student_tz = cls.get_student_timezone(db, student_id)
        start_of_today_utc, end_of_today_utc = cls.get_local_calendar_day_bounds_utc(
            student_tz, reference_time_utc=now_utc
        )

        states = db.query(ConceptReviewState).filter(
            ConceptReviewState.student_id == student_id
        ).all()

        due_today_count = 0
        overdue_count = 0
        upcoming_count = 0
        new_count = 0
        total_reviewed_count = 0

        for state in states:
            due_utc = state.due_at_utc
            if due_utc.tzinfo is None:
                due_utc = due_utc.replace(tzinfo=timezone.utc)

            last_rev_utc = state.last_review_at_utc
            if last_rev_utc and last_rev_utc.tzinfo is None:
                last_rev_utc = last_rev_utc.replace(tzinfo=timezone.utc)

            cat = cls.classify_status(
                due_at_utc=due_utc,
                total_reviews=state.total_reviews,
                start_of_today_utc=start_of_today_utc,
                end_of_today_utc=end_of_today_utc,
                last_review_at_utc=last_rev_utc,
            )

            if cat == RevisionStatusEnum.NEW:
                new_count += 1
            elif cat == RevisionStatusEnum.OVERDUE:
                overdue_count += 1
            elif cat == RevisionStatusEnum.DUE_TODAY:
                due_today_count += 1
            elif cat == RevisionStatusEnum.REVIEWED:
                total_reviewed_count += 1
            elif cat == RevisionStatusEnum.UPCOMING:
                upcoming_count += 1

        return RevisionSummaryResponse(
            due_today_count=due_today_count,
            overdue_count=overdue_count,
            upcoming_count=upcoming_count,
            new_count=new_count,
            total_reviewed_count=total_reviewed_count,
            student_timezone=str(student_tz),
        )

    @classmethod
    def get_revision_queue(
        cls,
        db: Session,
        student_id: int,
        status_filter: Optional[RevisionStatusEnum] = None,
        subject_id_filter: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        reference_time_utc: Optional[datetime] = None,
    ) -> RevisionQueueResponse:
        """
        Constructs and filters the personalized revision queue.
        Enforces daily display limit and daily new concept limits.
        """
        now_utc = reference_time_utc or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        student_tz = cls.get_student_timezone(db, student_id)
        start_of_today_utc, end_of_today_utc = cls.get_local_calendar_day_bounds_utc(
            student_tz, reference_time_utc=now_utc
        )

        scheduler = FSRSConfigurationService.get_scheduler_for_student(db, student_id)

        # Query all states with concept, chapter, subject join
        query = db.query(
            ConceptReviewState, Concept, Chapter, Subject
        ).join(
            Concept, ConceptReviewState.concept_id == Concept.id
        ).join(
            Chapter, Concept.chapter_id == Chapter.id
        ).join(
            Subject, Concept.subject_id == Subject.id
        ).filter(
            ConceptReviewState.student_id == student_id
        )

        if subject_id_filter is not None:
            query = query.filter(Concept.subject_id == subject_id_filter)

        rows = query.all()

        # Preload BKT masteries
        mastery_records = db.query(LearnerMastery).filter(
            LearnerMastery.student_id == student_id
        ).all()
        mastery_map: Dict[int, float] = {m.concept_id: m.current_mastery for m in mastery_records}

        pref = db.query(ReviewPreferences).filter(
            ReviewPreferences.student_id == student_id
        ).first()
        daily_new_limit = pref.daily_new_concept_limit if pref else 5
        daily_display_limit = pref.daily_review_display_limit if pref else 20

        all_items: List[RevisionQueueItem] = []
        new_items_count = 0

        for state, concept, chapter, subject in rows:
            due_utc = state.due_at_utc
            if due_utc.tzinfo is None:
                due_utc = due_utc.replace(tzinfo=timezone.utc)

            last_rev_utc = state.last_review_at_utc
            if last_rev_utc and last_rev_utc.tzinfo is None:
                last_rev_utc = last_rev_utc.replace(tzinfo=timezone.utc)

            status = cls.classify_status(
                due_at_utc=due_utc,
                total_reviews=state.total_reviews,
                start_of_today_utc=start_of_today_utc,
                end_of_today_utc=end_of_today_utc,
                last_review_at_utc=last_rev_utc,
            )

            if status_filter is not None and status != status_filter:
                continue

            # Retrievability
            card_obj = ReviewStateService.restore_card(state)
            retrievability = FSRSService.get_retrievability(scheduler, card_obj, now_utc)

            # BKT mastery
            bkt_mastery = mastery_map.get(concept.id, 0.1)

            # Priority score
            priority_score = cls.compute_priority_score(
                status=status,
                due_at_utc=due_utc,
                now_utc=now_utc,
                retrievability=retrievability,
                bkt_mastery=bkt_mastery,
                lapses=state.lapses,
            )

            # Recommended action text
            if status == RevisionStatusEnum.OVERDUE:
                action = "Critical revision required: recall probability has degraded below threshold."
            elif status == RevisionStatusEnum.DUE_TODAY:
                action = "Scheduled revision due today for optimal memory consolidation."
            elif status == RevisionStatusEnum.NEW:
                action = "Initial concept retention review."
            elif status == RevisionStatusEnum.REVIEWED:
                action = "Reviewed today; memory currently consolidated."
            else:
                action = "Concept is stable; review scheduled for a future date."

            item = RevisionQueueItem(
                concept_id=concept.id,
                concept_name=concept.name,
                subject_id=subject.id,
                subject_name=subject.name,
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                due_at_utc=due_utc,
                due_at_local=due_utc.astimezone(student_tz),
                status=status,
                current_bkt_mastery=bkt_mastery,
                fsrs_retrievability=retrievability if state.total_reviews > 0 else None,
                stability=state.stability,
                difficulty=state.difficulty,
                review_count=state.total_reviews,
                lapse_count=state.lapses,
                priority_score=priority_score,
                recommended_action=action,
            )
            all_items.append(item)

        # Sort deterministically by priority score descending, then due date ascending
        all_items.sort(key=lambda x: (-x.priority_score, x.due_at_utc))

        # Apply daily new concept pacing filter when not explicitly filtering by status
        paged_items: List[RevisionQueueItem] = []
        new_seen = 0

        for it in all_items:
            if it.status == RevisionStatusEnum.NEW:
                if status_filter is None and new_seen >= daily_new_limit:
                    continue
                new_seen += 1
            paged_items.append(it)

        total_matching = len(paged_items)

        # Apply daily display limit / user pagination
        effective_limit = min(limit, daily_display_limit) if status_filter is None else limit
        result_slice = paged_items[offset : offset + effective_limit]

        return RevisionQueueResponse(
            total_count=total_matching,
            timezone=str(student_tz),
            items=result_slice,
        )
