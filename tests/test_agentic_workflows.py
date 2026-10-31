import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.orm import Session

from app.agents import AdaptiveActionType, LearningState
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.providers.base import LLMResponse
from app.core.security import get_password_hash
from app.graph import execute_learning_turn
from app.models.assessment import Question, QuestionType
from app.models.concept_graph import ConceptPrerequisite
from app.models.learner_mastery import LearnerMastery
from app.models.syllabus import Chapter, Concept, DifficultyLevel, Subject
from app.models.user import User, UserRole


@pytest.fixture
def workflow_fixtures(db_session: Session):
    subj = Subject(name="Workflow Biology", code="WF-BIO-101")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    ch = Chapter(subject_id=subj.id, title="Cell Biology", chapter_number=1)
    db_session.add(ch)
    db_session.commit()
    db_session.refresh(ch)

    c1 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Cell Membrane", concept_code="WF-CELL-01", description="Diffusion")
    c2 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Active Transport", concept_code="WF-TRAN-02", description="ATP pump")
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    # Prerequisite: c1 -> c2
    prereq = ConceptPrerequisite(concept_id=c2.id, prerequisite_id=c1.id)
    db_session.add(prereq)
    db_session.commit()

    q_open = Question(
        concept_id=c1.id,
        question_type=QuestionType.OPEN_ENDED,
        question_text="How do molecules cross the cell membrane through simple diffusion?",
        correct_answer="Molecules move down their concentration gradient from high to low concentration without requiring cellular energy.",
        difficulty_level=DifficultyLevel.BEGINNER,
    )
    db_session.add(q_open)

    student = User(
        email="workflow_student@example.com",
        full_name="Workflow Student",
        hashed_password=get_password_hash("Secret123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(q_open)

    return {
        "student": student,
        "c1": c1,
        "c2": c2,
        "q_open": q_open,
    }


def _build_mock_mgr(deepseek_data: dict, llama_data: dict):
    mgr = MagicMock(spec=GPUExecutionManager)
    
    ds_resp = LLMResponse(content=json.dumps(deepseek_data), raw_response={})
    mgr.execute_deepseek = AsyncMock(return_value={"result": ds_resp, "metrics": {"deepseek_ms": 100.0}})

    llama_resp = LLMResponse(content=json.dumps(llama_data), raw_response={})
    mgr.execute_llama = AsyncMock(return_value={"result": llama_resp, "metrics": {"llama_ms": 80.0}})
    mgr.get_status = MagicMock(return_value=MagicMock(state="idle", active_model=None, monitoring_enabled=True))
    return mgr


# =====================================================================
# SCENARIO 1 – Student understands the concept
# =====================================================================

@pytest.mark.asyncio
async def test_scenario_1_student_understands_concept(db_session: Session, workflow_fixtures):
    fixtures = workflow_fixtures
    student = fixtures["student"]
    q = fixtures["q_open"]

    ds_payload = {
        "evaluation": {
            "is_correct": True,
            "answer_type": "correct",
            "reasoning_summary": "Accurately described passive movement along concentration gradient without ATP.",
            "confidence": 0.96,
        },
        "misconception": {
            "detected": False,
            "category": "none",
            "description": None,
        },
        "candidate_question": {
            "concept_id": q.concept_id,
            "difficulty": "medium",
            "question": "What type of molecules can cross the lipid bilayer directly via simple diffusion?",
            "expected_answer": "Small non-polar molecules like O2 and CO2.",
            "evaluation_criteria": ["Small size", "Non-polar/hydrophobic"],
        },
    }
    llama_payload = {
        "feedback": "Outstanding! You explained simple diffusion perfectly.",
        "socratic_hint": None,
        "next_question": "What type of molecules can cross the lipid bilayer directly?",
        "adaptive_action": "TARGETED_PRACTICE",
        "display_mastery": 0.50,
    }

    mgr = _build_mock_mgr(ds_payload, llama_payload)
    state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "Molecules diffuse from high concentration to low concentration passively without ATP.",
    }

    res = await execute_learning_turn(state, db_session, mgr)
    assert res["execution_status"] == "completed"
    assert res["evaluation_result"]["is_correct"] is True
    assert res["updated_mastery"] > 0.20
    assert res["student_feedback"]["feedback"] is not None
    assert "persist_outcome" in res["node_execution_trace"]


# =====================================================================
# SCENARIO 2 – Student has a misconception
# =====================================================================

@pytest.mark.asyncio
async def test_scenario_2_student_has_misconception(db_session: Session, workflow_fixtures):
    fixtures = workflow_fixtures
    student = fixtures["student"]
    q = fixtures["q_open"]

    ds_payload = {
        "evaluation": {
            "is_correct": False,
            "answer_type": "incorrect",
            "reasoning_summary": "Student confused simple diffusion with active transport by stating ATP is consumed.",
            "confidence": 0.93,
        },
        "misconception": {
            "detected": True,
            "concept_id": q.concept_id,
            "category": "conceptual_misconception",
            "description": "Believes simple diffusion consumes metabolic energy.",
        },
        "candidate_question": {
            "concept_id": q.concept_id,
            "difficulty": "easy",
            "question": "Does passive transport require cellular energy in the form of ATP?",
            "expected_answer": "No, passive transport occurs down gradient without ATP.",
            "evaluation_criteria": ["States No"],
        },
    }
    llama_payload = {
        "feedback": "You're thinking along transport mechanisms, but let's revisit energy consumption.",
        "socratic_hint": "Consider what happens when water drops spread in a beaker—is external energy needed?",
        "next_question": "Does passive transport require cellular energy in the form of ATP?",
        "adaptive_action": "CONCEPT_REMEDIATION",
        "display_mastery": 0.15,
    }

    mgr = _build_mock_mgr(ds_payload, llama_payload)
    state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "The cell uses ATP pumps to force molecules through the membrane during simple diffusion.",
    }

    res = await execute_learning_turn(state, db_session, mgr)
    assert res["execution_status"] == "completed"
    assert res["evaluation_result"]["is_correct"] is False
    assert res["misconception_analysis"]["detected"] is True
    assert res["adaptive_action"] == AdaptiveActionType.CONCEPT_REMEDIATION
    assert res["student_feedback"]["socratic_hint"] is not None


