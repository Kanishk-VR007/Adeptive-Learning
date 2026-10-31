import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class RelationshipType(str, enum.Enum):
    STRICT = "STRICT"
    RECOMMENDED = "RECOMMENDED"
    PREREQUISITE = "STRICT"


class ConceptPrerequisite(Base):
    __tablename__ = "concept_prerequisites"

    # concept_id: the concept that requires the prerequisite
    concept_id = Column(
        Integer,
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    # prerequisite_id: the required precursor concept
    prerequisite_id = Column(
        Integer,
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
        index=True
    )
    relationship_type = Column(
        Enum(RelationshipType),
        default=RelationshipType.STRICT,
        nullable=False
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        CheckConstraint("concept_id != prerequisite_id", name="ck_no_self_prerequisite"),
    )

    # Relationships
    concept = relationship(
        "Concept",
        foreign_keys=[concept_id],
        back_populates="prerequisites"
    )
    prerequisite_concept = relationship(
        "Concept",
        foreign_keys=[prerequisite_id],
        back_populates="dependents"
    )

    def __repr__(self) -> str:
        return f"<ConceptPrerequisite concept_id={self.concept_id} depends_on={self.prerequisite_id}>"
