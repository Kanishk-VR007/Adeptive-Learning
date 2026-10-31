from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class ConceptReviewState(Base):
    """
    Maintains the individual FSRS memory state (card) for each (student, concept) pair.
    The card is concept-level and independent of individual questions.
    """
    __tablename__ = "concept_review_states"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Official serialized Card state from Card.to_json() / Card.to_dict()
    fsrs_card_json = Column(JSON, nullable=False)
    fsrs_library_version = Column(String(20), default="6.3.2", nullable=False)

    # Key indexed scheduling attributes for queries & queue generation
    due_at_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    state = Column(Integer, default=1, nullable=False)  # 1: Learning, 2: Review, 3: Relearning
    stability = Column(Float, default=0.0, nullable=False)
    difficulty = Column(Float, default=0.0, nullable=False)
    last_review_at_utc = Column(DateTime(timezone=True), nullable=True)
    total_reviews = Column(Integer, default=0, nullable=False)
    lapses = Column(Integer, default=0, nullable=False)

    enrolled_at_utc = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at_utc = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("student_id", "concept_id", name="uq_student_concept_fsrs"),
    )

    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    concept = relationship("Concept", foreign_keys=[concept_id])

    def __repr__(self) -> str:
        return (
            f"<ConceptReviewState id={self.id} student_id={self.student_id} "
            f"concept_id={self.concept_id} state={self.state} due={self.due_at_utc}>"
        )


class ReviewHistory(Base):
    """
    Immutable historical audit log of every spaced repetition review event.
    Stores the exact rating, answer validation, stability delta, and serialized ReviewLog.
    """
    __tablename__ = "review_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True)
    response_id = Column(Integer, ForeignKey("learner_responses.id", ondelete="SET NULL"), nullable=True, index=True)
    evidence_id = Column(String(100), nullable=True, index=True)
    idempotency_key = Column(String(100), unique=True, index=True, nullable=False)

    rating = Column(Integer, nullable=False)  # 1: Again, 2: Hard, 3: Good, 4: Easy
    answer_correctness = Column(Boolean, nullable=False)

    previous_due_at_utc = Column(DateTime(timezone=True), nullable=True)
    next_due_at_utc = Column(DateTime(timezone=True), nullable=False)

    previous_stability = Column(Float, nullable=True)
    updated_stability = Column(Float, nullable=False)

    previous_difficulty = Column(Float, nullable=True)
    updated_difficulty = Column(Float, nullable=False)

    retrievability_before = Column(Float, nullable=True)

    review_timestamp_utc = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Official serialized ReviewLog from ReviewLog.to_json() / ReviewLog.to_dict()
    review_log_json = Column(JSON, nullable=False)

    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    concept = relationship("Concept", foreign_keys=[concept_id])
    question = relationship("Question", foreign_keys=[question_id])

    def __repr__(self) -> str:
        return (
            f"<ReviewHistory id={self.id} student_id={self.student_id} "
            f"concept_id={self.concept_id} rating={self.rating} next_due={self.next_due_at_utc}>"
        )


class ReviewPreferences(Base):
    """
    Per-student review preferences: desired retention, local IANA timezone, and display pacing limits.
    """
    __tablename__ = "review_preferences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    desired_retention = Column(Float, default=0.90, nullable=False)
    timezone_name = Column(String(50), default="UTC", nullable=False)
    daily_new_concept_limit = Column(Integer, default=5, nullable=False)
    daily_review_display_limit = Column(Integer, default=20, nullable=False)

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
    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return (
            f"<ReviewPreferences id={self.id} student_id={self.student_id} "
            f"retention={self.desired_retention} tz={self.timezone_name}>"
        )


class FSRSConfigRecord(Base):
    """
    Versioned scheduler configuration record.
    Tracks library version, retention target, custom intervals/fuzzing, and reproducibility.
    """
    __tablename__ = "fsrs_config_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    library_version = Column(String(20), default="6.3.2", nullable=False)
    desired_retention = Column(Float, default=0.90, nullable=False)
    learning_steps = Column(JSON, nullable=True)
    relearning_steps = Column(JSON, nullable=True)
    maximum_interval = Column(Integer, default=36500, nullable=False)
    enable_fuzzing = Column(Boolean, default=True, nullable=False)
    parameters = Column(JSON, nullable=True)
    config_version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<FSRSConfigRecord id={self.id} version={self.config_version} "
            f"retention={self.desired_retention} active={self.is_active}>"
        )
