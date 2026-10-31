from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.agents.state.learning_state import EvaluationItem, MisconceptionItem, StudentFeedbackOutput


class LearningTurnRequest(BaseModel):
    question_id: int = Field(..., description="ID of question being answered", gt=0)
    student_answer: str = Field(..., description="Student submitted response", min_length=1)
    session_id: Optional[int] = Field(default=None, description="Active learning session ID")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Self-reported confidence")
    time_spent_ms: Optional[int] = Field(default=None, ge=0, description="Response time in milliseconds")
    turn_type: Optional[str] = Field(default="NORMAL_PRACTICE", description="'NORMAL_PRACTICE' or 'SCHEDULED_REVISION'")
    review_rating: Optional[int] = Field(default=None, ge=1, le=4, description="Recall rating 1-4 for scheduled revision")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key for scheduled revision")


class LearningTurnResponse(BaseModel):
    run_id: str
    execution_status: str
    student_id: int
    question_id: int
    current_concept_id: int
    candidate_next_concept_id: Optional[int] = None
    current_mastery: float
    updated_mastery: Optional[float] = None
    evaluation_result: Optional[Dict[str, Any]] = None
    misconception_analysis: Optional[Dict[str, Any]] = None
    adaptive_action: Optional[str] = None
    adaptive_reasoning: Optional[str] = None
    student_feedback: Optional[Dict[str, Any]] = None
    node_execution_trace: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    turn_type: Optional[str] = None
    review_rating: Optional[int] = None
    fsrs_next_due_utc: Optional[str] = None
    fsrs_retrievability: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None



class LearningTurnStatusResponse(BaseModel):
    run_id: str
    execution_status: str
    node_execution_trace: List[str] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class GraphStatusResponse(BaseModel):
    status: str
    compiled_nodes: List[str]
    checkpointer_type: str
    gpu_manager_state: str
    active_model: Optional[str] = None
    gpu_monitoring_enabled: bool


class SessionHistoryTurnItem(BaseModel):
    id: int
    question_id: int
    response_text: str
    is_correct: bool
    confidence_score: Optional[float] = None
    time_spent_ms: Optional[int] = None
    ai_feedback: Optional[str] = None
    submitted_at: str


class SessionHistoryResponse(BaseModel):
    session_id: int
    student_id: int
    subject_id: int
    session_type: str
    started_at: str
    completed_at: Optional[str] = None
    responses: List[SessionHistoryTurnItem] = Field(default_factory=list)
