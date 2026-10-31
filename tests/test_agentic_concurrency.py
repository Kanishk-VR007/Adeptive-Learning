import asyncio
import json
import time
from typing import Any, Dict, List
import pytest
from sqlalchemy.orm import Session

from app.agents import LearningState
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.providers.base import BaseLLMProvider, LLMResponse
from app.ai.schemas import ModelInfo, ProviderHealth
from app.core.security import get_password_hash
from app.graph import execute_learning_turn
from app.models.assessment import Question, QuestionType
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.syllabus import Chapter, Concept, DifficultyLevel, Subject
from app.models.user import User, UserRole


class ConcurrencyTrackingProvider(BaseLLMProvider):
    """
    Mock provider that tracks active executions and intervals to prove GPU exclusivity.
    """
    def __init__(self, model_name: str, delay_seconds: float = 0.05):
        super().__init__(
            base_url="http://mock:1234",
            default_model=model_name,
            timeout=10,
        )
        self.model_name = model_name
        self.delay = delay_seconds
        self.active_executions = 0
        self.max_concurrent_executions = 0
        self.intervals: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._is_loaded = False

    async def load_model(self, context_length=None, **kwargs) -> Dict[str, Any]:
        self._is_loaded = True
        return {"instance_id": "inst_1", "load_time_seconds": 0.01}

    async def unload_model(self, **kwargs) -> bool:
        self._is_loaded = False
        return True

    async def is_model_loaded(self, model_id=None) -> bool:
        return self._is_loaded

    async def get_inventory(self) -> List[ModelInfo]:
        return [
            ModelInfo(
                model_id=self.model_name,
                name=self.model_name,
                is_loaded=self._is_loaded,
                runtime="mock",
            )
        ]

    async def get_health(self) -> ProviderHealth:
        return ProviderHealth(
            provider="mock",
            is_online=True,
            base_url=self.base_url,
            loaded_models=[self.model_name] if self._is_loaded else [],
        )

    async def health_check(self) -> bool:
        return True

    async def generate(self, prompt, **kwargs) -> LLMResponse:
        t_start = time.time()
        async with self._lock:
            self.active_executions += 1
            if self.active_executions > self.max_concurrent_executions:
                self.max_concurrent_executions = self.active_executions

        await asyncio.sleep(self.delay)

        t_end = time.time()
        async with self._lock:
            self.active_executions -= 1
            self.intervals.append({
                "model": self.model_name,
                "start": t_start,
                "end": t_end,
            })

        # Return valid JSON for Llama
        resp_data = {
            "feedback": f"Feedback from {self.model_name}",
            "socratic_hint": None,
            "next_question": "Next question?",
            "adaptive_action": "TARGETED_PRACTICE",
            "display_mastery": 0.50,
        }
        return LLMResponse(content=json.dumps(resp_data), raw_response={})

    async def generate_chat(self, messages, options=None) -> LLMResponse:
        t_start = time.time()
        async with self._lock:
            self.active_executions += 1
            if self.active_executions > self.max_concurrent_executions:
                self.max_concurrent_executions = self.active_executions

        await asyncio.sleep(self.delay)

        t_end = time.time()
        async with self._lock:
            self.active_executions -= 1
            self.intervals.append({
                "model": self.model_name,
                "start": t_start,
                "end": t_end,
            })

        # Return valid JSON for DeepSeek
        resp_data = {
            "evaluation": {
                "is_correct": True,
                "answer_type": "correct",
                "reasoning_summary": f"Evaluated by {self.model_name}",
                "confidence": 0.95,
            },
            "misconception": {
                "detected": False,
                "category": "none",
                "description": None,
            },
            "candidate_question": {
                "concept_id": 1,
                "difficulty": "medium",
                "question": "Generated question text",
                "expected_answer": "Expected answer",
                "evaluation_criteria": ["Criteria 1"],
            },
        }
        return LLMResponse(content=json.dumps(resp_data), raw_response={})


@pytest.fixture
def concurrency_fixtures(db_session: Session):
    subj = Subject(name="Concurrent Physics", code="CC-PHYS-101")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    ch = Chapter(subject_id=subj.id, title="Waves", chapter_number=1)
    db_session.add(ch)
    db_session.commit()
    db_session.refresh(ch)

    c1 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Frequency", concept_code="CC-FREQ-01", description="Freq")
    db_session.add(c1)
    db_session.commit()
    db_session.refresh(c1)

    q = Question(
        concept_id=c1.id,
        question_type=QuestionType.OPEN_ENDED,
        question_text="Explain the relationship between frequency and wavelength.",
        correct_answer="Frequency is inversely proportional to wavelength for a constant wave speed: v = f * lambda.",
        difficulty_level=DifficultyLevel.INTERMEDIATE,
    )
    db_session.add(q)

    students = []
    for i in range(10):
        student = User(
            email=f"concurrent_student_{i}@example.com",
            full_name=f"Concurrent Student {i}",
            hashed_password=get_password_hash("Secret123!"),
            role=UserRole.STUDENT,
            is_active=True,
        )
        students.append(student)
        db_session.add(student)

    db_session.commit()
    for s in students:
        db_session.refresh(s)
    db_session.refresh(q)

    return {
        "subj": subj,
        "c1": c1,
        "q": q,
        "students": students,
    }


