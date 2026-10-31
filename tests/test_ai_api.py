import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.ai.schemas import (
    DeepSeekReasoningOutput,
    ExecutionState,
    ExecutionTurnMetrics,
    GPUMemorySnapshot,
    GPUExecutionStatus,
    LearningTurnOutput,
    LlamaFormatOutput,
    ModelInfo,
    ProviderHealth,
)


def test_ai_health_unauthenticated_rejected(client: TestClient):
    res = client.get("/api/v1/ai/health")
    assert res.status_code == 401


def test_ai_health_authenticated_success(student_client: TestClient):
    mock_lm_health = ProviderHealth(provider="lmstudio", is_online=True, base_url="http://localhost:1234", loaded_models=["deepseek"])
    mock_ol_health = ProviderHealth(provider="ollama", is_online=True, base_url="http://localhost:11434", loaded_models=[])

    with patch("app.api.v1.endpoints.ai.get_lmstudio_provider") as mock_get_lm, \
         patch("app.api.v1.endpoints.ai.get_ollama_provider") as mock_get_ol:
        mock_lm = MagicMock()
        mock_lm.get_health = AsyncMock(return_value=mock_lm_health)
        mock_get_lm.return_value = mock_lm

        mock_ol = MagicMock()
        mock_ol.get_health = AsyncMock(return_value=mock_ol_health)
        mock_get_ol.return_value = mock_ol

        res = student_client.get("/api/v1/ai/health")

    assert res.status_code == 200
    data = res.json()
    assert "lmstudio" in data
    assert "ollama" in data
    assert data["lmstudio"]["is_online"] is True
    assert data["ollama"]["is_online"] is True


def test_ai_models_inventory_endpoint(student_client: TestClient):
    mock_models = [
        ModelInfo(model_id="deepseek-7b", name="DeepSeek 7B", is_loaded=True, runtime="lmstudio"),
        ModelInfo(model_id="llama3.2", name="Llama 3.2", is_loaded=False, runtime="ollama"),
    ]

    with patch("app.api.v1.endpoints.ai.get_lmstudio_provider") as mock_get_lm, \
         patch("app.api.v1.endpoints.ai.get_ollama_provider") as mock_get_ol:
        mock_lm = MagicMock()
        mock_lm.get_inventory = AsyncMock(return_value=[mock_models[0]])
        mock_get_lm.return_value = mock_lm

        mock_ol = MagicMock()
        mock_ol.get_inventory = AsyncMock(return_value=[mock_models[1]])
        mock_get_ol.return_value = mock_ol

        res = student_client.get("/api/v1/ai/models")

    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2
    assert items[0]["model_id"] == "deepseek-7b"
    assert items[1]["model_id"] == "llama3.2"


def test_ai_gpu_status_endpoint(student_client: TestClient):
    mock_snap = GPUMemorySnapshot(
        total_mb=6141.0,
        used_mb=1250.0,
        free_mb=4891.0,
        utilization_percent=12.0,
        temperature_c=50.0,
        is_available=True,
        timestamp=1234567.0,
    )

    with patch("app.api.v1.endpoints.ai.get_gpu_monitor") as mock_get_mon:
        mock_mon = MagicMock()
        mock_mon.get_memory_snapshot.return_value = mock_snap
        mock_get_mon.return_value = mock_mon

        res = student_client.get("/api/v1/ai/gpu-status")

    assert res.status_code == 200
    data = res.json()
    assert data["total_mb"] == 6141.0
    assert data["used_mb"] == 1250.0
    assert data["temperature_c"] == 50.0


def test_ai_execution_status_endpoint(student_client: TestClient):
    mock_status = GPUExecutionStatus(
        state=ExecutionState.IDLE,
        active_model=None,
        queue_size=0,
        last_transition_time=12345.0,
        prewarmed_model=None,
        mode="sequential",
        prewarm_mode="disabled",
    )

    with patch("app.api.v1.endpoints.ai.get_gpu_execution_manager") as mock_get_mgr:
        mock_mgr = MagicMock()
        mock_mgr.get_status.return_value = mock_status
        mock_get_mgr.return_value = mock_mgr

        res = student_client.get("/api/v1/ai/execution-status")

    assert res.status_code == 200
    data = res.json()
    assert data["state"] == "IDLE"
    assert data["mode"] == "sequential"


def test_test_inference_student_forbidden(student_client: TestClient):
    payload = {
        "concept_name": "Kinematics",
        "question_text": "v = u + at?",
        "expected_answer": "Yes",
        "student_answer": "Yes",
    }
    # Students cannot trigger test inference (must be 403 Forbidden)
    res = student_client.post("/api/v1/ai/test-inference", json=payload)
    assert res.status_code == 403


def test_test_inference_teacher_success(teacher_client: TestClient):
    payload = {
        "concept_name": "Kinematics",
        "question_text": "v = u + at?",
        "expected_answer": "Yes",
        "student_answer": "Yes",
    }

    mock_output = LearningTurnOutput(
        success=True,
        reasoning=DeepSeekReasoningOutput(
            answer_interpretation="Recognized formula",
            reasoning_analysis="Correct kinematic equation",
            identified_misconception=None,
            conceptual_correctness=True,
            recommended_learning_intervention="Continue practice",
            diagnostic_explanation="Equation applies for constant acceleration",
            suggested_follow_up_question=None,
        ),
        formatted_response=LlamaFormatOutput(
            friendly_feedback="Correct! You know your motion formulas.",
            socratic_hint=None,
            formatted_next_question=None,
            explanation="v = u + at is valid for constant acceleration.",
            conceptual_correctness=True,
        ),
        metrics=ExecutionTurnMetrics(
            deepseek_load_ms=10.0,
            deepseek_inference_ms=50.0,
            deepseek_unload_ms=10.0,
            llama_load_ms=10.0,
            llama_inference_ms=30.0,
            llama_unload_ms=10.0,
            total_turn_ms=120.0,
            peak_vram_mb=2500.0,
        ),
        error_message=None,
    )

    with patch("app.api.v1.endpoints.ai.get_orchestration_service") as mock_get_svc:
        mock_svc = MagicMock()
        mock_svc.process_learning_turn = AsyncMock(return_value=mock_output)
        mock_get_svc.return_value = mock_svc

        res = teacher_client.post("/api/v1/ai/test-inference", json=payload)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["reasoning"]["conceptual_correctness"] is True
    assert "Correct!" in data["formatted_response"]["friendly_feedback"]
    assert data["metrics"]["total_turn_ms"] == 120.0
