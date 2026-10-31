import abc
from typing import Any, Dict, List, Optional
from app.ai.schemas import ChatMessage, InferenceOptions, LLMResponse, ModelInfo, ProviderHealth


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class ProviderConnectionError(LLMProviderError):
    """Raised when the LLM provider runtime is unreachable."""
    pass


class ModelLoadError(LLMProviderError):
    """Raised when a model fails to load."""
    pass


class ModelUnloadError(LLMProviderError):
    """Raised when a model fails to unload or verify unloading."""
    pass


class InferenceTimeoutError(LLMProviderError):
    """Raised when inference exceeds the allowed timeout."""
    pass


class BaseLLMProvider(abc.ABC):
    """
    Abstract Base Class for local LLM providers (LM Studio, Ollama).
    Provides a standardized interface for model lifecycle and inference operations.
    """

    def __init__(self, base_url: str, default_model: str, timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    @abc.abstractmethod
    async def load_model(
        self,
        model_id: Optional[str] = None,
        context_length: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Loads the specified model into GPU memory.
        Returns a dict containing load statistics, e.g. {'instance_id': ..., 'load_time_seconds': ...}
        """
        pass

    @abc.abstractmethod
    async def unload_model(
        self,
        model_id: Optional[str] = None,
        instance_id: Optional[str] = None,
        **kwargs: Any
    ) -> bool:
        """
        Unloads the specified model from GPU memory.
        Returns True if unloaded and verified.
        """
        pass

    @abc.abstractmethod
    async def is_model_loaded(self, model_id: Optional[str] = None) -> bool:
        """
        Checks whether the specified model is currently loaded in the runtime memory.
        """
        pass

    @abc.abstractmethod
    async def generate_chat(
        self,
        messages: List[ChatMessage],
        options: Optional[InferenceOptions] = None,
        model_id: Optional[str] = None
    ) -> LLMResponse:
        """
        Executes a chat inference request against the loaded model.
        """
        pass

    @abc.abstractmethod
    async def get_inventory(self) -> List[ModelInfo]:
        """
        Returns an inventory of downloaded models and their load statuses.
        """
        pass

    @abc.abstractmethod
    async def get_health(self) -> ProviderHealth:
        """
        Checks connectivity and health of the provider runtime.
        """
        pass

    async def health_check(self) -> bool:
        """
        Convenience method returning True if provider is reachable, False otherwise.
        """
        try:
            health = await self.get_health()
            return bool(health.is_online)
        except Exception:
            return False