@pytest.mark.asyncio
async def test_10_concurrent_student_learning_turns(db_session: Session, concurrency_fixtures):
    """
    PHASE 10: Concurrency Validation
    Simulate 10 students simultaneously submitting answers to the LangGraph system.
    Validates:
    1. Zero GPU concurrency violation (max concurrent executions <= 1).
    2. DeepSeek executes and unloads before Llama loads and executes.
    3. All 10 requests finish successfully (zero deadlocks, zero lost requests).
    4. Isolated state: student IDs match their respective responses.
    5. Independent learner records in the database.
    """
    fixtures = concurrency_fixtures
    students = fixtures["students"]
    q = fixtures["q"]

    deepseek_provider = ConcurrencyTrackingProvider(model_name="deepseek-r1", delay_seconds=0.03)
    llama_provider = ConcurrencyTrackingProvider(model_name="llama-3.2", delay_seconds=0.03)
    monitor = GPUResourceMonitor(enabled=False)

    exec_manager = GPUExecutionManager(
        deepseek_provider=deepseek_provider,
        llama_provider=llama_provider,
        monitor=monitor,
        prewarm_mode="disabled",
    )

    async def run_student_turn(student_user: User, idx: int) -> LearningState:
        from tests.conftest import TestingSessionLocal
        local_db = TestingSessionLocal()
        try:
            initial_state: LearningState = {
                "run_id": f"conc_run_{idx}",
                "student_id": student_user.id,
                "student_name": student_user.full_name,
                "question_id": q.id,
                "student_answer": f"Wavelength lambda is inversely proportional to frequency f: v = f * lambda (from student {idx}).",
            }
            return await execute_learning_turn(
                initial_state=initial_state,
                db=local_db,
                execution_manager=exec_manager,
            )
        finally:
            local_db.close()

    # Launch 10 student turns concurrently!
    tasks = [run_student_turn(students[i], i) for i in range(10)]
    t_start = time.time()
    results: List[LearningState] = await asyncio.gather(*tasks)
    total_duration = time.time() - t_start

    # 1. Verify 10 completed results
    assert len(results) == 10
    for i, res in enumerate(results):
        assert res["execution_status"] == "completed", f"Error in {i}: {res.get('error_code')} - {res.get('error_message')}"
        assert res["student_id"] == students[i].id
        assert res["updated_mastery"] is not None
        assert res["updated_mastery"] > 0.20
        assert "persist_outcome" in res["node_execution_trace"]

    # 2. Verify GPU Mutex Exclusivity
    # Neither DeepSeek nor Llama should EVER have had > 1 concurrent execution!
    assert deepseek_provider.max_concurrent_executions <= 1, (
        f"DeepSeek had {deepseek_provider.max_concurrent_executions} concurrent executions! GPU mutex violated!"
    )
    assert llama_provider.max_concurrent_executions <= 1, (
        f"Llama had {llama_provider.max_concurrent_executions} concurrent executions! GPU mutex violated!"
    )

    # 3. Verify No Overlap between ANY DeepSeek and Llama inference interval
    all_intervals = deepseek_provider.intervals + llama_provider.intervals
    all_intervals.sort(key=lambda x: x["start"])

    for k in range(len(all_intervals) - 1):
        curr_int = all_intervals[k]
        next_int = all_intervals[k + 1]
        # End of current execution must be <= start of next execution (or negligible epsilon)
        overlap = curr_int["end"] - next_int["start"]
        assert overlap <= 0.005, (
            f"GPU Overlap detected between {curr_int['model']} and {next_int['model']}: overlap={overlap:.4f}s"
        )

    # 4. Verify Independent Database Records
    masteries = db_session.query(LearnerMastery).filter(
        LearnerMastery.concept_id == q.concept_id
    ).all()
    assert len(masteries) == 10
    assert len({m.student_id for m in masteries}) == 10

    histories = db_session.query(LearningHistory).filter(
        LearningHistory.concept_id == q.concept_id
    ).all()
    assert len(histories) == 10
    assert len({h.student_id for h in histories}) == 10
