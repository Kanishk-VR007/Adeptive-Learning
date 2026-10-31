from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.concept_graph import RelationshipType
from app.models.syllabus import DifficultyLevel
from app.schemas.syllabus import ConceptResponse


class PrerequisiteCreate(BaseModel):
    concept_id: int = Field(..., description="The ID of the concept that requires the prerequisite")
    prerequisite_id: int = Field(..., description="The ID of the prerequisite concept")
    relationship_type: RelationshipType = RelationshipType.STRICT


class PrerequisiteResponse(BaseModel):
    concept_id: int
    prerequisite_id: int
    relationship_type: RelationshipType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValidatePrerequisiteRequest(BaseModel):
    concept_id: int
    prerequisite_id: int


class ValidatePrerequisiteResponse(BaseModel):
    is_valid: bool
    would_form_cycle: bool
    message: str
    cycle_path: Optional[List[int]] = None


class GraphNode(BaseModel):
    id: int
    concept_code: str
    name: str
    difficulty_level: DifficultyLevel
    subject_id: int
    chapter_id: int

    model_config = ConfigDict(from_attributes=True)


class GraphEdge(BaseModel):
    from_concept_id: int = Field(..., description="Prerequisite concept ID (source of readiness)")
    to_concept_id: int = Field(..., description="Target concept ID (dependent concept)")
    relationship_type: RelationshipType

    model_config = ConfigDict(from_attributes=True)


class SubjectGraphResponse(BaseModel):
    subject_id: int
    total_nodes: int
    total_edges: int
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class LearningPathResponse(BaseModel):
    target_concept_id: int
    target_concept_name: str
    total_steps: int
    learning_sequence: List[ConceptResponse]
