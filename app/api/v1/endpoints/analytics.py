import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas.analytics import ClassAnalyticsResponse, ConceptPerformanceMetric, MisconceptionMetric
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Teacher Analytics"])


@router.get("/classes/{class_id}", response_model=ClassAnalyticsResponse)
@router.get("/classes/{class_id}/summary", response_model=ClassAnalyticsResponse)
def get_class_analytics_report(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
):
    """
    Returns a comprehensive, deterministic analytics report for a teacher's class.
    Enforces strict class ownership and computes metrics dynamically from persisted learning history.
    """
    try:
        return AnalyticsService.get_class_analytics(db=db, class_id=class_id, teacher_id=current_user.id)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: You do not own this class or have access to its analytics.",
        )


@router.get("/classes/{class_id}/misconceptions", response_model=List[MisconceptionMetric])
def get_class_common_misconceptions(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
):
    """Returns ranked list of common conceptual misconceptions detected across students in the class."""
    report = get_class_analytics_report(class_id=class_id, db=db, current_user=current_user)
    return report.common_misconceptions


@router.get("/classes/{class_id}/weak-concepts", response_model=List[ConceptPerformanceMetric])
def get_class_weak_concepts(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER)),
):
    """Returns list of weak concepts where enrolled students require remediation."""
    report = get_class_analytics_report(class_id=class_id, db=db, current_user=current_user)
    return report.weak_concepts
