import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.syllabus import Subject, Concept, DifficultyLevel
from app.models.assessment import Question, QuestionType, LearningSession, SessionType, LearnerResponse
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.concept_graph import ConceptPrerequisite
from app.services.bkt_service import BKTService
from app.services.graph_service import GraphService
from app.schemas.diagnostic import (
    DiagnosticSessionResponse,
    DiagnosticQuestionItem,
    DiagnosticSubmissionRequest,
    DiagnosticResultResponse,
    PrerequisiteGapItem,
)

logger = logging.getLogger(__name__)


class DiagnosticService:
    @staticmethod
    def start_diagnostic(db: Session, student_id: int, subject_id: int) -> DiagnosticSessionResponse:
        """
        Starts a diagnostic assessment session for a syllabus subject.
        Retrieves or generates calibrated diagnostic questions covering prerequisite and core concepts.
        """
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            raise ValueError(f"Subject with ID {subject_id} not found.")

        # 1. Topological order of concepts
        concepts = db.query(Concept).filter(Concept.subject_id == subject_id).all()
        if not concepts:
            raise ValueError(f"No syllabus concepts found for subject '{subject.name}'.")

        # Pick up to 5 concepts from root/fundamental concepts
        topo_order = GraphService.get_topological_sort(db, subject_id)
        concept_map = {c.id: c for c in concepts}
        ordered_concepts = [concept_map[cid] for cid in topo_order if cid in concept_map]
        if not ordered_concepts:
            ordered_concepts = concepts

        selected_concepts = ordered_concepts[:5]

        # 2. Gather or create diagnostic questions
        diagnostic_questions: List[Question] = []
        for c in selected_concepts:
            q = (
                db.query(Question)
                .filter(Question.concept_id == c.id)
                .first()
            )
            if not q:
                # Ensure diagnostic questions exist for testability
                q = Question(
                    concept_id=c.id,
                    question_text=f"Diagnostic check for {c.name}: What is the primary definition or fundamental principle of {c.name}?",
                    question_type=QuestionType.SHORT_ANSWER,
                    difficulty_level=DifficultyLevel.BEGINNER,
                    correct_answer=f"{c.name} definition",
                    explanation=f"Fundamental principle of {c.name}.",
                    rubric={"criteria": f"Understanding of {c.name}"},
                )
                db.add(q)
                db.commit()
                db.refresh(q)
            diagnostic_questions.append(q)

        # 3. Create LearningSession
        session = LearningSession(
            user_id=student_id,
            subject_id=subject_id,
            session_type=SessionType.DIAGNOSTIC,
            telemetry_summary={"total_questions": len(diagnostic_questions)},
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # 4. Format question items (without exposing answers)
        items = []
        for q in diagnostic_questions:
            c = concept_map.get(q.concept_id, selected_concepts[0])
            items.append(
                DiagnosticQuestionItem(
                    question_id=q.id,
                    concept_id=c.id,
                    concept_name=c.name,
                    concept_code=c.concept_code,
                    question_text=q.question_text,
                    options=None,
                    difficulty_level=q.difficulty_level.value if hasattr(q.difficulty_level, "value") else str(q.difficulty_level),
                )
            )

        logger.info(f"Student {student_id} started diagnostic session {session.id} for subject {subject.name} with {len(items)} questions")
        return DiagnosticSessionResponse(
            session_id=session.id,
            subject_id=subject.id,
            subject_name=subject.name,
            total_questions=len(items),
            questions=items,
        )

    @staticmethod
    def submit_diagnostic(
        db: Session, student_id: int, submission: DiagnosticSubmissionRequest
    ) -> DiagnosticResultResponse:
        """
        Evaluates diagnostic responses, updates BKT using empirical observation,
        identifies prerequisite knowledge gaps, and recommends an optimal learning path.
        """
        session = db.query(LearningSession).filter(
            LearningSession.id == submission.session_id,
            LearningSession.student_id == student_id,
        ).first()

        if not session:
            raise ValueError("Diagnostic session not found or unauthorized.")

        subject = db.query(Subject).filter(Subject.id == session.subject_id).first()
        subject_name = subject.name if subject else "Subject"

        correct_count = 0
        total_questions = len(submission.answers)
        prerequisite_gaps: List[PrerequisiteGapItem] = []
        initialized_masteries: Dict[str, float] = {}

        for ans in submission.answers:
            q = db.query(Question).filter(Question.id == ans.question_id).first()
            if not q:
                continue

            concept = db.query(Concept).filter(Concept.id == q.concept_id).first()
            if not concept:
                continue

            # Deterministic evaluation against expected answer
            clean_sub = ans.student_answer.strip().lower()
            clean_exp = q.correct_answer.strip().lower()

            # Flexible match (exact or substring or keyword)
            is_correct = (clean_sub == clean_exp) or (clean_exp in clean_sub) or (clean_sub in clean_exp and len(clean_sub) > 3)

            if is_correct:
                correct_count += 1
            else:
                # Flag prerequisite gap if incorrect on foundational concept
                prerequisite_gaps.append(
                    PrerequisiteGapItem(
                        concept_id=concept.id,
                        concept_name=concept.name,
                        concept_code=concept.concept_code,
                        reason=f"Failed diagnostic check on fundamental question for '{concept.name}'.",
                    )
                )

            # Persist LearnerResponse
            response_record = LearnerResponse(
                session_id=session.id,
                question_id=q.id,
                user_id=student_id,
                response_text=ans.student_answer,
                is_correct=is_correct,
                ai_feedback=None if is_correct else "Diagnostic Gap: Prerequisite Deficit",
            )
            db.add(response_record)

            # BKT update: Update knowledge probability using empirical observation
            from app.services.mastery_service import MasteryService
            _, updated_p, _ = MasteryService.update_mastery_on_response(
                db=db,
                user_id=student_id,
                concept_id=concept.id,
                is_correct=is_correct,
            )
            initialized_masteries[concept.name] = round(updated_p, 3)

        # Mark session finished
        session.completed_at = datetime.now(timezone.utc)
        session.telemetry_summary = {"total_questions": total_questions, "correct_count": correct_count}
        db.commit()

        # Determine recommended starting concept
        all_concepts = db.query(Concept).filter(Concept.subject_id == session.subject_id).all()
        topo_order = GraphService.get_topological_sort(db, session.subject_id)
        concept_map = {c.id: c for c in all_concepts}

        recommended_concept = None
        if prerequisite_gaps:
            # Pick earliest prerequisite gap in topological DAG
            gap_ids = {g.concept_id for g in prerequisite_gaps}
            for cid in topo_order:
                if cid in gap_ids and cid in concept_map:
                    recommended_concept = concept_map[cid]
                    break
        else:
            # If all passed, find the next unmastered concept in topo order
            for cid in topo_order:
                m = db.query(LearnerMastery).filter(
                    LearnerMastery.student_id == student_id,
                    LearnerMastery.concept_id == cid
                ).first()
                if not m or m.p_know < 0.85:
                    if cid in concept_map:
                        recommended_concept = concept_map[cid]
                        break

        if not recommended_concept and all_concepts:
            recommended_concept = all_concepts[0]

        rec_id = recommended_concept.id if recommended_concept else 0
        rec_name = recommended_concept.name if recommended_concept else "Core Subject Review"
        rec_code = recommended_concept.concept_code if recommended_concept else "CORE-001"

        accuracy_rate = round(correct_count / total_questions, 3) if total_questions > 0 else 0.0

        if prerequisite_gaps:
            summary = (
                f"Diagnostic completed with {accuracy_rate * 100:.1f}% accuracy. "
                f"Identified {len(prerequisite_gaps)} prerequisite knowledge gap(s). "
                f"Recommended starting point: '{rec_name}' to reinforce foundational concepts."
            )
        else:
            summary = (
                f"Diagnostic completed successfully with {accuracy_rate * 100:.1f}% accuracy. "
                f"Prerequisite foundations validated. Ready to begin adaptive mastery on '{rec_name}'."
            )

        logger.info(f"Diagnostic session {session.id} evaluated: {correct_count}/{total_questions} correct, recommended: {rec_name}")

        return DiagnosticResultResponse(
            session_id=session.id,
            subject_id=session.subject_id,
            subject_name=subject_name,
            total_questions=total_questions,
            correct_count=correct_count,
            accuracy_rate=accuracy_rate,
            prerequisite_gaps=prerequisite_gaps,
            initialized_masteries=initialized_masteries,
            recommended_concept_id=rec_id,
            recommended_concept_name=rec_name,
            recommended_concept_code=rec_code,
            learning_path_summary=summary,
        )
