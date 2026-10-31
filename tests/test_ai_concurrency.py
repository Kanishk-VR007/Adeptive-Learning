import asyncio
import time
import pytest
from typing import Any, Dict, List, Optional

from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.orchestration import ModelOrchestrationService
from app.ai.providers.base import BaseLLMProvider
from app.ai.schemas import (
    ChatMessage,
    ExecutionState,
    InferenceOptions,
    LearningTurnInput,
    LearningTurnOutput,
    LLMResponse,
    ModelInfo,
    ProviderHealth,
)


class ConcurrencyTestingProvider(BaseLLMProvider):
    def __init__(self, name: str, shared_tracker: Dict[str, Any]):
        super().__init__(base_url=f"http://{name}:1234", default_model=name)
        self.name = name
        self.tracker = shared_tracker
        self.is_loaded_state = False

    async def load_model(self, model_id: Optional[str] = None, context_length: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        self.tracker["active_model_count"] += 1
        self.tracker["max_simultaneous_models"] = max(
            self.tracker["max_simultaneous_models"], self.tracker["active_model_count"]
        )
        await asyncio.sleep(0.01)
        self.is_loaded_state = True
        return {"instance_id": f"{self.name}-inst", "load_time_seconds": 0.01}

    async def unload_model(self, model_id: Optional[str] = None, instance_id: Optional[str] = None, **kwargs) -> bool:
        await asyncio.sleep(0.01)
        self.is_loaded_state = False
        self.tracker["active_model_count"] = max(0, self.tracker["active_model_count"] - 1)
        return True

    async def is_model_loaded(self, model_id: Optional[str] = None) -> bool:
        return self.is_loaded_state

    async def generate_chat(self, messages: List[ChatMessage], options: Optional[InferenceOptions] = None, model_id: Optional[str] = None) -> LLMResponse:
        self.tracker["active_inference_count"] += 1
        self.tracker["max_simultaneous_inferences"] = max(
            self.tracker["max_simultaneous_inferences"], self.tracker["active_inference_count"]
        )
        self.tracker["total_inferences"] += 1
        # Extract turn index from user content
        user_content = messages[-1].content
        turn_token = "Turn "
        turn_idx = user_content[user_content.find(turn_token) + len(turn_token) : user_content.find(turn_token) + len(turn_token) + 2].strip()

        await asyncio.sleep(0.02)
        self.tracker["active_inference_count"] -= 1

        if self.name == "deepseek":
            content = (
                f'{{\n'
                f'  "answer_interpretation": "Turn {turn_idx} evaluated",\n'
                f'  "reasoning_analysis": "Diagnostic for Turn {turn_idx}",\n'
                f'  "identified_misconception": null,\n'
                f'  "conceptual_correctness": true,\n'
                f'  "recommended_learning_intervention": "Next concept",\n'
                f'  "diagnostic_explanation": "Explanation for Turn {turn_idx}",\n'
                f'  "suggested_follow_up_question": "Follow-up for {turn_idx}"\n'
                f'}}'
            )
        else:
            content = (
                f'{{\n'
                f'  "friendly_feedback": "Great job on Turn {turn_idx}!",\n'
                f'  "socratic_hint": null,\n'
                f'  "formatted_next_question": "Next probe for Turn {turn_idx}",\n'
                f'  "explanation": "Clear explanation for Turn {turn_idx}",\n'
                f'  "conceptual_correctness": true\n'
                f'}}'
            )
        return LLMResponse(content=content)

    async def get_inventory(self) -> List[ModelInfo]:
        return [ModelInfo(model_id=self.name, name=self.name, is_loaded=self.is_loaded_state, runtime="fake")]

    async def get_health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, is_online=True, base_url=self.base_url)


@pytest.mark.asyncio
async def test_high_concurrency_stress_queue():
    """
    Simulates 10 concurrent student learning requests arriving simultaneously.
    Verifies:
    1. Requests are queued cleanly.
    2. Zero deadlock, zero lost requests (all 10 complete with matching turn results).
    3. At no point are 2 models loaded simultaneously on the GPU (max_simultaneous_models == 1).
    4. At no point are 2 inferences running simultaneously (max_simultaneous_inferences == 1).
    5. State returns to IDLE.
    """
    shared_tracker = {
        "active_model_count": 0,
        "max_simultaneous_models": 0,
        "active_inference_count": 0,
        "max_simultaneous_inferences": 0,
        "total_inferences": 0,
    }

    ds = ConcurrencyTestingProvider("deepseek", shared_tracker)
    llama = ConcurrencyTestingProvider("llama", shared_tracker)
    monitor = GPUResourceMonitor(enabled=False)
    manager = GPUExecutionManager(deepseek_provider=ds, llama_provider=llama, monitor=monitor)
    service = ModelOrchestrationService(execution_manager=manager, deepseek_provider=ds, llama_provider=llama)

    async def student_turn(idx: int) -> LearningTurnOutput:
        inp = LearningTurnInput(
            student_id=100 + idx,
            concept_name=f"Concept Turn {idx}",
            question_text=f"Question for Turn {idx}",
            expected_answer=f"Answer {idx}",
            student_answer=f"Answer {idx}",
        )
        return await service.process_learning_turn(inp)

    # Launch 10 simultaneous requests
    tasks = [student_turn(i) for i in range(10)]
    results: List[LearningTurnOutput] = await asyncio.gather(*tasks)

    # 1. All 10 requests completed
    assert len(results) == 10
    for i, res in enumerate(results):
        assert res.success is True, f"Turn {i} failed: {res.error_message}"
        assert f"Turn {i}" in res.reasoning.answer_interpretation
        assert f"Turn {i}" in res.formatted_response.friendly_feedback

    # 2. Strict mutual exclusion guarantee
    assert shared_tracker["max_simultaneous_models"] == 1
    assert shared_tracker["max_simultaneous_inferences"] == 1

    # 3. Exactly 2 inferences per turn (1 DeepSeek + 1 Llama) * 10 turns = 20 inferences
    assert shared_tracker["total_inferences"] == 20

    # 4. Clean final state
    assert manager.state == ExecutionState.IDLE
    assert not manager._mutex.locked()
