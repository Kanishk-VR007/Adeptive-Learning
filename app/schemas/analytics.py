from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConceptPerformanceMetric(BaseModel):
    concept_id: int
    concept_name: str
    concept_code: str
    average_mastery: Optional[float] = None
    students_mastered: int = 0
    students_remediating: int = 0
    attempts_count: int = 0
    error_rate: float = 0.0


class MisconceptionMetric(BaseModel):
    category: str
    description: str
    occurrence_count: int
    concept_names: List[str] = Field(default_factory=list)


class StudentProgressSummary(BaseModel):
    student_id: int
    full_name: str
    email: str
    overall_mastery: Optional[float] = None
    questions_attempted: int = 0
    correct_attempts: int = 0
    accuracy_rate: Optional[float] = None
    revisions_completed: int = 0
    overdue_revisions: int = 0
    weak_concepts_count: int = 0
    last_active: Optional[datetime] = None


class ClassAnalyticsResponse(BaseModel):
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    total_enrolled: int
    active_students_count: int
    participation_rate: float = 0.0

    # Mastery Metrics
    average_mastery: Optional[float] = None
    concept_performances: List[ConceptPerformanceMetric] = Field(default_factory=list)
    weak_concepts: List[ConceptPerformanceMetric] = Field(default_factory=list)

    # Misconceptions & Errors
    common_misconceptions: List[MisconceptionMetric] = Field(default_factory=list)
    overall_accuracy_rate: Optional[float] = None
    total_questions_attempted: int = 0

    # Revision & Retention Metrics
    total_revisions_completed: int = 0
    total_overdue_revisions: int = 0
    retention_rate: Optional[float] = None

    # Student Breakdowns
    students_requiring_support: List[StudentProgressSummary] = Field(default_factory=list)


class SubjectAnalyticsSummary(BaseModel):
    subject_id: int
    subject_name: str
    subject_code: str
    total_students: int
    average_mastery: Optional[float] = None
    total_questions_attempted: int = 0
    accuracy_rate: Optional[float] = None
