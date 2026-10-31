import asyncio
import pytest
from typing import Any, Dict, List, Optional

from app.ai.gpu.execution_manager import (
    GPUExecutionManager,
    GPUExecutionError,
)
from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.orchestration import ModelOrchestrationService
from app.ai.providers.base import BaseLLMProvider, ModelLoadError, ModelUnloadError
from app.ai.schemas import (
    ChatMessage,
    ExecutionState,
    InferenceOptions,
    LearningTurnInput,
    LLMResponse,
    ModelInfo,
    ProviderHealth,
)


class EventTrackingProvider(BaseLLMProvider):
    """Tracks the exact lifecycle events in sequence."""

    def __init__(self, name: str, event_log: List[str]):
        super().__init__(base_url=f"http://{name}:1234", default_model=name)
        self.name = name
        self.event_log = event_log
        self.is_loaded_state = False
        self.fail_stage: Optional[str] = None

    async def load_model(self, model_id: Optional[str] = None, context_length: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        if self.fail_stage == "load":
            raise ModelLoadError(f"Simulated load failure for {self.name}")
        self.event_log.append(f"{self.name}:load")
        self.is_loaded_state = True
        return {"instance_id": f"{self.name}-inst", "load_time_seconds": 0.01}

    async def unload_model(self, model_id: Optional[str] = None, instance_id: Optional[str] = None, **kwargs) -> bool:
        if self.fail_stage == "unload":
            raise ModelUnloadError(f"Simulated unload failure for {self.name}")
        self.event_log.append(f"{self.name}:unload")
        self.is_loaded_state = False
        return True

    async def is_model_loaded(self, model_id: Optional[str] = None) -> bool:
        return self.is_loaded_state

    async def generate_chat(self, messages: List[ChatMessage], options: Optional[InferenceOptions] = None, model_id: Optional[str] = None) -> LLMResponse:
        if self.fail_stage == "inference":
            raise GPUExecutionError(f"Simulated inference failure for {self.name}")
        self.event_log.append(f"{self.name}:inference")

        if self.name == "deepseek":
            content = (
                '{\n'
                '  "answer_interpretation": "Student added voltages correctly",\n'
                '  "reasoning_analysis": "Ohm\'s law applied properly",\n'
                '  "identified_misconception": null,\n'
                '  "conceptual_correctness": true,\n'
                '  "recommended_learning_intervention": "Advance to parallel circuits",\n'
                '  "diagnostic_explanation": "V=IR relation maintained",\n'
                '  "suggested_follow_up_question": "What if resistance doubles?"\n'
                '}'
            )
        else:
            content = (
                '{\n'
                '  "friendly_feedback": "Excellent work on applying Ohm\'s Law!",\n'
                '  "socratic_hint": null,\n'
                '  "formatted_next_question": "Consider what happens if R doubles.",\n'
                '  "explanation": "Voltage scales linearly with resistance.",\n'
                '  "conceptual_correctness": true\n'
                '}'
            )
        return LLMResponse(content=content)

    async def get_inventory(self) -> List[ModelInfo]:
        return [ModelInfo(model_id=self.name, name=self.name, is_loaded=self.is_loaded_state, runtime="fake")]

    async def get_health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, is_online=True, base_url=self.base_url)


@pytest.fixture
def tracking_setup():
    event_log = []
    ds = EventTrackingProvider("deepseek", event_log)
    llama = EventTrackingProvider("llama", event_log)
    monitor = GPUResourceMonitor(enabled=False)
    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=monitor, prewarm_mode="disabled")
    service = ModelOrchestrationService(execution_manager=manager, deepseek_provider=ds, llama_provider=llama)
    return ds, llama, manager, service, event_log


@pytest.mark.asyncio
async def test_exact_sequential_event_order(tracking_setup):
    ds, llama, manager, service, event_log = tracking_setup

    turn_in = LearningTurnInput(
        concept_name="Ohm's Law",
        question_text="If V=10V and I=2A, what is R?",
        expected_answer="5 Ohms",
        student_answer="5 Ohms",
    )

    result = await service.process_learning_turn(turn_in)

    assert result.success is True
    assert result.reasoning.conceptual_correctness is True
    assert "Excellent work" in result.formatted_response.friendly_feedback

    # Mandatory sequence verification:
    expected_order = [
        "deepseek:load",
        "deepseek:inference",
        "deepseek:unload",
        "llama:load",
        "llama:inference",
        "llama:unload",
    ]
    assert event_log == expected_order
    assert manager.state == ExecutionState.IDLE


