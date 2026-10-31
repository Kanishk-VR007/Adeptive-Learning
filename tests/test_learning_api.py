import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.providers.base import LLMResponse
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.assessment import LearningSession, Question, QuestionType, SessionType
from app.models.concept_graph import ConceptPrerequisite
from app.models.learner_mastery import LearnerMastery
from app.models.syllabus import Chapter, Concept, DifficultyLevel, Subject
from app.models.user import User, UserRole


@pytest.fixture
def api_test_data(db_session: Session):
    subj = Subject(name="API Physics", code="API-PHYS-101")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    ch = Chapter(subject_id=subj.id, title="Thermodynamics", chapter_number=1)
    db_session.add(ch)
    db_session.commit()
    db_session.refresh(ch)

    c1 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Heat Capacity", concept_code="API-HEAT-01", description="Heat")
    db_session.add(c1)
    db_session.commit()
    db_session.refresh(c1)

    q1 = Question(
        concept_id=c1.id,
        question_type=QuestionType.MCQ,
        question_text="What is SI unit of heat capacity?",
        question_options=[{"id": "A", "text": "J/K"}, {"id": "B", "text": "J/kg"}],
        correct_answer="A",
        difficulty_level=DifficultyLevel.BEGINNER,
    )
    db_session.add(q1)

    student1 = User(
        email="api_student1@example.com",
        full_name="API Student 1",
        hashed_password=get_password_hash("Secret123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    student2 = User(
        email="api_student2@example.com",
        full_name="API Student 2",
        hashed_password=get_password_hash("Secret123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add_all([student1, student2])
    db_session.commit()
    db_session.refresh(student1)
    db_session.refresh(student2)
    db_session.refresh(q1)

    # Student 1 session
    sess1 = LearningSession(
        user_id=student1.id,
        subject_id=subj.id,
        session_type=SessionType.ADAPTIVE_PRACTICE,
    )
    db_session.add(sess1)
    db_session.commit()
    db_session.refresh(sess1)

    token1 = create_access_token(subject=student1.id)
    token2 = create_access_token(subject=student2.id)

    return {
        "student1": student1,
        "student2": student2,
        "token1": token1,
        "token2": token2,
        "subj": subj,
        "c1": c1,
        "q1": q1,
        "sess1": sess1,
    }


def _mock_exec_manager():
    mgr = MagicMock(spec=GPUExecutionManager)
    llama_payload = {
        "feedback": "Well done! Your understanding of heat capacity units is correct.",
        "socratic_hint": None,
        "next_question": "What is specific heat capacity?",
        "adaptive_action": "TARGETED_PRACTICE",
        "display_mastery": 0.55,
    }
    mgr.execute_llama = AsyncMock(return_value={"result": LLMResponse(content=json.dumps(llama_payload), raw_response={}), "metrics": {}})
    mgr.get_status = MagicMock(return_value=MagicMock(state="idle", active_model=None, monitoring_enabled=True))
    return mgr


def test_submit_learning_turn_unauthorized(client: TestClient, api_test_data):
    """POST /api/v1/learning/turns without authorization header must return 401."""
    q = api_test_data["q1"]
    payload = {
        "question_id": q.id,
        "student_answer": "A",
    }
    resp = client.post("/api/v1/learning/turns", json=payload)
    assert resp.status_code == 401


def test_submit_learning_turn_invalid_question(client: TestClient, api_test_data):
    """POST /api/v1/learning/turns with non-existent question returns 404."""
    token = api_test_data["token1"]
    payload = {
        "question_id": 999999,
        "student_answer": "A",
    }
    resp = client.post(
        "/api/v1/learning/turns",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_submit_learning_turn_cross_student_session_forbidden(client: TestClient, api_test_data):
    """Student 2 cannot submit under Student 1's learning session (403 Forbidden)."""
    token2 = api_test_data["token2"]  # Student 2
    sess1 = api_test_data["sess1"]    # Belongs to Student 1
    q = api_test_data["q1"]

    payload = {
        "question_id": q.id,
        "student_answer": "A",
        "session_id": sess1.id,
    }
    resp = client.post(
        "/api/v1/learning/turns",
        json=payload,
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 403
    assert "Unauthorized" in resp.json()["detail"]


@patch("app.services.learning_orchestration_service.get_gpu_execution_manager")
def test_submit_learning_turn_success_and_get_result(mock_get_mgr, client: TestClient, api_test_data):
    """Successful turn submission, status check, and result retrieval."""
    mock_get_mgr.return_value = _mock_exec_manager()
    token1 = api_test_data["token1"]
    student1 = api_test_data["student1"]
    q = api_test_data["q1"]
    sess1 = api_test_data["sess1"]

    payload = {
        "question_id": q.id,
        "student_answer": "A",
        "session_id": sess1.id,
    }
    resp = client.post(
        "/api/v1/learning/turns",
        json=payload,
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    run_id = data["run_id"]
    assert run_id.startswith("run_")
    assert data["student_id"] == student1.id
    assert data["execution_status"] == "completed"
    assert data["updated_mastery"] > 0.20
    assert "node_execution_trace" in data

    # 1. GET /api/v1/learning/turns/{run_id}
    status_resp = client.get(
        f"/api/v1/learning/turns/{run_id}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["run_id"] == run_id
    assert status_resp.json()["execution_status"] == "completed"

    # 2. GET /api/v1/learning/turns/{run_id}/result
    result_resp = client.get(
        f"/api/v1/learning/turns/{run_id}/result",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert result_resp.status_code == 200
    assert result_resp.json()["student_feedback"] is not None

    # 3. Cross-student access: Student 2 attempting to view Student 1's run -> 403 Forbidden!
    token2 = api_test_data["token2"]
    forbidden_resp = client.get(
        f"/api/v1/learning/turns/{run_id}/result",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert forbidden_resp.status_code == 403


def test_get_session_history_and_cross_student_protection(client: TestClient, api_test_data):
    """Verify session history retrieval and cross-student protection."""
    token1 = api_test_data["token1"]
    token2 = api_test_data["token2"]
    sess1 = api_test_data["sess1"]

    # Student 1 gets their history
    resp1 = client.get(
        f"/api/v1/learning/sessions/{sess1.id}/history",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["session_id"] == sess1.id

    # Student 2 cannot access Student 1's history
    resp2 = client.get(
        f"/api/v1/learning/sessions/{sess1.id}/history",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp2.status_code == 403


@patch("app.services.learning_orchestration_service.get_gpu_execution_manager")
def test_get_graph_status(mock_get_mgr, client: TestClient, api_test_data):
    """GET /api/v1/learning/graph/status returns healthy status and node inventory."""
    mock_get_mgr.return_value = _mock_exec_manager()
    token1 = api_test_data["token1"]

    resp = client.get(
        "/api/v1/learning/graph/status",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "validate_submission" in data["compiled_nodes"]
    assert "deepseek_evaluation" in data["compiled_nodes"]
    assert "student_feedback" in data["compiled_nodes"]
