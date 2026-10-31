from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_db, require_teacher, require_any_authenticated_user
from app.models.user import User
from app.models.syllabus import Concept
from app.schemas.syllabus import ChapterCreate, ChapterUpdate, ChapterResponse
from app.services.syllabus_service import SyllabusService

router = APIRouter(prefix="/chapters", tags=["Syllabus: Chapters"])


@router.get(
    "",
    response_model=List[ChapterResponse],
    summary="List chapters (optionally filter by subject_id)"
)
def list_chapters(
    subject_id: Optional[int] = Query(None, description="Filter chapters by subject ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Retrieve chapters, optionally filtered by parent subject."""
    return SyllabusService.list_chapters(db=db, subject_id=subject_id, skip=skip, limit=limit)


@router.post(
    "",
    response_model=ChapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chapter within a subject (Teacher only)"
)
def create_chapter(
    chapter_in: ChapterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Create a new chapter in a subject curriculum. Restricted to teachers."""
    return SyllabusService.create_chapter(db=db, obj_in=chapter_in)


@router.get(
    "/{chapter_id}",
    response_model=ChapterResponse,
    summary="Get chapter by ID"
)
def get_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Fetch details of a single chapter by ID."""
    chapter = SyllabusService.get_chapter(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter not found")
    resp = ChapterResponse.model_validate(chapter)
    resp.concepts_count = db.query(func.count(Concept.id)).filter(Concept.chapter_id == chapter.id).scalar() or 0
    return resp


@router.put(
    "/{chapter_id}",
    response_model=ChapterResponse,
    summary="Update chapter details (Teacher only)"
)
def update_chapter(
    chapter_id: int,
    chapter_in: ChapterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Update chapter information or sequence number. Restricted to teachers."""
    return SyllabusService.update_chapter(db=db, chapter_id=chapter_id, obj_in=chapter_in)


@router.delete(
    "/{chapter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chapter (Teacher only)"
)
def delete_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Delete a chapter and cascade delete its concepts. Restricted to teachers."""
    SyllabusService.delete_chapter(db=db, chapter_id=chapter_id)
    return None
