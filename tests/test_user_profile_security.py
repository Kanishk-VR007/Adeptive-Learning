import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.models.syllabus import Subject, Chapter, Concept
from app.models.learner_mastery import LearnerMastery
from app.models.fsrs_review import ConceptReviewState
from app.core.security import get_password_hash, create_access_token, verify_password

# client is provided by conftest fixture


@pytest.fixture
def student_with_data(db_session: Session):
    student = User(
        email="profile_student@adeptlearn.org",
        hashed_password=get_password_hash("OriginalPassword123"),
        full_name="Marie Curie",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.flush()

    sub = Subject(code="CHEM-101", name="General Chemistry", description="Inorganic Chemistry")
    db_session.add(sub)
    db_session.flush()

    ch = Chapter(subject_id=sub.id, chapter_number=1, title="Atomic Theory")
    db_session.add(ch)
    db_session.flush()

    c = Concept(
        subject_id=sub.id,
        chapter_id=ch.id,
        name="Radioactivity",
        concept_code="CHEM-001",
        description="Nuclear decay and radiation",
    )
    db_session.add(c)
    db_session.flush()

    # Mastery & review state
    db_session.add(LearnerMastery(student_id=student.id, concept_id=c.id, p_know=0.89, is_mastered=True))
    from datetime import datetime, timezone
    db_session.add(
        ConceptReviewState(
            student_id=student.id,
            concept_id=c.id,
            stability=4.5,
            difficulty=4.0,
            state=2,
            due_at_utc=datetime.now(timezone.utc),
            fsrs_card_json={"stability": 4.5, "difficulty": 4.0, "state": 2},
        )
    )
    db_session.commit()

    token = create_access_token(subject=str(student.id), extra_claims={"role": student.role.value})
    return {"student": student, "token": token, "subject": sub, "concept": c}


def test_user_profile_retrieval_and_update(client, student_with_data):
    """User can view and update profile information."""
    headers = {"Authorization": f"Bearer {student_with_data['token']}"}

    # 1. Get profile
    res = client.get("/api/v1/users/me", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "profile_student@adeptlearn.org"
    assert data["full_name"] == "Marie Curie"
    assert data["role"] == "STUDENT"

    # 2. Update name
    update_res = client.patch("/api/v1/users/me", json={"full_name": "Madame Marie Curie"}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Madame Marie Curie"


def test_user_password_change(client, student_with_data, db_session):
    """User can securely update password with current password verification."""
    headers = {"Authorization": f"Bearer {student_with_data['token']}"}

    # 1. Wrong current password fails
    fail_res = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "WrongPassword", "new_password": "NewSecretPassword123"},
        headers=headers,
    )
    assert fail_res.status_code == 400

    # 2. Correct current password succeeds
    success_res = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "OriginalPassword123", "new_password": "NewSecretPassword123"},
        headers=headers,
    )
    assert success_res.status_code == 200

    # 3. Verify in database
    st = db_session.query(User).filter(User.id == student_with_data["student"].id).first()
    assert verify_password("NewSecretPassword123", st.hashed_password)


def test_user_data_export(client, student_with_data):
    """GDPR-compliant data export retrieves all personal mastery and review records."""
    headers = {"Authorization": f"Bearer {student_with_data['token']}"}
    res = client.get("/api/v1/users/me/export", headers=headers)
    assert res.status_code == 200
    export_data = res.json()
    assert "user_profile" in export_data
    assert "mastery_records" in export_data
    assert len(export_data["mastery_records"]) == 1
    assert export_data["mastery_records"][0]["concept_name"] == "Radioactivity"
    assert export_data["mastery_records"][0]["p_know"] == 0.89
    assert len(export_data["revision_cards"]) == 1


def test_user_account_permanent_deletion(client, student_with_data, db_session):
    """Account deletion cascades correctly and removes personal learning data."""
    headers = {"Authorization": f"Bearer {student_with_data['token']}"}
    del_res = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"password": "OriginalPassword123", "permanent": True},
        headers=headers,
    )
    assert del_res.status_code == 200

    # Verify user and related records removed
    st_id = student_with_data["student"].id
    assert db_session.query(User).filter(User.id == st_id).first() is None
    assert db_session.query(LearnerMastery).filter(LearnerMastery.student_id == st_id).first() is None
    assert db_session.query(ConceptReviewState).filter(ConceptReviewState.student_id == st_id).first() is None
