import concurrent.futures
import os
import tempfile
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.models.assessment import Question, QuestionType
from app.models.fsrs_review import ConceptReviewState, ReviewHistory
from app.models.learner_mastery import LearnerMastery, LearningHistory
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.user import User, UserRole
from app.schemas.fsrs_review import CompleteRevisionRequest
from app.services.revision_service import RevisionService


@pytest.fixture
def concurrency_db_env():
    """
    Dedicated temporary file-backed SQLite database configured with WAL mode
    and 30s busy timeout, ensuring true multi-process/multi-thread ACID concurrency
    without in-memory C-level driver conflicts.
    """
    db_path = os.path.join(tempfile.gettempdir(), f"fsrs_conc_{uuid.uuid4().hex}.db").replace("\\", "/")
    engine = create_engine(f"sqlite:///{db_path}?timeout=30")
    Base.metadata.create_all(engine)

    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))
        conn.execute(text("PRAGMA foreign_keys=ON;"))
        conn.commit()

    SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield SessionMaker, engine

    engine.dispose()
    for ext in ["", "-wal", "-shm"]:
        p = f"{db_path}{ext}"
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


class TestFSRSConcurrency:
    """
    Simulates at least 10 concurrent student review submissions using independent
    threads and separate database transactions to verify thread-safety, transaction isolation,
    and absence of cross-student state contamination.
    """

    def test_concurrent_review_submissions_ten_students(self, concurrency_db_env):
        SessionMaker, _ = concurrency_db_env
        num_students = 10

        # Setup in primary session
        init_db = SessionMaker()
        try:
            teacher = User(
                email="conc_teacher@test.edu",
                hashed_password="pw",
                full_name="Prof Concurrency",
                role=UserRole.TEACHER,
                is_active=True,
            )
            init_db.add(teacher)
            init_db.commit()
            init_db.refresh(teacher)

            subj = Subject(name="Biology", code="BIO101", description="Cell Biology")
            init_db.add(subj)
            init_db.commit()
            init_db.refresh(subj)

            chap = Chapter(subject_id=subj.id, title="Cytology", chapter_number=1, description="Cell Structure")
            init_db.add(chap)
            init_db.commit()
            init_db.refresh(chap)

            concept = Concept(
                concept_code="BIO-CELL-001",
                subject_id=subj.id,
                chapter_id=chap.id,
                name="Mitochondria",
                description="Powerhouse of the cell",
                difficulty_level=DifficultyLevel.BEGINNER,
            )
            init_db.add(concept)
            init_db.commit()
            init_db.refresh(concept)

            question = Question(
                concept_id=concept.id,
                question_type=QuestionType.MCQ,
                question_text="Which organelle generates ATP?",
                question_options=[{"id": "A", "text": "Mitochondria"}, {"id": "B", "text": "Ribosome"}],
                correct_answer="A",
                evaluation_rubric={"explanation": "Mitochondria generates ATP"},
                created_by_id=teacher.id,
            )
            init_db.add(question)
            init_db.commit()
            init_db.refresh(question)

            # Pre-create 10 distinct students
            students = []
            for i in range(num_students):
                stu = User(
                    email=f"concurrent_student_{i}@test.edu",
                    hashed_password="pw",
                    full_name=f"Concurrent Student #{i}",
                    role=UserRole.STUDENT,
                    is_active=True,
                )
                init_db.add(stu)
                students.append(stu)
            init_db.commit()
            for s in students:
                init_db.refresh(s)

            student_ids = [s.id for s in students]
            concept_id = concept.id
            question_id = question.id
        finally:
            init_db.close()

        # Concurrent worker: each thread creates its own Session from SessionMaker
        def submit_student_review(student_id: int, idx: int):
            thread_db = SessionMaker()
            try:
                rating = 3 if idx % 2 == 0 else 4
                req = CompleteRevisionRequest(
                    question_id=question_id,
                    response_text="A",
                    rating=rating,
                    idempotency_key=f"concurrent_key_stu_{student_id}",
                )
                res = RevisionService.complete_revision_session(
                    db=thread_db,
                    student_id=student_id,
                    concept_id=concept_id,
                    request=req,
                )
                return {
                    "student_id": student_id,
                    "rating": rating,
                    "updated_stability": res.updated_stability,
                    "next_due_at_utc": res.next_due_at_utc,
                    "updated_bkt_mastery": res.updated_bkt_mastery,
                    "is_idempotent_duplicate": res.is_idempotent_duplicate,
                }
            finally:
                thread_db.close()

        # Execute 10 reviews concurrently across 10 threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_students) as executor:
            futures = [
                executor.submit(submit_student_review, student_ids[i], i)
                for i in range(num_students)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_students

        # Verification in a separate verification session
        verify_db = SessionMaker()
        try:
            for s_id in student_ids:
                # 1. Verify exact 1 ConceptReviewState per student
                states = verify_db.query(ConceptReviewState).filter(
                    ConceptReviewState.student_id == s_id,
                    ConceptReviewState.concept_id == concept_id,
                ).all()
                assert len(states) == 1, f"Expected 1 state for student {s_id}, found {len(states)}"
                card_state = states[0]
                assert card_state.total_reviews == 1
                assert card_state.stability > 0.0
                assert card_state.lapses == 0
                assert card_state.due_at_utc is not None

                # 2. Verify exact 1 ReviewHistory per student
                histories = verify_db.query(ReviewHistory).filter(
                    ReviewHistory.student_id == s_id,
                    ReviewHistory.concept_id == concept_id,
                ).all()
                assert len(histories) == 1
                assert histories[0].idempotency_key == f"concurrent_key_stu_{s_id}"

                # 3. Verify exact 1 LearnerMastery and 1 LearningHistory per student
                masteries = verify_db.query(LearnerMastery).filter(
                    LearnerMastery.student_id == s_id,
                    LearnerMastery.concept_id == concept_id,
                ).all()
                assert len(masteries) == 1

                lh = verify_db.query(LearningHistory).filter(
                    LearningHistory.student_id == s_id,
                    LearningHistory.concept_id == concept_id,
                ).all()
                assert len(lh) == 1

            # 4. Global integrity: exactly 10 ReviewHistory rows for this concept
            total_histories = verify_db.query(ReviewHistory).filter(
                ReviewHistory.concept_id == concept_id
            ).count()
            assert total_histories == num_students
        finally:
            verify_db.close()
