import pytest
from typing import Any, Dict, List, Optional

from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.orchestration import ModelOrchestrationService
from app.ai.providers.base import BaseLLMProvider, ModelLoadError
from app.ai.schemas import (
    ChatMessage,
    ExecutionState,
    InferenceOptions,
    LearningTurnInput,
    LLMResponse,
    ModelInfo,
    ProviderHealth,
)


class PrewarmTrackingProvider(BaseLLMProvider):
    def __init__(self, name: str, event_log: List[str]):
        super().__init__(base_url=f"http://{name}:1234", default_model=name)
        self.name = name
        self.event_log = event_log
        self.is_loaded_state = False
        self.load_count = 0
        self.fail_prewarm = False

    async def load_model(self, model_id: Optional[str] = None, context_length: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        if self.fail_prewarm and self.load_count >= 1:
            raise ModelLoadError("Prewarm load failure")
        self.load_count += 1
        self.event_log.append(f"{self.name}:load")
        self.is_loaded_state = True
        return {"instance_id": f"{self.name}-inst", "load_time_seconds": 0.01}

    async def unload_model(self, model_id: Optional[str] = None, instance_id: Optional[str] = None, **kwargs) -> bool:
        self.event_log.append(f"{self.name}:unload")
        self.is_loaded_state = False
        return True

    async def is_model_loaded(self, model_id: Optional[str] = None) -> bool:
        return self.is_loaded_state

    async def generate_chat(self, messages: List[ChatMessage], options: Optional[InferenceOptions] = None, model_id: Optional[str] = None) -> LLMResponse:
        self.event_log.append(f"{self.name}:inference")
        if self.name == "deepseek":
            content = (
                '{"answer_interpretation": "ok", "reasoning_analysis": "ok", "identified_misconception": null, '
                '"conceptual_correctness": true, "recommended_learning_intervention": "next", "diagnostic_explanation": "ok", '
                '"suggested_follow_up_question": null}'
            )
        else:
            content = (
                '{"friendly_feedback": "Well done!", "socratic_hint": null, "formatted_next_question": null, '
                '"explanation": "ok", "conceptual_correctness": true}'
            )
        return LLMResponse(content=content)

    async def get_inventory(self) -> List[ModelInfo]:
        return [ModelInfo(model_id=self.name, name=self.name, is_loaded=self.is_loaded_state, runtime="fake")]

    async def get_health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, is_online=True, base_url=self.base_url)


@pytest.mark.asyncio
async def test_prewarming_disabled_mode():
    event_log = []
    ds = PrewarmTrackingProvider("deepseek", event_log)
    llama = PrewarmTrackingProvider("llama", event_log)
    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=GPUResourceMonitor(enabled=False), prewarm_mode="disabled")
    service = ModelOrchestrationService(execution_manager=manager, deepseek_provider=ds, llama_provider=llama)

    turn_in = LearningTurnInput(
        concept_name="Math",
        question_text="2+2?",
        expected_answer="4",
        student_answer="4",
    )

    res = await service.process_learning_turn(turn_in)
    assert res.success is True
    # In disabled mode, DeepSeek is NOT loaded again at the end
    assert event_log == [
        "deepseek:load",
        "deepseek:inference",
        "deepseek:unload",
        "llama:load",
        "llama:inference",
        "llama:unload",
    ]
    assert manager.prewarmed_model is None
    assert manager.state == ExecutionState.IDLE


@pytest.mark.asyncio
async def test_prewarming_enabled_and_reused_on_next_request():
    event_log = []
    ds = PrewarmTrackingProvider("deepseek", event_log)
    llama = PrewarmTrackingProvider("llama", event_log)
    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=GPUResourceMonitor(enabled=False), prewarm_mode="enabled")
    service = ModelOrchestrationService(execution_manager=manager, deepseek_provider=ds, llama_provider=llama)

    turn1 = LearningTurnInput(
        concept_name="Algebra",
        question_text="x+1=2, x=?",
        expected_answer="1",
        student_answer="1",
    )

    # First turn: DeepSeek load -> infer -> unload -> Llama load -> infer -> unload -> DeepSeek prewarm load!
    res1 = await service.process_learning_turn(turn1)
    assert res1.success is True
    assert manager.prewarmed_model == "deepseek"
    assert ds.is_loaded_state is True

    expected_turn1_events = [
        "deepseek:load",
        "deepseek:inference",
        "deepseek:unload",
        "llama:load",
        "llama:inference",
        "llama:unload",
        "deepseek:load",  # Prewarm!
    ]
    assert event_log == expected_turn1_events

    # Second turn arrives while student was thinking:
    # DeepSeek is ALREADY prewarmed, so it should SKIP the initial load step!
    turn2 = LearningTurnInput(
        concept_name="Algebra",
        question_text="2x=4, x=?",
        expected_answer="2",
        student_answer="2",
    )
    res2 = await service.process_learning_turn(turn2)
    assert res2.success is True

    # Turn 2 events must begin directly with deepseek:inference (no duplicate deepseek:load)!
    turn2_events = event_log[len(expected_turn1_events):]
    assert turn2_events[0] == "deepseek:inference"


@pytest.mark.asyncio
async def test_prewarmed_model_evicted_triggers_safe_reload():
    event_log = []
    ds = PrewarmTrackingProvider("deepseek", event_log)
    llama = PrewarmTrackingProvider("llama", event_log)
    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=GPUResourceMonitor(enabled=False), prewarm_mode="enabled")
    service = ModelOrchestrationService(execution_manager=manager, deepseek_provider=ds, llama_provider=llama)

    # First turn sets up prewarming
    turn1 = LearningTurnInput(concept_name="A", question_text="Q1", expected_answer="A1", student_answer="A1")
    await service.process_learning_turn(turn1)
    assert manager.prewarmed_model == "deepseek"

    # Simulate unexpected eviction (e.g., driver reset or external app)
    ds.is_loaded_state = False

    # Second turn arrives: manager detects eviction and safely reloads DeepSeek
    event_log.clear()
    turn2 = LearningTurnInput(concept_name="A", question_text="Q2", expected_answer="A2", student_answer="A2")
    res2 = await service.process_learning_turn(turn2)

    assert res2.success is True
    assert event_log[0] == "deepseek:load"
    assert event_log[1] == "deepseek:inference"


@pytest.mark.asyncio
async def test_prewarming_failure_gracefully_handled():
    event_log = []
    ds = PrewarmTrackingProvider("deepseek", event_log)
    llama = PrewarmTrackingProvider("llama", event_log)
    ds.fail_prewarm = True  # Prewarming step fails

    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=GPUResourceMonitor(enabled=False), prewarm_mode="enabled")
    service = ModelOrchestrationService(execution_manager=manager, deepseek_provider=ds, llama_provider=llama)

    turn = LearningTurnInput(concept_name="Physics", question_text="F=?", expected_answer="ma", student_answer="ma")
    res = await service.process_learning_turn(turn)

    # The student turn itself succeeded; prewarm failure degraded safely to IDLE
    assert res.success is True
    assert manager.prewarmed_model is None
    assert manager.state == ExecutionState.IDLE
