import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models.teacher_class import Class, ClassEnrollment, generate_enrollment_code
from app.models.user import User, UserRole
from app.models.syllabus import Subject
from app.models.learner_mastery import LearnerMastery
from app.models.assessment import LearnerResponse
from app.schemas.teacher_class import ClassCreate, ClassUpdate, ClassResponse, EnrolledStudentItem, StudentClassResponse

logger = logging.getLogger(__name__)


class ClassService:
    @staticmethod
    def create_class(db: Session, teacher_id: int, data: ClassCreate) -> Class:
        """Creates a new class for an authorized teacher."""
        subject = db.query(Subject).filter(Subject.id == data.subject_id).first()
        if not subject:
            raise ValueError(f"Subject with ID {data.subject_id} not found.")

        # Generate unique enrollment code
        code = generate_enrollment_code()
        while db.query(Class).filter(Class.enrollment_code == code).first():
            code = generate_enrollment_code()

        new_class = Class(
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            enrollment_code=code,
            teacher_id=teacher_id,
            subject_id=data.subject_id,
            is_active=True,
        )
        db.add(new_class)
        db.commit()
        db.refresh(new_class)
        logger.info(f"Class '{new_class.name}' (id={new_class.id}, code={new_class.enrollment_code}) created by teacher {teacher_id}")
        return new_class

    @staticmethod
    def get_class(db: Session, class_id: int, teacher_id: Optional[int] = None) -> Optional[Class]:
        """Retrieves a class by ID, optionally verifying teacher ownership."""
        query = db.query(Class).options(joinedload(Class.subject)).filter(Class.id == class_id)
        if teacher_id is not None:
            query = query.filter(Class.teacher_id == teacher_id)
        return query.first()

    @staticmethod
    def list_classes_for_teacher(db: Session, teacher_id: int, skip: int = 0, limit: int = 50) -> Tuple[int, List[ClassResponse]]:
        """Lists classes owned by a teacher with enrolled student counts."""
        base_query = db.query(Class).filter(Class.teacher_id == teacher_id)
        total = base_query.count()

        classes = base_query.options(joinedload(Class.subject)).order_by(Class.created_at.desc()).offset(skip).limit(limit).all()

        results = []
        for c in classes:
            enrolled_count = db.query(ClassEnrollment).filter(
                ClassEnrollment.class_id == c.id,
                ClassEnrollment.is_active == True
            ).count()

            results.append(
                ClassResponse(
                    id=c.id,
                    name=c.name,
                    description=c.description,
                    enrollment_code=c.enrollment_code,
                    teacher_id=c.teacher_id,
                    subject_id=c.subject_id,
                    subject_name=c.subject.name if c.subject else None,
                    is_active=c.is_active,
                    enrolled_count=enrolled_count,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
            )
        return total, results

    @staticmethod
    def list_classes_for_student(db: Session, student_id: int) -> List[StudentClassResponse]:
        """Lists all active classes a student is enrolled in."""
        enrollments = (
            db.query(ClassEnrollment)
            .join(Class, ClassEnrollment.class_id == Class.id)
            .filter(ClassEnrollment.student_id == student_id, ClassEnrollment.is_active == True)
            .all()
        )

        results = []
        for e in enrollments:
            cls = e.class_obj
            teacher = cls.teacher
            results.append(
                StudentClassResponse(
                    enrollment_id=e.id,
                    class_id=cls.id,
                    class_name=cls.name,
                    teacher_name=teacher.full_name if teacher else "Instructor",
                    subject_id=cls.subject_id,
                    subject_name=cls.subject.name if cls.subject else "Subject",
                    enrolled_at=e.enrolled_at,
                    is_active=e.is_active,
                )
            )
        return results

    @staticmethod
    def enroll_student_by_code(db: Session, student_id: int, enrollment_code: str) -> ClassEnrollment:
        """Allows a student to join a class using an enrollment code."""
        clean_code = enrollment_code.strip().upper()
        cls = db.query(Class).filter(Class.enrollment_code == clean_code, Class.is_active == True).first()
        if not cls:
            raise ValueError(f"Invalid or inactive class enrollment code: {enrollment_code}")

        # Check existing enrollment
        existing = db.query(ClassEnrollment).filter(
            ClassEnrollment.class_id == cls.id,
            ClassEnrollment.student_id == student_id
        ).first()

        if existing:
            if not existing.is_active:
                existing.is_active = True
                db.commit()
                db.refresh(existing)
            return existing

        enrollment = ClassEnrollment(
            class_id=cls.id,
            student_id=student_id,
            is_active=True
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        logger.info(f"Student {student_id} successfully enrolled in class {cls.id} via code")
        return enrollment

    @staticmethod
    def enroll_student_direct(db: Session, teacher_id: int, class_id: int, student_email_or_id: str) -> ClassEnrollment:
        """Enrolls a student directly by email or ID, verified by class ownership."""
        cls = db.query(Class).filter(Class.id == class_id, Class.teacher_id == teacher_id).first()
        if not cls:
            raise PermissionError("Class not found or unauthorized access.")

        # Find student
        student = None
        if str(student_email_or_id).isdigit():
            student = db.query(User).filter(User.id == int(student_email_or_id)).first()
        if not student:
            student = db.query(User).filter(User.email == str(student_email_or_id).strip().lower()).first()

        if not student:
            raise ValueError(f"Student '{student_email_or_id}' not found.")
        if student.role != UserRole.STUDENT:
            raise ValueError(f"User '{student.email}' is not a student (role={student.role}).")

        existing = db.query(ClassEnrollment).filter(
            ClassEnrollment.class_id == class_id,
            ClassEnrollment.student_id == student.id
        ).first()

        if existing:
            if not existing.is_active:
                existing.is_active = True
                db.commit()
                db.refresh(existing)
            return existing

        enrollment = ClassEnrollment(
            class_id=class_id,
            student_id=student.id,
            is_active=True
        )
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    @staticmethod
    def get_class_roster(db: Session, class_id: int, teacher_id: int) -> List[EnrolledStudentItem]:
        """Retrieves list of enrolled students with real mastery summary."""
        cls = db.query(Class).filter(Class.id == class_id, Class.teacher_id == teacher_id).first()
        if not cls:
            raise PermissionError("Class not found or unauthorized access.")

        enrollments = (
            db.query(ClassEnrollment)
            .options(joinedload(ClassEnrollment.student))
            .filter(ClassEnrollment.class_id == class_id, ClassEnrollment.is_active == True)
            .all()
        )

        roster = []
        for e in enrollments:
            st = e.student
            # Compute mastery on this class subject
            mastery_query = (
                db.query(func.avg(LearnerMastery.p_know))
                .filter(LearnerMastery.student_id == st.id)
                .scalar()
            )
            overall_mastery = round(float(mastery_query), 3) if mastery_query is not None else None

            # Compute question attempts
            total_attempts = (
                db.query(LearnerResponse)
                .filter(LearnerResponse.user_id == st.id)
                .count()
            )
            correct_attempts = (
                db.query(LearnerResponse)
                .filter(LearnerResponse.user_id == st.id, LearnerResponse.is_correct == True)
                .count()
            )
            accuracy = round(correct_attempts / total_attempts, 3) if total_attempts > 0 else None

            roster.append(
                EnrolledStudentItem(
                    enrollment_id=e.id,
                    student_id=st.id,
                    student_name=st.full_name,
                    student_email=st.email,
                    enrolled_at=e.enrolled_at,
                    is_active=e.is_active,
                    overall_mastery=overall_mastery,
                    questions_attempted=total_attempts,
                    accuracy_rate=accuracy,
                )
            )
        return roster
