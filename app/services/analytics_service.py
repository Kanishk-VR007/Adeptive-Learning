import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.teacher_class import Class, ClassEnrollment
from app.models.user import User
from app.models.syllabus import Subject, Concept
from app.models.learner_mastery import LearnerMastery
from app.models.assessment import LearnerResponse
from app.models.fsrs_review import ConceptReviewState, ReviewHistory
from app.schemas.analytics import (
    ClassAnalyticsResponse,
    ConceptPerformanceMetric,
    MisconceptionMetric,
    StudentProgressSummary,
    SubjectAnalyticsSummary,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    @staticmethod
    def get_class_analytics(db: Session, class_id: int, teacher_id: int) -> ClassAnalyticsResponse:
        """
        Calculates deterministic, database-backed learning analytics for a teacher's class.
        Strictly enforces class ownership and never fabricates scores.
        """
        cls = db.query(Class).filter(Class.id == class_id, Class.teacher_id == teacher_id).first()
        if not cls:
            raise PermissionError("Class not found or unauthorized access.")

        # 1. Enrolled students
        enrollments = (
            db.query(ClassEnrollment)
            .filter(ClassEnrollment.class_id == class_id, ClassEnrollment.is_active == True)
            .all()
        )
        enrolled_student_ids = [e.student_id for e in enrollments]
        total_enrolled = len(enrolled_student_ids)

        if total_enrolled == 0:
            return ClassAnalyticsResponse(
                class_id=cls.id,
                class_name=cls.name,
                subject_id=cls.subject_id,
                subject_name=cls.subject.name if cls.subject else "Subject",
                total_enrolled=0,
                active_students_count=0,
                participation_rate=0.0,
                average_mastery=None,
                concept_performances=[],
                weak_concepts=[],
                common_misconceptions=[],
                overall_accuracy_rate=None,
                total_questions_attempted=0,
                total_revisions_completed=0,
                total_overdue_revisions=0,
                retention_rate=None,
                students_requiring_support=[],
            )

        # 2. Activity threshold (e.g. within last 30 days)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        active_student_ids = set(
            row[0] for row in (
                db.query(LearnerResponse.user_id)
                .filter(
                    LearnerResponse.user_id.in_(enrolled_student_ids),
                    LearnerResponse.submitted_at >= cutoff_date
                )
                .distinct()
                .all()
            )
        )
        active_count = len(active_student_ids)
        participation_rate = round(active_count / total_enrolled, 3)

        # 3. Concepts in this subject
        subject_concepts = db.query(Concept).filter(Concept.subject_id == cls.subject_id).all()
        concept_ids = [c.id for c in subject_concepts]

        # 4. Class average mastery across concepts
        mastery_avg = (
            db.query(func.avg(LearnerMastery.p_know))
            .filter(
                LearnerMastery.student_id.in_(enrolled_student_ids),
                LearnerMastery.concept_id.in_(concept_ids)
            )
            .scalar()
        )
        class_avg_mastery = round(float(mastery_avg), 3) if mastery_avg is not None else None

        # 5. Concept performance breakdown
        concept_metrics: List[ConceptPerformanceMetric] = []
        for c in subject_concepts:
            # Mastery stats
            c_masteries = (
                db.query(LearnerMastery.p_know)
                .filter(
                    LearnerMastery.concept_id == c.id,
                    LearnerMastery.student_id.in_(enrolled_student_ids)
                )
                .all()
            )
            scores = [m[0] for m in c_masteries if m[0] is not None]
            c_avg = round(sum(scores) / len(scores), 3) if scores else None
            mastered_cnt = sum(1 for s in scores if s >= 0.85)
            remed_cnt = sum(1 for s in scores if s < 0.60)

            # Response attempts & errors
            from app.models.assessment import Question
            attempts = (
                db.query(LearnerResponse)
                .join(Question, LearnerResponse.question_id == Question.id)
                .filter(
                    Question.concept_id == c.id,
                    LearnerResponse.user_id.in_(enrolled_student_ids)
                )
                .all()
            )
            total_att = len(attempts)
            incorrect_att = sum(1 for a in attempts if not a.is_correct)
            err_rate = round(incorrect_att / total_att, 3) if total_att > 0 else 0.0

            concept_metrics.append(
                ConceptPerformanceMetric(
                    concept_id=c.id,
                    concept_name=c.name,
                    concept_code=c.concept_code,
                    average_mastery=c_avg,
                    students_mastered=mastered_cnt,
                    students_remediating=remed_cnt,
                    attempts_count=total_att,
                    error_rate=err_rate,
                )
            )

        # Identify weak concepts: lowest mastery or error rate > 0.35
        weak_concepts = [
            cm for cm in concept_metrics
            if (cm.average_mastery is not None and cm.average_mastery < 0.60) or cm.error_rate > 0.35
        ]
        weak_concepts.sort(key=lambda x: (x.average_mastery if x.average_mastery is not None else 1.0))

        # 6. Common misconceptions
        misconception_records = (
            db.query(
                LearnerResponse.ai_feedback,
                Question.concept_id,
                func.count(LearnerResponse.id)
            )
            .join(Question, LearnerResponse.question_id == Question.id)
            .filter(
                LearnerResponse.user_id.in_(enrolled_student_ids),
                LearnerResponse.ai_feedback.isnot(None),
                LearnerResponse.ai_feedback != "none",
                LearnerResponse.ai_feedback != ""
            )
            .group_by(LearnerResponse.ai_feedback, Question.concept_id)
            .order_by(desc(func.count(LearnerResponse.id)))
            .limit(20)
            .all()
        )

        concept_name_map = {c.id: c.name for c in subject_concepts}
        misc_dict: Dict[str, MisconceptionMetric] = {}
        for misc_type, c_id, count in misconception_records:
            if misc_type not in misc_dict:
                misc_dict[misc_type] = MisconceptionMetric(
                    category=misc_type,
                    description=f"Identified misconception in {misc_type}",
                    occurrence_count=count,
                    concept_names=[concept_name_map.get(c_id, f"Concept #{c_id}")],
                )
            else:
                misc_dict[misc_type].occurrence_count += count
                c_name = concept_name_map.get(c_id, f"Concept #{c_id}")
                if c_name not in misc_dict[misc_type].concept_names:
                    misc_dict[misc_type].concept_names.append(c_name)

        common_misconceptions = sorted(misc_dict.values(), key=lambda x: x.occurrence_count, reverse=True)

        # 7. Overall accuracy
        total_q_attempts = (
            db.query(LearnerResponse)
            .filter(LearnerResponse.user_id.in_(enrolled_student_ids))
            .count()
        )
        total_correct = (
            db.query(LearnerResponse)
            .filter(
                LearnerResponse.user_id.in_(enrolled_student_ids),
                LearnerResponse.is_correct == True
            )
            .count()
        )
        overall_acc = round(total_correct / total_q_attempts, 3) if total_q_attempts > 0 else None

        # 8. Revisions & retention
        total_revisions_completed = (
            db.query(ReviewHistory)
            .filter(ReviewHistory.student_id.in_(enrolled_student_ids))
            .count()
        )

        now_utc = datetime.now(timezone.utc)
        total_overdue = (
            db.query(ConceptReviewState)
            .filter(
                ConceptReviewState.student_id.in_(enrolled_student_ids),
                ConceptReviewState.due_at_utc < now_utc
            )
            .count()
        )

        all_states = (
            db.query(ConceptReviewState)
            .filter(ConceptReviewState.student_id.in_(enrolled_student_ids))
            .all()
        )
        retention_rate = None
        if all_states:
            # Average stability or computed retrievability
            stabilities = [s.stability for s in all_states if s.stability > 0]
            retention_rate = round(sum(stabilities) / len(stabilities), 2) if stabilities else None

        # 9. Students requiring support
        support_students: List[StudentProgressSummary] = []
        for sid in enrolled_student_ids:
            student_user = db.query(User).filter(User.id == sid).first()
            if not student_user:
                continue

            st_mastery = (
                db.query(func.avg(LearnerMastery.p_know))
                .filter(
                    LearnerMastery.student_id == sid,
                    LearnerMastery.concept_id.in_(concept_ids)
                )
                .scalar()
            )
            st_mastery_val = round(float(st_mastery), 3) if st_mastery is not None else None

            st_attempts = db.query(LearnerResponse).filter(LearnerResponse.user_id == sid).count()
            st_correct = db.query(LearnerResponse).filter(LearnerResponse.user_id == sid, LearnerResponse.is_correct == True).count()
            st_acc = round(st_correct / st_attempts, 3) if st_attempts > 0 else None

            st_overdue = db.query(ConceptReviewState).filter(
                ConceptReviewState.student_id == sid,
                ConceptReviewState.due_at_utc < now_utc
            ).count()

            st_rev_done = db.query(ReviewHistory).filter(ReviewHistory.student_id == sid).count()

            st_weak_cnt = (
                db.query(LearnerMastery)
                .filter(
                    LearnerMastery.student_id == sid,
                    LearnerMastery.concept_id.in_(concept_ids),
                    LearnerMastery.p_know < 0.60
                )
                .count()
            )

            last_resp = (
                db.query(LearnerResponse.submitted_at)
                .filter(LearnerResponse.user_id == sid)
                .order_by(LearnerResponse.submitted_at.desc())
                .first()
            )
            last_active = last_resp[0] if last_resp else None

            # Add to support list if low mastery, high overdue, or weak concepts
            needs_help = (
                (st_mastery_val is not None and st_mastery_val < 0.60)
                or (st_acc is not None and st_acc < 0.50)
                or st_overdue >= 3
                or st_weak_cnt >= 2
            )

            if needs_help:
                support_students.append(
                    StudentProgressSummary(
                        student_id=sid,
                        full_name=student_user.full_name,
                        email=student_user.email,
                        overall_mastery=st_mastery_val,
                        questions_attempted=st_attempts,
                        correct_attempts=st_correct,
                        accuracy_rate=st_acc,
                        revisions_completed=st_rev_done,
                        overdue_revisions=st_overdue,
                        weak_concepts_count=st_weak_cnt,
                        last_active=last_active,
                    )
                )

        return ClassAnalyticsResponse(
            class_id=cls.id,
            class_name=cls.name,
            subject_id=cls.subject_id,
            subject_name=cls.subject.name if cls.subject else "Subject",
            total_enrolled=total_enrolled,
            active_students_count=active_count,
            participation_rate=participation_rate,
            average_mastery=class_avg_mastery,
            concept_performances=concept_metrics,
            weak_concepts=weak_concepts,
            common_misconceptions=common_misconceptions,
            overall_accuracy_rate=overall_acc,
            total_questions_attempted=total_q_attempts,
            total_revisions_completed=total_revisions_completed,
            total_overdue_revisions=total_overdue,
            retention_rate=retention_rate,
            students_requiring_support=support_students,
        )
