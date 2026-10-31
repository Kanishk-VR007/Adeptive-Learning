import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.assessment import Question, QuestionType, LearningSession, SessionType, LearnerResponse
from app.models.learner_mastery import LearnerMastery
from app.models.fsrs_review import ConceptReviewState, ReviewHistory
from app.models.teacher_class import Class, ClassEnrollment
from app.core.security import get_password_hash, create_access_token

# client is provided by conftest fixture


@pytest.fixture
def analytics_dataset(db_session: Session):
    """Sets up a comprehensive deterministic dataset for teacher analytics."""
    # 1. Teacher & Class
    teacher = User(
        email="teacher_analytics@adeptlearn.org",
        hashed_password=get_password_hash("Secret123"),
        full_name="Prof. Feynman",
        role=UserRole.TEACHER,
        is_active=True,
    )
    db_session.add(teacher)
    db_session.flush()

    sub = Subject(code="PHYS-201", name="Thermodynamics & Heat", description="Thermal Physics")
    db_session.add(sub)
    db_session.flush()

    ch = Chapter(subject_id=sub.id, chapter_number=1, title="Laws of Thermodynamics")
    db_session.add(ch)
    db_session.flush()

    c1 = Concept(
        subject_id=sub.id,
        chapter_id=ch.id,
        name="First Law of Thermodynamics",
        concept_code="THERMO-001",
        description="Conservation of energy",
    )
    c2 = Concept(
        subject_id=sub.id,
        chapter_id=ch.id,
        name="Entropy and Second Law",
        concept_code="THERMO-002",
        description="Entropy increases in isolated systems",
    )
    db_session.add_all([c1, c2])
    db_session.flush()

    cls = Class(
        name="Physics 201 - Spring 2026",
        enrollment_code="THERMO26",
        teacher_id=teacher.id,
        subject_id=sub.id,
        is_active=True,
    )
    db_session.add(cls)
    db_session.flush()

    # 2. Students: Student A (High Mastery) and Student B (Struggling)
    st_a = User(
        email="student_a@adeptlearn.org",
        hashed_password=get_password_hash("Secret123"),
        full_name="Alice Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    st_b = User(
        email="student_b@adeptlearn.org",
        hashed_password=get_password_hash("Secret123"),
        full_name="Bob Struggler",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add_all([st_a, st_b])
    db_session.flush()

    # Enroll students
    db_session.add_all([
        ClassEnrollment(class_id=cls.id, student_id=st_a.id, is_active=True),
        ClassEnrollment(class_id=cls.id, student_id=st_b.id, is_active=True),
    ])

    # 3. Learner Mastery: Alice=0.92 (Mastered), Bob=0.45 (Needs remediation on c2)
    db_session.add_all([
        LearnerMastery(student_id=st_a.id, concept_id=c1.id, initial_mastery=0.2, current_mastery=0.95),
        LearnerMastery(student_id=st_a.id, concept_id=c2.id, initial_mastery=0.2, current_mastery=0.88),
        LearnerMastery(student_id=st_b.id, concept_id=c1.id, initial_mastery=0.2, current_mastery=0.65),
        LearnerMastery(student_id=st_b.id, concept_id=c2.id, initial_mastery=0.2, current_mastery=0.25),
    ])

    # 4. Questions & Responses (Bob has misconception)
    q1 = Question(
        concept_id=c2.id,
        question_text="Can the total entropy of the universe decrease in a spontaneous process?",
        question_type=QuestionType.OPEN_ENDED,
        difficulty_level=DifficultyLevel.BEGINNER,
        correct_answer="No",
        explanation="Second law dictates universe entropy non-decreasing.",
    )
    db_session.add(q1)
    db_session.flush()

    sess_b = LearningSession(
        user_id=st_b.id, subject_id=sub.id, session_type=SessionType.ADAPTIVE_PRACTICE
    )
    db_session.add(sess_b)
    db_session.flush()

    db_session.add(
        LearnerResponse(
            session_id=sess_b.id,
            question_id=q1.id,
            user_id=st_b.id,
            response_text="Yes if temperature drops",
            is_correct=False,
            ai_feedback="Entropy-Reversibility Confusion",
        )
    )

    # 5. Overdue revision for Bob
    overdue_time = datetime.now(timezone.utc) - timedelta(days=2)
    db_session.add(
        ConceptReviewState(
            student_id=st_b.id,
            concept_id=c2.id,
            stability=1.2,
            difficulty=5.0,
            due_at_utc=overdue_time,
            state=2,
            fsrs_card_json={"stability": 1.2, "difficulty": 5.0, "state": 2},
        )
    )

    db_session.commit()

    token = create_access_token(subject=str(teacher.id), extra_claims={"role": teacher.role.value})
    return {
        "teacher": teacher,
        "token": token,
        "class": cls,
        "subject": sub,
        "concept_1": c1,
        "concept_2": c2,
        "student_a": st_a,
        "student_b": st_b,
    }


def test_class_analytics_deterministic_metrics(client, analytics_dataset):
    """Verifies that teacher analytics calculate strictly correct, deterministic metrics from database records."""
    headers = {"Authorization": f"Bearer {analytics_dataset['token']}"}
    class_id = analytics_dataset["class"].id

    res = client.get(f"/api/v1/analytics/classes/{class_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Verification of Class Overview
    assert data["total_enrolled"] == 2
    assert data["active_students_count"] == 1  # Only Bob submitted a response in dataset
    assert data["participation_rate"] == 0.5

    # Verification of Class Average Mastery: (0.95 + 0.88 + 0.65 + 0.25) / 4 = 2.73 / 4 = 0.6825 ~ 0.683
    assert data["average_mastery"] == pytest.approx(0.683, abs=0.01)

    # Verification of Concept Performances
    assert len(data["concept_performances"]) == 2
    c2_perf = next(cp for cp in data["concept_performances"] if cp["concept_id"] == analytics_dataset["concept_2"].id)
    # c2 mastery avg: (0.88 + 0.25) / 2 = 0.565
    assert c2_perf["average_mastery"] == pytest.approx(0.565, abs=0.01)
    assert c2_perf["students_mastered"] == 1
    assert c2_perf["students_remediating"] == 1
    assert c2_perf["error_rate"] == 1.0  # Bob attempted and missed

    # Weak Concepts should identify c2
    assert len(data["weak_concepts"]) == 1
    assert data["weak_concepts"][0]["concept_id"] == analytics_dataset["concept_2"].id

    # Misconceptions
    assert len(data["common_misconceptions"]) == 1
    assert data["common_misconceptions"][0]["category"] == "Entropy-Reversibility Confusion"
    assert data["common_misconceptions"][0]["occurrence_count"] == 1

    # Overdue reviews
    assert data["total_overdue_revisions"] == 1

    # Students requiring support
    assert len(data["students_requiring_support"]) == 1
    support_st = data["students_requiring_support"][0]
    assert support_st["student_id"] == analytics_dataset["student_b"].id
    assert support_st["full_name"] == "Bob Struggler"


def test_empty_class_analytics_returns_no_fabrication(client, db_session):
    """An empty class must return valid zero/None values and NEVER fabricate numbers."""
    teacher = User(
        email="teacher_empty@adeptlearn.org",
        hashed_password=get_password_hash("Secret123"),
        full_name="Prof. Empty",
        role=UserRole.TEACHER,
        is_active=True,
    )
    db_session.add(teacher)
    db_session.flush()

    sub = Subject(code="BIO-001", name="General Biology", description="Intro to biology")
    db_session.add(sub)
    db_session.flush()

    empty_cls = Class(
        name="Empty Biology Class",
        enrollment_code="BIOEMPTY",
        teacher_id=teacher.id,
        subject_id=sub.id,
        is_active=True,
    )
    db_session.add(empty_cls)
    db_session.commit()

    token = create_access_token(subject=str(teacher.id), extra_claims={"role": teacher.role.value})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/analytics/classes/{empty_cls.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_enrolled"] == 0
    assert data["average_mastery"] is None
    assert data["overall_accuracy_rate"] is None
    assert data["total_questions_attempted"] == 0
    assert data["common_misconceptions"] == []
    assert data["students_requiring_support"] == []
