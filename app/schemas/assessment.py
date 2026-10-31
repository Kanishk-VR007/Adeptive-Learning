from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from app.models.assessment import QuestionType, SessionType
from app.models.syllabus import DifficultyLevel


# --- Question Schemas ---
class QuestionBase(BaseModel):
    concept_id: int
    question_type: QuestionType = QuestionType.MCQ
    question_text: str = Field(..., min_length=5)
    question_options: Optional[List[Dict[str, str]]] = Field(
        None,
        description="List of options for MCQ e.g. [{'id': 'A', 'text': 'Option A'}]"
    )
    correct_answer: str = Field(..., min_length=1)
    evaluation_rubric: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Rubrics, scoring criteria, and explanations"
    )
    difficulty_level: DifficultyLevel = DifficultyLevel.BEGINNER


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    concept_id: Optional[int] = None
    question_type: Optional[QuestionType] = None
    question_text: Optional[str] = Field(None, min_length=5)
    question_options: Optional[List[Dict[str, str]]] = None
    correct_answer: Optional[str] = None
    evaluation_rubric: Optional[Dict[str, Any]] = None
    difficulty_level: Optional[DifficultyLevel] = None


class QuestionPracticeView(BaseModel):
    """View of a question for students during practice (omits correct_answer)."""
    id: int
    concept_id: int
    question_type: QuestionType
    question_text: str
    question_options: Optional[List[Dict[str, str]]] = None
    difficulty_level: DifficultyLevel

    model_config = ConfigDict(from_attributes=True)


class QuestionResponse(QuestionBase):
    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Session Schemas ---
class SessionCreate(BaseModel):
    subject_id: int
    session_type: SessionType = SessionType.ADAPTIVE_PRACTICE
    target_concept_id: Optional[int] = Field(None, description="Optional concept focus for practice")
    question_count: int = Field(5, ge=1, le=25)


class SessionResponse(BaseModel):
    id: int
    user_id: int
    subject_id: int
    session_type: SessionType
    started_at: datetime
    completed_at: Optional[datetime] = None
    telemetry_summary: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class SessionDetailResponse(SessionResponse):
    questions: List[QuestionPracticeView] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- Response & Evaluation Schemas ---
class ResponseSubmit(BaseModel):
    question_id: int
    session_id: Optional[int] = None
    response_text: str = Field(..., min_length=1)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    time_spent_ms: Optional[int] = Field(None, ge=0)


class ResponseEvaluationResult(BaseModel):
    response_id: int
    question_id: int
    is_correct: bool
    correct_answer: str
    ai_feedback: Optional[str] = None
    previous_mastery_probability: float
    new_mastery_probability: float
    practice_count: int


class LearnerResponseHistoryItem(BaseModel):
    id: int
    session_id: Optional[int]
    question_id: int
    response_text: str
    is_correct: bool
    confidence_score: Optional[float]
    time_spent_ms: Optional[int]
    ai_feedback: Optional[str]
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)
