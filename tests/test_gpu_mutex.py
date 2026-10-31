import asyncio
import time
import pytest
from typing import Any, Dict, List, Optional

from app.ai.gpu.execution_manager import (
    GPUExecutionManager,
    GPUExecutionError,
    InvalidStateTransitionError,
)
from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.providers.base import BaseLLMProvider
from app.ai.schemas import (
    ChatMessage,
    ExecutionState,
    InferenceOptions,
    LLMResponse,
    ModelInfo,
    ProviderHealth,
)


class FakeMockLLMProvider(BaseLLMProvider):
    """
    Fake LLM Provider for testing GPU execution mutex and sequential intervals.
    Records active load, inference, and unload timestamps.
    """

    def __init__(self, name: str, simulated_delay: float = 0.05):
        super().__init__(base_url=f"http://fake-{name}:1234", default_model=name)
        self.name = name
        self.simulated_delay = simulated_delay
        self.is_loaded_state = False
        self.active_intervals: List[Dict[str, float]] = []
        self._current_start: Optional[float] = None
        self.load_fail = False
        self.unload_fail = False
        self.infer_fail = False

    async def load_model(self, model_id: Optional[str] = None, context_length: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        if self.load_fail:
            raise GPUExecutionError(f"Simulated load failure for {self.name}")
        await asyncio.sleep(self.simulated_delay)
        self.is_loaded_state = True
        self._current_start = time.time()
        return {"instance_id": f"{self.name}-inst", "load_time_seconds": self.simulated_delay}

    async def unload_model(self, model_id: Optional[str] = None, instance_id: Optional[str] = None, **kwargs) -> bool:
        if self.unload_fail:
            raise GPUExecutionError(f"Simulated unload failure for {self.name}")
        await asyncio.sleep(self.simulated_delay)
        if self._current_start is not None:
            self.active_intervals.append({"start": self._current_start, "end": time.time()})
            self._current_start = None
        self.is_loaded_state = False
        return True

    async def is_model_loaded(self, model_id: Optional[str] = None) -> bool:
        return self.is_loaded_state

    async def generate_chat(self, messages: List[ChatMessage], options: Optional[InferenceOptions] = None, model_id: Optional[str] = None) -> LLMResponse:
        if self.infer_fail:
            raise GPUExecutionError(f"Simulated inference failure for {self.name}")
        await asyncio.sleep(self.simulated_delay)
        return LLMResponse(content=f"Output from {self.name}")

    async def get_inventory(self) -> List[ModelInfo]:
        return [ModelInfo(model_id=self.name, name=self.name, is_loaded=self.is_loaded_state, runtime="fake")]

    async def get_health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, is_online=True, base_url=self.base_url)


@pytest.fixture
def fake_providers():
    ds = FakeMockLLMProvider("deepseek", simulated_delay=0.03)
    llama = FakeMockLLMProvider("llama", simulated_delay=0.03)
    monitor = GPUResourceMonitor(enabled=False)
    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=monitor)
    return ds, llama, manager


@pytest.mark.asyncio
async def test_sequential_execution_no_overlap(fake_providers):
    ds, llama, manager = fake_providers

    async def ds_task():
        return await ds.generate_chat([ChatMessage(role="user", content="reason")])

    async def llama_task(reasoning):
        return await llama.generate_chat([ChatMessage(role="user", content="format")])

    result = await manager.execute_turn(reasoning_task=ds_task, formatting_task=llama_task)

    assert result["reasoning_result"].content == "Output from deepseek"
    assert result["formatting_result"].content == "Output from llama"
    assert manager.state == ExecutionState.IDLE

    # Verify that active intervals of DeepSeek and Llama never overlap!
    assert len(ds.active_intervals) >= 1
    assert len(llama.active_intervals) >= 1

    ds_interval = ds.active_intervals[0]
    llama_interval = llama.active_intervals[0]

    # DeepSeek must completely unload before Llama starts loading
    assert ds_interval["end"] <= llama_interval["start"]


@pytest.mark.asyncio
async def test_concurrent_requests_are_queued_and_never_overlap(fake_providers):
    ds, llama, manager = fake_providers
    active_now = 0
    max_active_simultaneous = 0

    async def run_student_turn(turn_id: int):
        nonlocal active_now, max_active_simultaneous

        async def ds_task():
            nonlocal active_now, max_active_simultaneous
            active_now += 1
            max_active_simultaneous = max(max_active_simultaneous, active_now)
            await asyncio.sleep(0.02)
            active_now -= 1
            return f"ds-{turn_id}"

        async def llama_task(res):
            nonlocal active_now, max_active_simultaneous
            active_now += 1
            max_active_simultaneous = max(max_active_simultaneous, active_now)
            await asyncio.sleep(0.02)
            active_now -= 1
            return f"llama-{turn_id}"

        return await manager.execute_turn(reasoning_task=ds_task, formatting_task=llama_task)

    # Launch 5 concurrent student turns simultaneously
    results = await asyncio.gather(*(run_student_turn(i) for i in range(5)))

    assert len(results) == 5
    # Crucial assertion: at no point during the 5 turns did more than 1 model execute simultaneously!
    assert max_active_simultaneous == 1
    assert manager.state == ExecutionState.IDLE


@pytest.mark.asyncio
async def test_lock_released_on_exception_and_recovery(fake_providers):
    ds, llama, manager = fake_providers
    ds.infer_fail = True  # Trigger failure inside DeepSeek inference

    async def ds_task():
        return await ds.generate_chat([ChatMessage(role="user", content="reason")])

    async def llama_task(reasoning):
        return await llama.generate_chat([ChatMessage(role="user", content="format")])

    with pytest.raises(GPUExecutionError):
        await manager.execute_turn(reasoning_task=ds_task, formatting_task=llama_task)

    # Mutex lock must be released, state recovered back to IDLE
    assert not manager._mutex.locked()
    assert manager.state == ExecutionState.IDLE

    # Next request must be able to succeed normally
    ds.infer_fail = False
    result = await manager.execute_turn(reasoning_task=ds_task, formatting_task=llama_task)
    assert result["reasoning_result"].content == "Output from deepseek"


@pytest.mark.asyncio
async def test_cancellation_releases_lock(fake_providers):
    ds, llama, manager = fake_providers

    async def long_task():
        async def ds_task():
            await asyncio.sleep(2.0)
            return "ok"

        async def llama_task(res):
            return "ok"

        await manager.execute_turn(reasoning_task=ds_task, formatting_task=llama_task)

    task = asyncio.create_task(long_task())
    await asyncio.sleep(0.05)  # Let it enter
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # Lock must be released
    assert not manager._mutex.locked()
    assert manager.state == ExecutionState.IDLE


@pytest.mark.asyncio
async def test_illegal_state_transition_raises():
    ds = FakeMockLLMProvider("deepseek")
    llama = FakeMockLLMProvider("llama")
    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=GPUResourceMonitor(enabled=False))

    # IDLE -> LLAMA_ACTIVE is illegal (must go through LLAMA_LOADING or DEEPSEEK first)
    with pytest.raises(InvalidStateTransitionError):
        manager._transition_to(ExecutionState.LLAMA_ACTIVE)

    assert manager.state == ExecutionState.ERROR
