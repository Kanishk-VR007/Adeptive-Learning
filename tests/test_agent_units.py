import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.orm import Session

from app.agents import (
    AdaptiveActionType,
    AdaptiveLearningAgent,
    AnswerEvaluationAgent,
    ConceptSelectionAgent,
    LearningContextAgent,
    LearnerModelingAgent,
    QuestionGenerationAgent,
    StudentFeedbackAgent,
    LearningState,
)
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.providers.base import LLMResponse
from app.core.security import get_password_hash
from app.models.assessment import Question, QuestionType
from app.models.concept_graph import ConceptPrerequisite
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.syllabus import Chapter, Concept, DifficultyLevel, Subject
from app.models.user import User, UserRole


@pytest.fixture
def test_setup(db_session: Session):
    """Seed test fixtures for agent testing."""
    # Subject, Chapter, Concepts
    subj = Subject(name="Agent Physics", code="AG-PHYS-101")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    ch = Chapter(subject_id=subj.id, title="Electromagnetism", chapter_number=1)
    db_session.add(ch)
    db_session.commit()
    db_session.refresh(ch)

    c1 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Electric Current", concept_code="C-CURR-01", description="Current")
    c2 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Ohm's Law", concept_code="C-OHM-02", description="Ohm")
    c3 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Joule Heating", concept_code="C-HEAT-03", description="Heat")
    db_session.add_all([c1, c2, c3])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)
    db_session.refresh(c3)

    # Prerequisite: c1 -> c2 (c1 is prerequisite to c2), c2 -> c3
    prereq1 = ConceptPrerequisite(concept_id=c2.id, prerequisite_id=c1.id)
    prereq2 = ConceptPrerequisite(concept_id=c3.id, prerequisite_id=c2.id)
    db_session.add_all([prereq1, prereq2])
    db_session.commit()

    # Questions
    q_mcq = Question(
        concept_id=c2.id,
        question_type=QuestionType.MCQ,
        question_text="If resistance doubles and voltage is constant, what happens to current?",
        question_options=[{"id": "A", "text": "Doubles"}, {"id": "B", "text": "Halves"}],
        correct_answer="B",
        difficulty_level=DifficultyLevel.BEGINNER,
    )
    q_open = Question(
        concept_id=c2.id,
        question_type=QuestionType.OPEN_ENDED,
        question_text="Explain Ohm's Law and its mathematical formulation.",
        correct_answer="Ohm's Law states that current is directly proportional to voltage and inversely proportional to resistance: I = V/R.",
        evaluation_rubric={"key_concepts": ["I = V/R", "proportionality"]},
        difficulty_level=DifficultyLevel.INTERMEDIATE,
    )
    db_session.add_all([q_mcq, q_open])

    # Student
    student = User(
        email="agent_student@example.com",
        full_name="Agent Student",
        hashed_password=get_password_hash("Secret123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(q_mcq)
    db_session.refresh(q_open)

    return {
        "student": student,
        "c1": c1,
        "c2": c2,
        "c3": c3,
        "q_mcq": q_mcq,
        "q_open": q_open,
    }


# =====================================================================
# AGENT 1: LEARNING CONTEXT AGENT TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_learning_context_agent_valid_student(db_session: Session, test_setup):
    student = test_setup["student"]
    q = test_setup["q_mcq"]
    c2 = test_setup["c2"]

    # Initial mastery
    m = LearnerMastery(student_id=student.id, concept_id=c2.id, current_mastery=0.45)
    db_session.add(m)
    db_session.commit()

    state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "concept_id": c2.id,
        "node_execution_trace": [],
    }

    res = await LearningContextAgent.run(state=state, db=db_session)
    assert res["current_concept_id"] == c2.id
    assert res["current_concept_name"] == "Ohm's Law"
    assert res["current_mastery"] == 0.45
    assert "load_learning_context" in res["node_execution_trace"]
    assert res["relevant_learning_context"]["concept_name"] == "Ohm's Law"
    assert len(res["relevant_learning_context"]["prerequisites"]) == 1


@pytest.mark.asyncio
async def test_learning_context_agent_empty_history(db_session: Session, test_setup):
    student = test_setup["student"]
    q = test_setup["q_mcq"]
    c2 = test_setup["c2"]

    state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "concept_id": c2.id,
        "node_execution_trace": [],
    }

    res = await LearningContextAgent.run(state=state, db=db_session)
    # Default initial mastery when no record exists
    assert res["current_mastery"] == 0.20
    assert res["relevant_learning_context"]["recent_misconceptions"] == []


# =====================================================================
# AGENT 2: CONCEPT SELECTION AGENT TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_concept_selection_weak_prerequisites(db_session: Session, test_setup):
    student = test_setup["student"]
    c1 = test_setup["c1"]
    c2 = test_setup["c2"]

    # Student has weak mastery on c1 (prereq of c2)
    m1 = LearnerMastery(student_id=student.id, concept_id=c1.id, current_mastery=0.25)
    db_session.add(m1)
    db_session.commit()

    state: LearningState = {
        "student_id": student.id,
        "current_concept_id": c2.id,
        "node_execution_trace": [],
    }

    res = await ConceptSelectionAgent.run(state=state, db=db_session)
    # Should select weak prereq c1 for reinforcement!
    assert res["candidate_next_concept_id"] == c1.id
    assert res["candidate_next_concept_name"] == "Electric Current"


