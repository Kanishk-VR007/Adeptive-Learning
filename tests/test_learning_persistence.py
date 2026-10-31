import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.orm import Session

from app.agents import LearningState
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.providers.base import LLMResponse
from app.core.security import get_password_hash
from app.graph import get_compiled_graph, execute_learning_turn
from app.models.assessment import Question, QuestionType, LearnerResponse
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.syllabus import Chapter, Concept, DifficultyLevel, Subject
from app.models.user import User, UserRole


@pytest.fixture
def persistence_fixtures(db_session: Session):
    subj = Subject(name="Persistence Physics", code="P-PHYS-101")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    ch = Chapter(subject_id=subj.id, title="Circuits", chapter_number=1)
    db_session.add(ch)
    db_session.commit()
    db_session.refresh(ch)

    c1 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Resistance", concept_code="P-RES-01", description="Ohm")
    db_session.add(c1)
    db_session.commit()
    db_session.refresh(c1)

    q1 = Question(
        concept_id=c1.id,
        question_type=QuestionType.MCQ,
        question_text="What is unit of resistance?",
        question_options=[{"id": "A", "text": "Ohm"}, {"id": "B", "text": "Volt"}],
        correct_answer="A",
        difficulty_level=DifficultyLevel.BEGINNER,
    )
    db_session.add(q1)

    student1 = User(
        email="persist_student1@example.com",
        full_name="Persist Student 1",
        hashed_password=get_password_hash("Secret123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    student2 = User(
        email="persist_student2@example.com",
        full_name="Persist Student 2",
        hashed_password=get_password_hash("Secret123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add_all([student1, student2])
    db_session.commit()
    db_session.refresh(student1)
    db_session.refresh(student2)
    db_session.refresh(q1)

    return {
        "student1": student1,
        "student2": student2,
        "c1": c1,
        "q1": q1,
    }


def _mock_manager():
    mgr = MagicMock(spec=GPUExecutionManager)
    llama_payload = {
        "feedback": "Correct!",
        "socratic_hint": None,
        "next_question": None,
        "adaptive_action": "TARGETED_PRACTICE",
        "display_mastery": 0.50,
    }
    mgr.execute_llama = AsyncMock(return_value={"result": LLMResponse(content=json.dumps(llama_payload), raw_response={}), "metrics": {}})
    mgr.get_status = MagicMock(return_value=MagicMock(state="idle", active_model=None, monitoring_enabled=True))
    return mgr


@pytest.mark.asyncio
async def test_graph_checkpoint_persistence_and_inspection(db_session: Session, persistence_fixtures):
    """Verify that graph checkpoints are saved under thread_id."""
    fixtures = persistence_fixtures
    student = fixtures["student1"]
    q1 = fixtures["q1"]
    checkpointer = MemorySaver()
    exec_mgr = _mock_manager()

    initial_state: LearningState = {
        "session_id": 10,
        "student_id": student.id,
        "question_id": q1.id,
        "student_answer": "A",
    }

    turn1 = await execute_learning_turn(
        initial_state=initial_state,
        db=db_session,
        execution_manager=exec_mgr,
        checkpointer=checkpointer,
    )

    thread_id = f"session_10_student_{student.id}"
    graph = get_compiled_graph(checkpointer=checkpointer)
    snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
    assert snapshot is not None
    assert snapshot.values.get("student_id") == student.id
    assert snapshot.values.get("execution_status") == "completed"


@pytest.mark.asyncio
async def test_repeated_execution_idempotency_prevents_double_counting(db_session: Session, persistence_fixtures):
    """
    Ensures that retrying an execution with the same evidence does NOT double count
    or corrupt student mastery or history records.
    """
    fixtures = persistence_fixtures
    student = fixtures["student1"]
    q1 = fixtures["q1"]
    exec_mgr = _mock_manager()

    initial_state: LearningState = {
        "session_id": 11,
        "student_id": student.id,
        "question_id": q1.id,
        "student_answer": "A",
    }

    # Run turn 1
    res1 = await execute_learning_turn(
        initial_state=initial_state,
        db=db_session,
        execution_manager=exec_mgr,
    )
    m1_val = res1["updated_mastery"]
    evidence_id = res1["evidence_id"]
    assert evidence_id is not None

    mastery_record_1 = db_session.query(LearnerMastery).filter(
        LearnerMastery.student_id == student.id,
        LearnerMastery.concept_id == q1.concept_id,
    ).first()
    assert mastery_record_1.total_attempts == 1

    # Retry the exact same turn state with identical evidence_id (simulating node retry/recovery)
    retry_state: LearningState = dict(res1)
    res2 = await execute_learning_turn(
        initial_state=retry_state,
        db=db_session,
        execution_manager=exec_mgr,
    )

    db_session.refresh(mastery_record_1)
    # MUST NOT have incremented total_attempts or shifted mastery further
    assert mastery_record_1.total_attempts == 1
    assert round(mastery_record_1.current_mastery, 4) == round(m1_val, 4)

    # Check LearnerResponse table has not duplicated records
    responses = db_session.query(LearnerResponse).filter(
        LearnerResponse.user_id == student.id,
        LearnerResponse.question_id == q1.id,
    ).all()
    assert len(responses) == 1


@pytest.mark.asyncio
async def test_multi_student_separate_thread_isolation(db_session: Session, persistence_fixtures):
    """
    Ensures that two students working concurrently have strictly separated checkpoints
    and independent thread_ids.
    """
    fixtures = persistence_fixtures
    s1 = fixtures["student1"]
    s2 = fixtures["student2"]
    q1 = fixtures["q1"]
    checkpointer = MemorySaver()
    exec_mgr = _mock_manager()

    state_s1: LearningState = {
        "session_id": 20,
        "student_id": s1.id,
        "question_id": q1.id,
        "student_answer": "A",  # Correct
    }
    state_s2: LearningState = {
        "session_id": 21,
        "student_id": s2.id,
        "question_id": q1.id,
        "student_answer": "B",  # Incorrect
    }

    turn_s1 = await execute_learning_turn(state_s1, db_session, exec_mgr, checkpointer)
    turn_s2 = await execute_learning_turn(state_s2, db_session, exec_mgr, checkpointer)

    graph = get_compiled_graph(checkpointer=checkpointer)
    snap1 = graph.get_state({"configurable": {"thread_id": f"session_20_student_{s1.id}"}})
    assert snap1.values["student_id"] == s1.id
    assert snap1.values["evaluation_result"]["is_correct"] is True

    snap2 = graph.get_state({"configurable": {"thread_id": f"session_21_student_{s2.id}"}})
    assert snap2.values["student_id"] == s2.id
    assert snap2.values["evaluation_result"]["is_correct"] is False
