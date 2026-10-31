from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.syllabus import DifficultyLevel


def classify_mastery(mastery_probability: float) -> str:
    """
    Classify continuous BKT mastery probability into standard pedagogical tiers:
    0–39%: Weak Understanding
    40–69%: Developing Understanding
    70–89%: Good Understanding
    90–100%: Mastered
    """
    prob = max(0.0, min(1.0, mastery_probability))
    if prob >= 0.90:
        return "Mastered"
    elif prob >= 0.70:
        return "Good Understanding"
    elif prob >= 0.40:
        return "Developing Understanding"
    else:
        return "Weak Understanding"


# --- Evidence Submission ---
class EvidenceSubmissionRequest(BaseModel):
    is_correct: bool = Field(..., description="Binary outcome of learner answer evaluation")
    evidence_id: Optional[str] = Field(
        None,
        description="Optional unique idempotency identifier. If omitted, a UUID will be generated."
    )


class EvidenceSubmissionResponse(BaseModel):
    evidence_id: str
    student_id: int
    concept_id: int
    concept_name: str
    is_correct: bool
    previous_mastery: float
    posterior_mastery: float
    updated_mastery: float
    mastery_classification: str
    total_attempts: int
    correct_attempts: int
    incorrect_attempts: int
    is_idempotent_duplicate: bool = False
    timestamp: datetime


# --- Mastery Record Schemas ---
class LearnerMasteryResponse(BaseModel):
    id: int
    student_id: int
    concept_id: int
    concept_name: str
    concept_code: str
    initial_mastery: float
    current_mastery: float
    mastery_classification: str
    total_attempts: int
    correct_attempts: int
    incorrect_attempts: int
    last_attempt_at: Optional[datetime] = None
    updated_at: datetime

    # Aliases for backward compatibility
    @property
    def user_id(self) -> int:
        return self.student_id

    @property
    def mastery_probability(self) -> float:
        return self.current_mastery

    @property
    def practice_count(self) -> int:
        return self.total_attempts

    @property
    def last_practiced_at(self) -> Optional[datetime]:
        return self.last_attempt_at

    model_config = ConfigDict(from_attributes=True)


class LearningHistoryResponse(BaseModel):
    id: int
    student_id: int
    concept_id: int
    evidence_id: str
    previous_mastery: float
    posterior_mastery: float
    updated_mastery: float
    is_correct: bool
    learning_transition: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# --- BKT Parameter Schemas ---
class BKTParameterOverrideCreate(BaseModel):
    subject_id: Optional[int] = Field(None, description="Optional subject scope")
    concept_id: Optional[int] = Field(None, description="Optional concept scope")
    p_l0: float = Field(0.20, ge=0.0, le=1.0)
    p_transit: float = Field(0.10, ge=0.0, le=1.0)
    p_guess: float = Field(0.20, ge=0.0, le=1.0)
    p_slip: float = Field(0.10, ge=0.0, le=1.0)


class BKTParameterResponse(BaseModel):
    id: Optional[int] = None
    subject_id: Optional[int] = None
    concept_id: Optional[int] = None
    p_l0: float
    p_transit: float
    p_guess: float
    p_slip: float

    model_config = ConfigDict(from_attributes=True)


# --- Aggregate Summaries ---
class ConceptMasterySummaryResponse(BaseModel):
    concept_id: int
    concept_code: str
    concept_name: str
    total_students_attempted: int
    average_mastery: float
    mastered_count: int      # >= 0.90
    good_count: int          # 0.70 - 0.89
    developing_count: int    # 0.40 - 0.69
    weak_count: int          # < 0.40


# Retained for existing endpoints
class ConceptMasteryItem(BaseModel):
    concept_id: int
    concept_code: str
    concept_name: str
    chapter_id: int
    difficulty_level: DifficultyLevel
    mastery_probability: float
    practice_count: int
    status: str
    last_practiced_at: Optional[datetime] = None


class SubjectMasterySummary(BaseModel):
    user_id: int
    subject_id: int
    subject_code: str
    subject_name: str
    total_concepts: int
    mastered_count: int
    in_progress_count: int
    not_started_count: int
    average_mastery: float
    concepts: List[ConceptMasteryItem]
