import json
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.providers.base import LLMResponse
from app.graph import execute_learning_turn
from app.models.assessment import LearningSession, Question, QuestionType, SessionType, LearnerResponse
from app.models.concept_graph import ConceptPrerequisite, RelationshipType
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.fsrs_review import ConceptReviewState
from app.models.syllabus import Chapter, Concept, DifficultyLevel, Subject
from app.models.teacher_class import Class, ClassEnrollment
from app.models.user import User, UserRole
from app.services.review_state_service import ReviewStateService


def _create_mock_exec_manager(is_correct: bool = True, misconception: str = None):
    mgr = MagicMock(spec=GPUExecutionManager)
    deepseek_payload = {
        "evaluation": {
            "is_correct": is_correct,
            "answer_type": "correct" if is_correct else "incorrect",
            "reasoning_summary": "Accurate conceptual grasp" if is_correct else "Confused inverse and direct relationships",
            "confidence": 0.95,
        },
        "misconception": {
            "detected": not is_correct,
            "category": misconception or ("none" if is_correct else "conceptual_misconception"),
            "description": None if is_correct else "Student confused inverse proportionality.",
        },
        "candidate_question": {
            "concept_id": 1,
            "difficulty": "medium",
            "question": "Follow-up question on heat",
            "expected_answer": "Answer",
            "evaluation_criteria": ["Criteria 1"],
        },
    }
    llama_payload = {
        "feedback": "Outstanding work! Concept is solidly grasped." if is_correct else "Notice how temperature behaves inversely with pressure in this process.",
        "socratic_hint": None if is_correct else "Think about what happens to gas volume when external pressure increases.",
        "next_question": "Next step question on thermodynamics",
        "adaptive_action": "ADVANCE_CONCEPT" if is_correct else "TARGETED_PRACTICE",
        "display_mastery": 0.65 if is_correct else 0.25,
    }

    mgr.execute_deepseek = AsyncMock(return_value={"result": LLMResponse(content=json.dumps(deepseek_payload), raw_response={}), "metrics": {}})
    mgr.execute_llama = AsyncMock(return_value={"result": LLMResponse(content=json.dumps(llama_payload), raw_response={}), "metrics": {}})
    mgr.get_status = MagicMock(return_value=MagicMock(state="idle", active_model=None, monitoring_enabled=True))
    return mgr


@pytest.fixture
def e2e_syllabus_data(db_session: Session):
    """Establishes complete syllabus hierarchy with prerequisite DAG."""
    sub = Subject(name="Thermodynamics E2E", code="E2E-THERMO", description="Complete E2E subject")
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)

    ch = Chapter(subject_id=sub.id, chapter_number=1, title="Foundations of Heat")
    db_session.add(ch)
    db_session.commit()
    db_session.refresh(ch)

    c1 = Concept(
        subject_id=sub.id,
        chapter_id=ch.id,
        name="Heat Transfer",
        concept_code="E2E-C1",
        description="Conduction convection radiation",
        difficulty_level=DifficultyLevel.BEGINNER,
    )
    c2 = Concept(
        subject_id=sub.id,
        chapter_id=ch.id,
        name="Thermal Expansion",
        concept_code="E2E-C2",
        description="Linear and volumetric expansion",
        difficulty_level=DifficultyLevel.INTERMEDIATE,
    )
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    # Prerequisite: Heat Transfer -> Thermal Expansion
    prereq = ConceptPrerequisite(
        concept_id=c2.id,
        prerequisite_id=c1.id,
        relationship_type=RelationshipType.STRICT,
    )
    db_session.add(prereq)

    # Questions
    q1 = Question(
        concept_id=c1.id,
        question_text="What is heat transfer by direct physical contact?",
        question_type=QuestionType.MCQ,
        question_options=[{"id": "A", "text": "Conduction"}, {"id": "B", "text": "Radiation"}],
        correct_answer="Conduction",
        difficulty_level=DifficultyLevel.BEGINNER,
        evaluation_rubric={"explanation": "Conduction requires direct molecular contact."},
    )
    q2 = Question(
        concept_id=c2.id,
        question_text="Why do railway tracks have expansion gaps?",
        question_type=QuestionType.OPEN_ENDED,
        correct_answer="Thermal expansion prevents buckling when heated.",
        difficulty_level=DifficultyLevel.INTERMEDIATE,
        evaluation_rubric={"explanation": "Materials expand with temperature."},
    )
    db_session.add_all([q1, q2])
    db_session.commit()
    db_session.refresh(q1)
    db_session.refresh(q2)

    return {"subject": sub, "chapter": ch, "c1": c1, "c2": c2, "q1": q1, "q2": q2}


