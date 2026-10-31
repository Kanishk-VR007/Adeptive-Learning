import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.assessment import Question, QuestionType
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.user import User, UserRole
from app.core.security import create_access_token
from app.services.review_state_service import ReviewStateService


@pytest.fixture
def setup_api_data(db_session: Session, teacher_user: User, student_user: User):
    subj = Subject(name="Chemistry", code="CHEM101", description="General Chemistry")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    chap = Chapter(subject_id=subj.id, title="Atomic Structure", chapter_number=1, description="Atoms and Orbitals")
    db_session.add(chap)
    db_session.commit()
    db_session.refresh(chap)

    concept = Concept(
        concept_code="CHEM-ATOM-001",
        subject_id=subj.id,
        chapter_id=chap.id,
        name="Bohr Model",
        description="Quantized electron orbits",
        difficulty_level=DifficultyLevel.BEGINNER,
    )
    db_session.add(concept)
    db_session.commit()
    db_session.refresh(concept)

    question = Question(
        concept_id=concept.id,
        question_type=QuestionType.MCQ,
        question_text="What orbits the nucleus in the Bohr model?",
        question_options=[{"id": "A", "text": "Electrons"}, {"id": "B", "text": "Photons"}],
        correct_answer="A",
        evaluation_rubric={"explanation": "Electrons orbit the nucleus"},
        created_by_id=teacher_user.id,
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)

    # Second student for cross-tenant testing
    student_b = User(
        email="bob@adaptive.edu",
        hashed_password="pw",
        full_name="Bob Miller",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student_b)
    db_session.commit()
    db_session.refresh(student_b)

    return subj, chap, concept, question, student_b


class TestFSRSAPISecurity:
    """
    Tests security, authentication, RBAC, ownership isolation,
    and parameter validation on all newly created revision endpoints.
    """

    def test_unauthenticated_requests_rejected(self, client: TestClient, setup_api_data):
        _, _, concept, _, _ = setup_api_data

        # All revision endpoints must reject missing authorization
        r1 = client.get("/api/v1/revisions/summary")
        assert r1.status_code == 401

        r2 = client.get("/api/v1/revisions/queue")
        assert r2.status_code == 401

        r3 = client.get(f"/api/v1/revisions/{concept.id}/state")
        assert r3.status_code == 401

        r4 = client.post(f"/api/v1/revisions/{concept.id}/start")
        assert r4.status_code == 401

        r5 = client.post(f"/api/v1/revisions/{concept.id}/complete", json={"question_id": 1, "response_text": "A", "rating": 3})
        assert r5.status_code == 401

        r6 = client.get("/api/v1/revisions/preferences")
        assert r6.status_code == 401

    def test_student_isolated_queue_and_summary(
        self, student_client: TestClient, db_session: Session, student_user: User, setup_api_data
    ):
        _, _, concept, _, student_b = setup_api_data

        # Enroll concept for student A
        ReviewStateService.enroll_concept(db_session, student_user.id, concept.id, ignore_daily_limit=True)

        # Student A checks queue
        resp_a = student_client.get("/api/v1/revisions/queue")
        assert resp_a.status_code == 200
        data_a = resp_a.json()
        assert data_a["total_count"] == 1
        assert data_a["items"][0]["concept_id"] == concept.id

        # Student B checks queue via separate token
        token_b = create_access_token(subject=student_b.id, extra_claims={"role": student_b.role.value, "email": student_b.email})
        resp_b = student_client.get("/api/v1/revisions/queue", headers={"Authorization": f"Bearer {token_b}"})
        assert resp_b.status_code == 200
        data_b = resp_b.json()
        # Student B has no enrolled cards
        assert data_b["total_count"] == 0
        assert len(data_b["items"]) == 0

    def test_student_cannot_access_unenrolled_or_other_students_card(
        self, student_client: TestClient, db_session: Session, setup_api_data
    ):
        _, _, concept, _, student_b = setup_api_data

        # Enroll concept ONLY for Student B
        ReviewStateService.enroll_concept(db_session, student_b.id, concept.id, ignore_daily_limit=True)

        # Student A requests state for this concept -> 404 (concept not enrolled for this student)
        resp = student_client.get(f"/api/v1/revisions/{concept.id}/state")
        assert resp.status_code == 404
        assert "not enrolled in spaced repetition for this student" in resp.json()["detail"]

    def test_question_mismatch_validation(
        self, student_client: TestClient, db_session: Session, student_user: User, setup_api_data
    ):
        subj, chap, concept, question, _ = setup_api_data

        # Create another concept with its own question
        other_concept = Concept(
            concept_code="CHEM-BOND-002",
            subject_id=subj.id,
            chapter_id=chap.id,
            name="Covalent Bonding",
            description="Sharing electrons",
            difficulty_level=DifficultyLevel.BEGINNER,
        )
        db_session.add(other_concept)
        db_session.commit()
        db_session.refresh(other_concept)

        # Attempt to complete revision for 'other_concept' using a question belonging to 'concept'
        payload = {
            "question_id": question.id,
            "response_text": "A",
            "rating": 3,
            "idempotency_key": "sec_test_mismatch",
        }
        resp = student_client.post(f"/api/v1/revisions/{other_concept.id}/complete", json=payload)
        assert resp.status_code == 400
        assert f"belongs to concept {question.concept_id}, not {other_concept.id}" in resp.json()["detail"]

    def test_invalid_preferences_rejected(self, student_client: TestClient):
        # Invalid retention (< 0.70)
        r1 = student_client.patch("/api/v1/revisions/preferences", json={"desired_retention": 0.50})
        assert r1.status_code == 422 or r1.status_code == 400

        # Invalid retention (> 0.99)
        r2 = student_client.patch("/api/v1/revisions/preferences", json={"desired_retention": 1.05})
        assert r2.status_code == 422 or r2.status_code == 400

        # Invalid IANA timezone name
        r3 = student_client.patch("/api/v1/revisions/preferences", json={"timezone_name": "Mars/Olympus_Mons"})
        assert r3.status_code == 422 or r3.status_code == 400

        # Valid update
        r4 = student_client.patch(
            "/api/v1/revisions/preferences",
            json={"desired_retention": 0.88, "timezone_name": "Asia/Kolkata", "daily_new_concept_limit": 10},
        )
        assert r4.status_code == 200
        data = r4.json()
        assert data["desired_retention"] == 0.88
        assert data["timezone_name"] == "Asia/Kolkata"
        assert data["daily_new_concept_limit"] == 10
