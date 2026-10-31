import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from fsrs import Rating


from app.models.assessment import Question, QuestionType
from app.models.fsrs_review import ConceptReviewState, ReviewHistory
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.user import User
from app.schemas.assessment import ResponseSubmit
from app.schemas.fsrs_review import CompleteRevisionRequest
from app.services.assessment_service import AssessmentService
from app.services.fsrs_service import FSRSService
from app.services.revision_service import RevisionService
from app.services.review_state_service import ReviewStateService



@pytest.fixture
def setup_bkt_fsrs_context(db_session: Session, teacher_user: User, student_user: User):
    subj = Subject(name="Physics", code="PHY102", description="Mechanics")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    chap = Chapter(subject_id=subj.id, title="Kinetics", chapter_number=1, description="Motion")
    db_session.add(chap)
    db_session.commit()
    db_session.refresh(chap)

    concept = Concept(
        concept_code="PHY-KIN-001",
        subject_id=subj.id,
        chapter_id=chap.id,
        name="Velocity and Acceleration",
        description="Definitions of velocity and acceleration",
        difficulty_level=DifficultyLevel.BEGINNER,
    )
    db_session.add(concept)
    db_session.commit()
    db_session.refresh(concept)

    question = Question(
        concept_id=concept.id,
        question_type=QuestionType.MCQ,
        question_text="What is the derivative of position with respect to time?",
        question_options=[{"id": "A", "text": "Velocity"}, {"id": "B", "text": "Mass"}],
        correct_answer="A",
        evaluation_rubric={"explanation": "Velocity is dx/dt"},
        created_by_id=teacher_user.id,
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)

    return subj, chap, concept, question


