import uuid
from datetime import datetime, timezone
import zoneinfo
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.assessment import LearningSession, Question, QuestionType, SessionType, LearnerResponse
from app.models.fsrs_review import ConceptReviewState, ReviewHistory, ReviewPreferences
from app.models.learner_mastery import LearnerMastery
from app.models.syllabus import Concept
from app.schemas.fsrs_review import (
    CompleteRevisionRequest,
    CompleteRevisionResponse,
    ConceptReviewStateResponse,
    ReviewPreferencesResponse,
    ReviewPreferencesUpdate,
    StartRevisionResponse,
)
from app.schemas.learner_mastery import EvidenceSubmissionRequest
from app.services.fsrs_configuration_service import FSRSConfigurationService
from app.services.fsrs_service import FSRSService
from app.services.learner_model_service import LearnerModelService
from app.services.review_history_service import ReviewHistoryService
from app.services.review_rating_service import ReviewRatingService
from app.services.review_state_service import ReviewStateService


class RevisionService:
    """
    High-level orchestrator coordinating scheduled revisions, question retrieval,
    answer evaluation, rating policy enforcement, independent BKT evidence updates,
    and FSRS memory state transitions.
    """

    @classmethod
    def get_or_create_preferences(
        cls,
        db: Session,
        student_id: int,
    ) -> ReviewPreferences:
        """Retrieves or creates initial review preferences for a student."""
        pref = db.query(ReviewPreferences).filter(
            ReviewPreferences.student_id == student_id
        ).first()

        if not pref:
            pref = ReviewPreferences(
                student_id=student_id,
                desired_retention=getattr(settings, "FSRS_DESIRED_RETENTION", 0.90),
                timezone_name=getattr(settings, "FSRS_DEFAULT_TIMEZONE", "UTC"),
                daily_new_concept_limit=getattr(settings, "FSRS_DAILY_NEW_LIMIT", 5),
                daily_review_display_limit=getattr(settings, "FSRS_DAILY_REVIEW_LIMIT", 20),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)

        return pref

    @classmethod
    def update_preferences(
        cls,
        db: Session,
        student_id: int,
        obj_in: ReviewPreferencesUpdate,
    ) -> ReviewPreferences:
        """Updates student review preferences with validation."""
        pref = cls.get_or_create_preferences(db, student_id)

        if obj_in.desired_retention is not None:
            if not FSRSService.validate_desired_retention(obj_in.desired_retention):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Desired retention must be between 0.70 and 0.99, received {obj_in.desired_retention}",
                )
            pref.desired_retention = obj_in.desired_retention

        if obj_in.timezone_name is not None:
            clean_tz = obj_in.timezone_name.strip()
            try:
                zoneinfo.ZoneInfo(clean_tz)
                pref.timezone_name = clean_tz
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid IANA timezone name: '{clean_tz}'",
                )

        if obj_in.daily_new_concept_limit is not None:
            pref.daily_new_concept_limit = obj_in.daily_new_concept_limit

        if obj_in.daily_review_display_limit is not None:
            pref.daily_review_display_limit = obj_in.daily_review_display_limit

        pref.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(pref)
        return pref

    @classmethod
    def get_concept_review_state(
        cls,
        db: Session,
        student_id: int,
        concept_id: int,
    ) -> ConceptReviewStateResponse:
        """Retrieves the student's FSRS state for a concept."""
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID {concept_id} does not exist.",
            )

        state = ReviewStateService.get_review_state(db, student_id, concept_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept '{concept.name}' is not enrolled in spaced repetition for this student.",
            )

        pref = cls.get_or_create_preferences(db, student_id)
        try:
            tz = zoneinfo.ZoneInfo(pref.timezone_name)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        scheduler = FSRSConfigurationService.get_scheduler_for_student(db, student_id)
        card = ReviewStateService.restore_card(state)
        now_utc = datetime.now(timezone.utc)
        retrievability = FSRSService.get_retrievability(scheduler, card, now_utc)

        state_names = {1: "Learning", 2: "Review", 3: "Relearning"}

        due_utc = state.due_at_utc if state.due_at_utc.tzinfo else state.due_at_utc.replace(tzinfo=timezone.utc)

        return ConceptReviewStateResponse(
            id=state.id,
            student_id=state.student_id,
            concept_id=state.concept_id,
            concept_name=concept.name,
            state=state.state,
            state_name=state_names.get(state.state, "Unknown"),
            stability=state.stability,
            difficulty=state.difficulty,
            retrievability=retrievability if state.total_reviews > 0 else None,
            due_at_utc=due_utc,
            due_at_local=due_utc.astimezone(tz),
            last_review_at_utc=state.last_review_at_utc,
            total_reviews=state.total_reviews,
            lapses=state.lapses,
            enrolled_at_utc=state.enrolled_at_utc,
        )

    @classmethod
    def start_revision_session(
        cls,
        db: Session,
        student_id: int,
        concept_id: int,
    ) -> StartRevisionResponse:
        """
        Starts an authorized revision session: verifies concept, enrolls card if needed,
        retrieves or provisions a retrieval question, and opens a revision session.
        """
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID {concept_id} not found.",
            )

        # Check or enroll card
        state = ReviewStateService.get_review_state(db, student_id, concept_id)
        if not state:
            # Auto-enroll on deliberate revision start
            state = ReviewStateService.enroll_concept(db, student_id, concept_id, ignore_daily_limit=True)

        # Retrieve a question for this concept
        question = db.query(Question).filter(Question.concept_id == concept_id).first()
        if not question:
            # Create a default retrieval check question if none exists
            question = Question(
                concept_id=concept_id,
                question_type=QuestionType.MCQ,
                question_text=f"Which statement correctly describes the core principle of {concept.name}?",
                question_options=[
                    {"id": "A", "text": f"It defines the standard properties and theorems of {concept.name}."},
                    {"id": "B", "text": "It is an unrelated phenomenon."},
                    {"id": "C", "text": "It has no practical applications."},
                    {"id": "D", "text": "None of the above."},
                ],
                correct_answer="A",
                evaluation_rubric={"explanation": f"Core definition and principles of {concept.name}."},
                created_by_id=student_id,
            )
            db.add(question)
            db.commit()
            db.refresh(question)

        # Create LearningSession of type REVISION
        session = LearningSession(
            user_id=student_id,
            subject_id=concept.subject_id,
            session_type=SessionType.REVISION,
            telemetry_summary={
                "target_concept_id": concept_id,
                "revision_mode": "FSRS_SCHEDULED",
            },
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Current BKT mastery
        mastery = db.query(LearnerMastery).filter(
            LearnerMastery.student_id == student_id,
            LearnerMastery.concept_id == concept_id,
        ).first()
        bkt_p = mastery.current_mastery if mastery else 0.1

        # Retrievability
        scheduler = FSRSConfigurationService.get_scheduler_for_student(db, student_id)
        card = ReviewStateService.restore_card(state)
        now_utc = datetime.now(timezone.utc)
        r = FSRSService.get_retrievability(scheduler, card, now_utc)

        return StartRevisionResponse(
            session_id=session.id,
            concept_id=concept.id,
            concept_name=concept.name,
            question_id=question.id,
            question_text=question.question_text,
            question_type=question.question_type.value if hasattr(question.question_type, "value") else str(question.question_type),
            question_options=question.question_options,
            current_bkt_mastery=bkt_p,
            retrievability=r if state.total_reviews > 0 else None,
            started_at_utc=session.started_at,
        )

    @classmethod
    def complete_revision_session(
        cls,
        db: Session,
        student_id: int,
        concept_id: int,
        request: CompleteRevisionRequest,
    ) -> CompleteRevisionResponse:
        """
        Coordinates full scheduled revision completion:
        1. Enforces idempotency via idempotency_key.
        2. Validates question ownership and evaluates correctness.
        3. Enforces rating policy against correctness.
        4. Updates BKT mastery independently.
        5. Runs official FSRS scheduling update on Card.
        6. Persists ConceptReviewState and immutable ReviewHistory.
        """
        # 1. Idempotency Check
        idempotency_key = request.idempotency_key or f"rev_{uuid.uuid4().hex}"
        existing_history = ReviewHistoryService.get_by_idempotency_key(db, idempotency_key)

        pref = cls.get_or_create_preferences(db, student_id)
        try:
            student_tz = zoneinfo.ZoneInfo(pref.timezone_name)
        except Exception:
            student_tz = zoneinfo.ZoneInfo("UTC")

        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID {concept_id} not found.",
            )

        if existing_history:
            # Idempotent response: return existing saved result
            mastery = db.query(LearnerMastery).filter(
                LearnerMastery.student_id == student_id,
                LearnerMastery.concept_id == concept_id,
            ).first()
            current_p = mastery.current_mastery if mastery else 0.5

            state = ReviewStateService.get_review_state(db, student_id, concept_id)
            scheduler = FSRSConfigurationService.get_scheduler_for_student(db, student_id)
            r = 0.0
            if state:
                card = ReviewStateService.restore_card(state)
                r = FSRSService.get_retrievability(scheduler, card, datetime.now(timezone.utc))

            next_due_utc = existing_history.next_due_at_utc
            if next_due_utc.tzinfo is None:
                next_due_utc = next_due_utc.replace(tzinfo=timezone.utc)

            return CompleteRevisionResponse(
                idempotency_key=existing_history.idempotency_key,
                concept_id=concept_id,
                concept_name=concept.name,
                rating=existing_history.rating,
                rating_name=ReviewRatingService.get_rating_name(existing_history.rating),
                answer_correctness=existing_history.answer_correctness,
                rating_valid=True,
                rating_message="Idempotent duplicate submission retrieved.",
                previous_due_at_utc=existing_history.previous_due_at_utc,
                next_due_at_utc=next_due_utc,
                next_due_at_local=next_due_utc.astimezone(student_tz),
                previous_stability=existing_history.previous_stability,
                updated_stability=existing_history.updated_stability,
                previous_difficulty=existing_history.previous_difficulty,
                updated_difficulty=existing_history.updated_difficulty,
                retrievability=r,
                updated_bkt_mastery=current_p,
                is_idempotent_duplicate=True,
                review_timestamp_utc=existing_history.review_timestamp_utc,
            )

        # 2. Validate Question
        question = db.query(Question).filter(Question.id == request.question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID {request.question_id} not found.",
            )
        if question.concept_id != concept_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {request.question_id} belongs to concept {question.concept_id}, not {concept_id}.",
            )

        # 3. Evaluate correctness
        user_ans = request.response_text.strip()
        correct_ans = question.correct_answer.strip()
        is_correct = False

        if question.question_type == QuestionType.MCQ:
            is_correct = user_ans.upper() == correct_ans.upper()
        elif question.question_type == QuestionType.NUMERIC:
            try:
                is_correct = abs(float(user_ans) - float(correct_ans)) < 1e-4
            except ValueError:
                is_correct = user_ans.lower() == correct_ans.lower()
        else:
            is_correct = user_ans.lower() == correct_ans.lower()

        # 4. Enforce Rating Policy
        is_rating_valid, rating_msg = ReviewRatingService.validate_rating(
            rating=request.rating,
            is_correct=is_correct,
            is_partially_correct=False,
            is_unclear=False,
        )
        if not is_rating_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=rating_msg,
            )

        # 5. Retrieve or enroll student's ConceptReviewState
        review_state = ReviewStateService.get_review_state(db, student_id, concept_id)
        if not review_state:
            review_state = ReviewStateService.enroll_concept(
                db, student_id, concept_id, ignore_daily_limit=True
            )

        # 6. Execute BKT update (in separate, distinct learner model service)
        evidence_in = EvidenceSubmissionRequest(
            concept_id=concept_id,
            is_correct=is_correct,
            evidence_id=f"rev_ev_{idempotency_key}",
        )
        bkt_res = LearnerModelService.record_learning_evidence(
            db=db,
            student_id=student_id,
            concept_id=concept_id,
            evidence_in=evidence_in,
        )

        # 7. Execute official FSRS update
        scheduler = FSRSConfigurationService.get_scheduler_for_student(db, student_id)
        card = ReviewStateService.restore_card(review_state)
        now_utc = datetime.now(timezone.utc)

        prev_due_utc = review_state.due_at_utc
        if prev_due_utc.tzinfo is None:
            prev_due_utc = prev_due_utc.replace(tzinfo=timezone.utc)

        prev_stability = review_state.stability
        prev_difficulty = review_state.difficulty
        retrievability_before = FSRSService.get_retrievability(scheduler, card, now_utc)

        updated_card, review_log = FSRSService.review_card(
            scheduler=scheduler,
            card=card,
            rating=request.rating,
            review_datetime=now_utc,
        )

        # 8. Persist updated card state
        ReviewStateService.update_card_state(
            db=db,
            review_state=review_state,
            updated_card=updated_card,
            rating=request.rating,
            log=review_log,
        )

        # 9. Persist immutable ReviewHistory
        history_rec, _ = ReviewHistoryService.record_review(
            db=db,
            student_id=student_id,
            concept_id=concept_id,
            idempotency_key=idempotency_key,
            rating=request.rating,
            answer_correctness=is_correct,
            previous_due_at_utc=prev_due_utc,
            next_due_at_utc=updated_card.due,
            previous_stability=prev_stability,
            updated_stability=float(updated_card.stability),
            previous_difficulty=prev_difficulty,
            updated_difficulty=float(updated_card.difficulty),
            retrievability_before=retrievability_before,
            review_log=review_log,
            question_id=question.id,
            response_id=request.response_id,
            evidence_id=f"rev_ev_{idempotency_key}",
        )

        # 10. Commit all updates together in one atomic transaction
        db.commit()
        db.refresh(review_state)

        next_due_utc = updated_card.due
        if next_due_utc.tzinfo is None:
            next_due_utc = next_due_utc.replace(tzinfo=timezone.utc)

        current_retrievability = FSRSService.get_retrievability(scheduler, updated_card, now_utc)

        return CompleteRevisionResponse(
            idempotency_key=idempotency_key,
            concept_id=concept_id,
            concept_name=concept.name,
            rating=request.rating,
            rating_name=ReviewRatingService.get_rating_name(request.rating),
            answer_correctness=is_correct,
            rating_valid=True,
            rating_message=rating_msg,
            previous_due_at_utc=prev_due_utc,
            next_due_at_utc=next_due_utc,
            next_due_at_local=next_due_utc.astimezone(student_tz),
            previous_stability=prev_stability,
            updated_stability=review_state.stability,
            previous_difficulty=prev_difficulty,
            updated_difficulty=review_state.difficulty,
            retrievability=current_retrievability,
            updated_bkt_mastery=bkt_res.updated_mastery,
            is_idempotent_duplicate=False,
            review_timestamp_utc=history_rec.review_timestamp_utc,
        )
