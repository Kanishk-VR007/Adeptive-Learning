from typing import List, Optional, Union
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_teacher, require_any_authenticated_user
from app.models.user import User, UserRole
from app.schemas.assessment import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionPracticeView
)
from app.services.assessment_service import AssessmentService

router = APIRouter(prefix="/questions", tags=["Assessment: Question Bank"])


@router.post(
    "",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new question in the question bank (Teacher only)"
)
def create_question(
    question_in: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Author a new question tied to a concept with evaluation rubrics and correct answer."""
    return AssessmentService.create_question(db=db, obj_in=question_in, creator_id=current_user.id)


@router.get(
    "",
    response_model=List[QuestionResponse],
    summary="List questions in question bank (Teacher only)"
)
def list_questions(
    concept_id: Optional[int] = Query(None, description="Filter by concept ID"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty"),
    question_type: Optional[str] = Query(None, description="Filter by question type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Retrieve questions with full rubric details. Restricted to teachers."""
    return AssessmentService.list_questions(
        db=db,
        concept_id=concept_id,
        difficulty_level=difficulty_level,
        question_type=question_type,
        skip=skip,
        limit=limit
    )


@router.get(
    "/{question_id}",
    response_model=Union[QuestionResponse, QuestionPracticeView],
    summary="Get question by ID (Teachers see answer/rubric; students see practice view)"
)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Fetch question details. Correct answer is omitted for student accounts to preserve practice integrity."""
    q = AssessmentService.get_question(db, question_id)
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    if current_user.role == UserRole.TEACHER:
        return QuestionResponse.model_validate(q)
    return QuestionPracticeView.model_validate(q)


@router.put(
    "/{question_id}",
    response_model=QuestionResponse,
    summary="Update question in question bank (Teacher only)"
)
def update_question(
    question_id: int,
    question_in: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Update question content, rubrics, or options. Restricted to teachers."""
    return AssessmentService.update_question(db=db, question_id=question_id, obj_in=question_in)


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a question (Teacher only)"
)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Remove a question from the question bank. Restricted to teachers."""
    AssessmentService.delete_question(db=db, question_id=question_id)
    return None