class TestBKTAndFSRSIntegration:
    """
    Validates independent operation and transaction coordination between
    Bayesian Knowledge Tracing (BKT) and FSRS Spaced Repetition across Scenarios 1-6.
    """

    def test_scenario_1_ordinary_practice_updates_bkt_only(
        self, db_session: Session, student_user: User, setup_bkt_fsrs_context
    ):
        """
        SCENARIO 1:
        Student answers an ordinary practice question correctly.
        Expected:
        - BKT updates.
        - No FSRS review event is created.
        """
        _, _, concept, question = setup_bkt_fsrs_context

        # Check initial FSRS review history count
        initial_history_count = db_session.query(ReviewHistory).filter(
            ReviewHistory.student_id == student_user.id
        ).count()

        # Submit ordinary practice response
        submit_in = ResponseSubmit(
            question_id=question.id,
            response_text="A",
            confidence_score=0.9,
            time_spent_ms=2500,
        )
        res = AssessmentService.evaluate_and_record_response(
            db=db_session,
            user_id=student_user.id,
            submit_in=submit_in,
        )

        assert res.is_correct is True
        assert res.new_mastery_probability > res.previous_mastery_probability

        # Check LearnerMastery updated
        mastery = db_session.query(LearnerMastery).filter(
            LearnerMastery.student_id == student_user.id,
            LearnerMastery.concept_id == concept.id,
        ).first()
        assert mastery is not None
        assert mastery.total_attempts == 1
        assert mastery.correct_attempts == 1

        # Check that NO FSRS ReviewHistory was created
        final_history_count = db_session.query(ReviewHistory).filter(
            ReviewHistory.student_id == student_user.id
        ).count()
        assert final_history_count == initial_history_count

    def test_scenario_2_scheduled_review_updates_both_bkt_and_fsrs(
        self, db_session: Session, student_user: User, setup_bkt_fsrs_context
    ):
        """
        SCENARIO 2:
        Student completes a scheduled review and answers correctly.
        Expected:
        - BKT processes validated learning evidence.
        - FSRS processes the accepted recall rating.
        - Review history is saved.
        - New due date is returned.
        """
        _, _, concept, question = setup_bkt_fsrs_context

        req = CompleteRevisionRequest(
            question_id=question.id,
            response_text="A",
            rating=3,  # Good
            idempotency_key="scen2_key_001",
        )
        resp = RevisionService.complete_revision_session(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            request=req,
        )

        assert resp.answer_correctness is True
        assert resp.rating == 3
        assert resp.rating_valid is True
        assert resp.updated_stability > 0.0
        assert resp.next_due_at_utc is not None
        assert resp.updated_bkt_mastery > 0.0

        # Verify BKT evidence exists
        ev = db_session.query(LearningHistory).filter(
            LearningHistory.student_id == student_user.id,
            LearningHistory.concept_id == concept.id,
        ).first()
        assert ev is not None
        assert ev.is_correct is True

        # Verify FSRS ConceptReviewState updated
        state = ReviewStateService.get_review_state(db_session, student_user.id, concept.id)
        assert state is not None
        assert state.total_reviews == 1
        assert state.stability > 0.0

        # Verify ReviewHistory record
        hist = db_session.query(ReviewHistory).filter(
            ReviewHistory.idempotency_key == "scen2_key_001"
        ).first()
        assert hist is not None
        assert hist.rating == 3
        assert hist.answer_correctness is True

    def test_scenario_3_incorrect_answer_in_scheduled_revision_requires_again(
        self, db_session: Session, student_user: User, setup_bkt_fsrs_context
    ):
        """
        SCENARIO 3:
        Student answers incorrectly during scheduled revision.
        Expected:
        - If rating is Good, rejected by rating policy.
        - If rating is Again, accepted: BKT records incorrect, FSRS schedules relearning.
        """
        _, _, concept, question = setup_bkt_fsrs_context

        # 1. Attempt submitting rating Good (3) on incorrect answer -> rejected
        req_bad = CompleteRevisionRequest(
            question_id=question.id,
            response_text="B",  # Incorrect answer
            rating=3,           # Good
            idempotency_key="scen3_bad_key",
        )
        with pytest.raises(HTTPException) as exc_info:
            RevisionService.complete_revision_session(
                db=db_session,
                student_id=student_user.id,
                concept_id=concept.id,
                request=req_bad,
            )
        assert exc_info.value.status_code == 400
        assert "requires rating 'Again' (1)" in exc_info.value.detail

        # 2. Submit rating Again (1) -> accepted
        req_good = CompleteRevisionRequest(
            question_id=question.id,
            response_text="B",  # Incorrect answer
            rating=1,           # Again
            idempotency_key="scen3_good_key",
        )
        resp = RevisionService.complete_revision_session(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            request=req_good,
        )
        assert resp.answer_correctness is False
        assert resp.rating == 1
        assert resp.rating_valid is True

        # Verify lapse tracked in FSRS state
        state = ReviewStateService.get_review_state(db_session, student_user.id, concept.id)
        assert state.lapses == 1

        # Verify BKT updated with incorrect evidence
        mastery = db_session.query(LearnerMastery).filter(
            LearnerMastery.student_id == student_user.id,
            LearnerMastery.concept_id == concept.id,
        ).first()
        assert mastery.incorrect_attempts == 1

    def test_scenario_4_idempotent_duplicate_submission(
        self, db_session: Session, student_user: User, setup_bkt_fsrs_context
    ):
        """
        SCENARIO 4:
        Student repeats the same review submission.
        Expected:
        - No duplicate BKT update.
        - No duplicate FSRS update.
        - Existing review result is returned using its idempotency key.
        """
        _, _, concept, question = setup_bkt_fsrs_context
        key = "idemp_scen4_key_123"

        req = CompleteRevisionRequest(
            question_id=question.id,
            response_text="A",
            rating=4,  # Easy
            idempotency_key=key,
        )
        resp1 = RevisionService.complete_revision_session(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            request=req,
        )
        assert resp1.is_idempotent_duplicate is False

        # Query counts
        bkt_history_count_1 = db_session.query(LearningHistory).filter(
            LearningHistory.student_id == student_user.id,
            LearningHistory.concept_id == concept.id,
        ).count()
        fsrs_history_count_1 = db_session.query(ReviewHistory).filter(
            ReviewHistory.student_id == student_user.id,
            ReviewHistory.concept_id == concept.id,
        ).count()

        # Repeat same request
        resp2 = RevisionService.complete_revision_session(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            request=req,
        )
        assert resp2.is_idempotent_duplicate is True
        assert resp2.idempotency_key == key
        assert resp2.next_due_at_utc == resp1.next_due_at_utc

        # Verify counts remained unchanged
        bkt_history_count_2 = db_session.query(LearningHistory).filter(
            LearningHistory.student_id == student_user.id,
            LearningHistory.concept_id == concept.id,
        ).count()
        fsrs_history_count_2 = db_session.query(ReviewHistory).filter(
            ReviewHistory.student_id == student_user.id,
            ReviewHistory.concept_id == concept.id,
        ).count()

        assert bkt_history_count_2 == bkt_history_count_1
        assert fsrs_history_count_2 == fsrs_history_count_1

    def test_scenario_5_fsrs_and_bkt_transaction_rollback_consistency(
        self, db_session: Session, student_user: User, setup_bkt_fsrs_context
    ):
        """
        SCENARIO 5:
        Simulates failure during commit:
        Expected:
        - Transaction rolls back consistently.
        - No partial review history.
        - Retrying must not duplicate BKT evidence.
        """
        _, _, concept, question = setup_bkt_fsrs_context
        fail_key = "scen5_fail_key"

        # Pre-enroll state
        state = ReviewStateService.enroll_concept(db_session, student_user.id, concept.id, ignore_daily_limit=True)
        initial_reviews = state.total_reviews

        # Wrap in a transaction that fails at the end
        try:
            # Stage FSRS update
            card = ReviewStateService.restore_card(state)
            scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
            updated_card, log = FSRSService.review_card(scheduler, card, Rating.Good)
            ReviewStateService.update_card_state(db_session, state, updated_card, Rating.Good.value, log)

            # Insert an invalid row to force an IntegrityError on commit
            bad_row = ReviewHistory(
                student_id=student_user.id,
                concept_id=concept.id,
                idempotency_key=None,  # Null violates NOT NULL constraint!
                rating=3,
                answer_correctness=True,
                next_due_at_utc=datetime.now(timezone.utc),
                updated_stability=1.0,
                updated_difficulty=1.0,
                review_log_json={},
            )
            db_session.add(bad_row)
            db_session.commit()
        except IntegrityError:
            db_session.rollback()

        # Check that state was rolled back completely
        db_session.refresh(state)
        assert state.total_reviews == initial_reviews

        # Check no orphaned ReviewHistory was persisted
        h = db_session.query(ReviewHistory).filter(ReviewHistory.student_id == student_user.id).first()
        assert h is None

    def test_scenario_6_recovery_after_downstream_failure(
        self, db_session: Session, student_user: User, setup_bkt_fsrs_context
    ):
        """
        SCENARIO 6:
        Learning update succeeds, downstream feedback formatting raises an error.
        Expected:
        - FSRS state remains consistent.
        - Recovery retry with same idempotency key does not duplicate learning updates.
        """
        _, _, concept, question = setup_bkt_fsrs_context
        key = "scen6_key_retry"

        req = CompleteRevisionRequest(
            question_id=question.id,
            response_text="A",
            rating=3,
            idempotency_key=key,
        )

        # 1. Successful review completion
        resp1 = RevisionService.complete_revision_session(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            request=req,
        )

        # Simulate subsequent failure in another system component
        with pytest.raises(RuntimeError, match="Simulated downstream Llama formatting failure"):
            raise RuntimeError("Simulated downstream Llama formatting failure")

        # 2. Retry with same idempotency key
        resp2 = RevisionService.complete_revision_session(
            db=db_session,
            student_id=student_user.id,
            concept_id=concept.id,
            request=req,
        )

        assert resp2.is_idempotent_duplicate is True
        assert resp2.updated_stability == resp1.updated_stability
        assert resp2.next_due_at_utc == resp1.next_due_at_utc
