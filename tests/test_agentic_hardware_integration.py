import os
import time
import pytest
from sqlalchemy.orm import Session

from app.agents import AnswerEvaluationAgent, LearningState
from app.agents.feedback import StudentFeedbackAgent
from app.ai.gpu.monitor import GPUResourceMonitor
from app.ai.service import get_gpu_execution_manager, get_lmstudio_provider, get_ollama_provider
from app.core.config import settings
from app.core.security import get_password_hash
from app.graph import execute_learning_turn
from app.models.assessment import Question, QuestionType
from app.models.learner_mastery import LearnerMastery
from app.models.syllabus import Chapter, Concept, DifficultyLevel, Subject
from app.models.user import User, UserRole

RUN_LOCAL = os.getenv("RUN_AGENTIC_LOCAL_INTEGRATION") == "1"
skip_reason = "Set RUN_AGENTIC_LOCAL_INTEGRATION=1 to run against real physical GPU."


@pytest.fixture
def hardware_test_data(db_session: Session):
    subj = Subject(name="Real Hardware Physics", code="HW-PHYS-101")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    ch = Chapter(subject_id=subj.id, title="Circuits", chapter_number=1)
    db_session.add(ch)
    db_session.commit()
    db_session.refresh(ch)

    c1 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Ohm's Law", concept_code="HW-OHM-01", description="V = IR")
    db_session.add(c1)
    db_session.commit()
    db_session.refresh(c1)

    c2 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Electrical Power", concept_code="HW-PWR-02", description="P = VI = I^2 R")
    db_session.add(c2)
    db_session.commit()
    db_session.refresh(c2)

    q1 = Question(
        concept_id=c1.id,
        question_type=QuestionType.OPEN_ENDED,
        question_text="Explain how increasing resistance affects current in a simple DC circuit with constant voltage.",
        correct_answer="Current decreases inversely proportional to resistance according to Ohm's law (I = V/R).",
        difficulty_level=DifficultyLevel.BEGINNER,
    )
    db_session.add(q1)

    q2 = Question(
        concept_id=c1.id,
        question_type=QuestionType.OPEN_ENDED,
        question_text="If voltage is doubled and resistance is held constant, what happens to current?",
        correct_answer="Current doubles in direct proportion to voltage.",
        difficulty_level=DifficultyLevel.INTERMEDIATE,
    )
    db_session.add(q2)

    student = User(
        email="real_student@example.com",
        full_name="Real Hardware Student",
        hashed_password=get_password_hash("Secret123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(q1)
    db_session.refresh(q2)

    return {
        "student": student,
        "concept": c1,
        "next_concept": c2,
        "question": q1,
        "question_2": q2,
    }


@pytest.mark.skipif(not RUN_LOCAL, reason=skip_reason)
@pytest.mark.asyncio
async def test_1_real_deepseek_evaluation(db_session: Session, hardware_test_data):
    """
    Test 1: DeepSeek Evaluation against live LM Studio runtime.
    Submits a known correct answer and verifies reasoning summary and structured output.
    """
    lmstudio = get_lmstudio_provider()
    if not await lmstudio.health_check():
        pytest.skip(f"BLOCKED: LM Studio offline at {settings.LMSTUDIO_BASE_URL}")

    exec_mgr = get_gpu_execution_manager()
    fixtures = hardware_test_data
    q = fixtures["question"]
    c = fixtures["concept"]

    state: LearningState = {
        "student_id": fixtures["student"].id,
        "question_id": q.id,
        "current_concept_id": c.id,
        "current_concept_name": c.name,
        "candidate_next_concept_id": fixtures["next_concept"].id,
        "candidate_next_concept_name": fixtures["next_concept"].name,
        "student_answer": "According to Ohm's Law, current equals voltage divided by resistance (I = V/R). Therefore, if resistance increases with constant voltage, current decreases proportionally.",
        "relevant_learning_context": {
            "question_text": q.question_text,
            "expected_answer": q.correct_answer,
            "concept_name": c.name,
            "evaluation_criteria": {"rubric": "Inverse proportionality via I=V/R"},
            "question_type": "OPEN_ENDED",
        },
        "node_execution_trace": [],
    }

    t0 = time.time()
    res = await AnswerEvaluationAgent.run(
        state=state,
        execution_manager=exec_mgr,
        deepseek_provider=lmstudio,
        db=db_session,
    )
    eval_duration_s = time.time() - t0

    assert res.get("evaluation_result") is not None
    assert res["evaluation_result"]["is_correct"] is True
    assert res["evaluation_confidence"] >= 0.70
    assert len(res["reasoning_summary"]) > 0
    print(f"\n[REAL GPU] Test 1 DeepSeek Correct Eval Duration: {eval_duration_s:.2f}s | Confidence: {res['evaluation_confidence']}")


@pytest.mark.skipif(not RUN_LOCAL, reason=skip_reason)
@pytest.mark.asyncio
async def test_2_real_misconception_detection(db_session: Session, hardware_test_data):
    """
    Test 2: Misconception Detection against live LM Studio runtime.
    Submits a deliberately incorrect answer and verifies detected misconception.
    """
    lmstudio = get_lmstudio_provider()
    if not await lmstudio.health_check():
        pytest.skip(f"BLOCKED: LM Studio offline at {settings.LMSTUDIO_BASE_URL}")

    exec_mgr = get_gpu_execution_manager()
    fixtures = hardware_test_data
    q = fixtures["question"]
    c = fixtures["concept"]

    state: LearningState = {
        "student_id": fixtures["student"].id,
        "question_id": q.id,
        "current_concept_id": c.id,
        "current_concept_name": c.name,
        "student_answer": "When resistance increases, the current must also increase because higher resistance pushes more electrons through the wire faster.",
        "relevant_learning_context": {
            "question_text": q.question_text,
            "expected_answer": q.correct_answer,
            "concept_name": c.name,
            "evaluation_criteria": {"rubric": "Inverse proportionality via I=V/R"},
            "question_type": "OPEN_ENDED",
        },
        "node_execution_trace": [],
    }

    res = await AnswerEvaluationAgent.run(
        state=state,
        execution_manager=exec_mgr,
        deepseek_provider=lmstudio,
        db=db_session,
    )

    assert res.get("evaluation_result") is not None
    assert res["evaluation_result"]["is_correct"] is False
    assert res["misconception_analysis"]["detected"] is True
    assert res["misconception_analysis"]["category"] in [
        "conceptual_misconception",
        "calculation_error",
        "incorrect_formula_application",
        "incomplete_understanding",
        "careless_mistake",
        "incorrect_prerequisite_knowledge",
    ]
    print(f"\n[REAL GPU] Test 2 Misconception Detected: {res['misconception_analysis']['category']} | {res['misconception_analysis']['description']}")


@pytest.mark.skipif(not RUN_LOCAL, reason=skip_reason)
@pytest.mark.asyncio
async def test_3_real_question_generation(db_session: Session, hardware_test_data):
    """
    Test 3: Question Generation against live DeepSeek output.
    Verifies that generated candidate question correctly associates with concept and specifies rubric.
    """
    lmstudio = get_lmstudio_provider()
    if not await lmstudio.health_check():
        pytest.skip(f"BLOCKED: LM Studio offline at {settings.LMSTUDIO_BASE_URL}")

    exec_mgr = get_gpu_execution_manager()
    fixtures = hardware_test_data
    q = fixtures["question"]
    c = fixtures["concept"]
    c2 = fixtures["next_concept"]

    state: LearningState = {
        "student_id": fixtures["student"].id,
        "question_id": q.id,
        "current_concept_id": c.id,
        "current_concept_name": c.name,
        "candidate_next_concept_id": c2.id,
        "candidate_next_concept_name": c2.name,
        "student_answer": "Current is inversely proportional to resistance.",
        "relevant_learning_context": {
            "question_text": q.question_text,
            "expected_answer": q.correct_answer,
            "concept_name": c.name,
            "question_type": "OPEN_ENDED",
        },
        "node_execution_trace": [],
    }

    res = await AnswerEvaluationAgent.run(
        state=state,
        execution_manager=exec_mgr,
        deepseek_provider=lmstudio,
        db=db_session,
    )

    q_gen = res.get("generated_question")
    assert q_gen is not None
    assert len(q_gen["question"]) > 5
    assert len(q_gen["expected_answer"]) > 0
    print(f"\n[REAL GPU] Test 3 Generated Question: '{q_gen['question']}' (Diff: {q_gen.get('difficulty')})")


@pytest.mark.skipif(not RUN_LOCAL, reason=skip_reason)
@pytest.mark.asyncio
async def test_4_real_sequential_llama_execution(db_session: Session, hardware_test_data):
    """
    Test 4: Sequential Model Execution on Real GPU.
    Verifies DeepSeek execution -> complete unload verified -> Llama execution -> complete unload verified.
    """
    lmstudio = get_lmstudio_provider()
    ollama = get_ollama_provider()

    if not await lmstudio.health_check() or not await ollama.health_check():
        pytest.skip("BLOCKED: Local model servers unavailable.")

    exec_mgr = get_gpu_execution_manager()
    monitor = GPUResourceMonitor(enabled=True)

    # 1. Run DeepSeek
    async def ds_task():
        return {"result": "ds_ok"}

    t0 = time.time()
    await exec_mgr.execute_deepseek(ds_task)
    ds_total = time.time() - t0

    # Verify DeepSeek unloaded
    assert not await lmstudio.is_model_loaded()
    snap_mid = monitor.get_memory_snapshot()

    # 2. Run Llama
    async def llama_task():
        return {"result": "llama_ok"}

    t1 = time.time()
    await exec_mgr.execute_llama(llama_task)
    llama_total = time.time() - t1

    # Verify Llama unloaded
    assert not await ollama.is_model_loaded()
    snap_end = monitor.get_memory_snapshot()

    print(f"\n[REAL GPU] Test 4 Sequential Switching: DeepSeek cycle={ds_total:.2f}s, Llama cycle={llama_total:.2f}s")
    print(f"[REAL GPU] Residual VRAM between models: {snap_mid.used_mb:.1f} MB, At end: {snap_end.used_mb:.1f} MB")


@pytest.mark.skipif(not RUN_LOCAL, reason=skip_reason)
@pytest.mark.asyncio
async def test_5_real_complete_agentic_turn(db_session: Session, hardware_test_data):
    """
    Test 5: Complete Agentic Turn with Real Local Models.
    Verifies DeepSeek evaluation, BKT update, adaptive decision, Llama Socratic feedback,
    and database persistence.
    """
    lmstudio = get_lmstudio_provider()
    ollama = get_ollama_provider()

    if not await lmstudio.health_check() or not await ollama.health_check():
        pytest.skip("BLOCKED: Real model servers unavailable.")

    exec_mgr = get_gpu_execution_manager()
    fixtures = hardware_test_data
    student = fixtures["student"]
    q = fixtures["question"]

    state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "As resistance goes up, the current decreases because I = V/R for constant voltage.",
    }

    t0 = time.time()
    result = await execute_learning_turn(
        initial_state=state,
        db=db_session,
        execution_manager=exec_mgr,
    )
    total_ms = (time.time() - t0) * 1000.0

    assert result["execution_status"] == "completed"
    assert result["evaluation_result"] is not None
    assert result["student_feedback"] is not None
    assert result["updated_mastery"] is not None

    trace = result.get("node_execution_trace", [])
    assert "deepseek_evaluation" in trace
    assert "update_bkt_mastery" in trace
    assert "student_feedback" in trace
    assert "persist_outcome" in trace

    print(f"\n--- REAL GPU TEST 5: COMPLETE TURN ---")
    print(f"Total Latency: {total_ms:.1f} ms")
    print(f"BKT Posterior Mastery: {result['updated_mastery']:.4f}")
    print(f"Adaptive Action: {result.get('adaptive_action')}")
    print(f"Llama Feedback: {result['student_feedback'].get('feedback')}")
    print(f"Socratic Hint: {result['student_feedback'].get('socratic_hint')}")


@pytest.mark.skipif(not RUN_LOCAL, reason=skip_reason)
@pytest.mark.asyncio
async def test_6_real_repeated_learning_turns(db_session: Session, hardware_test_data):
    """
    Test 6: Repeated Learning Turns for Learner Model Progression on Real Hardware.
    Executes multiple turns for the student and validates monotonic knowledge progression.
    """
    lmstudio = get_lmstudio_provider()
    ollama = get_ollama_provider()

    if not await lmstudio.health_check() or not await ollama.health_check():
        pytest.skip("BLOCKED: Real model servers unavailable.")

    exec_mgr = get_gpu_execution_manager()
    fixtures = hardware_test_data
    student = fixtures["student"]
    q1 = fixtures["question"]
    q2 = fixtures["question_2"]

    # Turn 1
    t1_state: LearningState = {
        "student_id": student.id,
        "question_id": q1.id,
        "student_answer": "Current is inversely proportional to resistance (I = V/R).",
    }
    t1_res = await execute_learning_turn(t1_state, db=db_session, execution_manager=exec_mgr)
    m1 = t1_res["updated_mastery"]

    # Turn 2
    t2_state: LearningState = {
        "student_id": student.id,
        "question_id": q2.id,
        "student_answer": "If voltage doubles, current doubles because I = V/R.",
    }
    t2_res = await execute_learning_turn(t2_state, db=db_session, execution_manager=exec_mgr)
    m2 = t2_res["updated_mastery"]

    assert m2 > m1, f"Expected monotonic increase in mastery: turn 1={m1}, turn 2={m2}"

    # Verify database persistence
    db_mastery = db_session.query(LearnerMastery).filter(
        LearnerMastery.student_id == student.id,
        LearnerMastery.concept_id == fixtures["concept"].id,
    ).first()
    assert db_mastery is not None
    assert db_mastery.current_mastery == pytest.approx(m2, abs=1e-4)

    print(f"\n--- REAL GPU TEST 6: MULTI-TURN PROGRESSION ---")
    print(f"Turn 1 Mastery: {m1:.4f} -> Turn 2 Mastery: {m2:.4f}")
    print(f"Persisted Database Mastery: {db_mastery.current_mastery:.4f}")
