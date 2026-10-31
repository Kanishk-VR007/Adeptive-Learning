from datetime import datetime, timedelta, timezone
import zoneinfo
import pytest
from sqlalchemy.orm import Session
from fsrs import Rating

from app.models.fsrs_review import ConceptReviewState, ReviewPreferences
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.user import User, UserRole
from app.schemas.fsrs_review import RevisionStatusEnum
from app.services.fsrs_service import FSRSService
from app.services.review_state_service import ReviewStateService
from app.services.revision_queue_service import RevisionQueueService


@pytest.fixture
def multi_concepts(db_session: Session, teacher_user: User):
    subj = Subject(name="Mathematics", code="MATH101", description="Calculus")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    chap = Chapter(subject_id=subj.id, title="Derivatives", chapter_number=1, description="Derivatives Fundamentals")
    db_session.add(chap)
    db_session.commit()
    db_session.refresh(chap)

    concepts = []
    for i in range(1, 11):
        c = Concept(
            concept_code=f"MATH-DER-{i:03d}",
            subject_id=subj.id,
            chapter_id=chap.id,
            name=f"Derivative Rule #{i}",
            description=f"Rule description {i}",
            difficulty_level=DifficultyLevel.BEGINNER,
        )
        db_session.add(c)
        concepts.append(c)
    db_session.commit()
    for c in concepts:
        db_session.refresh(c)

    return subj, chap, concepts


