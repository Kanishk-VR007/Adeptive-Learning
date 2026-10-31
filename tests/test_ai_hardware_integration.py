import os
import time
import pytest

from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.orchestration import ModelOrchestrationService
from app.ai.providers.lmstudio import LMStudioProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.schemas import ChatMessage, ExecutionState, InferenceOptions, LearningTurnInput
from app.core.config import settings

RUN_INTEGRATION = os.environ.get("RUN_LOCAL_LLM_INTEGRATION", "").lower() in ("1", "true")
skip_reason = "Set RUN_LOCAL_LLM_INTEGRATION=1 to run tests against real local GPU runtimes."


@pytest.mark.skipif(not RUN_INTEGRATION, reason=skip_reason)
@pytest.mark.asyncio
async def test_real_hardware_deepseek_loading_and_inference():
    """TEST 1: Load DeepSeek into LM Studio, inspect GPU memory, run inference."""
    provider = LMStudioProvider(
        base_url=settings.LMSTUDIO_BASE_URL,
        default_model=settings.LMSTUDIO_MODEL,
        load_timeout=settings.MODEL_LOAD_TIMEOUT,
    )
    monitor = GPUResourceMonitor(enabled=True)

    # 1. Check health
    health = await provider.get_health()
    if not health.is_online:
        pytest.skip(f"LM Studio server is offline at {settings.LMSTUDIO_BASE_URL}")

    # 2. Load model
    t0 = time.time()
    load_res = await provider.load_model()
    load_time = time.time() - t0
    print(f"\n[REAL GPU] DeepSeek load time: {load_time:.2f}s, instance_id={load_res.get('instance_id')}")

    # 3. Inspect GPU memory
    snap = monitor.get_memory_snapshot()
    print(f"[REAL GPU] After DeepSeek load: VRAM Used={snap.used_mb}MB / {snap.total_mb}MB")
    assert snap.used_mb > 500  # Model weights loaded into GPU

    # 4. Short inference
    messages = [ChatMessage(role="user", content="What is 2+2? Answer in one word.")]
    res = await provider.generate_chat(messages=messages, options=InferenceOptions(max_tokens=100))
    print(f"[REAL GPU] DeepSeek output: '{res.content.strip()}' (took {res.stats.eval_duration_ms:.1f}ms)")
    assert len(res.content.strip()) > 0


@pytest.mark.skipif(not RUN_INTEGRATION, reason=skip_reason)
@pytest.mark.asyncio
async def test_real_hardware_deepseek_unloading():
    """TEST 2: Unload DeepSeek and verify runtime inventory & GPU memory."""
    provider = LMStudioProvider(
        base_url=settings.LMSTUDIO_BASE_URL,
        default_model=settings.LMSTUDIO_MODEL,
        unload_timeout=settings.MODEL_UNLOAD_TIMEOUT,
    )
    monitor = GPUResourceMonitor(enabled=True)

    # Unload
    t0 = time.time()
    unloaded = await provider.unload_model()
    unload_time = time.time() - t0
    print(f"\n[REAL GPU] DeepSeek unload time: {unload_time:.2f}s")
    assert unloaded is True

    # Verify inventory
    is_loaded = await provider.is_model_loaded()
    assert is_loaded is False

    snap = monitor.get_memory_snapshot()
    print(f"[REAL GPU] After DeepSeek unload: VRAM Used={snap.used_mb}MB / {snap.total_mb}MB")


@pytest.mark.skipif(not RUN_INTEGRATION, reason=skip_reason)
@pytest.mark.asyncio
async def test_real_hardware_llama_loading_and_inference():
    """TEST 3: Load Llama 3.2 through Ollama, run short inference."""
    provider = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL,
        default_model=settings.OLLAMA_MODEL,
        load_timeout=settings.MODEL_LOAD_TIMEOUT,
    )
    monitor = GPUResourceMonitor(enabled=True)

    health = await provider.get_health()
    if not health.is_online:
        pytest.skip(f"Ollama server is offline at {settings.OLLAMA_BASE_URL}")

    t0 = time.time()
    load_res = await provider.load_model()
    load_time = time.time() - t0
    print(f"\n[REAL GPU] Llama 3.2 load time: {load_time:.2f}s")

    snap = monitor.get_memory_snapshot()
    print(f"[REAL GPU] After Llama load: VRAM Used={snap.used_mb}MB / {snap.total_mb}MB")

    messages = [ChatMessage(role="user", content="Reply with JSON: {'status': 'ok'}")]
    res = await provider.generate_chat(messages=messages, options=InferenceOptions(format_json=True, max_tokens=30))
    print(f"[REAL GPU] Llama output: '{res.content.strip()}' (eval={res.stats.eval_duration_ms:.1f}ms)")
    assert "status" in res.content


