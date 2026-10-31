from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_any_authenticated_user, require_teacher
from app.ai.schemas import (
    GPUExecutionStatus,
    GPUMemorySnapshot,
    LearningTurnInput,
    LearningTurnOutput,
    ModelInfo,
    ProviderHealth,
)
from app.ai.service import (
    get_gpu_execution_manager,
    get_gpu_monitor,
    get_lmstudio_provider,
    get_ollama_provider,
    get_orchestration_service,
)
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["AI: Local Infrastructure & GPU Management"])


@router.get(
    "/health",
    response_model=Dict[str, ProviderHealth],
    summary="Check health and connectivity of local AI runtimes",
)
async def get_ai_health(
    current_user: User = Depends(require_any_authenticated_user),
) -> Dict[str, ProviderHealth]:
    """
    Inspects connectivity and loaded models for both LM Studio and Ollama local runtimes.
    """
    lmstudio = get_lmstudio_provider()
    ollama = get_ollama_provider()

    lm_health = await lmstudio.get_health()
    ollama_health = await ollama.get_health()

    return {
        "lmstudio": lm_health,
        "ollama": ollama_health,
    }


@router.get(
    "/models",
    response_model=List[ModelInfo],
    summary="List available and loaded models across local runtimes",
)
async def get_available_models(
    current_user: User = Depends(require_any_authenticated_user),
) -> List[ModelInfo]:
    """
    Retrieves the complete inventory of downloaded and loaded models across LM Studio and Ollama.
    """
    lmstudio = get_lmstudio_provider()
    ollama = get_ollama_provider()

    models: List[ModelInfo] = []
    try:
        models.extend(await lmstudio.get_inventory())
    except Exception as e:
        # If LM Studio server is offline, return what we have without crashing
        pass

    try:
        models.extend(await ollama.get_inventory())
    except Exception as e:
        # If Ollama server is offline, continue
        pass

    return models


@router.get(
    "/gpu-status",
    response_model=GPUMemorySnapshot,
    summary="Query real-time GPU VRAM, utilization, and temperature",
)
def get_gpu_status(
    current_user: User = Depends(require_any_authenticated_user),
) -> GPUMemorySnapshot:
    """
    Queries current GPU memory metrics using NVIDIA NVML or nvidia-smi fallback.
    """
    monitor = get_gpu_monitor()
    return monitor.get_memory_snapshot()


@router.get(
    "/execution-status",
    response_model=GPUExecutionStatus,
    summary="Query current GPU execution mutex and state machine status",
)
def get_execution_status(
    current_user: User = Depends(require_any_authenticated_user),
) -> GPUExecutionStatus:
    """
    Returns the real-time execution manager state, active model, queue size, and prewarm mode.
    """
    manager = get_gpu_execution_manager()
    return manager.get_status()


@router.post(
    "/test-inference",
    response_model=LearningTurnOutput,
    summary="Execute a test learning turn through the sequential GPU pipeline (Teachers only)",
)
async def test_learning_turn_inference(
    turn_in: LearningTurnInput,
    current_user: User = Depends(require_teacher),
) -> LearningTurnOutput:
    """
    Runs a test pedagogical reasoning & Socratic formatting turn through the sequential GPU execution manager.
    Strictly restricted to Teachers to prevent unauthorized GPU resource consumption.
    """
    service = get_orchestration_service()
    result = await service.process_learning_turn(turn_in)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI pipeline execution failed: {result.error_message}",
        )
    return result