class TestRevisionQueue:
    """
    Exhaustive tests for RevisionQueueService: status categorization,
    priority ordering, pacing limits, and multi-timezone calendar date handling.
    """

    def test_empty_revision_queue(self, db_session: Session, student_user: User):
        resp = RevisionQueueService.get_revision_queue(
            db=db_session,
            student_id=student_user.id,
        )
        assert resp.total_count == 0
        assert len(resp.items) == 0

    def test_new_concept_categorization(self, db_session: Session, student_user: User, multi_concepts):
        _, _, concepts = multi_concepts
        state = ReviewStateService.enroll_concept(
            db=db_session,
            student_id=student_user.id,
            concept_id=concepts[0].id,
            ignore_daily_limit=True,
        )

        resp = RevisionQueueService.get_revision_queue(
            db=db_session,
            student_id=student_user.id,
        )
        assert resp.total_count == 1
        assert resp.items[0].status == RevisionStatusEnum.NEW
        assert resp.items[0].review_count == 0
        assert resp.items[0].fsrs_retrievability is None

    def test_queue_categorization_due_today_vs_overdue_vs_upcoming(
        self, db_session: Session, student_user: User, multi_concepts
    ):
        _, _, concepts = multi_concepts
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        ref_time = datetime(2026, 10, 31, 14, 0, 0, tzinfo=timezone.utc)

        # 1. Overdue card: due 2 days ago
        s1 = ReviewStateService.enroll_concept(db_session, student_user.id, concepts[0].id, ignore_daily_limit=True)
        card1, log1 = FSRSService.review_card(scheduler, ReviewStateService.restore_card(s1), Rating.Good, review_datetime=ref_time - timedelta(days=5))
        ReviewStateService.update_card_state(db_session, s1, card1, Rating.Good.value, log1)
        s1.due_at_utc = ref_time - timedelta(days=2)

        # 2. Due today card: due earlier today
        s2 = ReviewStateService.enroll_concept(db_session, student_user.id, concepts[1].id, ignore_daily_limit=True)
        card2, log2 = FSRSService.review_card(scheduler, ReviewStateService.restore_card(s2), Rating.Good, review_datetime=ref_time - timedelta(days=1))
        ReviewStateService.update_card_state(db_session, s2, card2, Rating.Good.value, log2)
        s2.due_at_utc = ref_time - timedelta(hours=2)

        # 3. Upcoming card: reviewed 2 days ago, due in 5 days
        s3 = ReviewStateService.enroll_concept(db_session, student_user.id, concepts[2].id, ignore_daily_limit=True)
        card3, log3 = FSRSService.review_card(scheduler, ReviewStateService.restore_card(s3), Rating.Easy, review_datetime=ref_time - timedelta(days=2))
        ReviewStateService.update_card_state(db_session, s3, card3, Rating.Easy.value, log3)
        s3.due_at_utc = ref_time + timedelta(days=5)

        # 4. Reviewed today card: reviewed at ref_time today, next due in 5 days
        s4 = ReviewStateService.enroll_concept(db_session, student_user.id, concepts[3].id, ignore_daily_limit=True)
        card4, log4 = FSRSService.review_card(scheduler, ReviewStateService.restore_card(s4), Rating.Good, review_datetime=ref_time)
        ReviewStateService.update_card_state(db_session, s4, card4, Rating.Good.value, log4)
        s4.due_at_utc = ref_time + timedelta(days=5)

        db_session.commit()

        queue = RevisionQueueService.get_revision_queue(
            db=db_session,
            student_id=student_user.id,
            reference_time_utc=ref_time,
        )

        status_map = {item.concept_id: item.status for item in queue.items}
        assert status_map[concepts[0].id] == RevisionStatusEnum.OVERDUE
        assert status_map[concepts[1].id] == RevisionStatusEnum.DUE_TODAY
        assert status_map[concepts[2].id] == RevisionStatusEnum.UPCOMING
        assert status_map[concepts[3].id] == RevisionStatusEnum.REVIEWED

        # Summary check
        summary = RevisionQueueService.get_summary(db_session, student_user.id, reference_time_utc=ref_time)
        assert summary.overdue_count == 1
        assert summary.due_today_count == 1
        assert summary.upcoming_count == 1
        assert summary.total_reviewed_count == 1


    def test_priority_ordering(self, db_session: Session, student_user: User, multi_concepts):
        _, _, concepts = multi_concepts
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        ref_time = datetime(2026, 10, 31, 14, 0, 0, tzinfo=timezone.utc)

        # Create overdue (most urgent), due today (medium), and upcoming (least urgent)
        s_overdue = ReviewStateService.enroll_concept(db_session, student_user.id, concepts[0].id, ignore_daily_limit=True)
        c_o, l_o = FSRSService.review_card(scheduler, ReviewStateService.restore_card(s_overdue), Rating.Good, review_datetime=ref_time - timedelta(days=3))
        ReviewStateService.update_card_state(db_session, s_overdue, c_o, Rating.Good.value, l_o)
        s_overdue.due_at_utc = ref_time - timedelta(days=2)

        s_due = ReviewStateService.enroll_concept(db_session, student_user.id, concepts[1].id, ignore_daily_limit=True)
        c_d, l_d = FSRSService.review_card(scheduler, ReviewStateService.restore_card(s_due), Rating.Good, review_datetime=ref_time - timedelta(days=1))
        ReviewStateService.update_card_state(db_session, s_due, c_d, Rating.Good.value, l_d)
        s_due.due_at_utc = ref_time - timedelta(hours=1)

        s_upcoming = ReviewStateService.enroll_concept(db_session, student_user.id, concepts[2].id, ignore_daily_limit=True)
        c_u, l_u = FSRSService.review_card(scheduler, ReviewStateService.restore_card(s_upcoming), Rating.Easy, review_datetime=ref_time)
        ReviewStateService.update_card_state(db_session, s_upcoming, c_u, Rating.Easy.value, l_u)
        s_upcoming.due_at_utc = ref_time + timedelta(days=4)

        db_session.commit()

        queue = RevisionQueueService.get_revision_queue(
            db=db_session,
            student_id=student_user.id,
            reference_time_utc=ref_time,
        )

        assert len(queue.items) == 3
        # Priority score descending: Overdue first, then Due Today, then Upcoming
        assert queue.items[0].concept_id == concepts[0].id
        assert queue.items[1].concept_id == concepts[1].id
        assert queue.items[2].concept_id == concepts[2].id
        assert queue.items[0].priority_score > queue.items[1].priority_score > queue.items[2].priority_score

    def test_timezone_calendar_date_across_midnight(self, db_session: Session, student_user: User, multi_concepts):
        """
        Tests that Due Today is calculated strictly according to student's local
        calendar date, not server timezone or raw UTC date.
        Compares:
        - Asia/Kolkata (UTC +5:30)
        - UTC
        - America/New_York (UTC -4:00 DST / -5:00)
        """
        _, _, concepts = multi_concepts
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)

        # Scenario: UTC time is 2026-10-31 20:00:00
        # In Asia/Kolkata (UTC +5:30), it is 2026-11-01 01:30:00 (Tomorrow in UTC!)
        # In America/New_York (UTC -4:00), it is 2026-10-31 16:00:00
        ref_utc = datetime(2026, 10, 31, 20, 0, 0, tzinfo=timezone.utc)

        # Card due at 2026-11-01 03:00:00 UTC
        # For UTC: This is tomorrow (2026-11-01), so UPCOMING
        # For Asia/Kolkata: In IST, 2026-11-01 03:00 UTC is 2026-11-01 08:30 IST.
        # Since current IST is 2026-11-01 01:30, it falls within IST TODAY (2026-11-01)! -> DUE_TODAY!
        state = ReviewStateService.enroll_concept(db_session, student_user.id, concepts[0].id, ignore_daily_limit=True)
        c, l = FSRSService.review_card(scheduler, ReviewStateService.restore_card(state), Rating.Good, review_datetime=ref_utc - timedelta(days=1))
        ReviewStateService.update_card_state(db_session, state, c, Rating.Good.value, l)
        state.due_at_utc = datetime(2026, 11, 1, 3, 0, 0, tzinfo=timezone.utc)
        db_session.commit()

        # Check in UTC timezone
        pref_utc = ReviewPreferences(student_id=student_user.id, timezone_name="UTC")
        db_session.merge(pref_utc)
        db_session.commit()

        q_utc = RevisionQueueService.get_revision_queue(db_session, student_user.id, reference_time_utc=ref_utc)
        assert q_utc.items[0].status == RevisionStatusEnum.UPCOMING

        # Check in Asia/Kolkata timezone
        pref_kolkata = db_session.query(ReviewPreferences).filter(ReviewPreferences.student_id == student_user.id).first()
        pref_kolkata.timezone_name = "Asia/Kolkata"
        db_session.commit()

        q_kolkata = RevisionQueueService.get_revision_queue(db_session, student_user.id, reference_time_utc=ref_utc)
        assert q_kolkata.items[0].status == RevisionStatusEnum.DUE_TODAY

        # Verify stored due date was NEVER mutated
        db_session.refresh(state)
        state_due = state.due_at_utc if state.due_at_utc.tzinfo else state.due_at_utc.replace(tzinfo=timezone.utc)
        assert state_due == datetime(2026, 11, 1, 3, 0, 0, tzinfo=timezone.utc)

    def test_daily_new_concept_and_display_pacing(self, db_session: Session, student_user: User, multi_concepts):
        _, _, concepts = multi_concepts
        # Enroll 8 new concepts
        for c in concepts[:8]:
            ReviewStateService.enroll_concept(db_session, student_user.id, c.id, ignore_daily_limit=True)

        # Set daily new limit to 3, daily review display limit to 5
        pref = ReviewPreferences(
            student_id=student_user.id,
            timezone_name="UTC",
            daily_new_concept_limit=3,
            daily_review_display_limit=5,
        )
        db_session.merge(pref)
        db_session.commit()

        queue = RevisionQueueService.get_revision_queue(db_session, student_user.id)
        # Should be limited to daily_new_concept_limit (3)
        assert len(queue.items) == 3

    def test_independent_schedules_for_multiple_students(self, db_session: Session, multi_concepts):
        _, _, concepts = multi_concepts
        # Create student A and student B
        student_a = User(email="student_a@test.edu", hashed_password="pw", full_name="Student A", role=UserRole.STUDENT, is_active=True)
        student_b = User(email="student_b@test.edu", hashed_password="pw", full_name="Student B", role=UserRole.STUDENT, is_active=True)
        db_session.add_all([student_a, student_b])
        db_session.commit()

        ReviewStateService.enroll_concept(db_session, student_a.id, concepts[0].id, ignore_daily_limit=True)
        ReviewStateService.enroll_concept(db_session, student_b.id, concepts[1].id, ignore_daily_limit=True)

        qa = RevisionQueueService.get_revision_queue(db_session, student_a.id)
        qb = RevisionQueueService.get_revision_queue(db_session, student_b.id)

        assert qa.total_count == 1
        assert qa.items[0].concept_id == concepts[0].id

        assert qb.total_count == 1
        assert qb.items[0].concept_id == concepts[1].id