@pytest.mark.asyncio
async def test_concept_selection_strong_advance(db_session: Session, test_setup):
    student = test_setup["student"]
    c1 = test_setup["c1"]
    c2 = test_setup["c2"]
    c3 = test_setup["c3"]

    # Student has mastered c1 and c2
    m1 = LearnerMastery(student_id=student.id, concept_id=c1.id, current_mastery=0.92)
    m2 = LearnerMastery(student_id=student.id, concept_id=c2.id, current_mastery=0.88)
    db_session.add_all([m1, m2])
    db_session.commit()

    state: LearningState = {
        "student_id": student.id,
        "current_concept_id": c2.id,
        "node_execution_trace": [],
    }

    res = await ConceptSelectionAgent.run(state=state, db=db_session)
    # Should advance to dependent concept c3
    assert res["candidate_next_concept_id"] == c3.id
    assert res["candidate_next_concept_name"] == "Joule Heating"


# =====================================================================
# AGENT 3 & 4: ANSWER EVALUATION & MISCONCEPTION DETECTION TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_answer_evaluation_deterministic_mcq_correct(db_session: Session, test_setup):
    q_mcq = test_setup["q_mcq"]
    mock_exec_mgr = MagicMock(spec=GPUExecutionManager)

    state: LearningState = {
        "question_id": q_mcq.id,
        "student_answer": "B",
        "current_concept_id": q_mcq.concept_id,
        "node_execution_trace": [],
    }

    res = await AnswerEvaluationAgent.run(state=state, execution_manager=mock_exec_mgr, db=db_session)
    assert res["evaluation_result"]["is_correct"] is True
    assert res["evaluation_result"]["confidence"] == 1.0
    assert res["is_uncertain_evaluation"] is False
    assert res["misconception_analysis"]["detected"] is False
    # Deterministic evaluation did not need to invoke LLM
    mock_exec_mgr.execute_deepseek.assert_not_called()


@pytest.mark.asyncio
async def test_answer_evaluation_llm_with_misconception(db_session: Session, test_setup):
    q_open = test_setup["q_open"]
    mock_exec_mgr = MagicMock(spec=GPUExecutionManager)

    # Mock DeepSeek structured output
    deepseek_json = {
        "evaluation": {
            "is_correct": False,
            "answer_type": "partially_correct",
            "reasoning_summary": "Student confused proportional relation of voltage with inverse.",
            "confidence": 0.88,
        },
        "misconception": {
            "detected": True,
            "concept_id": q_open.concept_id,
            "category": "conceptual_misconception",
            "description": "Believes voltage decreases when current increases in a resistive circuit.",
        },
        "candidate_question": {
            "concept_id": q_open.concept_id,
            "difficulty": "easy",
            "question": "If voltage increases across a resistor, what happens to current?",
            "expected_answer": "Current increases proportionally.",
            "evaluation_criteria": ["Identifies direct proportionality"],
        },
    }

    import json
    mock_llm_resp = LLMResponse(content=json.dumps(deepseek_json), raw_response={})
    mock_exec_mgr.execute_deepseek = AsyncMock(return_value={"result": mock_llm_resp, "metrics": {"deepseek_inference_ms": 150.0}})

    state: LearningState = {
        "question_id": q_open.id,
        "student_answer": "Current goes up because voltage goes down according to Ohm's rule.",
        "current_concept_id": q_open.concept_id,
        "candidate_next_concept_id": q_open.concept_id,
        "node_execution_trace": [],
    }

    res = await AnswerEvaluationAgent.run(state=state, execution_manager=mock_exec_mgr, db=db_session)
    assert res["evaluation_result"]["is_correct"] is False
    assert res["misconception_analysis"]["detected"] is True
    assert res["misconception_analysis"]["category"] == "conceptual_misconception"
    assert res["is_uncertain_evaluation"] is False
    assert res["generated_question"]["difficulty"] == "easy"


# =====================================================================
# AGENT 5: LEARNER MODELING AGENT (BKT) TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_learner_modeling_bkt_update_and_idempotency(db_session: Session, test_setup):
    student = test_setup["student"]
    c2 = test_setup["c2"]

    state: LearningState = {
        "student_id": student.id,
        "current_concept_id": c2.id,
        "evaluation_result": {"is_correct": True},
        "node_execution_trace": [],
    }

    # First attempt: Updates BKT
    res1 = await LearnerModelingAgent.run(state=state, db=db_session)
    updated_mastery_1 = res1["updated_mastery"]
    assert updated_mastery_1 > 0.20  # increased from prior 0.20
    evidence_id = res1["evidence_id"]
    assert evidence_id is not None

    # Check database record
    m = db_session.query(LearnerMastery).filter(
        LearnerMastery.student_id == student.id,
        LearnerMastery.concept_id == c2.id,
    ).first()
    assert m is not None
    assert round(m.current_mastery, 4) == round(updated_mastery_1, 4)
    assert m.total_attempts == 1

    # Second invocation with same evidence_id (e.g. graph retry): Must be idempotent!
    state["evidence_id"] = evidence_id
    res2 = await LearnerModelingAgent.run(state=state, db=db_session)
    assert res2["updated_mastery"] == updated_mastery_1
    m_recheck = db_session.query(LearnerMastery).filter(
        LearnerMastery.student_id == student.id,
        LearnerMastery.concept_id == c2.id,
    ).first()
    assert m_recheck.total_attempts == 1  # Not double counted!