# =====================================================================
# SCENARIO 3 – Student partially understands
# =====================================================================

@pytest.mark.asyncio
async def test_scenario_3_student_partially_understands(db_session: Session, workflow_fixtures):
    fixtures = workflow_fixtures
    student = fixtures["student"]
    q = fixtures["q_open"]

    # Pre-set student mastery in developing range (0.50)
    m = LearnerMastery(student_id=student.id, concept_id=q.concept_id, current_mastery=0.50)
    db_session.add(m)
    db_session.commit()

    ds_payload = {
        "evaluation": {
            "is_correct": False,
            "answer_type": "partially_correct",
            "reasoning_summary": "Identified concentration gradient but missed the passive nature.",
            "confidence": 0.85,
        },
        "misconception": {
            "detected": False,
            "category": "incomplete_understanding",
            "description": "Incomplete definition of passive diffusion.",
        },
        "candidate_question": {
            "concept_id": q.concept_id,
            "difficulty": "medium",
            "question": "What is the driving force behind molecular movement in simple diffusion?",
            "expected_answer": "Thermal motion and concentration differences.",
            "evaluation_criteria": ["Thermal motion", "Gradient"],
        },
    }
    llama_payload = {
        "feedback": "You identified the concentration gradient! Let's complete the picture.",
        "socratic_hint": "Think about whether any cellular pumps are involved.",
        "next_question": "What is the driving force behind molecular movement?",
        "adaptive_action": "TARGETED_PRACTICE",
        "display_mastery": 0.45,
    }

    mgr = _build_mock_mgr(ds_payload, llama_payload)
    state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "Molecules move from high to low concentration gradient.",
    }

    res = await execute_learning_turn(state, db_session, mgr)
    assert res["execution_status"] == "completed"
    assert res["adaptive_action"] in (AdaptiveActionType.TARGETED_PRACTICE, AdaptiveActionType.CONCEPT_REMEDIATION)


# =====================================================================
# SCENARIO 4 – Insufficient evidence (Low confidence)
# =====================================================================

