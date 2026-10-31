import logging
import time
from typing import Any, Dict, List, Optional
import httpx

from app.ai.providers.base import (
    BaseLLMProvider,
    LLMProviderError,
    ModelLoadError,
    ModelUnloadError,
    InferenceTimeoutError,
    ProviderConnectionError,
)
from app.ai.schemas import ChatMessage, InferenceOptions, InferenceStats, LLMResponse, ModelInfo, ProviderHealth

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """
    Provider adapter for Ollama REST API.
    Interacts with /api/chat for inference and keep_alive lifecycle, and /api/ps for loaded inventory.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.2:latest",
        timeout: int = 120,
        load_timeout: int = 180,
        unload_timeout: int = 60,
        keep_alive: str = "0",
    ):
        super().__init__(base_url=base_url, default_model=default_model, timeout=timeout)
        self.load_timeout = load_timeout
        self.unload_timeout = unload_timeout
        self.keep_alive = keep_alive

    async def get_health(self) -> ProviderHealth:
        """Checks connectivity and returns loaded models via /api/ps."""
        url = f"{self.base_url}/api/ps"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    loaded = [m.get("model", m.get("name", "")) for m in data.get("models", [])]
                    return ProviderHealth(
                        provider="ollama",
                        is_online=True,
                        base_url=self.base_url,
                        loaded_models=loaded,
                        error=None,
                    )
                return ProviderHealth(
                    provider="ollama",
                    is_online=False,
                    base_url=self.base_url,
                    error=f"HTTP {res.status_code}: {res.text}",
                )
        except Exception as e:
            return ProviderHealth(
                provider="ollama",
                is_online=False,
                base_url=self.base_url,
                error=str(e),
            )

    async def get_inventory(self) -> List[ModelInfo]:
        """Queries /api/tags (available) and /api/ps (loaded) to build full inventory."""
        tags_url = f"{self.base_url}/api/tags"
        ps_url = f"{self.base_url}/api/ps"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                tags_res = await client.get(tags_url)
                if tags_res.status_code != 200:
                    raise ProviderConnectionError(f"Ollama tags error HTTP {tags_res.status_code}")
                tags_data = tags_res.json()

                ps_res = await client.get(ps_url)
                loaded_names = set()
                if ps_res.status_code == 200:
                    ps_data = ps_res.json()
                    for m in ps_data.get("models", []):
                        loaded_names.add(m.get("name", ""))
                        loaded_names.add(m.get("model", ""))

                models = []
                for m in tags_data.get("models", []):
                    name = m.get("name", "")
                    details = m.get("details", {})
                    quantization = details.get("quantization_level") if isinstance(details, dict) else None
                    is_loaded = (name in loaded_names) or (m.get("model", "") in loaded_names)
                    models.append(
                        ModelInfo(
                            model_id=name,
                            name=name,
                            size_bytes=m.get("size"),
                            quantization=quantization,
                            is_loaded=is_loaded,
                            runtime="ollama",
                        )
                    )
                return models
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"Failed to connect to Ollama at {self.base_url}: {e}") from e

    async def is_model_loaded(self, model_id: Optional[str] = None) -> bool:
        """Inspects /api/ps to determine if the target model is currently in memory."""
        target_model = model_id or self.default_model
        # Ollama models might be referred to as 'llama3.2' or 'llama3.2:latest'
        target_base = target_model.split(":")[0]
        url = f"{self.base_url}/api/ps"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code != 200:
                    return False
                data = res.json()
                for m in data.get("models", []):
                    m_name = m.get("name", "")
                    m_model = m.get("model", "")
                    if (
                        target_model in (m_name, m_model)
                        or m_name.startswith(target_base)
                        or m_model.startswith(target_base)
                    ):
                        return True
                return False
        except Exception:
            return False

    async def load_model(
        self,
        model_id: Optional[str] = None,
        context_length: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Loads the configured model into memory in Ollama by issuing an empty / priming chat request.
        """
        target_model = model_id or self.default_model
        url = f"{self.base_url}/api/chat"
        # In Ollama, an empty message or keep_alive ping warms/loads the model into VRAM
        payload = {
            "model": target_model,
            "messages": [],
            "keep_alive": kwargs.get("keep_alive", "10m"),  # Keep warm while active
            "options": {},
        }
        if context_length is not None:
            payload["options"]["num_ctx"] = context_length

        logger.info(f"Loading/warming model '{target_model}' into Ollama...")
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=float(self.load_timeout)) as client:
                res = await client.post(url, json=payload)
                elapsed = time.time() - start_time
                if res.status_code not in (200, 400):
                    # Some versions return 200 with empty or short message, or accept the load
                    pass

            # Verification: Check /api/ps
            is_loaded = await self.is_model_loaded(target_model)
            logger.info(f"Model '{target_model}' in Ollama loaded status: {is_loaded} (took {elapsed:.2f}s)")
            return {
                "instance_id": target_model,
                "load_time_seconds": elapsed,
                "status": "loaded" if is_loaded else "ready",
            }
        except httpx.TimeoutException as e:
            raise ModelLoadError(f"Ollama model load timed out after {self.load_timeout}s for '{target_model}'") from e
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"Failed to communicate with Ollama load endpoint: {e}") from e

    async def unload_model(
        self,
        model_id: Optional[str] = None,
        instance_id: Optional[str] = None,
        **kwargs: Any
    ) -> bool:
        """
        Unloads model by sending keep_alive: 0 (or "0") to Ollama and verifying absent from /api/ps.
        """
        target_model = model_id or instance_id or self.default_model
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": target_model,
            "messages": [],
            "keep_alive": 0,
        }

        logger.info(f"Requesting immediate unload for Ollama model '{target_model}' with keep_alive: 0...")
        try:
            async with httpx.AsyncClient(timeout=float(self.unload_timeout)) as client:
                res = await client.post(url, json=payload)
                if res.status_code not in (200, 400):
                    # Also try /api/generate with keep_alive: 0
                    gen_url = f"{self.base_url}/api/generate"
                    await client.post(gen_url, json={"model": target_model, "keep_alive": 0})

            # Verification: Confirm that the model is no longer present in /api/ps
            is_loaded = await self.is_model_loaded(target_model)
            if is_loaded:
                import asyncio
                await asyncio.sleep(0.5)
                is_loaded = await self.is_model_loaded(target_model)
                if is_loaded:
                    raise ModelUnloadError(f"Model '{target_model}' still detected in Ollama memory after keep_alive: 0 unload request!")

            logger.info(f"Model '{target_model}' confirmed unloaded from Ollama.")
            return True
        except httpx.TimeoutException as e:
            raise ModelUnloadError(f"Ollama unload timed out after {self.unload_timeout}s") from e
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"Failed to communicate with Ollama during unload: {e}") from e

    async def generate_chat(
        self,
        messages: List[ChatMessage],
        options: Optional[InferenceOptions] = None,
        model_id: Optional[str] = None
    ) -> LLMResponse:
        """
        Executes chat completion against Ollama POST /api/chat.
        Supports structured JSON output and captures runtime statistics.
        """
        opts = options or InferenceOptions()
        target_model = model_id or self.default_model
        url = f"{self.base_url}/api/chat"

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": opts.temperature if opts.temperature is not None else 0.3,
            },
        }

        # Handle keep-alive: if memory-saving mode, keep_alive can be 0 or specified
        if self.keep_alive is not None:
            # 0 or "0" sets immediate unload after inference
            payload["keep_alive"] = 0 if str(self.keep_alive) == "0" else self.keep_alive

        if opts.max_tokens is not None:
            payload["options"]["num_predict"] = opts.max_tokens
        if opts.context_length is not None:
            payload["options"]["num_ctx"] = opts.context_length
        if opts.format_json:
            payload["format"] = "json"

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
                res = await client.post(url, json=payload)
                duration_ms = (time.time() - start_time) * 1000.0
                if res.status_code != 200:
                    raise LLMProviderError(f"Ollama chat error HTTP {res.status_code}: {res.text}")

                data = res.json()
                message_obj = data.get("message", {})
                content = message_obj.get("content", "")

                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)
                eval_duration_ns = data.get("eval_duration", 0)
                eval_duration_ms = (eval_duration_ns / 1_000_000.0) if eval_duration_ns else duration_ms

                stats = InferenceStats(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    eval_duration_ms=eval_duration_ms,
                )
                return LLMResponse(content=content, raw=data, stats=stats)
        except httpx.TimeoutException as e:
            raise InferenceTimeoutError(f"Ollama inference timed out after {self.timeout}s") from e
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"Failed to communicate with Ollama inference endpoint: {e}") from e
