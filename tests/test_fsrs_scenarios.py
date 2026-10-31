import time
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from fsrs import Rating

from app.models.assessment import Question, QuestionType
from app.models.fsrs_review import ConceptReviewState
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.user import User
from app.schemas.assessment import ResponseSubmit
from app.schemas.fsrs_review import RevisionStatusEnum
from app.services.assessment_service import AssessmentService
from app.services.fsrs_service import FSRSService
from app.services.review_state_service import ReviewStateService
from app.services.revision_queue_service import RevisionQueueService
from app.services.revision_service import RevisionService


@pytest.fixture
def scenario_syllabus(db_session: Session, teacher_user: User):
    subj = Subject(name="Physics", code="PHY-SCEN", description="Physics Scenarios")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    chap = Chapter(subject_id=subj.id, title="Thermodynamics", chapter_number=1, description="Heat & Work")
    db_session.add(chap)
    db_session.commit()
    db_session.refresh(chap)

    concepts = []
    questions = []
    for i in range(1, 4):
        c = Concept(
            concept_code=f"PHY-THERMO-{i:03d}",
            subject_id=subj.id,
            chapter_id=chap.id,
            name=f"Thermo Law #{i}",
            description=f"Thermodynamic law {i}",
            difficulty_level=DifficultyLevel.BEGINNER,
        )
        db_session.add(c)
        concepts.append(c)

    db_session.commit()
    for c in concepts:
        db_session.refresh(c)
        q = Question(
            concept_id=c.id,
            question_type=QuestionType.MCQ,
            question_text=f"Question regarding {c.name}?",
            question_options=[{"id": "A", "text": "Correct Law Statement"}, {"id": "B", "text": "Incorrect"}],
            correct_answer="A",
            evaluation_rubric={"explanation": f"Explanation for {c.name}"},
            created_by_id=teacher_user.id,
        )
        db_session.add(q)
        questions.append(q)

    db_session.commit()
    for q in questions:
        db_session.refresh(q)

    return subj, chap, concepts, questions


