from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.assessment import Question, QuestionType, LearningSession, SessionType, LearnerResponse
from app.models.syllabus import Concept, Subject
from app.schemas.assessment import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionPracticeView,
    SessionCreate,
    SessionDetailResponse,
    ResponseSubmit,
    ResponseEvaluationResult,
    LearnerResponseHistoryItem
)
from app.services.mastery_service import MasteryService


class AssessmentService:
    # --- Question Management ---
    @classmethod
    def create_question(cls, db: Session, obj_in: QuestionCreate, creator_id: Optional[int] = None) -> QuestionResponse:
        concept = db.query(Concept).filter(Concept.id == obj_in.concept_id).first()
        if not concept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found")

        q = Question(
            concept_id=obj_in.concept_id,
            question_type=obj_in.question_type,
            question_text=obj_in.question_text.strip(),
            question_options=obj_in.question_options,
            correct_answer=obj_in.correct_answer.strip(),
            evaluation_rubric=obj_in.evaluation_rubric or {},
            difficulty_level=obj_in.difficulty_level,
            created_by_id=creator_id
        )
        db.add(q)
        db.commit()
        db.refresh(q)
        return QuestionResponse.model_validate(q)

    @classmethod
    def get_question(cls, db: Session, question_id: int) -> Optional[Question]:
        return db.query(Question).filter(Question.id == question_id).first()

    @classmethod
    def list_questions(
        cls,
        db: Session,
        concept_id: Optional[int] = None,
        difficulty_level: Optional[str] = None,
        question_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[QuestionResponse]:
        query = db.query(Question)
        if concept_id:
            query = query.filter(Question.concept_id == concept_id)
        if difficulty_level:
            query = query.filter(Question.difficulty_level == difficulty_level)
        if question_type:
            query = query.filter(Question.question_type == question_type)
        questions = query.offset(skip).limit(limit).all()
        return [QuestionResponse.model_validate(q) for q in questions]

    @classmethod
    def update_question(cls, db: Session, question_id: int, obj_in: QuestionUpdate) -> QuestionResponse:
        q = cls.get_question(db, question_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        if obj_in.concept_id is not None:
            concept = db.query(Concept).filter(Concept.id == obj_in.concept_id).first()
            if not concept:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target concept not found")
            q.concept_id = obj_in.concept_id

        if obj_in.question_type is not None:
            q.question_type = obj_in.question_type
        if obj_in.question_text is not None:
            q.question_text = obj_in.question_text.strip()
        if obj_in.question_options is not None:
            q.question_options = obj_in.question_options
        if obj_in.correct_answer is not None:
            q.correct_answer = obj_in.correct_answer.strip()
        if obj_in.evaluation_rubric is not None:
            q.evaluation_rubric = obj_in.evaluation_rubric
        if obj_in.difficulty_level is not None:
            q.difficulty_level = obj_in.difficulty_level

        db.commit()
        db.refresh(q)
        return QuestionResponse.model_validate(q)

    @classmethod
    def delete_question(cls, db: Session, question_id: int) -> None:
        q = cls.get_question(db, question_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        db.delete(q)
        db.commit()

    # --- Session Management ---
    @classmethod
    def create_learning_session(
        cls,
        db: Session,
        user_id: int,
        session_in: SessionCreate
    ) -> SessionDetailResponse:
        subject = db.query(Subject).filter(Subject.id == session_in.subject_id).first()
        if not subject:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

        # Select questions based on session type
        query = db.query(Question).join(Concept, Question.concept_id == Concept.id).filter(
            Concept.subject_id == session_in.subject_id
        )

        if session_in.target_concept_id:
            query = query.filter(Question.concept_id == session_in.target_concept_id)

        selected_questions = query.limit(session_in.question_count).all()

        session = LearningSession(
            user_id=user_id,
            subject_id=session_in.subject_id,
            session_type=session_in.session_type,
            telemetry_summary={
                "target_concept_id": session_in.target_concept_id,
                "requested_questions": session_in.question_count,
                "assigned_questions": len(selected_questions)
            }
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        practice_views = [QuestionPracticeView.model_validate(q) for q in selected_questions]

        resp = SessionDetailResponse.model_validate(session)
        resp.questions = practice_views
        return resp

    # --- Response Submission & BKT Evaluation ---
    @classmethod
    def evaluate_and_record_response(
        cls,
        db: Session,
        user_id: int,
        submit_in: ResponseSubmit
    ) -> ResponseEvaluationResult:
        question = cls.get_question(db, submit_in.question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

        # Validate Session if provided
        if submit_in.session_id:
            session = db.query(LearningSession).filter(
                LearningSession.id == submit_in.session_id,
                LearningSession.user_id == user_id
            ).first()
            if not session:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning session not found")

        # Evaluate correctness
        user_ans = submit_in.response_text.strip()
        correct_ans = question.correct_answer.strip()
        is_correct = False

        if question.question_type == QuestionType.MCQ:
            is_correct = user_ans.upper() == correct_ans.upper()
        elif question.question_type == QuestionType.NUMERIC:
            try:
                # Approximate float match with tolerance 1e-4
                is_correct = abs(float(user_ans) - float(correct_ans)) < 1e-4
            except ValueError:
                is_correct = user_ans.lower() == correct_ans.lower()
        else:
            # Open-ended: normalized string equality or keyword coverage
            is_correct = user_ans.lower() == correct_ans.lower()

        # Generate feedback
        rubric = question.evaluation_rubric or {}
        if is_correct:
            feedback = rubric.get("positive_feedback", "Correct! Well done.")
        else:
            feedback = rubric.get("explanation", f"Incorrect. The expected answer is: {correct_ans}")

        # Record response
        response_rec = LearnerResponse(
            session_id=submit_in.session_id,
            user_id=user_id,
            question_id=question.id,
            response_text=user_ans,
            is_correct=is_correct,
            confidence_score=submit_in.confidence_score,
            time_spent_ms=submit_in.time_spent_ms,
            ai_feedback=feedback
        )
        db.add(response_rec)
        db.commit()
        db.refresh(response_rec)

        # Update Bayesian Knowledge Tracing (BKT) mastery state
        prev_p, new_p, count = MasteryService.update_mastery_on_response(
            db=db,
            user_id=user_id,
            concept_id=question.concept_id,
            is_correct=is_correct
        )

        return ResponseEvaluationResult(
            response_id=response_rec.id,
            question_id=question.id,
            is_correct=is_correct,
            correct_answer=correct_ans,
            ai_feedback=feedback,
            previous_mastery_probability=prev_p,
            new_mastery_probability=new_p,
            practice_count=count
        )

    @classmethod
    def get_user_history(
        cls,
        db: Session,
        user_id: int,
        limit: int = 50
    ) -> List[LearnerResponseHistoryItem]:
        records = db.query(LearnerResponse).filter(
            LearnerResponse.user_id == user_id
        ).order_by(LearnerResponse.submitted_at.desc()).limit(limit).all()
        return [LearnerResponseHistoryItem.model_validate(r) for r in records]