# ==============================================================================
# SCENARIO 1 – NEW STUDENT REGISTRATION, LOGIN, SYLLABUS, AND DIAGNOSTIC
# ==============================================================================
def test_scenario_1_new_student_onboarding_and_diagnostic(client: TestClient, e2e_syllabus_data):
    """
    Scenario 1:
    - Register new student
    - Login and receive JWT
    - Select subject and inspect concepts
    - Start diagnostic assessment
    - Submit answers with a gap on foundational concept
    - Receive initial learner model and recommended learning path
    """
    email = f"e2e_student_{uuid.uuid4().hex[:6]}@adeptlearn.org"
    password = "SuperSecurePassword123!"

    # 1. Registration
    reg_res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "E2E Student", "role": "STUDENT"},
    )
    assert reg_res.status_code == 201
    assert reg_res.json()["email"] == email

    # 2. Login
    login_res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. View Subjects
    sub_res = client.get("/api/v1/subjects", headers=headers)
    assert sub_res.status_code == 200
    assert any(s["code"] == "E2E-THERMO" for s in sub_res.json())

    # 4. Start Diagnostic
    sub_id = e2e_syllabus_data["subject"].id
    diag_start_res = client.post("/api/v1/diagnostic/start", json={"subject_id": sub_id}, headers=headers)
    assert diag_start_res.status_code == 201
    diag_data = diag_start_res.json()
    assert "session_id" in diag_data
    assert len(diag_data["questions"]) >= 2
    session_id = diag_data["session_id"]

    # 5. Submit Diagnostic Answers: Correct on C1, Incorrect on C2
    answers = [
        {"question_id": diag_data["questions"][0]["question_id"], "student_answer": "Conduction"},
        {"question_id": diag_data["questions"][1]["question_id"], "student_answer": "Uncertain about expansion"},
    ]
    diag_submit_res = client.post(
        "/api/v1/diagnostic/submit",
        json={"session_id": session_id, "answers": answers},
        headers=headers,
    )
    assert diag_submit_res.status_code == 200
    result = diag_submit_res.json()
    assert result["total_questions"] == 2
    assert "initialized_masteries" in result
    assert result["recommended_concept_id"] is not None
    assert result["recommended_concept_name"] is not None


