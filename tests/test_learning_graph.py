import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.orm import Session

from app.agents import (
    AdaptiveActionType,
    DeepSeekAnalysisOutput,
    LearningState,
)
from app.ai.gpu.execution_manager import GPUExecutionManager
from app.ai.providers.base import LLMResponse
from app.core.security import get_password_hash
from app.graph import build_learning_graph, execute_learning_turn, get_compiled_graph
from app.models.assessment import Question, QuestionType
from app.models.concept_graph import ConceptPrerequisite
from app.models.learner_mastery import LearnerMastery
from app.models.syllabus import Chapter, Concept, DifficultyLevel, Subject
from app.models.user import User, UserRole


@pytest.fixture
def graph_test_fixtures(db_session: Session):
    subj = Subject(name="Graph Physics", code="G-PHYS-101")
    db_session.add(subj)
    db_session.commit()
    db_session.refresh(subj)

    ch = Chapter(subject_id=subj.id, title="Mechanics", chapter_number=1)
    db_session.add(ch)
    db_session.commit()
    db_session.refresh(ch)

    c1 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Kinematics", concept_code="G-KIN-01", description="Velocity")
    c2 = Concept(subject_id=subj.id, chapter_id=ch.id, name="Forces", concept_code="G-FOR-02", description="Newton Laws")
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    # Prerequisite: c1 -> c2
    prereq = ConceptPrerequisite(concept_id=c2.id, prerequisite_id=c1.id)
    db_session.add(prereq)
    db_session.commit()

    q_mcq = Question(
        concept_id=c1.id,
        question_type=QuestionType.MCQ,
        question_text="What is velocity?",
        question_options=[{"id": "A", "text": "Displacement over time"}, {"id": "B", "text": "Distance squared"}],
        correct_answer="A",
        difficulty_level=DifficultyLevel.BEGINNER,
    )
    db_session.add(q_mcq)

    student = User(
        email="graph_student@example.com",
        full_name="Graph Student",
        hashed_password=get_password_hash("Secret123!"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(q_mcq)

    return {
        "student": student,
        "c1": c1,
        "c2": c2,
        "q_mcq": q_mcq,
    }


def _create_mock_execution_manager():
    mgr = MagicMock(spec=GPUExecutionManager)
    
    # Mock deepseek
    deepseek_payload = {
        "evaluation": {
            "is_correct": True,
            "answer_type": "correct",
            "reasoning_summary": "Solid grasp of velocity definition.",
            "confidence": 0.95,
        },
        "misconception": {
            "detected": False,
            "concept_id": None,
            "category": "none",
            "description": None,
        },
        "candidate_question": {
            "concept_id": 1,
            "difficulty": "medium",
            "question": "What is the difference between speed and velocity?",
            "expected_answer": "Velocity includes direction; speed is scalar.",
            "evaluation_criteria": ["Mentions direction", "Mentions scalar vs vector"],
        },
    }
    llm_resp_ds = LLMResponse(content=json.dumps(deepseek_payload), raw_response={})
    mgr.execute_deepseek = AsyncMock(return_value={"result": llm_resp_ds, "metrics": {"deepseek_inference_ms": 120.0}})

    # Mock llama
    llama_payload = {
        "feedback": "Great job! Your answer accurately captures velocity.",
        "socratic_hint": None,
        "next_question": "What is the difference between speed and velocity?",
        "adaptive_action": "TARGETED_PRACTICE",
        "display_mastery": 0.50,
    }
    llm_resp_llama = LLMResponse(content=json.dumps(llama_payload), raw_response={})
    mgr.execute_llama = AsyncMock(return_value={"result": llm_resp_llama, "metrics": {"llama_inference_ms": 90.0}})

    mgr.get_status = MagicMock(return_value=MagicMock(state="idle", active_model=None, monitoring_enabled=True))
    return mgr


# =====================================================================
# A. GRAPH CONSTRUCTION TESTS
# =====================================================================

def test_graph_construction_and_compilation():
    builder = build_learning_graph()
    assert builder is not None

    compiled = get_compiled_graph()
    assert compiled is not None

    expected_nodes = {
        "__start__",
        "validate_submission",
        "load_learning_context",
        "select_candidate_concept",
        "deepseek_evaluation",
        "validate_evaluation_output",
        "request_clarification",
        "update_bkt_mastery",
        "adaptive_decision",
        "remediation_node",
        "targeted_practice_node",
        "advance_concept_node",
        "revision_node",
        "validate_question",
        "student_feedback",
        "persist_outcome",
    }
    actual_nodes = set(compiled.nodes.keys())
    assert expected_nodes.issubset(actual_nodes)


# =====================================================================
# B. CONDITIONAL ROUTING TESTS
# =====================================================================

@pytest.mark.asyncio
async def test_graph_path_normal_correct_answer(db_session: Session, graph_test_fixtures):
    """
    Path 1: Correct answer -> update BKT -> adaptive decision -> targeted practice -> feedback -> persist
    """
    fixtures = graph_test_fixtures
    student = fixtures["student"]
    q = fixtures["q_mcq"]
    exec_mgr = _create_mock_execution_manager()

    initial_state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "A",
    }

    result = await execute_learning_turn(
        initial_state=initial_state,
        db=db_session,
        execution_manager=exec_mgr,
    )

    trace = result.get("node_execution_trace", [])
    assert "validate_submission" in trace
    assert "load_learning_context" in trace
    assert "select_candidate_concept" in trace
    assert "deepseek_evaluation" in trace
    assert "validate_evaluation_output" in trace
    assert "update_bkt_mastery" in trace
    assert "adaptive_decision" in trace
    assert "validate_question" in trace
    assert "student_feedback" in trace
    assert "persist_outcome" in trace

    # Assert that request_clarification was NOT executed
    assert "request_clarification" not in trace

    assert result["execution_status"] == "completed"
    assert result["updated_mastery"] is not None
    assert result["updated_mastery"] > 0.20


@pytest.mark.asyncio
async def test_graph_path_uncertain_evaluation_routes_to_clarification(db_session: Session, graph_test_fixtures):
    """
    Path 2: Uncertain evaluation (confidence < 0.60 or ambiguous)
    Must route to request_clarification, then directly to student_feedback,
    and MUST NOT execute update_bkt_mastery.
    """
    fixtures = graph_test_fixtures
    student = fixtures["student"]
    q = fixtures["q_mcq"]
    exec_mgr = _create_mock_execution_manager()

    # DeepSeek returns ambiguous evaluation with low confidence (0.40)
    low_conf_payload = {
        "evaluation": {
            "is_correct": False,
            "answer_type": "ambiguous",
            "reasoning_summary": "Student answer was fragmented and incomprehensible.",
            "confidence": 0.40,
        },
        "misconception": {
            "detected": False,
            "category": "unclear_response",
            "description": "Fragmented sentence without conceptual argument.",
        },
    }
    llm_resp_low = LLMResponse(content=json.dumps(low_conf_payload), raw_response={})
    exec_mgr.execute_deepseek = AsyncMock(return_value={"result": llm_resp_low, "metrics": {}})

    initial_state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "umm... it might be something like moving around maybe",
    }

    result = await execute_learning_turn(
        initial_state=initial_state,
        db=db_session,
        execution_manager=exec_mgr,
    )

    trace = result.get("node_execution_trace", [])
    assert "validate_evaluation_output" in trace
    assert "request_clarification" in trace
    assert "student_feedback" in trace
    assert "persist_outcome" in trace

    # CRITICAL INVARIANT: BKT mastery update MUST be bypassed on uncertain evaluation!
    assert "update_bkt_mastery" not in trace
    assert "adaptive_decision" not in trace
    assert result["adaptive_action"] == AdaptiveActionType.CLARIFICATION_REQUIRED


