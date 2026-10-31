from datetime import datetime, timezone
from typing import Optional, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.learner_mastery import LearnerMastery
from app.models.syllabus import Subject, Concept
from app.schemas.learner_mastery import SubjectMasterySummary, ConceptMasteryItem, LearnerMasteryResponse


class MasteryService:
    @classmethod
    def get_or_create_mastery(
        cls,
        db: Session,
        user_id: int,
        concept_id: int
    ) -> LearnerMastery:
        """Fetch existing mastery record or create initial state."""
        mastery = db.query(LearnerMastery).filter(
            LearnerMastery.student_id == user_id,
            LearnerMastery.concept_id == concept_id
        ).first()

        if not mastery:
            from app.services.bkt_parameter_manager import BKTParameterManager
            params = BKTParameterManager.get_parameters_for_concept(db, concept_id)
            mastery = LearnerMastery(
                student_id=user_id,
                concept_id=concept_id,
                initial_mastery=params.p_l0,
                current_mastery=params.p_l0,
                total_attempts=0,
                correct_attempts=0,
                incorrect_attempts=0
            )
            db.add(mastery)
            db.commit()
            db.refresh(mastery)

        return mastery

    @classmethod
    def update_mastery_on_response(
        cls,
        db: Session,
        user_id: int,
        concept_id: int,
        is_correct: bool
    ) -> tuple[float, float, int]:
        """
        Update student mastery probability using the standard Bayesian Knowledge Tracing (BKT) formula.
        Returns: (previous_p, updated_p, practice_count)
        """
        from app.services.bkt_parameter_manager import BKTParameterManager
        from app.services.bkt_service import BKTService

        mastery = cls.get_or_create_mastery(db, user_id, concept_id)
        params = BKTParameterManager.get_parameters_for_concept(db, concept_id)
        previous_p = mastery.current_mastery

        res = BKTService.update_mastery(
            current_mastery=mastery.current_mastery,
            is_correct=is_correct,
            params=params
        )

        mastery.current_mastery = round(res.updated_mastery, 4)
        mastery.total_attempts += 1
        if is_correct:
            mastery.correct_attempts += 1
        else:
            mastery.incorrect_attempts += 1
        mastery.last_attempt_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(mastery)

        return previous_p, mastery.current_mastery, mastery.total_attempts

    @classmethod
    def get_user_subject_mastery(
        cls,
        db: Session,
        user_id: int,
        subject_id: int
    ) -> SubjectMasterySummary:
        """Compute the aggregate mastery summary and concept breakdown for a user in a subject."""
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

        concepts = db.query(Concept).filter(Concept.subject_id == subject_id).all()
        if not concepts:
            return SubjectMasterySummary(
                user_id=user_id,
                subject_id=subject_id,
                subject_code=subject.code,
                subject_name=subject.name,
                total_concepts=0,
                mastered_count=0,
                in_progress_count=0,
                not_started_count=0,
                average_mastery=0.0,
                concepts=[]
            )

        concept_ids = [c.id for c in concepts]
        mastery_records = db.query(LearnerMastery).filter(
            LearnerMastery.student_id == user_id,
            LearnerMastery.concept_id.in_(concept_ids)
        ).all()

        mastery_map: Dict[int, LearnerMastery] = {m.concept_id: m for m in mastery_records}

        mastered_count = 0
        in_progress_count = 0
        not_started_count = 0
        total_p = 0.0
        concept_items = []

        for c in concepts:
            m = mastery_map.get(c.id)
            p = m.current_mastery if m else 0.20
            count = m.total_attempts if m else 0
            last_date = m.last_attempt_at if m else None

            if p >= 0.85:
                status_str = "MASTERED"
                mastered_count += 1
            elif p >= 0.25:
                status_str = "IN_PROGRESS"
                in_progress_count += 1
            else:
                status_str = "NOT_STARTED"
                not_started_count += 1

            total_p += p
            concept_items.append(
                ConceptMasteryItem(
                    concept_id=c.id,
                    concept_code=c.concept_code,
                    concept_name=c.name,
                    chapter_id=c.chapter_id,
                    difficulty_level=c.difficulty_level,
                    mastery_probability=round(p, 4),
                    practice_count=count,
                    status=status_str,
                    last_practiced_at=last_date
                )
            )

        avg_mastery = round(total_p / len(concepts), 4) if concepts else 0.0

        return SubjectMasterySummary(
            user_id=user_id,
            subject_id=subject.id,
            subject_code=subject.code,
            subject_name=subject.name,
            total_concepts=len(concepts),
            mastered_count=mastered_count,
            in_progress_count=in_progress_count,
            not_started_count=not_started_count,
            average_mastery=avg_mastery,
            concepts=concept_items
        )