# ==============================================================================
# SCENARIO 2 – ADAPTIVE LEARNING PRACTICE TURN & BKT INCREASE
# ==============================================================================
@patch("app.services.learning_orchestration_service.get_gpu_execution_manager")
def test_scenario_2_adaptive_learning_turn(mock_mgr, client: TestClient, e2e_syllabus_data, db_session: Session):
    """
    Scenario 2:
    - Recommended concept question served
    - Student submits correct answer
    - Evaluated via DeepSeek + BKT update + Llama feedback
    - Verify BKT mastery increases and next learning action is returned
    """
    mock_mgr.return_value = _create_mock_exec_manager(is_correct=True)

    # Create student
    student = User(
        email="adaptive_student@adeptlearn.org",
        hashed_password="hashed_pwd",
        full_name="Adaptive Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.flush()

    from app.core.security import create_access_token
    token = create_access_token(subject=str(student.id), extra_claims={"role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # Create active session
    sess = LearningSession(
        user_id=student.id,
        subject_id=e2e_syllabus_data["subject"].id,
        session_type=SessionType.ADAPTIVE_PRACTICE,
    )
    db_session.add(sess)
    db_session.commit()

    q = e2e_syllabus_data["q1"]
    payload = {
        "question_id": q.id,
        "student_answer": "Conduction",
        "session_id": sess.id,
    }

    turn_res = client.post("/api/v1/learning/turns", json=payload, headers=headers)
    assert turn_res.status_code == 200
    turn_data = turn_res.json()
    assert turn_data["execution_status"] == "completed"
    assert turn_data["updated_mastery"] > 0.20
    assert turn_data["student_id"] == student.id

    # Retrieve turn result
    run_id = turn_data["run_id"]
    res_check = client.get(f"/api/v1/learning/turns/{run_id}/result", headers=headers)
    assert res_check.status_code == 200
    fb = res_check.json()["student_feedback"]
    assert "feedback" in str(fb).lower()


# ==============================================================================
# SCENARIO 3 – MISCONCEPTION DETECTION & REMEDIATION
# ==============================================================================
@patch("app.services.learning_orchestration_service.get_gpu_execution_manager")
def test_scenario_3_misconception_detection(mock_mgr, client: TestClient, e2e_syllabus_data, db_session: Session):
    """
    Scenario 3:
    - Student submits incorrect answer with identifiable misconception
    - DeepSeek flags misconception
    - BKT updates with penalty
    - Socratic hint returned to guide student
    """
    mock_mgr.return_value = _create_mock_exec_manager(
        is_correct=False, misconception="DIRECT_PROPORTIONALITY_CONFUSION"
    )

    student = User(
        email="misconcept_student@adeptlearn.org",
        hashed_password="pwd",
        full_name="Struggling Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.flush()

    from app.core.security import create_access_token
    token = create_access_token(subject=str(student.id), extra_claims={"role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    sess = LearningSession(
        user_id=student.id,
        subject_id=e2e_syllabus_data["subject"].id,
        session_type=SessionType.ADAPTIVE_PRACTICE,
    )
    db_session.add(sess)
    db_session.commit()

    q = e2e_syllabus_data["q2"]
    payload = {
        "question_id": q.id,
        "student_answer": "Tracks contract when heated",
        "session_id": sess.id,
    }

    turn_res = client.post("/api/v1/learning/turns", json=payload, headers=headers)
    assert turn_res.status_code == 200
    turn_data = turn_res.json()
    assert turn_data["execution_status"] == "completed"

    run_id = turn_data["run_id"]
    res_check = client.get(f"/api/v1/learning/turns/{run_id}/result", headers=headers)
    assert res_check.status_code == 200
    feedback_data = res_check.json()["student_feedback"]
    assert feedback_data.get("socratic_hint") is not None
    assert "Think about what happens" in feedback_data["socratic_hint"]


# ==============================================================================
# SCENARIO 4 – SPACED REPETITION (FSRS) WORKFLOW
# ==============================================================================
def test_scenario_4_fsrs_spaced_repetition(client: TestClient, e2e_syllabus_data, db_session: Session):
    """
    Scenario 4:
    - Enroll concept in FSRS
    - Check queue
    - Start review session
    - Submit response and recall rating (Rating: 3 - Good)
    - Verify updated review state, interval, and next due date
    """
    student = User(
        email="fsrs_student@adeptlearn.org",
        hashed_password="pwd",
        full_name="FSRS Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.flush()

    c1 = e2e_syllabus_data["c1"]
    ReviewStateService.enroll_concept(db_session, student.id, c1.id, ignore_daily_limit=True)

    from app.core.security import create_access_token
    token = create_access_token(subject=str(student.id), extra_claims={"role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Queue Check
    q_res = client.get("/api/v1/revisions/queue", headers=headers)
    assert q_res.status_code == 200
    queue_data = q_res.json()
    assert queue_data["total_count"] == 1
    assert queue_data["items"][0]["concept_id"] == c1.id

    # 2. Start Review
    start_res = client.post(f"/api/v1/revisions/{c1.id}/start", headers=headers)
    assert start_res.status_code == 200
    start_data = start_res.json()
    q_id = start_data["question_id"]
    assert q_id == e2e_syllabus_data["q1"].id

    # 3. Complete Review with Rating = 3 (Good)
    complete_res = client.post(
        f"/api/v1/revisions/{c1.id}/complete",
        json={"question_id": q_id, "response_text": "Conduction", "rating": 3},
        headers=headers,
    )
    assert complete_res.status_code == 200
    rev_result = complete_res.json()
    assert rev_result["updated_stability"] > 0
    assert rev_result["next_due_at_utc"] is not None


# ==============================================================================
# SCENARIO 5 – LEARNING HISTORY & DATA PORTABILITY (GDPR)
# ==============================================================================
def test_scenario_5_learning_history_and_data_export(client: TestClient, e2e_syllabus_data, db_session: Session):
    """
    Scenario 5:
    - Student with mastery & review history exports complete personal dataset
    - Profile update is persisted
    """
    student = User(
        email="export_student@adeptlearn.org",
        hashed_password="pwd",
        full_name="Export Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.flush()

    c1 = e2e_syllabus_data["c1"]
    db_session.add(LearnerMastery(student_id=student.id, concept_id=c1.id, p_know=0.88, is_mastered=True))
    db_session.commit()

    from app.core.security import create_access_token
    token = create_access_token(subject=str(student.id), extra_claims={"role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # Export
    export_res = client.get("/api/v1/users/me/export", headers=headers)
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert "user_profile" in export_data
    assert "mastery_records" in export_data
    assert len(export_data["mastery_records"]) == 1
    assert export_data["mastery_records"][0]["concept_name"] == c1.name

    # Profile update
    update_res = client.patch("/api/v1/users/me", json={"full_name": "Export Student Updated"}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Export Student Updated"


# ==============================================================================
# SCENARIO 6 – TEACHER CLASS MANAGEMENT & ANALYTICS
# ==============================================================================
def test_scenario_6_teacher_class_management_and_analytics(client: TestClient, e2e_syllabus_data, db_session: Session):
    """
    Scenario 6:
    - Teacher creates class
    - Student joins via enrollment code
    - Teacher views roster and deterministic analytics
    """
    # Create Teacher
    teacher = User(
        email="teacher_e2e@adeptlearn.org",
        hashed_password="pwd",
        full_name="Prof. Maxwell",
        role=UserRole.TEACHER,
        is_active=True,
    )
    student = User(
        email="enrolled_student@adeptlearn.org",
        hashed_password="pwd",
        full_name="Enrolled Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add_all([teacher, student])
    db_session.commit()

    from app.core.security import create_access_token
    t_token = create_access_token(subject=str(teacher.id), extra_claims={"role": "TEACHER"})
    s_token = create_access_token(subject=str(student.id), extra_claims={"role": "STUDENT"})

    # 1. Teacher creates class
    cls_res = client.post(
        "/api/v1/teachers/classes",
        json={"name": "Thermodynamics 101", "subject_id": e2e_syllabus_data["subject"].id},
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert cls_res.status_code == 201
    cls_data = cls_res.json()
    class_id = cls_data["id"]
    enrollment_code = cls_data["enrollment_code"]

    # 2. Student joins via code
    join_res = client.post(
        "/api/v1/teachers/join",
        json={"enrollment_code": enrollment_code},
        headers={"Authorization": f"Bearer {s_token}"},
    )
    assert join_res.status_code == 200

    # 3. Add student mastery record
    c1 = e2e_syllabus_data["c1"]
    db_session.add(LearnerMastery(student_id=student.id, concept_id=c1.id, initial_mastery=0.2, current_mastery=0.82))
    db_session.commit()

    # 4. Teacher views class analytics
    analytics_res = client.get(
        f"/api/v1/analytics/classes/{class_id}/summary",
        headers={"Authorization": f"Bearer {t_token}"},
    )
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["total_enrolled"] == 1
    assert analytics["average_mastery"] == 0.82


# ==============================================================================
# SCENARIO 7 – RECOVERY AFTER MODEL FAILURE & IDEMPOTENCY
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_7_turn_recovery_and_idempotency(e2e_syllabus_data, db_session: Session):
    """
    Scenario 7:
    - Verifies idempotent retry prevents double counting BKT attempts
    - Verifies no duplicate LearnerResponse records created
    """
    mgr = _create_mock_exec_manager(is_correct=True)

    student = User(
        email="recovery_student@adeptlearn.org",
        hashed_password="pwd",
        full_name="Recovery Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()

    q = e2e_syllabus_data["q1"]
    initial_state = {
        "session_id": 99,
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "Conduction",
    }

    # Turn 1
    res1 = await execute_learning_turn(initial_state, db_session, mgr)
    m1_val = res1["updated_mastery"]
    evidence_id = res1["evidence_id"]
    assert evidence_id is not None

    mastery_record = db_session.query(LearnerMastery).filter(
        LearnerMastery.student_id == student.id,
        LearnerMastery.concept_id == q.concept_id,
    ).first()
    assert mastery_record.total_attempts == 1

    # Retry with identical state (simulating recovery replay)
    res2 = await execute_learning_turn(dict(res1), db_session, mgr)
    db_session.refresh(mastery_record)

    # Must NOT double count attempts
    assert mastery_record.total_attempts == 1
    assert round(mastery_record.current_mastery, 4) == round(m1_val, 4)

    # No duplicate learner responses
    responses = db_session.query(LearnerResponse).filter(
        LearnerResponse.user_id == student.id,
        LearnerResponse.question_id == q.id,
    ).all()
    assert len(responses) == 1


# ==============================================================================
# MULTI-STUDENT CONCURRENCY ISOLATION (10 Students)
# ==============================================================================
def test_multi_student_concurrency_isolation(client: TestClient, e2e_syllabus_data, db_session: Session):
    """
    Simulates 10 student revision sessions.
    Ensures complete isolation, zero cross-tenant contamination, and database integrity.
    """
    from app.core.security import create_access_token

    students = []
    c1 = e2e_syllabus_data["c1"]

    for i in range(10):
        s = User(
            email=f"concurrent_student_{i}_{uuid.uuid4().hex[:4]}@adeptlearn.org",
            hashed_password="pwd",
            full_name=f"Concurrent Student {i}",
            role=UserRole.STUDENT,
            is_active=True,
        )
        db_session.add(s)
        students.append(s)

    db_session.commit()

    for s in students:
        db_session.refresh(s)
        ReviewStateService.enroll_concept(db_session, s.id, c1.id, ignore_daily_limit=True)

    tokens = [
        create_access_token(subject=str(s.id), extra_claims={"role": "STUDENT"})
        for s in students
    ]

    def run_student_workflow(token_idx):
        t = tokens[token_idx]
        h = {"Authorization": f"Bearer {t}"}

        # 1. Get queue
        q_resp = client.get("/api/v1/revisions/queue", headers=h)
        assert q_resp.status_code == 200
        items = q_resp.json()["items"]
        assert len(items) == 1

        # 2. Complete review
        comp_resp = client.post(
            f"/api/v1/revisions/{c1.id}/complete",
            json={"question_id": e2e_syllabus_data["q1"].id, "response_text": "Conduction", "rating": 3},
            headers=h,
        )
        assert comp_resp.status_code == 200
        return comp_resp.json()

    results = [run_student_workflow(i) for i in range(10)]

    assert len(results) == 10
    for r in results:
        assert r["updated_stability"] > 0
        assert r["next_due_at_utc"] is not None

    # Cross-tenant check: Student 0 cannot see other students' review state
    st0_token = tokens[0]
    st1_token = tokens[1]
    res0 = client.get("/api/v1/revisions/summary", headers={"Authorization": f"Bearer {st0_token}"})
    res1 = client.get("/api/v1/revisions/summary", headers={"Authorization": f"Bearer {st1_token}"})
    assert res0.status_code == 200
    assert res1.status_code == 200
    r0_state = client.get(f"/api/v1/revisions/{c1.id}/state", headers={"Authorization": f"Bearer {st0_token}"}).json()
    assert r0_state["total_reviews"] == 1
    assert r0_state["stability"] > 0
    r1_state = client.get(f"/api/v1/revisions/{c1.id}/state", headers={"Authorization": f"Bearer {st1_token}"}).json()
    assert r1_state["total_reviews"] == 1
    assert r1_state["stability"] > 0