@pytest.mark.skipif(not RUN_INTEGRATION, reason=skip_reason)
@pytest.mark.asyncio
async def test_real_hardware_llama_unloading():
    """TEST 4: Unload Llama via keep_alive: 0 and verify absent from /api/ps."""
    provider = OllamaProvider(
        base_url=settings.OLLAMA_BASE_URL,
        default_model=settings.OLLAMA_MODEL,
        unload_timeout=settings.MODEL_UNLOAD_TIMEOUT,
    )
    monitor = GPUResourceMonitor(enabled=True)

    t0 = time.time()
    unloaded = await provider.unload_model()
    unload_time = time.time() - t0
    print(f"\n[REAL GPU] Llama unload time: {unload_time:.2f}s")
    assert unloaded is True

    is_loaded = await provider.is_model_loaded()
    assert is_loaded is False

    snap = monitor.get_memory_snapshot()
    print(f"[REAL GPU] After Llama unload: VRAM Used={snap.used_mb}MB / {snap.total_mb}MB")


@pytest.mark.skipif(not RUN_INTEGRATION, reason=skip_reason)
@pytest.mark.asyncio
async def test_real_hardware_complete_sequential_turn():
    """TEST 5: Complete sequential turn: DeepSeek -> Unload -> Llama -> Unload."""
    monitor = GPUResourceMonitor(enabled=True)
    ds = LMStudioProvider(base_url=settings.LMSTUDIO_BASE_URL, default_model=settings.LMSTUDIO_MODEL)
    llama = OllamaProvider(base_url=settings.OLLAMA_BASE_URL, default_model=settings.OLLAMA_MODEL)
    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=monitor, prewarm_mode="disabled")
    service = ModelOrchestrationService(execution_manager=manager, deepseek_provider=ds, llama_provider=llama)

    turn_in = LearningTurnInput(
        concept_name="Newton's Second Law",
        question_text="A mass of 2 kg accelerates at 3 m/s^2. What is the net force?",
        expected_answer="6 Newtons",
        student_answer="6 N because F = m * a",
    )

    result = await service.process_learning_turn(turn_in)
    print(f"\n[REAL GPU] Complete sequential turn result: success={result.success}")
    print(f"[REAL GPU] Metrics: DeepSeek load={result.metrics.deepseek_load_ms:.0f}ms, "
          f"infer={result.metrics.deepseek_inference_ms:.0f}ms, unload={result.metrics.deepseek_unload_ms:.0f}ms | "
          f"Llama load={result.metrics.llama_load_ms:.0f}ms, infer={result.metrics.llama_inference_ms:.0f}ms, "
          f"unload={result.metrics.llama_unload_ms:.0f}ms | Peak VRAM={result.metrics.peak_vram_mb:.0f}MB, "
          f"Total Turn={result.metrics.total_turn_ms:.0f}ms")

    assert result.success is True
    assert result.reasoning is not None
    assert result.formatted_response is not None
    assert manager.state == ExecutionState.IDLE


@pytest.mark.skipif(not RUN_INTEGRATION, reason=skip_reason)
@pytest.mark.asyncio
async def test_real_hardware_repeated_switching_benchmark():
    """TEST 6: Repeated switching cycles to measure switching overhead and stability."""
    monitor = GPUResourceMonitor(enabled=True)
    ds = LMStudioProvider(base_url=settings.LMSTUDIO_BASE_URL, default_model=settings.LMSTUDIO_MODEL)
    llama = OllamaProvider(base_url=settings.OLLAMA_BASE_URL, default_model=settings.OLLAMA_MODEL)
    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=monitor, prewarm_mode="disabled")
    service = ModelOrchestrationService(execution_manager=manager, deepseek_provider=ds, llama_provider=llama)

    cycles = 2
    metrics_list = []
    for c in range(cycles):
        turn_in = LearningTurnInput(
            concept_name="Thermodynamics",
            question_text=f"Cycle {c+1}: Is heat a state function?",
            expected_answer="No, path function",
            student_answer="No, heat is a path function depending on process",
        )
        res = await service.process_learning_turn(turn_in)
        assert res.success is True
        metrics_list.append(res.metrics)

    avg_total = sum(m.total_turn_ms for m in metrics_list) / len(metrics_list)
    avg_peak = max(m.peak_vram_mb for m in metrics_list)
    print(f"\n[REAL GPU] Repeated Benchmark ({cycles} cycles): Avg Turn Duration={avg_total:.1f}ms, Peak VRAM={avg_peak:.1f}MB")