# =====================================================================
# AGENT 6: ADAPTIVE LEARNING AGENT TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_adaptive_agent_threshold_decisions(db_session: Session, test_setup):
    student = test_setup["student"]
    c1 = test_setup["c1"]
    c2 = test_setup["c2"]

    # 1. Low mastery (< 0.40) -> CONCEPT_REMEDIATION
    state_low: LearningState = {
        "student_id": student.id,
        "current_concept_id": c2.id,
        "updated_mastery": 0.28,
        "node_execution_trace": [],
    }
    res_low = await AdaptiveLearningAgent.run(state=state_low, db=db_session)
    assert res_low["adaptive_action"] == AdaptiveActionType.CONCEPT_REMEDIATION

    # 2. Developing mastery (0.40 - 0.69) -> TARGETED_PRACTICE
    state_mid: LearningState = {
        "student_id": student.id,
        "current_concept_id": c2.id,
        "updated_mastery": 0.55,
        "node_execution_trace": [],
    }
    res_mid = await AdaptiveLearningAgent.run(state=state_mid, db=db_session)
    assert res_mid["adaptive_action"] == AdaptiveActionType.TARGETED_PRACTICE

    # 3. High mastery (>= 0.90) with candidate concept -> ADVANCE_TO_NEXT_CONCEPT
    state_high: LearningState = {
        "student_id": student.id,
        "current_concept_id": c2.id,
        "candidate_next_concept_id": c1.id,
        "updated_mastery": 0.94,
        "node_execution_trace": [],
    }
    res_high = await AdaptiveLearningAgent.run(state=state_high, db=db_session)
    assert res_high["adaptive_action"] == AdaptiveActionType.ADVANCE_TO_NEXT_CONCEPT


# =====================================================================
# AGENT 7: QUESTION GENERATION AGENT TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_question_generation_agent_fallback_to_db(db_session: Session, test_setup):
    c2 = test_setup["c2"]
    q_mcq = test_setup["q_mcq"]
    q_open = test_setup["q_open"]

    state: LearningState = {
        "candidate_next_concept_id": c2.id,
        "adaptive_action": AdaptiveActionType.TARGETED_PRACTICE,
        "generated_question": None,  # No LLM draft provided
        "node_execution_trace": [],
    }

    res = await QuestionGenerationAgent.run(state=state, db=db_session)
    validated_q = res["validated_next_question"]
    assert validated_q is not None
    assert validated_q["concept_id"] == c2.id
    assert validated_q["question"] in (q_mcq.question_text, q_open.question_text)


# =====================================================================
# AGENT 8: STUDENT FEEDBACK AGENT TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_student_feedback_agent_enforces_deterministic_integrity(test_setup):
    mock_exec_mgr = MagicMock(spec=GPUExecutionManager)
    student = test_setup["student"]

    # Model hallucinates a wrong display_mastery and wrong adaptive_action
    llama_json = {
        "feedback": "You did great on understanding current!",
        "socratic_hint": "Think about V = IR",
        "next_question": "What is the unit of resistance?",
        "adaptive_action": "WRONG_HALLUCINATED_ACTION",
        "display_mastery": 0.99,  # Hallucinated!
    }

    import json
    mock_llm_resp = LLMResponse(content=json.dumps(llama_json), raw_response={})
    mock_exec_mgr.execute_llama = AsyncMock(return_value={"result": mock_llm_resp, "metrics": {"llama_inference_ms": 110.0}})

    state: LearningState = {
        "student_id": student.id,
        "student_name": student.full_name,
        "current_concept_id": 2,
        "current_concept_name": "Ohm's Law",
        "evaluation_result": {"is_correct": False, "answer_type": "incorrect", "reasoning_summary": "Sign error"},
        "adaptive_action": AdaptiveActionType.CONCEPT_REMEDIATION,  # True Python decision
        "updated_mastery": 0.35,  # True Python BKT mastery
        "node_execution_trace": [],
    }

    res = await StudentFeedbackAgent.run(state=state, execution_manager=mock_exec_mgr)
    fb = res["student_feedback"]

    # MUST strictly enforce deterministic values
    assert fb["adaptive_action"] == AdaptiveActionType.CONCEPT_REMEDIATION
    assert fb["display_mastery"] == 0.35
    assert fb["socratic_hint"] == "Think about V = IR"
    assert "student_feedback" in res["node_execution_trace"]
