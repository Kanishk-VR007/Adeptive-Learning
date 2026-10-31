from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_teacher, require_any_authenticated_user
from app.models.user import User
from app.schemas.syllabus import SubjectCreate, SubjectUpdate, SubjectResponse
from app.services.syllabus_service import SyllabusService

router = APIRouter(prefix="/subjects", tags=["Syllabus: Subjects"])


@router.get(
    "",
    response_model=List[SubjectResponse],
    summary="List all subjects"
)
def list_subjects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Retrieve all available curriculum subjects."""
    return SyllabusService.list_subjects(db=db, skip=skip, limit=limit)


@router.post(
    "",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subject (Teacher only)"
)
def create_subject(
    subject_in: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Create a new academic subject. Restricted to teachers."""
    return SyllabusService.create_subject(db=db, obj_in=subject_in)


@router.get(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Get subject by ID"
)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Fetch details of a single subject by ID."""
    subject = SyllabusService.get_subject(db, subject_id)
    if not subject:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    resp = SubjectResponse.model_validate(subject)
    from sqlalchemy import func
    from app.models.syllabus import Chapter
    resp.chapters_count = db.query(func.count(Chapter.id)).filter(Chapter.subject_id == subject.id).scalar() or 0
    return resp


@router.put(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Update subject details (Teacher only)"
)
def update_subject(
    subject_id: int,
    subject_in: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Update subject information. Restricted to teachers."""
    return SyllabusService.update_subject(db=db, subject_id=subject_id, obj_in=subject_in)


@router.delete(
    "/{subject_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subject (Teacher only)"
)
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Delete a subject and cascade delete chapters and concepts. Restricted to teachers."""
    SyllabusService.delete_subject(db=db, subject_id=subject_id)
    return None
