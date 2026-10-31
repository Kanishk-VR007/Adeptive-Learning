from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class DiagnosticStartRequest(BaseModel):
    subject_id: int = Field(..., description="ID of the syllabus subject for diagnostic assessment")


class DiagnosticQuestionItem(BaseModel):
    question_id: int
    concept_id: int
    concept_name: str
    concept_code: str
    question_text: str
    options: Optional[List[str]] = None
    difficulty_level: str


class DiagnosticSessionResponse(BaseModel):
    session_id: int
    subject_id: int
    subject_name: str
    total_questions: int
    questions: List[DiagnosticQuestionItem]


class DiagnosticAnswerItem(BaseModel):
    question_id: int
    student_answer: str = Field(..., min_length=1)


class DiagnosticSubmissionRequest(BaseModel):
    session_id: int
    answers: List[DiagnosticAnswerItem]


class PrerequisiteGapItem(BaseModel):
    concept_id: int
    concept_name: str
    concept_code: str
    reason: str


class DiagnosticResultResponse(BaseModel):
    session_id: int
    subject_id: int
    subject_name: str
    total_questions: int
    correct_count: int
    accuracy_rate: float
    prerequisite_gaps: List[PrerequisiteGapItem] = Field(default_factory=list)
    initialized_masteries: Dict[str, float] = Field(default_factory=dict)
    recommended_concept_id: int
    recommended_concept_name: str
    recommended_concept_code: str
    learning_path_summary: str
