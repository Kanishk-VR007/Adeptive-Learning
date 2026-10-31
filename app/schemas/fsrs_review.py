import enum
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import zoneinfo


class ReviewRatingEnum(int, enum.Enum):
    AGAIN = 1
    HARD = 2
    GOOD = 3
    EASY = 4


class ReviewStateEnum(int, enum.Enum):
    LEARNING = 1
    REVIEW = 2
    RELEARNING = 3


class RevisionStatusEnum(str, enum.Enum):
    NEW = "NEW"
    DUE_TODAY = "DUE_TODAY"
    OVERDUE = "OVERDUE"
    UPCOMING = "UPCOMING"
    REVIEWED = "REVIEWED"


class ReviewPreferencesResponse(BaseModel):
    student_id: int
    desired_retention: float
    timezone_name: str
    daily_new_concept_limit: int
    daily_review_display_limit: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewPreferencesUpdate(BaseModel):
    desired_retention: Optional[float] = Field(None, ge=0.70, le=0.99, description="Target retention rate (0.70 - 0.99)")
    timezone_name: Optional[str] = Field(None, description="Valid IANA timezone, e.g. 'Asia/Kolkata', 'UTC', 'America/New_York'")
    daily_new_concept_limit: Optional[int] = Field(None, ge=1, le=50, description="Max new concepts enrolled daily")
    daily_review_display_limit: Optional[int] = Field(None, ge=1, le=200, description="Max daily reviews displayed")

    @field_validator("timezone_name")
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean_tz = v.strip()
            try:
                zoneinfo.ZoneInfo(clean_tz)
            except Exception:
                raise ValueError(f"Invalid IANA timezone name: '{clean_tz}'")
            return clean_tz
        return v


class ConceptReviewStateResponse(BaseModel):
    id: int
    student_id: int
    concept_id: int
    concept_name: Optional[str] = None
    state: int
    state_name: str
    stability: float
    difficulty: float
    retrievability: Optional[float] = None
    due_at_utc: datetime
    due_at_local: Optional[datetime] = None
    last_review_at_utc: Optional[datetime] = None
    total_reviews: int
    lapses: int
    enrolled_at_utc: datetime

    model_config = {"from_attributes": True}


class RevisionQueueItem(BaseModel):
    concept_id: int
    concept_name: str
    subject_id: int
    subject_name: str
    chapter_id: int
    chapter_title: str
    due_at_utc: datetime
    due_at_local: datetime
    status: RevisionStatusEnum
    current_bkt_mastery: float
    fsrs_retrievability: Optional[float] = None
    stability: float
    difficulty: float
    review_count: int
    lapse_count: int
    priority_score: float
    recommended_action: str


class RevisionQueueResponse(BaseModel):
    total_count: int
    timezone: str
    items: List[RevisionQueueItem]


class RevisionSummaryResponse(BaseModel):
    due_today_count: int
    overdue_count: int
    upcoming_count: int
    new_count: int
    total_reviewed_count: int
    student_timezone: str


class StartRevisionResponse(BaseModel):
    session_id: int
    concept_id: int
    concept_name: str
    question_id: int
    question_text: str
    question_type: str
    question_options: Optional[Any] = None
    current_bkt_mastery: float
    retrievability: Optional[float] = None
    started_at_utc: datetime


class CompleteRevisionRequest(BaseModel):
    question_id: int
    response_text: str
    rating: int = Field(..., ge=1, le=4, description="1: Again, 2: Hard, 3: Good, 4: Easy")
    idempotency_key: Optional[str] = Field(None, description="Unique client idempotency token")
    response_id: Optional[int] = Field(None, description="Optional existing response ID if pre-submitted")


class CompleteRevisionResponse(BaseModel):
    idempotency_key: str
    concept_id: int
    concept_name: str
    rating: int
    rating_name: str
    answer_correctness: bool
    rating_valid: bool
    rating_message: Optional[str] = None
    previous_due_at_utc: Optional[datetime] = None
    next_due_at_utc: datetime
    next_due_at_local: datetime
    previous_stability: Optional[float] = None
    updated_stability: float
    previous_difficulty: Optional[float] = None
    updated_difficulty: float
    retrievability: float
    updated_bkt_mastery: float
    is_idempotent_duplicate: bool = False
    review_timestamp_utc: datetime


class ReviewHistoryItemResponse(BaseModel):
    id: int
    concept_id: int
    concept_name: Optional[str] = None
    rating: int
    rating_name: str
    answer_correctness: bool
    previous_due_at_utc: Optional[datetime] = None
    next_due_at_utc: datetime
    previous_stability: Optional[float] = None
    updated_stability: float
    previous_difficulty: Optional[float] = None
    updated_difficulty: float
    retrievability_before: Optional[float] = None
    review_timestamp_utc: datetime
    idempotency_key: str

    model_config = {"from_attributes": True}
