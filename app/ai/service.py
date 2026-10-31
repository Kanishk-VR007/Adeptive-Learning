from typing import Optional
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.orchestration import ModelOrchestrationService
from app.ai.providers.lmstudio import LMStudioProvider
from app.ai.providers.ollama import OllamaProvider
from app.core.config import settings

_monitor: Optional[GPUResourceMonitor] = None
_lmstudio_provider: Optional[LMStudioProvider] = None
_ollama_provider: Optional[OllamaProvider] = None
_execution_manager: Optional[GPUExecutionManager] = None
_orchestration_service: Optional[ModelOrchestrationService] = None


def get_gpu_monitor() -> GPUResourceMonitor:
    global _monitor
    if _monitor is None:
        _monitor = GPUResourceMonitor(enabled=settings.GPU_MONITORING_ENABLED)
    return _monitor


def get_lmstudio_provider() -> LMStudioProvider:
    global _lmstudio_provider
    if _lmstudio_provider is None:
        _lmstudio_provider = LMStudioProvider(
            base_url=settings.LMSTUDIO_BASE_URL,
            default_model=settings.LMSTUDIO_MODEL,
            api_token=settings.LMSTUDIO_API_TOKEN,
            timeout=settings.MODEL_REQUEST_TIMEOUT,
            load_timeout=settings.MODEL_LOAD_TIMEOUT,
            unload_timeout=settings.MODEL_UNLOAD_TIMEOUT,
            gpu_offload=settings.LMSTUDIO_GPU_OFFLOAD,
        )
    return _lmstudio_provider


def get_ollama_provider() -> OllamaProvider:
    global _ollama_provider
    if _ollama_provider is None:
        _ollama_provider = OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            default_model=settings.OLLAMA_MODEL,
            timeout=settings.MODEL_REQUEST_TIMEOUT,
            load_timeout=settings.MODEL_LOAD_TIMEOUT,
            unload_timeout=settings.MODEL_UNLOAD_TIMEOUT,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )
    return _ollama_provider


def get_gpu_execution_manager() -> GPUExecutionManager:
    global _execution_manager
    if _execution_manager is None:
        _execution_manager = GPUExecutionManager(
            deepseek_provider=get_lmstudio_provider(),
            llama_provider=get_ollama_provider(),
            monitor=get_gpu_monitor(),
            prewarm_mode=settings.GPU_PREWARM_MODE,
        )
    return _execution_manager


def get_orchestration_service() -> ModelOrchestrationService:
    global _orchestration_service
    if _orchestration_service is None:
        _orchestration_service = ModelOrchestrationService(
            execution_manager=get_gpu_execution_manager(),
            deepseek_provider=get_lmstudio_provider(),
            llama_provider=get_ollama_provider(),
        )
    return _orchestration_service
