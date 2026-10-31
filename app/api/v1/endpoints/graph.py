from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_teacher, require_any_authenticated_user
from app.models.user import User
from app.schemas.concept_graph import (
    PrerequisiteCreate,
    PrerequisiteResponse,
    ValidatePrerequisiteRequest,
    ValidatePrerequisiteResponse,
    SubjectGraphResponse,
    LearningPathResponse
)
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["Concept Knowledge Graph"])


@router.post(
    "/prerequisites",
    response_model=PrerequisiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a directed prerequisite edge with cycle prevention (Teacher only)"
)
def add_prerequisite(
    edge_in: PrerequisiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """
    Establish a directed prerequisite relationship: `concept_id` requires `prerequisite_id`.
    Automatically checks and rejects requests that would create an invalid dependency cycle.
    Restricted to teachers.
    """
    edge = GraphService.add_prerequisite(
        db=db,
        concept_id=edge_in.concept_id,
        prerequisite_id=edge_in.prerequisite_id,
        relationship_type=edge_in.relationship_type
    )
    return PrerequisiteResponse.model_validate(edge)


@router.delete(
    "/prerequisites/{concept_id}/{prerequisite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a prerequisite relationship (Teacher only)"
)
def remove_prerequisite(
    concept_id: int,
    prerequisite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """
    Remove an existing directed prerequisite relationship.
    Restricted to teachers.
    """
    GraphService.remove_prerequisite(
        db=db,
        concept_id=concept_id,
        prerequisite_id=prerequisite_id
    )
    return None


@router.post(
    "/validate-link",
    response_model=ValidatePrerequisiteResponse,
    summary="Pre-flight validation for a proposed prerequisite link"
)
def validate_link(
    req: ValidatePrerequisiteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """
    Pre-flight check without saving to database: test whether adding this link
    would introduce a cycle or violate constraints.
    """
    return GraphService.validate_prerequisite(
        db=db,
        concept_id=req.concept_id,
        prerequisite_id=req.prerequisite_id
    )


@router.get(
    "/subject/{subject_id}",
    response_model=SubjectGraphResponse,
    summary="Get full concept graph (nodes and edges) for a subject"
)
def get_subject_graph(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """
    Retrieve all concept nodes and directed prerequisite edges for a subject.
    Ideal for curriculum visualization and DAG rendering.
    """
    return GraphService.get_subject_graph(db=db, subject_id=subject_id)


@router.get(
    "/concepts/{concept_id}/learning-path",
    response_model=LearningPathResponse,
    summary="Compute topological learning sequence for a concept"
)
def get_concept_learning_path(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """
    Generate an optimal, prerequisite-ordered learning sequence (topologically sorted)
    starting from prerequisite fundamentals and leading to the target concept.
    """
    return GraphService.get_learning_path(db=db, target_concept_id=concept_id)
