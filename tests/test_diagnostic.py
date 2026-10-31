import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.assessment import Question, QuestionType
from app.models.concept_graph import ConceptPrerequisite, RelationshipType
from app.models.learner_mastery import LearnerMastery
from app.core.security import get_password_hash, create_access_token

# client is provided by conftest fixture


@pytest.fixture
def diagnostic_subject(db_session: Session):
    """Creates a subject with a prerequisite DAG: Vectors -> Kinematics -> Dynamics."""
    sub = Subject(code="PHYS-DIAG", name="Introductory Mechanics", description="Mechanics Diagnostic")
    db_session.add(sub)
    db_session.flush()

    ch = Chapter(subject_id=sub.id, chapter_number=1, title="Mechanics Basics")
    db_session.add(ch)
    db_session.flush()

    c_vec = Concept(
        subject_id=sub.id, chapter_id=ch.id, name="Vectors and Scalars", concept_code="MEC-001", description="Vectors description"
    )
    c_kin = Concept(
        subject_id=sub.id, chapter_id=ch.id, name="1D Kinematics", concept_code="MEC-002", description="Kinematics description"
    )
    c_dyn = Concept(
        subject_id=sub.id, chapter_id=ch.id, name="Newtonian Dynamics", concept_code="MEC-003", description="Dynamics description"
    )
    db_session.add_all([c_vec, c_kin, c_dyn])
    db_session.flush()

    # Prerequisites: Vectors -> Kinematics -> Dynamics
    db_session.add_all([
        ConceptPrerequisite(concept_id=c_kin.id, prerequisite_id=c_vec.id, relationship_type=RelationshipType.PREREQUISITE),
        ConceptPrerequisite(concept_id=c_dyn.id, prerequisite_id=c_kin.id, relationship_type=RelationshipType.PREREQUISITE),
    ])

    # Questions
    q_vec = Question(
        concept_id=c_vec.id,
        question_text="Does a vector quantity have magnitude and direction?",
        question_type=QuestionType.SHORT_ANSWER,
        difficulty_level=DifficultyLevel.BEGINNER,
        correct_answer="Yes",
        explanation="Vectors have both magnitude and direction.",
    )
    q_kin = Question(
        concept_id=c_kin.id,
        question_text="What is the derivative of position with respect to time?",
        question_type=QuestionType.SHORT_ANSWER,
        difficulty_level=DifficultyLevel.BEGINNER,
        correct_answer="Velocity",
        explanation="Velocity is rate of change of position.",
    )
    db_session.add_all([q_vec, q_kin])
    db_session.commit()

    return {"subject": sub, "c_vec": c_vec, "c_kin": c_kin, "c_dyn": c_dyn, "q_vec": q_vec, "q_kin": q_kin}


@pytest.fixture
def student_headers(db_session: Session):
    student = User(
        email="student_diag@adeptlearn.org",
        hashed_password=get_password_hash("Secret123"),
        full_name="Isaac Newton",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()

    token = create_access_token(subject=str(student.id), extra_claims={"role": student.role.value})
    return {"Authorization": f"Bearer {token}", "student": student}


def test_diagnostic_workflow_with_prerequisite_gap(client, diagnostic_subject, student_headers, db_session):
    """
    Complete Diagnostic Assessment Lifecycle:
    1. Student starts diagnostic assessment.
    2. Receives questions covering prerequisite DAG.
    3. Student answers Vector question incorrectly (prerequisite gap) and Kinematics question correctly.
    4. Diagnostic evaluates responses and identifies prerequisite gap in Vectors.
    5. Verifies BKT knowledge values are initialized from observation evidence (not arbitrary constants).
    6. Verifies recommended starting concept points to the gap in 'Vectors and Scalars'.
    """
    headers = {"Authorization": student_headers["Authorization"]}
    sub_id = diagnostic_subject["subject"].id

    # 1. Start diagnostic
    start_res = client.post("/api/v1/diagnostic/start", json={"subject_id": sub_id}, headers=headers)
    assert start_res.status_code == 201
    start_data = start_res.json()
    session_id = start_data["session_id"]
    assert start_data["total_questions"] >= 2
    # Ensure answer is not leaked in question response
    for q in start_data["questions"]:
        assert "correct_answer" not in q

    q_vec_id = diagnostic_subject["q_vec"].id
    q_kin_id = diagnostic_subject["q_kin"].id

    # 2. Submit answers: Miss vector question, get kinematics right
    submission_payload = {
        "session_id": session_id,
        "answers": [
            {"question_id": q_vec_id, "student_answer": "No it only has magnitude"},  # Incorrect
            {"question_id": q_kin_id, "student_answer": "Velocity"},                  # Correct
        ],
    }

    sub_res = client.post("/api/v1/diagnostic/submit", json=submission_payload, headers=headers)
    assert sub_res.status_code == 200
    res_data = sub_res.json()

    assert res_data["total_questions"] == 2
    assert res_data["correct_count"] == 1
    assert res_data["accuracy_rate"] == 0.5

    # 3. Prerequisite gap detection
    assert len(res_data["prerequisite_gaps"]) == 1
    gap = res_data["prerequisite_gaps"][0]
    assert gap["concept_id"] == diagnostic_subject["c_vec"].id
    assert gap["concept_name"] == "Vectors and Scalars"

    # 4. Recommended concept should point to foundational gap
    assert res_data["recommended_concept_id"] == diagnostic_subject["c_vec"].id
    assert res_data["recommended_concept_name"] == "Vectors and Scalars"

    # 5. Verify BKT mastery records persisted in DB
    st_id = student_headers["student"].id
    m_vec = db_session.query(LearnerMastery).filter(
        LearnerMastery.student_id == st_id,
        LearnerMastery.concept_id == diagnostic_subject["c_vec"].id
    ).first()
    m_kin = db_session.query(LearnerMastery).filter(
        LearnerMastery.student_id == st_id,
        LearnerMastery.concept_id == diagnostic_subject["c_kin"].id
    ).first()

    assert m_vec is not None
    assert m_kin is not None
    # Failed attempt should yield lower mastery than successful attempt
    assert m_vec.p_know < m_kin.p_know
    assert not m_vec.is_mastered