@pytest.mark.asyncio
async def test_scenario_4_insufficient_evidence_clarification(db_session: Session, workflow_fixtures):
    fixtures = workflow_fixtures
    student = fixtures["student"]
    q = fixtures["q_open"]

    initial_m_val = 0.42
    m = LearnerMastery(student_id=student.id, concept_id=q.concept_id, current_mastery=initial_m_val)
    db_session.add(m)
    db_session.commit()

    # Model evaluation has confidence 0.35 (< 0.60 threshold)
    ds_payload = {
        "evaluation": {
            "is_correct": False,
            "answer_type": "ambiguous",
            "reasoning_summary": "Student wrote a single fragmented word.",
            "confidence": 0.35,
        },
        "misconception": {
            "detected": False,
            "category": "unclear_response",
            "description": "Ambiguous fragment.",
        },
    }
    llama_payload = {
        "feedback": "Could you please elaborate on your thought process?",
        "socratic_hint": "Explain how molecules move across the membrane.",
        "next_question": None,
        "adaptive_action": "CLARIFICATION_REQUIRED",
        "display_mastery": initial_m_val,
    }

    mgr = _build_mock_mgr(ds_payload, llama_payload)
    state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "crossing",
    }

    res = await execute_learning_turn(state, db_session, mgr)
    assert res["execution_status"] == "completed"
    assert res["adaptive_action"] == AdaptiveActionType.CLARIFICATION_REQUIRED

    # Check that mastery in DB was preserved completely unchanged
    db_session.refresh(m)
    assert m.current_mastery == initial_m_val
    assert m.total_attempts == 0


# =====================================================================
# SCENARIO 5 – Model failure in DeepSeek
# =====================================================================

@pytest.mark.asyncio
async def test_scenario_5_deepseek_model_failure_handled_safely(db_session: Session, workflow_fixtures):
    fixtures = workflow_fixtures
    student = fixtures["student"]
    q = fixtures["q_open"]

    mgr = MagicMock(spec=GPUExecutionManager)
    # DeepSeek execution raises an unhandled runtime error
    mgr.execute_deepseek = AsyncMock(side_effect=RuntimeError("LM Studio server offline"))
    mgr.get_status = MagicMock(return_value=MagicMock(state="error", active_model=None, monitoring_enabled=True))

    state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "Molecules cross by diffusion.",
    }

    res = await execute_learning_turn(state, db_session, mgr)
    print("DEBUG SCENARIO 5 TRACE:", res.get("node_execution_trace"))
    print("DEBUG SCENARIO 5 KEYS:", {k: v for k, v in res.items() if k in ("updated_mastery", "current_mastery", "execution_status", "error_code")})
    # Must enter controlled error state
    assert res["execution_status"] == "error"
    assert res["error_code"] is not None


# =====================================================================
# SCENARIO 6 – Llama failure fallback
# =====================================================================

@pytest.mark.asyncio
async def test_scenario_6_llama_feedback_failure_fallback_deterministic(db_session: Session, workflow_fixtures):
    fixtures = workflow_fixtures
    student = fixtures["student"]
    q = fixtures["q_open"]

    ds_payload = {
        "evaluation": {
            "is_correct": True,
            "answer_type": "correct",
            "reasoning_summary": "Correct understanding.",
            "confidence": 0.95,
        },
        "misconception": {
            "detected": False,
            "category": "none",
            "description": None,
        },
        "candidate_question": {
            "concept_id": q.concept_id,
            "difficulty": "medium",
            "question": "Follow-up question?",
            "expected_answer": "Answer",
            "evaluation_criteria": [],
        },
    }

    mgr = MagicMock(spec=GPUExecutionManager)
    ds_resp = LLMResponse(content=json.dumps(ds_payload), raw_response={})
    mgr.execute_deepseek = AsyncMock(return_value={"result": ds_resp, "metrics": {}})
    # Llama execution fails completely
    mgr.execute_llama = AsyncMock(side_effect=RuntimeError("Ollama connection reset by peer"))
    mgr.get_status = MagicMock(return_value=MagicMock(state="idle", active_model=None, monitoring_enabled=True))

    state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "Passive movement down concentration gradient without ATP.",
    }

    res = await execute_learning_turn(state, db_session, mgr)
    print("DEBUG SCENARIO 6 TRACE:", res.get("node_execution_trace"))
    print("DEBUG SCENARIO 6 ERROR:", res.get("error_code"), res.get("error_message"))
    # Fallback template must ensure turn completes and returns friendly feedback
    assert res["execution_status"] == "completed"
    assert res["student_feedback"] is not None
    assert "Excellent work" in res["student_feedback"]["feedback"]
    assert res["updated_mastery"] > 0.20
