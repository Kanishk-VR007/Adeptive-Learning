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


class LMStudioProvider(BaseLLMProvider):
    """
    Provider adapter for LM Studio native v1 REST API.
    Interacts with /api/v1/models for lifecycle and /v1/chat/completions for inference.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234",
        default_model: str = "oreal-deepseek-r1-distill-qwen-7b",
        api_token: str = "",
        timeout: int = 120,
        load_timeout: int = 180,
        unload_timeout: int = 60,
        gpu_offload: str = "max",
    ):
        super().__init__(base_url=base_url, default_model=default_model, timeout=timeout)
        self.api_token = api_token
        self.load_timeout = load_timeout
        self.unload_timeout = unload_timeout
        self.gpu_offload = gpu_offload
        self._active_instance_id: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def get_health(self) -> ProviderHealth:
        """Checks connectivity and returns loaded models."""
        url = f"{self.base_url}/api/v1/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    loaded = []
                    for m in data.get("models", []):
                        for inst in m.get("loaded_instances", []):
                            loaded.append(inst.get("id", m.get("key", "")))
                    return ProviderHealth(
                        provider="lmstudio",
                        is_online=True,
                        base_url=self.base_url,
                        loaded_models=loaded,
                        error=None,
                    )
                return ProviderHealth(
                    provider="lmstudio",
                    is_online=False,
                    base_url=self.base_url,
                    error=f"HTTP {res.status_code}: {res.text}",
                )
        except Exception as e:
            return ProviderHealth(
                provider="lmstudio",
                is_online=False,
                base_url=self.base_url,
                error=str(e),
            )

    async def get_inventory(self) -> List[ModelInfo]:
        """Queries /api/v1/models to list available and loaded models."""
        url = f"{self.base_url}/api/v1/models"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(url, headers=self._get_headers())
                if res.status_code != 200:
                    raise ProviderConnectionError(f"LM Studio API returned {res.status_code}: {res.text}")
                data = res.json()
                models = []
                for m in data.get("models", []):
                    loaded_instances = m.get("loaded_instances", [])
                    is_loaded = len(loaded_instances) > 0
                    q = m.get("quantization")
                    q_name = q.get("name") if isinstance(q, dict) else str(q) if q else None
                    models.append(
                        ModelInfo(
                            model_id=m.get("key", ""),
                            name=m.get("display_name", m.get("key", "")),
                            size_bytes=m.get("size_bytes"),
                            quantization=q_name,
                            is_loaded=is_loaded,
                            runtime="lmstudio",
                        )
                    )
                return models
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"Failed to connect to LM Studio at {self.base_url}: {e}") from e

    async def is_model_loaded(self, model_id: Optional[str] = None) -> bool:
        """Checks if the given model (or any instance) is loaded in LM Studio."""
        target_model = model_id or self.default_model
        inventory = await self.get_inventory()
        for item in inventory:
            if item.model_id == target_model and item.is_loaded:
                return True
        return False

    async def load_model(
        self,
        model_id: Optional[str] = None,
        context_length: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Loads the configured model using POST /api/v1/models/load.
        Captures and stores active instance_id.
        """
        target_model = model_id or self.default_model
        url = f"{self.base_url}/api/v1/models/load"
        payload: Dict[str, Any] = {
            "model": target_model,
            "echo_load_config": True,
        }
        if context_length is not None:
            payload["context_length"] = context_length
        if "flash_attention" in kwargs:
            payload["flash_attention"] = kwargs["flash_attention"]
        if "eval_batch_size" in kwargs:
            payload["eval_batch_size"] = kwargs["eval_batch_size"]

        logger.info(f"Loading model '{target_model}' into LM Studio: payload={payload}")
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=float(self.load_timeout)) as client:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                elapsed = time.time() - start_time
                if res.status_code != 200:
                    err_msg = f"Failed to load model '{target_model}' (HTTP {res.status_code}): {res.text}"
                    logger.error(err_msg)
                    raise ModelLoadError(err_msg)

                data = res.json()
                instance_id = data.get("instance_id")
                if not instance_id:
                    # If instance_id is not explicitly returned in root, look in load result or default to model key
                    instance_id = target_model

                self._active_instance_id = instance_id
                logger.info(f"Model '{target_model}' successfully loaded as instance '{instance_id}' in {elapsed:.2f}s")
                return {
                    "instance_id": instance_id,
                    "load_time_seconds": data.get("load_time_seconds", elapsed),
                    "load_config": data.get("load_config", {}),
                    "status": "loaded",
                }
        except httpx.TimeoutException as e:
            raise ModelLoadError(f"Model load timed out after {self.load_timeout}s for '{target_model}'") from e
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"Connection error while loading model '{target_model}': {e}") from e

    async def unload_model(
        self,
        model_id: Optional[str] = None,
        instance_id: Optional[str] = None,
        **kwargs: Any
    ) -> bool:
        """
        Unloads model using POST /api/v1/models/unload and verifies it is absent from memory.
        """
        target_instance = instance_id or self._active_instance_id or model_id or self.default_model
        url = f"{self.base_url}/api/v1/models/unload"
        payload = {"instance_id": target_instance}

        logger.info(f"Unloading instance '{target_instance}' from LM Studio...")
        try:
            async with httpx.AsyncClient(timeout=float(self.unload_timeout)) as client:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if res.status_code not in (200, 404):
                    raise ModelUnloadError(f"LM Studio unload error HTTP {res.status_code}: {res.text}")

            # Verification: Poll until confirmed unloaded or timeout reached
            import asyncio
            target_model = model_id or self.default_model
            max_wait = min(15.0, float(self.unload_timeout))
            poll_start = time.time()
            is_loaded = await self.is_model_loaded(target_model)
            while is_loaded and (time.time() - poll_start) < max_wait:
                await asyncio.sleep(0.5)
                is_loaded = await self.is_model_loaded(target_model)

            if is_loaded:
                raise ModelUnloadError(f"Model '{target_model}' still detected in LM Studio memory after unload request!")

            self._active_instance_id = None
            logger.info(f"Instance '{target_instance}' confirmed unloaded from LM Studio.")
            return True
        except httpx.TimeoutException as e:
            raise ModelUnloadError(f"Model unload timed out after {self.unload_timeout}s") from e
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"Connection error unloading from LM Studio: {e}") from e

    async def generate_chat(
        self,
        messages: List[ChatMessage],
        options: Optional[InferenceOptions] = None,
        model_id: Optional[str] = None
    ) -> LLMResponse:
        """
        Executes a chat completion request using POST /v1/chat/completions (OpenAI compatible).
        """
        opts = options or InferenceOptions()
        target_model = model_id or self.default_model
        url = f"{self.base_url}/v1/chat/completions"

        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "temperature": opts.temperature if opts.temperature is not None else 0.6,
            "stream": False,
        }
        if opts.max_tokens is not None:
            payload["max_tokens"] = opts.max_tokens

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                duration_ms = (time.time() - start_time) * 1000.0
                if res.status_code != 200:
                    raise LLMProviderError(f"LM Studio inference error HTTP {res.status_code}: {res.text}")

                data = res.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("LM Studio returned empty choices in chat completion.")

                message_obj = choices[0].get("message", {})
                content = message_obj.get("content") or ""
                reasoning_content = message_obj.get("reasoning_content") or ""
                # For reasoning models (DeepSeek-R1), content may be empty while thinking
                if not content.strip() and reasoning_content.strip():
                    content = reasoning_content.strip()

                usage = data.get("usage", {})
                stats = InferenceStats(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    eval_duration_ms=duration_ms,
                )
                return LLMResponse(content=content, raw=data, stats=stats)
        except httpx.TimeoutException as e:
            raise InferenceTimeoutError(f"LM Studio inference timed out after {self.timeout}s") from e
        except httpx.RequestError as e:
            raise ProviderConnectionError(f"Failed to communicate with LM Studio inference endpoint: {e}") from e
