import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class DifficultyLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

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
    chapters = relationship(
        "Chapter",
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="Chapter.chapter_number"
    )
    concepts = relationship(
        "Concept",
        back_populates="subject",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Subject id={self.id} code={self.code} name={self.name}>"


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

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
        UniqueConstraint("subject_id", "chapter_number", name="uq_subject_chapter_number"),
    )

    # Relationships
    subject = relationship("Subject", back_populates="chapters")
    concepts = relationship(
        "Concept",
        back_populates="chapter",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Chapter id={self.id} subject_id={self.subject_id} #{self.chapter_number}: {self.title}>"


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    concept_code = Column(String(64), unique=True, index=True, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    difficulty_level = Column(Enum(DifficultyLevel), default=DifficultyLevel.BEGINNER, nullable=False)
    learning_objectives = Column(JSON, default=list, nullable=False)

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
    subject = relationship("Subject", back_populates="concepts")
    chapter = relationship("Chapter", back_populates="concepts")

    # Directed prerequisite relations
    # concept_id is the downstream concept that HAS the prerequisite
    prerequisites = relationship(
        "ConceptPrerequisite",
        foreign_keys="[ConceptPrerequisite.concept_id]",
        back_populates="concept",
        cascade="all, delete-orphan"
    )
    # prerequisite_id is this concept, dependents are the downstream concepts
    dependents = relationship(
        "ConceptPrerequisite",
        foreign_keys="[ConceptPrerequisite.prerequisite_id]",
        back_populates="prerequisite_concept",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Concept id={self.id} code={self.concept_code} name={self.name}>"