@pytest.mark.asyncio
async def test_deepseek_load_failure_recovery(tracking_setup):
    ds, llama, manager, service, event_log = tracking_setup
    ds.fail_stage = "load"

    turn_in = LearningTurnInput(
        concept_name="Gravity",
        question_text="What is g on Earth?",
        expected_answer="9.8 m/s^2",
        student_answer="9.8 m/s^2",
    )

    result = await service.process_learning_turn(turn_in)
    assert result.success is False
    assert "Simulated load failure for deepseek" in result.error_message
    assert manager.state == ExecutionState.IDLE
    # Llama was never loaded!
    assert "llama:load" not in event_log


@pytest.mark.asyncio
async def test_deepseek_inference_failure_recovery(tracking_setup):
    ds, llama, manager, service, event_log = tracking_setup
    ds.fail_stage = "inference"

    turn_in = LearningTurnInput(
        concept_name="Thermodynamics",
        question_text="What is absolute zero?",
        expected_answer="0 Kelvin",
        student_answer="0 Kelvin",
    )

    result = await service.process_learning_turn(turn_in)
    assert result.success is False
    assert manager.state == ExecutionState.IDLE
    # DeepSeek should have been unloaded during recovery
    assert "deepseek:unload" in event_log
    assert "llama:load" not in event_log


@pytest.mark.asyncio
async def test_deepseek_unload_failure_recovery(tracking_setup):
    ds, llama, manager, service, event_log = tracking_setup
    ds.fail_stage = "unload"

    turn_in = LearningTurnInput(
        concept_name="Optics",
        question_text="Speed of light?",
        expected_answer="3e8 m/s",
        student_answer="3e8 m/s",
    )

    result = await service.process_learning_turn(turn_in)
    assert result.success is False
    # Crucial: Llama must NEVER be loaded when DeepSeek fails to unload!
    assert "llama:load" not in event_log
    assert manager.state == ExecutionState.IDLE


@pytest.mark.asyncio
async def test_llama_load_failure_recovery(tracking_setup):
    ds, llama, manager, service, event_log = tracking_setup
    llama.fail_stage = "load"

    turn_in = LearningTurnInput(
        concept_name="Chemistry",
        question_text="Atomic number of C?",
        expected_answer="6",
        student_answer="6",
    )

    result = await service.process_learning_turn(turn_in)
    assert result.success is False
    assert "Simulated load failure for llama" in result.error_message
    assert manager.state == ExecutionState.IDLE


@pytest.mark.asyncio
async def test_llama_inference_failure_recovery(tracking_setup):
    ds, llama, manager, service, event_log = tracking_setup
    llama.fail_stage = "inference"

    turn_in = LearningTurnInput(
        concept_name="Biology",
        question_text="Powerhouse of cell?",
        expected_answer="Mitochondria",
        student_answer="Mitochondria",
    )

    result = await service.process_learning_turn(turn_in)
    assert result.success is False
    assert manager.state == ExecutionState.IDLE
    # Llama must have been unloaded during recovery
    assert "llama:unload" in event_log


@pytest.mark.asyncio
async def test_unexpected_model_already_resident_handled_safely(tracking_setup):
    ds, llama, manager, service, event_log = tracking_setup
    # Simulate an unexpected resident model left behind by a stale session
    ds.is_loaded_state = True
    manager._state = ExecutionState.DEEPSEEK_ACTIVE

    turn_in = LearningTurnInput(
        concept_name="Calculus",
        question_text="Derivative of x^2?",
        expected_answer="2x",
        student_answer="2x",
    )

    # Manager detects non-IDLE state, recovers, then completes successfully
    result = await service.process_learning_turn(turn_in)
    assert result.success is True
    assert manager.state == ExecutionState.IDLE
