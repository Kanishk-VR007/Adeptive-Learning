import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.syllabus import Concept
from app.services.bkt_service import BKTService
from app.services.bkt_parameter_manager import BKTParameterManager
from app.schemas.learner_mastery import (
    classify_mastery,
    EvidenceSubmissionRequest,
    EvidenceSubmissionResponse,
    LearnerMasteryResponse,
    LearningHistoryResponse,
    ConceptMasterySummaryResponse
)


class LearnerModelService:
    """
    Core orchestrator for individual student knowledge tracing.
    Guarantees that each student and concept pair maintains an isolated,
    deterministic knowledge state without combining records.
    """

    @classmethod
    def record_learning_evidence(
        cls,
        db: Session,
        student_id: int,
        concept_id: int,
        evidence_in: EvidenceSubmissionRequest
    ) -> EvidenceSubmissionResponse:
        # 1. Validate concept exists
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID {concept_id} not found"
            )

        # 2. Idempotency Check: prevent duplicate evidence processing
        evidence_id = evidence_in.evidence_id or f"ev_{uuid.uuid4().hex}"
        existing_history = db.query(LearningHistory).filter(
            LearningHistory.evidence_id == evidence_id
        ).first()

        if existing_history:
            # If evidence was already processed, retrieve current state idempotently
            mastery = db.query(LearnerMastery).filter(
                LearnerMastery.student_id == student_id,
                LearnerMastery.concept_id == concept_id
            ).first()
            current_p = mastery.current_mastery if mastery else existing_history.updated_mastery
            return EvidenceSubmissionResponse(
                evidence_id=existing_history.evidence_id,
                student_id=existing_history.student_id,
                concept_id=existing_history.concept_id,
                concept_name=concept.name,
                is_correct=existing_history.is_correct,
                previous_mastery=existing_history.previous_mastery,
                posterior_mastery=existing_history.posterior_mastery,
                updated_mastery=existing_history.updated_mastery,
                mastery_classification=classify_mastery(existing_history.updated_mastery),
                total_attempts=mastery.total_attempts if mastery else 1,
                correct_attempts=mastery.correct_attempts if mastery else (1 if existing_history.is_correct else 0),
                incorrect_attempts=mastery.incorrect_attempts if mastery else (0 if existing_history.is_correct else 1),
                is_idempotent_duplicate=True,
                timestamp=existing_history.timestamp
            )

        # 3. Retrieve or initialize LearnerMastery record
        params = BKTParameterManager.get_parameters_for_concept(db, concept_id)
        mastery = db.query(LearnerMastery).filter(
            LearnerMastery.student_id == student_id,
            LearnerMastery.concept_id == concept_id
        ).first()

        now = datetime.now(timezone.utc)
        if not mastery:
            mastery = LearnerMastery(
                student_id=student_id,
                concept_id=concept_id,
                initial_mastery=params.p_l0,
                current_mastery=params.p_l0,
                total_attempts=0,
                correct_attempts=0,
                incorrect_attempts=0,
                last_attempt_at=now
            )
            db.add(mastery)
            db.flush()

        # 4. Calculate BKT update
        result = BKTService.update_mastery(
            current_mastery=mastery.current_mastery,
            is_correct=evidence_in.is_correct,
            params=params
        )

        # 5. Update Mastery Record
        mastery.current_mastery = result.updated_mastery
        mastery.total_attempts += 1
        if evidence_in.is_correct:
            mastery.correct_attempts += 1
        else:
            mastery.incorrect_attempts += 1
        mastery.last_attempt_at = now

        # 6. Insert Immutable Learning History Record
        history_entry = LearningHistory(
            student_id=student_id,
            concept_id=concept_id,
            evidence_id=evidence_id,
            previous_mastery=result.previous_mastery,
            posterior_mastery=result.posterior_mastery,
            updated_mastery=result.updated_mastery,
            is_correct=evidence_in.is_correct,
            learning_transition=params.p_transit,
            timestamp=now
        )
        db.add(history_entry)

        # Commit entire transaction
        db.commit()
        db.refresh(mastery)

        return EvidenceSubmissionResponse(
            evidence_id=evidence_id,
            student_id=student_id,
            concept_id=concept_id,
            concept_name=concept.name,
            is_correct=evidence_in.is_correct,
            previous_mastery=result.previous_mastery,
            posterior_mastery=result.posterior_mastery,
            updated_mastery=result.updated_mastery,
            mastery_classification=classify_mastery(result.updated_mastery),
            total_attempts=mastery.total_attempts,
            correct_attempts=mastery.correct_attempts,
            incorrect_attempts=mastery.incorrect_attempts,
            is_idempotent_duplicate=False,
            timestamp=now
        )

    @classmethod
    def get_student_mastery_list(
        cls,
        db: Session,
        student_id: int
    ) -> List[LearnerMasteryResponse]:
        """Fetch all mastery records for an individual student."""
        records = db.query(LearnerMastery).filter(
            LearnerMastery.student_id == student_id
        ).all()

        results = []
        for r in records:
            c = r.concept
            results.append(
                LearnerMasteryResponse(
                    id=r.id,
                    student_id=r.student_id,
                    concept_id=r.concept_id,
                    concept_name=c.name if c else f"Concept {r.concept_id}",
                    concept_code=c.concept_code if c else "",
                    initial_mastery=r.initial_mastery,
                    current_mastery=r.current_mastery,
                    mastery_classification=classify_mastery(r.current_mastery),
                    total_attempts=r.total_attempts,
                    correct_attempts=r.correct_attempts,
                    incorrect_attempts=r.incorrect_attempts,
                    last_attempt_at=r.last_attempt_at,
                    updated_at=r.updated_at
                )
            )
        return results

    @classmethod
    def get_student_concept_mastery(
        cls,
        db: Session,
        student_id: int,
        concept_id: int
    ) -> LearnerMasteryResponse:
        """Fetch a student's mastery for a single concept, initializing if not attempted."""
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID {concept_id} not found"
            )

        mastery = db.query(LearnerMastery).filter(
            LearnerMastery.student_id == student_id,
            LearnerMastery.concept_id == concept_id
        ).first()

        params = BKTParameterManager.get_parameters_for_concept(db, concept_id)
        now = datetime.now(timezone.utc)

        if not mastery:
            return LearnerMasteryResponse(
                id=0,
                student_id=student_id,
                concept_id=concept_id,
                concept_name=concept.name,
                concept_code=concept.concept_code,
                initial_mastery=params.p_l0,
                current_mastery=params.p_l0,
                mastery_classification=classify_mastery(params.p_l0),
                total_attempts=0,
                correct_attempts=0,
                incorrect_attempts=0,
                last_attempt_at=None,
                updated_at=now
            )

        return LearnerMasteryResponse(
            id=mastery.id,
            student_id=mastery.student_id,
            concept_id=mastery.concept_id,
            concept_name=concept.name,
            concept_code=concept.concept_code,
            initial_mastery=mastery.initial_mastery,
            current_mastery=mastery.current_mastery,
            mastery_classification=classify_mastery(mastery.current_mastery),
            total_attempts=mastery.total_attempts,
            correct_attempts=mastery.correct_attempts,
            incorrect_attempts=mastery.incorrect_attempts,
            last_attempt_at=mastery.last_attempt_at,
            updated_at=mastery.updated_at
        )

    @classmethod
    def get_student_learning_history(
        cls,
        db: Session,
        student_id: int,
        concept_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[LearningHistoryResponse]:
        """Fetch paginated, immutable learning history for a student."""
        query = db.query(LearningHistory).filter(LearningHistory.student_id == student_id)
        if concept_id:
            query = query.filter(LearningHistory.concept_id == concept_id)

        records = query.order_by(LearningHistory.timestamp.desc()).offset(skip).limit(limit).all()
        return [LearningHistoryResponse.model_validate(r) for r in records]

    @classmethod
    def get_concept_cohort_summary(
        cls,
        db: Session,
        concept_id: int
    ) -> ConceptMasterySummaryResponse:
        """Authorized aggregate summary of student cohort mastery on a concept."""
        concept = db.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Concept with ID {concept_id} not found"
            )

        mastery_records = db.query(LearnerMastery).filter(
            LearnerMastery.concept_id == concept_id
        ).all()

        total = len(mastery_records)
        if total == 0:
            return ConceptMasterySummaryResponse(
                concept_id=concept.id,
                concept_code=concept.concept_code,
                concept_name=concept.name,
                total_students_attempted=0,
                average_mastery=0.0,
                mastered_count=0,
                good_count=0,
                developing_count=0,
                weak_count=0
            )

        mastered = sum(1 for m in mastery_records if m.current_mastery >= 0.90)
        good = sum(1 for m in mastery_records if 0.70 <= m.current_mastery < 0.90)
        developing = sum(1 for m in mastery_records if 0.40 <= m.current_mastery < 0.70)
        weak = sum(1 for m in mastery_records if m.current_mastery < 0.40)
        avg = sum(m.current_mastery for m in mastery_records) / total

        return ConceptMasterySummaryResponse(
            concept_id=concept.id,
            concept_code=concept.concept_code,
            concept_name=concept.name,
            total_students_attempted=total,
            average_mastery=round(avg, 4),
            mastered_count=mastered,
            good_count=good,
            developing_count=developing,
            weak_count=weak
        )