@pytest.mark.asyncio
async def test_graph_path_adaptive_remediation(db_session: Session, graph_test_fixtures):
    """
    Path 3: Severe misconception or very low mastery routes to remediation_node.
    """
    fixtures = graph_test_fixtures
    student = fixtures["student"]
    q = fixtures["q_mcq"]
    exec_mgr = _create_mock_execution_manager()

    # Pre-set low mastery
    m = LearnerMastery(student_id=student.id, concept_id=q.concept_id, current_mastery=0.15)
    db_session.add(m)
    db_session.commit()

    # Incorrect answer with conceptual misconception
    misc_payload = {
        "evaluation": {
            "is_correct": False,
            "answer_type": "incorrect",
            "reasoning_summary": "Confuses velocity with acceleration.",
            "confidence": 0.92,
        },
        "misconception": {
            "detected": True,
            "category": "conceptual_misconception",
            "description": "Thinks velocity is rate of change of speed.",
        },
    }
    exec_mgr.execute_deepseek = AsyncMock(return_value={"result": LLMResponse(content=json.dumps(misc_payload), raw_response={}), "metrics": {}})

    initial_state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "Velocity is the rate of change of speed over time.",
    }

    result = await execute_learning_turn(
        initial_state=initial_state,
        db=db_session,
        execution_manager=exec_mgr,
    )

    trace = result.get("node_execution_trace", [])
    assert "update_bkt_mastery" in trace
    assert "adaptive_decision" in trace
    assert "remediation_node" in trace
    assert result["adaptive_action"] == AdaptiveActionType.CONCEPT_REMEDIATION


@pytest.mark.asyncio
async def test_graph_path_adaptive_advance_concept(db_session: Session, graph_test_fixtures):
    """
    Path 4: High mastery (>= 0.90) routes to advance_concept_node when eligible candidate exists.
    """
    fixtures = graph_test_fixtures
    student = fixtures["student"]
    q = fixtures["q_mcq"]
    c1 = fixtures["c1"]
    c2 = fixtures["c2"]
    exec_mgr = _create_mock_execution_manager()

    # Set prior mastery already high
    m1 = LearnerMastery(student_id=student.id, concept_id=c1.id, current_mastery=0.92)
    db_session.add(m1)
    db_session.commit()

    initial_state: LearningState = {
        "student_id": student.id,
        "question_id": q.id,
        "student_answer": "A",
    }

    result = await execute_learning_turn(
        initial_state=initial_state,
        db=db_session,
        execution_manager=exec_mgr,
    )

    trace = result.get("node_execution_trace", [])
    assert "adaptive_decision" in trace
    assert "advance_concept_node" in trace
    assert result["adaptive_action"] == AdaptiveActionType.ADVANCE_TO_NEXT_CONCEPT
    assert result["candidate_next_concept_id"] == c2.id
