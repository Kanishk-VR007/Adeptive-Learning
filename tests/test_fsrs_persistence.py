from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fsrs import Rating

from app.models.fsrs_review import ConceptReviewState, ReviewHistory, ReviewPreferences
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.user import User
from app.services.fsrs_service import FSRSService
from app.services.review_history_service import ReviewHistoryService
from app.services.review_state_service import ReviewStateService


@pytest.fixture
def sample_syllabus(db_session: Session, teacher_user: User):
    subj = Subject(name="Physics", code="PHY101", description="General Physics")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    chap = Chapter(subject_id=subj.id, title="Mechanics", chapter_number=1, description="Newtonian Mechanics")
    db_session.add(chap)
    db_session.commit()
    db_session.refresh(chap)

    concept = Concept(
        concept_code="PHY-MEC-001",
        subject_id=subj.id,
        chapter_id=chap.id,
        name="Newton's Third Law",
        description="Action and reaction forces",
        difficulty_level=DifficultyLevel.BEGINNER,
    )

    db_session.add(concept)
    db_session.commit()
    db_session.refresh(concept)


    return subj, chap, concept


class TestFSRSPersistence:
    """
    Tests database persistence, unique constraints, foreign keys,
    immutability, and transactional integrity for FSRS models.
    """

    def test_enroll_concept_creates_valid_state(self, db_session: Session, student_user: User, sample_syllabus):
        _, _, concept = sample_syllabus
        state = ReviewStateService.enroll_concept(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            ignore_daily_limit=True,
        )

        assert state.id is not None
        assert state.student_id == student_user.id
        assert state.concept_id == concept.id
        assert state.state == 1  # State.Learning
        assert state.stability == 0.0
        assert state.difficulty == 0.0
        assert state.total_reviews == 0
        assert state.lapses == 0
        assert state.due_at_utc is not None
        assert state.fsrs_card_json is not None
        assert state.fsrs_library_version == "6.3.2"

    def test_duplicate_enrollment_prevention(self, db_session: Session, student_user: User, sample_syllabus):
        _, _, concept = sample_syllabus
        state1 = ReviewStateService.enroll_concept(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            ignore_daily_limit=True,
        )
        # Second call returns the existing record idempotently
        state2 = ReviewStateService.enroll_concept(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            ignore_daily_limit=True,
        )
        assert state1.id == state2.id

        # Direct DB duplicate insertion must fail unique constraint
        duplicate_rec = ConceptReviewState(
            student_id=student_user.id,
            concept_id=concept.id,
            fsrs_card_json={"card_id": 999},
            due_at_utc=datetime.now(timezone.utc),
            state=1,
            stability=0.0,
            difficulty=0.0,
            enrolled_at_utc=datetime.now(timezone.utc),
            updated_at_utc=datetime.now(timezone.utc),
        )
        db_session.add(duplicate_rec)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_update_card_state_persists_review_outcome(self, db_session: Session, student_user: User, sample_syllabus):
        _, _, concept = sample_syllabus
        state = ReviewStateService.enroll_concept(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            ignore_daily_limit=True,
        )

        card = ReviewStateService.restore_card(state)
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        now = datetime.now(timezone.utc)
        updated_card, log = FSRSService.review_card(scheduler, card, Rating.Good, review_datetime=now)

        ReviewStateService.update_card_state(
            db=db_session,
            review_state=state,
            updated_card=updated_card,
            rating=Rating.Good.value,
            log=log,
        )
        db_session.commit()
        db_session.refresh(state)

        assert state.total_reviews == 1
        assert state.lapses == 0
        assert state.stability > 0.0
        assert state.difficulty > 0.0
        state_due_utc = state.due_at_utc if state.due_at_utc.tzinfo else state.due_at_utc.replace(tzinfo=timezone.utc)
        assert state_due_utc == updated_card.due
        state_last_review_utc = state.last_review_at_utc if state.last_review_at_utc.tzinfo else state.last_review_at_utc.replace(tzinfo=timezone.utc)
        assert state_last_review_utc == now


    def test_lapse_increments_lapses_counter(self, db_session: Session, student_user: User, sample_syllabus):
        _, _, concept = sample_syllabus
        state = ReviewStateService.enroll_concept(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            ignore_daily_limit=True,
        )
        card = ReviewStateService.restore_card(state)
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        updated_card, log = FSRSService.review_card(scheduler, card, Rating.Again)

        ReviewStateService.update_card_state(
            db=db_session,
            review_state=state,
            updated_card=updated_card,
            rating=Rating.Again.value,
            log=log,
        )
        db_session.commit()
        db_session.refresh(state)

        assert state.total_reviews == 1
        assert state.lapses == 1

    def test_review_history_insertion_and_fields(self, db_session: Session, student_user: User, sample_syllabus):
        _, _, concept = sample_syllabus
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        card = FSRSService.create_new_card()
        now = datetime.now(timezone.utc)
        updated_card, log = FSRSService.review_card(scheduler, card, Rating.Good, review_datetime=now)

        history, is_dup = ReviewHistoryService.record_review(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            idempotency_key="idemp_unique_test_1",
            rating=Rating.Good.value,
            answer_correctness=True,
            previous_due_at_utc=card.due,
            next_due_at_utc=updated_card.due,
            previous_stability=None,
            updated_stability=float(updated_card.stability),
            previous_difficulty=None,
            updated_difficulty=float(updated_card.difficulty),
            retrievability_before=0.0,
            review_log=log,
        )
        db_session.commit()
        db_session.refresh(history)

        assert is_dup is False
        assert history.id is not None
        assert history.student_id == student_user.id
        assert history.concept_id == concept.id
        assert history.rating == Rating.Good.value
        assert history.answer_correctness is True
        assert history.idempotency_key == "idemp_unique_test_1"
        assert history.updated_stability == float(updated_card.stability)
        assert history.review_log_json is not None

    def test_review_history_idempotency_constraint(self, db_session: Session, student_user: User, sample_syllabus):
        _, _, concept = sample_syllabus
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        card = FSRSService.create_new_card()
        updated_card, log = FSRSService.review_card(scheduler, card, Rating.Good)

        hist1, is_dup1 = ReviewHistoryService.record_review(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            idempotency_key="idemp_dup_check",
            rating=Rating.Good.value,
            answer_correctness=True,
            previous_due_at_utc=card.due,
            next_due_at_utc=updated_card.due,
            previous_stability=None,
            updated_stability=float(updated_card.stability),
            previous_difficulty=None,
            updated_difficulty=float(updated_card.difficulty),
            retrievability_before=0.0,
            review_log=log,
        )
        db_session.commit()

        hist2, is_dup2 = ReviewHistoryService.record_review(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            idempotency_key="idemp_dup_check",
            rating=Rating.Good.value,
            answer_correctness=True,
            previous_due_at_utc=card.due,
            next_due_at_utc=updated_card.due,
            previous_stability=None,
            updated_stability=float(updated_card.stability),
            previous_difficulty=None,
            updated_difficulty=float(updated_card.difficulty),
            retrievability_before=0.0,
            review_log=log,
        )

        assert is_dup1 is False
        assert is_dup2 is True
        assert hist1.id == hist2.id

    def test_cascade_delete_on_student_deletion(self, db_session: Session, student_user: User, sample_syllabus):
        _, _, concept = sample_syllabus
        state = ReviewStateService.enroll_concept(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            ignore_daily_limit=True,
        )
        state_id = state.id
        assert state_id is not None

        # Delete student
        db_session.delete(student_user)
        db_session.commit()

        # ConceptReviewState should be deleted via cascade
        remaining = db_session.query(ConceptReviewState).filter(ConceptReviewState.id == state_id).first()
        assert remaining is None


    def test_database_transaction_rollback_guarantee(self, db_session: Session, student_user: User, sample_syllabus):
        _, _, concept = sample_syllabus
        state = ReviewStateService.enroll_concept(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            ignore_daily_limit=True,
        )
        initial_stability = state.stability

        # Attempt transactional update with an intentional failure
        try:
            state.stability = 99.9
            db_session.flush()

            # Intentional invalid insert to trigger failure
            invalid_history = ReviewHistory(
                student_id=999999,  # Non-existent FK
                concept_id=concept.id,
                idempotency_key="fail_key",
                rating=1,
                answer_correctness=False,
                next_due_at_utc=datetime.now(timezone.utc),
                updated_stability=1.0,
                updated_difficulty=1.0,
                review_log_json={},
            )
            db_session.add(invalid_history)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()

        # Verify rollback preserved initial state
        db_session.refresh(state)
        assert state.stability == initial_stability
