import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.ai.providers.base import (
    LLMProviderError,
    ModelLoadError,
    ModelUnloadError,
    InferenceTimeoutError,
    ProviderConnectionError,
)
from app.ai.providers.lmstudio import LMStudioProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.schemas import ChatMessage, InferenceOptions


# ============================================================================
# LM Studio Provider Tests
# ============================================================================

@pytest.mark.asyncio
async def test_lmstudio_health_and_connection_success():
    provider = LMStudioProvider(base_url="http://localhost:1234")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "models": [
            {
                "key": "deepseek-7b",
                "loaded_instances": [{"id": "inst-1"}],
            }
        ]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        health = await provider.get_health()

    assert health.is_online is True
    assert "inst-1" in health.loaded_models
    assert health.error is None


@pytest.mark.asyncio
async def test_lmstudio_server_unavailable():
    provider = LMStudioProvider(base_url="http://localhost:1234")

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        health = await provider.get_health()

    assert health.is_online is False
    assert "Connection refused" in (health.error or "")


@pytest.mark.asyncio
async def test_lmstudio_load_model_success():
    provider = LMStudioProvider(base_url="http://localhost:1234", default_model="deepseek-7b")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "instance_id": "deepseek-7b-instance-42",
        "load_time_seconds": 2.35,
        "load_config": {"context_length": 4096, "flash_attention": True},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await provider.load_model(
            model_id="deepseek-7b",
            context_length=4096,
            flash_attention=True,
        )

    assert result["instance_id"] == "deepseek-7b-instance-42"
    assert result["load_time_seconds"] == 2.35
    assert provider._active_instance_id == "deepseek-7b-instance-42"


@pytest.mark.asyncio
async def test_lmstudio_load_model_timeout():
    provider = LMStudioProvider(base_url="http://localhost:1234", default_model="deepseek-7b", load_timeout=1)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timed out loading weights")
        with pytest.raises(ModelLoadError) as exc_info:
            await provider.load_model(model_id="deepseek-7b")

    assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_lmstudio_unload_model_and_verification():
    provider = LMStudioProvider(base_url="http://localhost:1234", default_model="deepseek-7b")
    provider._active_instance_id = "deepseek-7b-instance-42"

    mock_unload_resp = MagicMock(status_code=200)
    mock_unload_resp.json.return_value = {"instance_id": "deepseek-7b-instance-42"}

    mock_inventory_resp = MagicMock(status_code=200)
    mock_inventory_resp.json.return_value = {
        "models": [
            {
                "key": "deepseek-7b",
                "loaded_instances": [],  # Verified empty!
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_post.return_value = mock_unload_resp
        mock_get.return_value = mock_inventory_resp

        res = await provider.unload_model()

    assert res is True
    assert provider._active_instance_id is None


@pytest.mark.asyncio
async def test_lmstudio_unload_model_verification_failure():
    provider = LMStudioProvider(base_url="http://localhost:1234", default_model="deepseek-7b")
    provider._active_instance_id = "deepseek-7b-instance-42"

    mock_unload_resp = MagicMock(status_code=200)
    mock_inventory_resp = MagicMock(status_code=200)
    mock_inventory_resp.json.return_value = {
        "models": [
            {
                "key": "deepseek-7b",
                "loaded_instances": [{"id": "deepseek-7b-instance-42"}],  # Still resident!
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_post.return_value = mock_unload_resp
        mock_get.return_value = mock_inventory_resp

        with pytest.raises(ModelUnloadError) as exc_info:
            await provider.unload_model()

    assert "still detected in lm studio memory" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_lmstudio_inference_success():
    provider = LMStudioProvider(base_url="http://localhost:1234", default_model="deepseek-7b")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "DeepSeek step-by-step reasoning"}}],
        "usage": {"prompt_tokens": 15, "completion_tokens": 40, "total_tokens": 55},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await provider.generate_chat(
            messages=[ChatMessage(role="user", content="Explain Ohm's law")],
            options=InferenceOptions(temperature=0.5, max_tokens=100),
        )

    assert "step-by-step reasoning" in res.content
    assert res.stats.total_tokens == 55


@pytest.mark.asyncio
async def test_lmstudio_inference_timeout():
    provider = LMStudioProvider(base_url="http://localhost:1234", default_model="deepseek-7b", timeout=1)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Inference timeout")
        with pytest.raises(InferenceTimeoutError):
            await provider.generate_chat(messages=[ChatMessage(role="user", content="hello")])


# ============================================================================
# Ollama Provider Tests
# ============================================================================

@pytest.mark.asyncio
async def test_ollama_health_and_ps_inventory():
    provider = OllamaProvider(base_url="http://localhost:11434")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "models": [{"name": "llama3.2:latest", "model": "llama3.2:latest"}]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        health = await provider.get_health()
        loaded = await provider.is_model_loaded("llama3.2")

    assert health.is_online is True
    assert "llama3.2:latest" in health.loaded_models
    assert loaded is True


@pytest.mark.asyncio
async def test_ollama_inference_with_json_and_stats():
    provider = OllamaProvider(base_url="http://localhost:11434", default_model="llama3.2:latest")
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {
        "message": {"content": '{"friendly_feedback": "Great attempt!", "socratic_hint": "Check V=IR"}'},
        "prompt_eval_count": 20,
        "eval_count": 35,
        "eval_duration": 120_000_000,  # 120 ms
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await provider.generate_chat(
            messages=[ChatMessage(role="user", content="Format student response")],
            options=InferenceOptions(format_json=True),
        )

    assert "friendly_feedback" in res.content
    assert res.stats.prompt_tokens == 20
    assert res.stats.completion_tokens == 35
    assert res.stats.eval_duration_ms == 120.0


@pytest.mark.asyncio
async def test_ollama_unload_model_with_keep_alive_zero():
    provider = OllamaProvider(base_url="http://localhost:11434", default_model="llama3.2:latest")
    mock_post_resp = MagicMock(status_code=200)
    mock_get_resp = MagicMock(status_code=200)
    mock_get_resp.json.return_value = {"models": []}  # Verified empty after unload

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_post.return_value = mock_post_resp
        mock_get.return_value = mock_get_resp

        success = await provider.unload_model()

    assert success is True
    # Verify keep_alive: 0 was sent in payload
    call_args = mock_post.call_args[1]
    assert call_args["json"]["keep_alive"] == 0


@pytest.mark.asyncio
async def test_ollama_server_unavailable():
    provider = OllamaProvider(base_url="http://localhost:11434")

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Ollama daemon down")
        health = await provider.get_health()

    assert health.is_online is False
    assert "Ollama daemon down" in (health.error or "")
