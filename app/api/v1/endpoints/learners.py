from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_any_authenticated_user, require_teacher
from app.models.user import User
from app.schemas.learner_mastery import (
    EvidenceSubmissionRequest,
    EvidenceSubmissionResponse,
    LearnerMasteryResponse,
    LearningHistoryResponse,
    ConceptMasterySummaryResponse,
    BKTParameterOverrideCreate,
    BKTParameterResponse
)
from app.services.learner_model_service import LearnerModelService
from app.services.bkt_parameter_manager import BKTParameterManager

router = APIRouter(prefix="/learners", tags=["Learner Knowledge Model (BKT)"])


@router.get(
    "/me/mastery",
    response_model=List[LearnerMasteryResponse],
    summary="Get all concept mastery records for authenticated student"
)
def get_my_mastery_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Retrieve the continuous BKT mastery probabilities and attempt records for the student."""
    return LearnerModelService.get_student_mastery_list(db=db, student_id=current_user.id)


@router.get(
    "/me/mastery/{concept_id}",
    response_model=LearnerMasteryResponse,
    summary="Get mastery probability for a specific concept"
)
def get_my_concept_mastery(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Retrieve or initialize the student's mastery level for an individual concept."""
    return LearnerModelService.get_student_concept_mastery(
        db=db,
        student_id=current_user.id,
        concept_id=concept_id
    )


@router.get(
    "/me/history",
    response_model=List[LearningHistoryResponse],
    summary="Get student's historical learning event trail"
)
def get_my_learning_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Retrieve immutable chronological log of learning events and transition updates."""
    return LearnerModelService.get_student_learning_history(
        db=db,
        student_id=current_user.id,
        skip=skip,
        limit=limit
    )


@router.get(
    "/me/history/{concept_id}",
    response_model=List[LearningHistoryResponse],
    summary="Get student's learning history for an individual concept"
)
def get_my_concept_history(
    concept_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """Retrieve chronological learning history entries specifically for the specified concept."""
    return LearnerModelService.get_student_learning_history(
        db=db,
        student_id=current_user.id,
        concept_id=concept_id,
        skip=skip,
        limit=limit
    )


@router.post(
    "/me/concepts/{concept_id}/evidence",
    response_model=EvidenceSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit validated learning evidence and update BKT mastery"
)
def submit_concept_evidence(
    concept_id: int,
    evidence_in: EvidenceSubmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated_user)
):
    """
    Submit evaluated answer evidence (correct/incorrect) to update the concept mastery state.
    Executes pure Python BKT equations, updates attempts, and records immutable history.
    Supports idempotent resubmission via optional `evidence_id`.
    """
    return LearnerModelService.record_learning_evidence(
        db=db,
        student_id=current_user.id,
        concept_id=concept_id,
        evidence_in=evidence_in
    )


@router.get(
    "/concepts/{concept_id}/mastery-summary",
    response_model=ConceptMasterySummaryResponse,
    summary="Get cohort mastery summary on a concept (Teacher only)"
)
def get_concept_cohort_mastery(
    concept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Retrieve aggregate distribution of students in Mastered, Developing, and Weak tiers."""
    return LearnerModelService.get_concept_cohort_summary(
        db=db,
        concept_id=concept_id
    )


@router.get(
    "/{student_id}/mastery",
    response_model=List[LearnerMasteryResponse],
    summary="Get specific student's mastery profile (Teacher only)"
)
def get_student_mastery_as_teacher(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Teacher diagnostic inspection of a specific student's knowledge profile."""
    return LearnerModelService.get_student_mastery_list(db=db, student_id=student_id)


@router.post(
    "/parameters/override",
    response_model=BKTParameterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Configure subject or concept BKT parameter override (Teacher only)"
)
def set_parameter_override(
    override_in: BKTParameterOverrideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher)
):
    """Configure specialized BKT learning rates or slip/guess parameters for a subject or concept."""
    return BKTParameterManager.set_parameter_override(db=db, override_in=override_in)
