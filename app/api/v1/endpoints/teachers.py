import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas.teacher_class import (
    ClassCreate,
    ClassResponse,
    ClassListResponse,
    EnrollStudentRequest,
    EnrolledStudentItem,
    StudentClassResponse,
)
from app.services.class_service import ClassService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teachers", tags=["Teacher & Class Management"])


@router.post("/classes", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
def create_class(
    data: ClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
):
    """Creates a new class owned by the authenticated teacher."""
    try:
        new_class = ClassService.create_class(db=db, teacher_id=current_user.id, data=data)
        return ClassResponse(
            id=new_class.id,
            name=new_class.name,
            description=new_class.description,
            enrollment_code=new_class.enrollment_code,
            teacher_id=new_class.teacher_id,
            subject_id=new_class.subject_id,
            subject_name=new_class.subject.name if new_class.subject else None,
            is_active=new_class.is_active,
            enrolled_count=0,
            created_at=new_class.created_at,
            updated_at=new_class.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/classes", response_model=ClassListResponse)
def list_my_classes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
):
    """Lists classes created by the authenticated teacher with enrollment statistics."""
    total, items = ClassService.list_classes_for_teacher(
        db=db, teacher_id=current_user.id, skip=skip, limit=limit
    )
    return ClassListResponse(total=total, items=items)


@router.get("/classes/{class_id}", response_model=ClassResponse)
def get_class_details(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
):
    """Retrieves single class details, verifying teacher ownership."""
    cls = ClassService.get_class(db=db, class_id=class_id, teacher_id=current_user.id)
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class {class_id} not found or unauthorized.",
        )
    roster = ClassService.get_class_roster(db=db, class_id=class_id, teacher_id=current_user.id)
    return ClassResponse(
        id=cls.id,
        name=cls.name,
        description=cls.description,
        enrollment_code=cls.enrollment_code,
        teacher_id=cls.teacher_id,
        subject_id=cls.subject_id,
        subject_name=cls.subject.name if cls.subject else None,
        is_active=cls.is_active,
        enrolled_count=len(roster),
        created_at=cls.created_at,
        updated_at=cls.updated_at,
    )


@router.get("/classes/{class_id}/roster", response_model=List[EnrolledStudentItem])
def get_class_roster(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
):
    """Retrieves student roster for a class with real-time mastery metrics."""
    try:
        return ClassService.get_class_roster(db=db, class_id=class_id, teacher_id=current_user.id)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: You do not own this class.",
        )


@router.post("/classes/{class_id}/enroll", status_code=status.HTTP_200_OK)
def direct_enroll_student(
    class_id: int,
    req: EnrollStudentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
):
    """Teacher directly invites or enrolls a student by email or ID."""
    target = req.student_email or (str(req.student_id) if req.student_id else None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide student_email or student_id to enroll.",
        )
    try:
        enrollment = ClassService.enroll_student_direct(
            db=db, teacher_id=current_user.id, class_id=class_id, student_email_or_id=target
        )
        return {
            "message": "Student successfully enrolled.",
            "enrollment_id": enrollment.id,
            "student_id": enrollment.student_id,
            "class_id": enrollment.class_id,
        }
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access to class.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/join", response_model=StudentClassResponse, status_code=status.HTTP_200_OK)
def student_join_class(
    req: EnrollStudentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
):
    """Allows a student to join a class using an alphanumeric enrollment code."""
    if not req.enrollment_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="enrollment_code is required to join a class.",
        )
    try:
        enrollment = ClassService.enroll_student_by_code(
            db=db, student_id=current_user.id, enrollment_code=req.enrollment_code
        )
        cls = enrollment.class_obj
        return StudentClassResponse(
            enrollment_id=enrollment.id,
            class_id=cls.id,
            class_name=cls.name,
            teacher_name=cls.teacher.full_name if cls.teacher else "Teacher",
            subject_id=cls.subject_id,
            subject_name=cls.subject.name if cls.subject else "Subject",
            enrolled_at=enrollment.enrolled_at,
            is_active=enrollment.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/my-enrolled-classes", response_model=List[StudentClassResponse])
def get_my_enrolled_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.STUDENT)),
):
    """Retrieves all active classes the current student is enrolled in."""
    return ClassService.list_classes_for_student(db=db, student_id=current_user.id)