class TestFSRSScenarios:
    """
    End-to-End Scenarios A-E simulating complete real-world student lifecycles
    plus performance profiling.
    """

    def test_scenario_a_first_concept_enrollment(
        self, student_client: TestClient, db_session: Session, student_user: User, scenario_syllabus
    ):
        """
        Scenario A: First concept enrollment
        Student completes an eligible learning activity (first practice answer).
        Concept becomes enrolled in spaced repetition.
        FSRS state is created.
        Concept enters the new review queue.
        """
        _, _, concepts, questions = scenario_syllabus
        c1 = concepts[0]
        q1 = questions[0]

        # 1. Student answers practice question
        submit_in = ResponseSubmit(
            question_id=q1.id,
            response_text="A",
            confidence_score=0.9,
            time_spent_ms=1200,
        )
        AssessmentService.evaluate_and_record_response(db_session, student_user.id, submit_in)

        # 2. Check eligibility & enroll
        eligible, msg = ReviewStateService.is_concept_eligible_for_enrollment(db_session, student_user.id, c1.id)
        assert eligible is True

        state = ReviewStateService.enroll_concept(db_session, student_user.id, c1.id)
        assert state is not None
        assert state.concept_id == c1.id
        assert state.total_reviews == 0

        # 3. Queue shows concept under NEW status
        q_resp = student_client.get("/api/v1/revisions/queue")
        assert q_resp.status_code == 200
        items = q_resp.json()["items"]
        assert len(items) == 1
        assert items[0]["concept_id"] == c1.id
        assert items[0]["status"] == RevisionStatusEnum.NEW.value

    def test_scenario_b_due_revision_flow(
        self, student_client: TestClient, db_session: Session, student_user: User, scenario_syllabus
    ):
        """
        Scenario B: Due revision
        Student opens revision queue.
        A due concept is displayed.
        Student starts a revision session.
        Student submits an answer.
        Student provides a recall rating (Good).
        FSRS updates stability & next due date.
        """
        _, _, concepts, questions = scenario_syllabus
        c1 = concepts[0]
        q1 = questions[0]

        # Enroll and simulate past review that has now become due
        state = ReviewStateService.enroll_concept(db_session, student_user.id, c1.id, ignore_daily_limit=True)
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        past_time = datetime.now(timezone.utc) - timedelta(days=2)
        card, log = FSRSService.review_card(scheduler, ReviewStateService.restore_card(state), Rating.Good, review_datetime=past_time)
        ReviewStateService.update_card_state(db_session, state, card, Rating.Good.value, log)
        state.due_at_utc = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        # 1. Queue displays concept
        q_resp = student_client.get("/api/v1/revisions/queue")
        assert q_resp.status_code == 200
        items = q_resp.json()["items"]
        assert len(items) == 1

        # 2. Student starts revision session
        start_resp = student_client.post(f"/api/v1/revisions/{c1.id}/start")
        assert start_resp.status_code == 200
        start_data = start_resp.json()
        assert start_data["concept_id"] == c1.id
        assert start_data["question_id"] == q1.id

        # 3. Student completes review with answer and rating 'Good' (3)
        complete_payload = {
            "question_id": q1.id,
            "response_text": "A",
            "rating": 3,
            "idempotency_key": "scen_b_review_01",
        }
        comp_resp = student_client.post(f"/api/v1/revisions/{c1.id}/complete", json=complete_payload)
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        assert comp_data["answer_correctness"] is True
        assert comp_data["rating"] == 3
        assert comp_data["updated_stability"] > 0.0
        assert comp_data["next_due_at_utc"] is not None

        # 4. State is updated in DB
        db_session.refresh(state)
        assert state.total_reviews == 2
        assert state.lapses == 0

    def test_scenario_c_forgotten_concept_lapse_and_relearning(
        self, student_client: TestClient, db_session: Session, student_user: User, scenario_syllabus
    ):
        """
        Scenario C: Forgotten concept
        Student fails to recall a due concept (answers incorrectly, rating Again).
        FSRS schedules relearning interval.
        Lapses count increments.
        """
        _, _, concepts, questions = scenario_syllabus
        c1 = concepts[0]
        q1 = questions[0]

        state = ReviewStateService.enroll_concept(db_session, student_user.id, c1.id, ignore_daily_limit=True)
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        card, log = FSRSService.review_card(scheduler, ReviewStateService.restore_card(state), Rating.Easy)
        ReviewStateService.update_card_state(db_session, state, card, Rating.Easy.value, log)
        db_session.commit()

        # Submit review failure: incorrect answer + Rating Again (1)
        complete_payload = {
            "question_id": q1.id,
            "response_text": "B",  # Incorrect
            "rating": 1,           # Again
            "idempotency_key": "scen_c_lapse_01",
        }
        comp_resp = student_client.post(f"/api/v1/revisions/{c1.id}/complete", json=complete_payload)
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        assert comp_data["answer_correctness"] is False
        assert comp_data["rating"] == 1

        db_session.refresh(state)
        assert state.lapses == 1
        assert state.state == 3  # State.Relearning

    def test_scenario_d_strong_recall_easy(
        self, student_client: TestClient, db_session: Session, student_user: User, scenario_syllabus
    ):
        """
        Scenario D: Strong recall
        Student recalls easily with Rating Easy (4).
        FSRS assigns larger stability and longer next interval.
        """
        _, _, concepts, questions = scenario_syllabus
        c1 = concepts[0]
        q1 = questions[0]

        state = ReviewStateService.enroll_concept(db_session, student_user.id, c1.id, ignore_daily_limit=True)

        complete_payload = {
            "question_id": q1.id,
            "response_text": "A",
            "rating": 4,  # Easy
            "idempotency_key": "scen_d_easy_01",
        }
        comp_resp = student_client.post(f"/api/v1/revisions/{c1.id}/complete", json=complete_payload)
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        assert comp_data["rating"] == 4
        # High stability for Easy
        assert comp_data["updated_stability"] >= 8.0

        db_session.refresh(state)
        assert state.state == 2  # State.Review

    def test_scenario_e_no_due_concepts_empty_and_upcoming(
        self, student_client: TestClient, db_session: Session, student_user: User, scenario_syllabus
    ):
        """
        Scenario E: No due concepts
        When all cards are scheduled in the future, queue due filter returns empty,
        while summary and upcoming filter return future cards.
        """
        _, _, concepts, questions = scenario_syllabus
        c1 = concepts[0]

        state = ReviewStateService.enroll_concept(db_session, student_user.id, c1.id, ignore_daily_limit=True)
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        past_time = datetime.now(timezone.utc) - timedelta(days=2)
        card, log = FSRSService.review_card(scheduler, ReviewStateService.restore_card(state), Rating.Easy, review_datetime=past_time)

        ReviewStateService.update_card_state(db_session, state, card, Rating.Easy.value, log)
        # Schedule far in the future
        state.due_at_utc = datetime.now(timezone.utc) + timedelta(days=14)
        db_session.commit()


        # Query due today -> empty
        r_due = student_client.get("/api/v1/revisions/queue?status=DUE_TODAY")
        assert r_due.status_code == 200
        assert r_due.json()["total_count"] == 0

        # Query upcoming -> shows card
        r_up = student_client.get("/api/v1/revisions/queue?status=UPCOMING")
        assert r_up.status_code == 200
        assert r_up.json()["total_count"] == 1

        # Summary shows upcoming=1, due_today=0
        r_sum = student_client.get("/api/v1/revisions/summary")
        assert r_sum.status_code == 200
        assert r_sum.json()["due_today_count"] == 0
        assert r_sum.json()["upcoming_count"] == 1

    def test_performance_measurements(
        self, student_client: TestClient, db_session: Session, student_user: User, scenario_syllabus
    ):
        """
        Measures exact latencies for:
        - FSRS scheduler algorithm execution (engine layer, microseconds)
        - DB read time
        - DB write time
        - Revision queue generation latency
        - Full API endpoint latency for review completion
        """
        _, _, concepts, questions = scenario_syllabus
        c1 = concepts[0]
        q1 = questions[0]
        scheduler = FSRSService.get_default_scheduler(enable_fuzzing=False)
        card = FSRSService.create_new_card()

        # 1. Pure FSRS algorithm execution time (100 iterations)
        t0 = time.perf_counter()
        for _ in range(100):
            _c, _l = FSRSService.review_card(scheduler, card, Rating.Good)
        fsrs_engine_avg_ms = ((time.perf_counter() - t0) / 100) * 1000.0

        # 2. DB write time (enrollment)
        t0 = time.perf_counter()
        state = ReviewStateService.enroll_concept(db_session, student_user.id, c1.id, ignore_daily_limit=True)
        db_write_ms = (time.perf_counter() - t0) * 1000.0

        # 3. DB read time
        t0 = time.perf_counter()
        _s = ReviewStateService.get_review_state(db_session, student_user.id, c1.id)
        db_read_ms = (time.perf_counter() - t0) * 1000.0

        # 4. Revision queue generation latency
        t0 = time.perf_counter()
        _q = RevisionQueueService.get_revision_queue(db_session, student_user.id)
        queue_gen_ms = (time.perf_counter() - t0) * 1000.0

        # 5. Full REST API review completion latency
        payload = {
            "question_id": q1.id,
            "response_text": "A",
            "rating": 3,
            "idempotency_key": "perf_test_review_key",
        }
        t0 = time.perf_counter()
        api_resp = student_client.post(f"/api/v1/revisions/{c1.id}/complete", json=payload)
        api_latency_ms = (time.perf_counter() - t0) * 1000.0

        assert api_resp.status_code == 200

        print(f"\n--- FSRS PERFORMANCE BENCHMARKS ---")
        print(f"FSRS Algorithm Engine Latency (per review): {fsrs_engine_avg_ms:.4f} ms")
        print(f"Database Read Latency:                     {db_read_ms:.4f} ms")
        print(f"Database Write Latency:                    {db_write_ms:.4f} ms")
        print(f"Revision Queue Generation Latency:         {queue_gen_ms:.4f} ms")
        print(f"Complete Revision API Latency:             {api_latency_ms:.4f} ms")

        # FSRS engine execution must be deterministic and sub-millisecond
        assert fsrs_engine_avg_ms < 1.0, f"FSRS calculation took {fsrs_engine_avg_ms} ms, expected < 1 ms"
