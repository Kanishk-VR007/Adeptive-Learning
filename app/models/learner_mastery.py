from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, Boolean, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, synonym
from app.db.session import Base


class LearnerMastery(Base):
    """
    Maintains the individual knowledge state and BKT mastery probability
    for every student and every concept independently.
    """
    __tablename__ = "learner_mastery"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)

    initial_mastery = Column(Float, default=0.20, nullable=False)
    current_mastery = Column(Float, default=0.20, nullable=False)
    total_attempts = Column(Integer, default=0, nullable=False)
    correct_attempts = Column(Integer, default=0, nullable=False)
    incorrect_attempts = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)

    # Synonyms for seamless interoperability
    p_know = synonym("current_mastery")

    @property
    def is_mastered(self) -> bool:
        return self.current_mastery >= 0.85

    @is_mastered.setter
    def is_mastered(self, value: bool):
        if value and self.current_mastery < 0.85:
            self.current_mastery = 0.85

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

    __table_args__ = (
        UniqueConstraint("student_id", "concept_id", name="uq_student_concept_mastery"),
    )

    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    concept = relationship("Concept", foreign_keys=[concept_id])

    # Backward compatibility properties
    @property
    def user_id(self) -> int:
        return self.student_id

    @user_id.setter
    def user_id(self, value: int):
        self.student_id = value

    @property
    def mastery_probability(self) -> float:
        return self.current_mastery

    @mastery_probability.setter
    def mastery_probability(self, value: float):
        self.current_mastery = value

    @property
    def practice_count(self) -> int:
        return self.total_attempts

    @practice_count.setter
    def practice_count(self, value: int):
        self.total_attempts = value

    @property
    def last_practiced_at(self):
        return self.last_attempt_at

    @last_practiced_at.setter
    def last_practiced_at(self, value):
        self.last_attempt_at = value

    def __repr__(self) -> str:
        return f"<LearnerMastery student_id={self.student_id} concept_id={self.concept_id} mastery={self.current_mastery:.4f}>"


class LearningHistory(Base):
    """
    Immutable historical audit log of every learning event, posterior calculation,
    and transition update for reproducibility and time-series mastery tracking.
    """
    __tablename__ = "learning_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(String(100), nullable=False, unique=True, index=True)

    previous_mastery = Column(Float, nullable=False)
    posterior_mastery = Column(Float, nullable=False)
    updated_mastery = Column(Float, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    learning_transition = Column(Float, default=0.10, nullable=False)

    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    created_at = synonym("timestamp")
    p_know_before = synonym("previous_mastery")
    p_know_after = synonym("updated_mastery")

    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    concept = relationship("Concept", foreign_keys=[concept_id])

    def __repr__(self) -> str:
        return (f"<LearningHistory id={self.id} student_id={self.student_id} "
                f"concept_id={self.concept_id} evidence={self.evidence_id} correct={self.is_correct}>")


class BKTParameterConfig(Base):
    """
    Configurable BKT parameter management mechanism with hierarchical inheritance:
    Concept-level override > Subject-level override > System global defaults.
    """
    __tablename__ = "bkt_parameters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=True, index=True)

    p_l0 = Column(Float, default=0.20, nullable=False)
    p_transit = Column(Float, default=0.10, nullable=False)
    p_guess = Column(Float, default=0.20, nullable=False)
    p_slip = Column(Float, default=0.10, nullable=False)

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

    __table_args__ = (
        UniqueConstraint("subject_id", "concept_id", name="uq_bkt_param_scope"),
    )

    # Relationships
    subject = relationship("Subject")
    concept = relationship("Concept")

    def __repr__(self) -> str:
        return f"<BKTParameterConfig id={self.id} subject_id={self.subject_id} concept_id={self.concept_id}>"
