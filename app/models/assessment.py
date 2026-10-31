import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship, synonym
from app.db.session import Base
from app.models.syllabus import DifficultyLevel


class QuestionType(str, enum.Enum):
    MCQ = "MCQ"
    NUMERIC = "NUMERIC"
    OPEN_ENDED = "OPEN_ENDED"
    SHORT_ANSWER = "OPEN_ENDED"


class SessionType(str, enum.Enum):
    DIAGNOSTIC = "DIAGNOSTIC"
    ADAPTIVE_PRACTICE = "ADAPTIVE_PRACTICE"
    REVISION = "REVISION"
    PRACTICE = "ADAPTIVE_PRACTICE"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_type = Column(Enum(QuestionType), default=QuestionType.MCQ, nullable=False)
    question_text = Column(Text, nullable=False)
    # List of strings or dicts e.g. [{"id": "A", "text": "4"}, {"id": "B", "text": "8"}]
    question_options = Column(JSON, nullable=True)
    correct_answer = Column(Text, nullable=False)
    # Evaluation rubric guidelines, hints, or explanations
    evaluation_rubric = Column(JSON, default=dict, nullable=False)
    rubric = synonym("evaluation_rubric")
    difficulty_level = Column(Enum(DifficultyLevel), default=DifficultyLevel.BEGINNER, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    @property
    def explanation(self) -> str:
        if isinstance(self.evaluation_rubric, dict):
            return self.evaluation_rubric.get("explanation", "")
        return ""

    @explanation.setter
    def explanation(self, value: str):
        if not isinstance(self.evaluation_rubric, dict):
            self.evaluation_rubric = {}
        rubric = dict(self.evaluation_rubric)
        rubric["explanation"] = value
        self.evaluation_rubric = rubric

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    concept = relationship("Concept")
    author = relationship("User", foreign_keys=[created_by_id])
    responses = relationship("LearnerResponse", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Question id={self.id} concept_id={self.concept_id} type={self.question_type}>"


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    session_type = Column(Enum(SessionType), default=SessionType.ADAPTIVE_PRACTICE, nullable=False)

    started_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    telemetry_summary = Column(JSON, default=dict, nullable=False)

    # Synonyms for interoperability
    student_id = synonym("user_id")

    # Relationships
    user = relationship("User")
    subject = relationship("Subject")
    responses = relationship("LearnerResponse", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<LearningSession id={self.id} user_id={self.user_id} type={self.session_type}>"


class LearnerResponse(Base):
    __tablename__ = "learner_responses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("learning_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)

    response_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    confidence_score = Column(Float, nullable=True)  # Student reported confidence 0.0 - 1.0
    time_spent_ms = Column(Integer, nullable=True)   # Latency in milliseconds
    ai_feedback = Column(Text, nullable=True)        # Feedback or remediation explanation

    submitted_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Synonyms for interoperability
    student_id = synonym("user_id")
    student_answer = synonym("response_text")
    responded_at = synonym("submitted_at")
    misconception_type = synonym("ai_feedback")

    # Relationships
    session = relationship("LearningSession", back_populates="responses")
    user = relationship("User")
    question = relationship("Question", back_populates="responses")

    def __repr__(self) -> str:
        return f"<LearnerResponse id={self.id} user_id={self.user_id} correct={self.is_correct}>"

