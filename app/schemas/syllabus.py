from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.syllabus import DifficultyLevel


# --- Subject Schemas ---
class SubjectBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, examples=["MATH101"])
    name: str = Field(..., min_length=2, max_length=150, examples=["Calculus I"])
    description: Optional[str] = Field(None, max_length=1000)


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None


class SubjectResponse(SubjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    chapters_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# --- Chapter Schemas ---
class ChapterBase(BaseModel):
    subject_id: int
    chapter_number: int = Field(..., ge=1, examples=[1])
    title: str = Field(..., min_length=2, max_length=200, examples=["Limits and Continuity"])
    description: Optional[str] = Field(None, max_length=1000)


class ChapterCreate(ChapterBase):
    pass


class ChapterUpdate(BaseModel):
    chapter_number: Optional[int] = Field(None, ge=1)
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None


class ChapterResponse(ChapterBase):
    id: int
    created_at: datetime
    updated_at: datetime
    concepts_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


# --- Concept Schemas ---
class ConceptBase(BaseModel):
    concept_code: str = Field(..., min_length=2, max_length=64, examples=["CALC_LIMIT_01"])
    subject_id: int
    chapter_id: int
    name: str = Field(..., min_length=2, max_length=200, examples=["Introduction to Limits"])
    description: str = Field(..., min_length=5)
    difficulty_level: DifficultyLevel = DifficultyLevel.BEGINNER
    learning_objectives: List[str] = Field(
        default_factory=list,
        examples=[["Understand the intuitive definition of a limit", "Evaluate one-sided limits"]]
    )


class ConceptCreate(ConceptBase):
    prerequisite_ids: Optional[List[int]] = Field(default_factory=list)


class ConceptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, min_length=5)
    difficulty_level: Optional[DifficultyLevel] = None
    learning_objectives: Optional[List[str]] = None
    chapter_id: Optional[int] = None


class ConceptSummary(BaseModel):
    id: int
    concept_code: str
    name: str
    difficulty_level: DifficultyLevel

    model_config = ConfigDict(from_attributes=True)


class ConceptResponse(ConceptBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConceptDetailResponse(ConceptResponse):
    prerequisites: List[ConceptSummary] = Field(default_factory=list)
    dependents: List[ConceptSummary] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
