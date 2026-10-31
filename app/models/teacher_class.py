import enum
import secrets
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


def generate_enrollment_code(length: int = 8) -> str:
    """Generates an uppercase alphanumeric enrollment code."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    enrollment_code = Column(String(32), unique=True, index=True, nullable=False, default=generate_enrollment_code)

    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

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
    teacher = relationship("User", foreign_keys=[teacher_id])
    subject = relationship("Subject", foreign_keys=[subject_id])
    enrollments = relationship(
        "ClassEnrollment",
        back_populates="class_obj",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Class id={self.id} name='{self.name}' code='{self.enrollment_code}' teacher_id={self.teacher_id}>"


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    enrolled_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_class_student_enrollment"),
    )

    # Relationships
    class_obj = relationship("Class", back_populates="enrollments")
    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return f"<ClassEnrollment id={self.id} class_id={self.class_id} student_id={self.student_id}>"
