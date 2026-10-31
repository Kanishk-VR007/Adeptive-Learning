from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_teacher, require_any_authenticated_user
from app.models.user import User
from app.models.syllabus import DifficultyLevel
from app.schemas.syllabus import (
    ConceptCreate,
    ConceptUpdate,
    ConceptResponse,
    ConceptDetailResponse
)
from app.services.syllabus_service import SyllabusService

router = APIRouter(prefix="/concepts", tags=["Syllabus: Concepts"])


@router.get(
    "",
    response_model=List[ConceptResponse],
    summary="List concepts with optional filters"
)
def list_concepts(
    subject_id: Optional[int] = Query(None, description="Filter by subject ID"),
    chapter_id: Optional[int] = Query(None, description="Filter by chapter ID"),
    difficulty_level: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Retrieve concepts, filterable by subject, chapter, and difficulty level."""
    return SyllabusService.list_concepts(
        db=db,
        subject_id=subject_id,
        chapter_id=chapter_id,
        difficulty_level=difficulty_level,
        skip=skip,
        limit=limit
    )


@router.post(
    "",
    response_model=ConceptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new concept (Teacher only)"
)
def create_concept(
    concept_in: ConceptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """
    Create a new concept with learning objectives and optional initial prerequisite linkages.
    Restricted to teachers.
    """
    return SyllabusService.create_concept(db=db, obj_in=concept_in)


@router.get(
    "/{concept_id}",
    response_model=ConceptDetailResponse,
    summary="Get concept details with prerequisites and dependents"
)
def get_concept(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Retrieve detailed concept information, including direct prerequisites and downstream dependents."""
    return SyllabusService.get_concept_detail(db=db, concept_id=concept_id)


@router.put(
    "/{concept_id}",
    response_model=ConceptResponse,
    summary="Update concept attributes (Teacher only)"
)
def update_concept(
    concept_id: int,
    concept_in: ConceptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Update concept properties like title, description, difficulty, or learning objectives."""
    return SyllabusService.update_concept(db=db, concept_id=concept_id, obj_in=concept_in)


@router.delete(
    "/{concept_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a concept (Teacher only)"
)
def delete_concept(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Delete a concept and cascade clean its prerequisite links. Restricted to teachers."""
    SyllabusService.delete_concept(db=db, concept_id=concept_id)
    return None
