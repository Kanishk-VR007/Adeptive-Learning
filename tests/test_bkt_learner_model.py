import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.syllabus import DifficultyLevel
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
def bkt_setup(teacher_client: TestClient, db_session: Session):
    """Create test syllabus concepts and 2 isolated student users."""
    # 1. Create Subject & Chapter
    s = teacher_client.post("/api/v1/subjects", json={"code": "MATH301", "name": "Calculus II"}).json()
    ch = teacher_client.post("/api/v1/chapters", json={"subject_id": s["id"], "chapter_number": 1, "title": "Series"}).json()

    # 2. Create Concepts
    c1 = teacher_client.post("/api/v1/concepts", json={
        "concept_code": "SER_CONV_01",
        "subject_id": s["id"],
        "chapter_id": ch["id"],
        "name": "Convergence Tests",
        "description": "Ratio and root convergence tests",
        "difficulty_level": DifficultyLevel.INTERMEDIATE.value,
        "learning_objectives": ["Apply ratio test to geometric series"]
    }).json()

    c2 = teacher_client.post("/api/v1/concepts", json={
        "concept_code": "SER_TAY_01",
        "subject_id": s["id"],
        "chapter_id": ch["id"],
        "name": "Taylor Series",
        "description": "Taylor polynomials and Maclaurin expansions",
        "difficulty_level": DifficultyLevel.ADVANCED.value,
        "learning_objectives": ["Compute Taylor polynomials"]
    }).json()

    # 3. Create Student A
    student_a = User(
        email="student_a@adaptive.edu",
        hashed_password=get_password_hash("passwordA"),
        full_name="Student Alice",
        role=UserRole.STUDENT,
        is_active=True
    )
    # 4. Create Student B
    student_b = User(
        email="student_b@adaptive.edu",
        hashed_password=get_password_hash("passwordB"),
        full_name="Student Bob",
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(student_a)
    db_session.add(student_b)
    db_session.commit()
    db_session.refresh(student_a)
    db_session.refresh(student_b)

    token_a = create_access_token(subject=student_a.id, extra_claims={"role": "STUDENT"})
    token_b = create_access_token(subject=student_b.id, extra_claims={"role": "STUDENT"})

    return {
        "subject": s,
        "chapter": ch,
        "concept_1": c1,
        "concept_2": c2,
        "student_a": student_a,
        "student_b": student_b,
        "token_a": token_a,
        "token_b": token_b
    }


def test_first_evidence_initialization_and_update(client: TestClient, bkt_setup):
    """Phase 4 & 5: First answer submission properly initializes P(L0)=0.20 and updates BKT."""
    c1 = bkt_setup["concept_1"]
    token = bkt_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit correct answer for the first time
    evidence_id = f"ev_test_{uuid.uuid4().hex}"
    res = client.post(
        f"/api/v1/learners/me/concepts/{c1['id']}/evidence",
        json={"is_correct": True, "evidence_id": evidence_id},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["evidence_id"] == evidence_id
    assert data["is_correct"] is True
    assert data["previous_mastery"] == 0.20
    # Expected: P(L | 1) = 0.5294..., P(L_next) = 0.5765...
    assert 0.57 <= data["updated_mastery"] <= 0.58
    assert data["total_attempts"] == 1
    assert data["correct_attempts"] == 1
    assert data["incorrect_attempts"] == 0
    assert data["is_idempotent_duplicate"] is False
    assert data["mastery_classification"] in ["Developing Understanding", "Good Understanding"]


def test_idempotent_evidence_resubmission(client: TestClient, bkt_setup):
    """Phase 4 & 5: Submitting identical evidence_id returns existing state without double-updating."""
    c1 = bkt_setup["concept_1"]
    token = bkt_setup["token_a"]
    headers = {"Authorization": f"Bearer {token}"}
    evidence_id = f"ev_fixed_{uuid.uuid4().hex}"

    # First submission
    res1 = client.post(
        f"/api/v1/learners/me/concepts/{c1['id']}/evidence",
        json={"is_correct": True, "evidence_id": evidence_id},
        headers=headers
    )
    assert res1.status_code == 200
    assert res1.json()["total_attempts"] == 1
    mastery_first = res1.json()["updated_mastery"]

    # Re-submit with SAME evidence_id
    res2 = client.post(
        f"/api/v1/learners/me/concepts/{c1['id']}/evidence",
        json={"is_correct": True, "evidence_id": evidence_id},
        headers=headers
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_idempotent_duplicate"] is True
    assert data2["total_attempts"] == 1
    assert data2["updated_mastery"] == mastery_first


def test_learner_isolation(client: TestClient, bkt_setup):
    """Phase 7: Student A's answers and knowledge states are completely isolated from Student B."""
    c1 = bkt_setup["concept_1"]
    token_a = bkt_setup["token_a"]
    token_b = bkt_setup["token_b"]

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Student A answers correctly 3 times
    for _ in range(3):
        client.post(
            f"/api/v1/learners/me/concepts/{c1['id']}/evidence",
            json={"is_correct": True},
            headers=headers_a
        )

    # Student B answers incorrectly 1 time
    client.post(
        f"/api/v1/learners/me/concepts/{c1['id']}/evidence",
        json={"is_correct": False},
        headers=headers_b
    )

    # Query Student A's mastery
    res_a = client.get(f"/api/v1/learners/me/mastery/{c1['id']}", headers=headers_a)
    assert res_a.status_code == 200
    mastery_a = res_a.json()
    assert mastery_a["total_attempts"] == 3
    assert mastery_a["correct_attempts"] == 3
    assert mastery_a["current_mastery"] > 0.80

    # Query Student B's mastery: must reflect ONLY Bob's single incorrect attempt
    res_b = client.get(f"/api/v1/learners/me/mastery/{c1['id']}", headers=headers_b)
    assert res_b.status_code == 200
    mastery_b = res_b.json()
    assert mastery_b["total_attempts"] == 1
    assert mastery_b["correct_attempts"] == 0
    assert mastery_b["incorrect_attempts"] == 1
    assert mastery_b["current_mastery"] < 0.20

    # Verify history isolation: Student B cannot see Student A's learning history
    history_b = client.get("/api/v1/learners/me/history", headers=headers_b).json()
    assert len(history_b) == 1
    assert history_b[0]["is_correct"] is False


def test_student_cannot_view_other_student_mastery_directly(client: TestClient, bkt_setup):
    """Students cannot access teacher endpoints for specific students."""
    student_b_id = bkt_setup["student_b"].id
    headers_a = {"Authorization": f"Bearer {bkt_setup['token_a']}"}

    res = client.get(f"/api/v1/learners/{student_b_id}/mastery", headers=headers_a)
    assert res.status_code == 403


def test_teacher_can_view_student_mastery_and_cohort_summary(client: TestClient, teacher_client: TestClient, bkt_setup):
    """Teachers have authorized access to student mastery profiles and concept cohort summaries."""
    c1 = bkt_setup["concept_1"]
    student_a_id = bkt_setup["student_a"].id
    headers_a = {"Authorization": f"Bearer {bkt_setup['token_a']}"}

    # Student A submits evidence
    client.post(
        f"/api/v1/learners/me/concepts/{c1['id']}/evidence",
        json={"is_correct": True},
        headers=headers_a
    )

    # Teacher inspects Student A
    teacher_res = teacher_client.get(f"/api/v1/learners/{student_a_id}/mastery")
    assert teacher_res.status_code == 200
    mastery_list = teacher_res.json()
    assert len(mastery_list) >= 1
    assert mastery_list[0]["student_id"] == student_a_id

    # Teacher inspects concept cohort summary
    cohort_res = teacher_client.get(f"/api/v1/learners/concepts/{c1['id']}/mastery-summary")
    assert cohort_res.status_code == 200
    summary = cohort_res.json()
    assert summary["concept_id"] == c1["id"]
    assert summary["total_students_attempted"] >= 1


def test_learning_history_immutability(client: TestClient, db_session: Session, bkt_setup):
    """LearningHistory records are immutable and track chronological progress."""
    c1 = bkt_setup["concept_1"]
    headers = {"Authorization": f"Bearer {bkt_setup['token_a']}"}

    # Send 2 attempts
    client.post(f"/api/v1/learners/me/concepts/{c1['id']}/evidence", json={"is_correct": True}, headers=headers)
    client.post(f"/api/v1/learners/me/concepts/{c1['id']}/evidence", json={"is_correct": False}, headers=headers)

    # Check history endpoint
    hist_res = client.get(f"/api/v1/learners/me/history/{c1['id']}", headers=headers)
    assert hist_res.status_code == 200
    records = hist_res.json()
    assert len(records) == 2
    # Chronological descending order (most recent first)
    assert records[0]["is_correct"] is False
    assert records[1]["is_correct"] is True


def test_bkt_parameter_override_hierarchy(client: TestClient, teacher_client: TestClient, bkt_setup):
    """Test custom concept BKT parameter override changes initial prior and learning rate."""
    c2 = bkt_setup["concept_2"]
    token_a = bkt_setup["token_a"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Teacher sets custom parameters for c2: P(L0)=0.40, P(T)=0.20
    override_res = teacher_client.post("/api/v1/learners/parameters/override", json={
        "concept_id": c2["id"],
        "p_l0": 0.40,
        "p_transit": 0.20,
        "p_guess": 0.15,
        "p_slip": 0.05
    })
    assert override_res.status_code == 201

    # Student A submits first answer to c2: initial mastery must be 0.40!
    ans_res = client.post(
        f"/api/v1/learners/me/concepts/{c2['id']}/evidence",
        json={"is_correct": True},
        headers=headers_a
    )
    assert ans_res.status_code == 200
    data = ans_res.json()
    assert data["previous_mastery"] == 0.40
    # Higher prior + lower slip leads to strong jump
    assert data["updated_mastery"] > 0.70


def test_unauthenticated_requests_rejected(client: TestClient, bkt_setup):
    """Requests without token or with invalid token return 401."""
    c1 = bkt_setup["concept_1"]
    # No auth
    assert client.get("/api/v1/learners/me/mastery").status_code == 401
    assert client.post(f"/api/v1/learners/me/concepts/{c1['id']}/evidence", json={"is_correct": True}).status_code == 401

    # Invalid auth
    bad_headers = {"Authorization": "Bearer badtoken123"}
    assert client.get("/api/v1/learners/me/mastery", headers=bad_headers).status_code == 401


def test_invalid_concept_not_found(client: TestClient, bkt_setup):
    """Submitting evidence for non-existent concept returns 404."""
    headers = {"Authorization": f"Bearer {bkt_setup['token_a']}"}
    res = client.post("/api/v1/learners/me/concepts/999999/evidence", json={"is_correct": True}, headers=headers)
    assert res.status_code == 404
