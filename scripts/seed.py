r"""
Utility script to seed the development database with sample users, syllabus, concept graph, and questions.
Run via:
    .venv\Scripts\python scripts/seed.py
"""
import sys
import os

# Ensure app is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.syllabus import Subject, Chapter, Concept, DifficultyLevel
from app.models.concept_graph import RelationshipType
from app.models.assessment import Question, QuestionType
from app.core.security import get_password_hash
from app.services.graph_service import GraphService


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("[*] Seeding database...")

        # 1. Create Users
        teacher = db.query(User).filter(User.email == "teacher@adaptive.edu").first()
        if not teacher:
            teacher = User(
                email="teacher@adaptive.edu",
                hashed_password=get_password_hash("teacher123"),
                full_name="Prof. David Hilbert",
                role=UserRole.TEACHER,
                is_active=True
            )
            db.add(teacher)

        student = db.query(User).filter(User.email == "student@adaptive.edu").first()
        if not student:
            student = User(
                email="student@adaptive.edu",
                hashed_password=get_password_hash("student123"),
                full_name="Emmy Noether",
                role=UserRole.STUDENT,
                is_active=True
            )
            db.add(student)
        db.commit()

        # 2. Create Subject
        calc = db.query(Subject).filter(Subject.code == "MATH101").first()
        if not calc:
            calc = Subject(
                code="MATH101",
                name="Calculus I: Differential & Integral Calculus",
                description="Foundational calculus covering functions, limits, derivatives, and integration."
            )
            db.add(calc)
            db.commit()
            db.refresh(calc)

        # 3. Create Chapters
        ch1 = db.query(Chapter).filter(Chapter.subject_id == calc.id, Chapter.chapter_number == 1).first()
        if not ch1:
            ch1 = Chapter(
                subject_id=calc.id,
                chapter_number=1,
                title="Functions and Limits",
                description="Study of real functions, limit definitions, and continuity."
            )
            db.add(ch1)

        ch2 = db.query(Chapter).filter(Chapter.subject_id == calc.id, Chapter.chapter_number == 2).first()
        if not ch2:
            ch2 = Chapter(
                subject_id=calc.id,
                chapter_number=2,
                title="Derivatives & Rules",
                description="Definition of derivative, basic differentiation rules, and chain rule."
            )
            db.add(ch2)

        ch3 = db.query(Chapter).filter(Chapter.subject_id == calc.id, Chapter.chapter_number == 3).first()
        if not ch3:
            ch3 = Chapter(
                subject_id=calc.id,
                chapter_number=3,
                title="Integration",
                description="Antiderivatives, Riemann sums, and Fundamental Theorem of Calculus."
            )
            db.add(ch3)
        db.commit()
        db.refresh(ch1)
        db.refresh(ch2)
        db.refresh(ch3)

        # 4. Create Concepts
        concept_defs = [
            (
                "CALC_FUNC_01",
                ch1.id,
                "Real Functions and Domains",
                "Understanding single-variable functions, domains, codomains, and ranges.",
                DifficultyLevel.BEGINNER,
                ["Identify domain and range of rational and root functions", "Compose functions"]
            ),
            (
                "CALC_LIMIT_01",
                ch1.id,
                "Intuitive Limits and Continuity",
                "Evaluating one-sided and two-sided limits and defining continuous functions.",
                DifficultyLevel.BEGINNER,
                ["Evaluate limits algebraically and graphically", "Identify discontinuities"]
            ),
            (
                "CALC_DERIV_01",
                ch2.id,
                "Definition of the Derivative",
                "The limit definition of derivative as the instantaneous rate of change.",
                DifficultyLevel.INTERMEDIATE,
                ["Calculate derivative using difference quotient limit", "Interpret tangent slope"]
            ),
            (
                "CALC_DERIV_02",
                ch2.id,
                "Power, Product, and Quotient Rules",
                "Computational rules for differentiating polynomial, rational, and product functions.",
                DifficultyLevel.INTERMEDIATE,
                ["Apply power rule", "Apply product and quotient rules accurately"]
            ),
            (
                "CALC_CHAIN_01",
                ch2.id,
                "The Chain Rule",
                "Differentiation technique for composed functions.",
                DifficultyLevel.ADVANCED,
                ["Decompose composite functions", "Compute derivatives using the chain rule"]
            ),
            (
                "CALC_INT_01",
                ch3.id,
                "Antiderivatives & Indefinite Integrals",
                "Reversing differentiation to find antiderivative families.",
                DifficultyLevel.INTERMEDIATE,
                ["Compute indefinite integrals of polynomials and trig functions"]
            ),
            (
                "CALC_FTC_01",
                ch3.id,
                "Fundamental Theorem of Calculus",
                "Connecting differentiation and integration via definite integrals.",
                DifficultyLevel.ADVANCED,
                ["Evaluate definite integrals", "Apply FTC Parts 1 and 2"]
            )
        ]

        concept_map = {}
        for code, ch_id, name, desc, diff, objs in concept_defs:
            c = db.query(Concept).filter(Concept.concept_code == code).first()
            if not c:
                c = Concept(
                    concept_code=code,
                    subject_id=calc.id,
                    chapter_id=ch_id,
                    name=name,
                    description=desc,
                    difficulty_level=diff,
                    learning_objectives=objs
                )
                db.add(c)
                db.commit()
                db.refresh(c)
            concept_map[code] = c

        # 5. Create Prerequisite Edges (target depends on prerequisite)
        edges = [
            ("CALC_LIMIT_01", "CALC_FUNC_01"),   # Limits requires Functions
            ("CALC_DERIV_01", "CALC_LIMIT_01"),  # Derivative def requires Limits
            ("CALC_DERIV_02", "CALC_DERIV_01"),  # Rules require Derivative def
            ("CALC_CHAIN_01", "CALC_DERIV_02"),  # Chain rule requires Rules
            ("CALC_INT_01", "CALC_DERIV_02"),    # Integrals require Rules
            ("CALC_FTC_01", "CALC_CHAIN_01"),    # FTC requires Chain rule
            ("CALC_FTC_01", "CALC_INT_01"),      # FTC requires Integrals
        ]

        for target_code, prereq_code in edges:
            target_id = concept_map[target_code].id
            prereq_id = concept_map[prereq_code].id
            try:
                GraphService.add_prerequisite(
                    db=db,
                    concept_id=target_id,
                    prerequisite_id=prereq_id,
                    relationship_type=RelationshipType.STRICT
                )
                print(f"  [+] Edge added: {target_code} depends on {prereq_code}")
            except Exception:
                pass

        # 6. Create Sample Questions
        sample_questions = [
            (
                "CALC_FUNC_01",
                QuestionType.MCQ,
                "What is the domain of f(x) = 1 / sqrt(x - 3)?",
                [
                    {"id": "A", "text": "x >= 3"},
                    {"id": "B", "text": "x > 3"},
                    {"id": "C", "text": "x <= 3"},
                    {"id": "D", "text": "All real numbers"}
                ],
                "B",
                {"explanation": "The expression inside the square root must be strictly positive since division by zero is undefined."},
                DifficultyLevel.BEGINNER
            ),
            (
                "CALC_LIMIT_01",
                QuestionType.MCQ,
                "What is lim (x -> 2) of (x^2 - 4) / (x - 2)?",
                [
                    {"id": "A", "text": "0"},
                    {"id": "B", "text": "2"},
                    {"id": "C", "text": "4"},
                    {"id": "D", "text": "Undefined"}
                ],
                "C",
                {"explanation": "Factor the numerator into (x - 2)(x + 2). Canceling (x - 2) gives x + 2. Substituting x=2 yields 4."},
                DifficultyLevel.BEGINNER
            ),
            (
                "CALC_DERIV_01",
                QuestionType.MCQ,
                "By definition, the derivative f'(x) represents:",
                [
                    {"id": "A", "text": "The area under the curve f(x)"},
                    {"id": "B", "text": "The instantaneous slope of the tangent line to f(x)"},
                    {"id": "C", "text": "The average value of f(x) over [a, b]"},
                    {"id": "D", "text": "The x-intercept of f(x)"}
                ],
                "B",
                {"explanation": "f'(x) is the limit of the secant line slope as delta x approaches 0, giving the instantaneous tangent slope."},
                DifficultyLevel.INTERMEDIATE
            ),
            (
                "CALC_DERIV_02",
                QuestionType.NUMERIC,
                "If f(x) = 4x^3 - 5x + 7, what is the value of f'(2)?",
                None,
                "43",
                {"explanation": "f'(x) = 12x^2 - 5. For x=2, f'(2) = 12(4) - 5 = 48 - 5 = 43."},
                DifficultyLevel.INTERMEDIATE
            ),
            (
                "CALC_CHAIN_01",
                QuestionType.MCQ,
                "If h(x) = sin(x^2), what is h'(x)?",
                [
                    {"id": "A", "text": "cos(x^2)"},
                    {"id": "B", "text": "2x * cos(x^2)"},
                    {"id": "C", "text": "-2x * cos(x^2)"},
                    {"id": "D", "text": "2x * sin(x^2)"}
                ],
                "B",
                {"explanation": "By the chain rule, d/dx[sin(u)] = cos(u) * u'. Here u = x^2 and u' = 2x, so h'(x) = 2x * cos(x^2)."},
                DifficultyLevel.ADVANCED
            ),
            (
                "CALC_INT_01",
                QuestionType.NUMERIC,
                "Evaluate the definite integral of 3x^2 from x = 0 to x = 3.",
                None,
                "27",
                {"explanation": "Antiderivative of 3x^2 is x^3. Evaluating [x^3] from 0 to 3 gives 3^3 - 0 = 27."},
                DifficultyLevel.INTERMEDIATE
            ),
            (
                "CALC_FTC_01",
                QuestionType.MCQ,
                "According to the Fundamental Theorem of Calculus Part 1, if F(x) = integral from 0 to x of sqrt(1 + t^3) dt, then F'(x) is:",
                [
                    {"id": "A", "text": "sqrt(1 + x^3)"},
                    {"id": "B", "text": "3x^2 / (2 * sqrt(1 + x^3))"},
                    {"id": "C", "text": "0"},
                    {"id": "D", "text": "sqrt(1 + x^3) - 1"}
                ],
                "A",
                {"explanation": "FTC Part 1 directly states that d/dx [integral from a to x of f(t) dt] = f(x)."},
                DifficultyLevel.ADVANCED
            )
        ]

        teacher_user = db.query(User).filter(User.email == "teacher@adaptive.edu").first()

        for c_code, q_type, q_text, q_opts, c_ans, rubric, diff in sample_questions:
            c = concept_map[c_code]
            existing_q = db.query(Question).filter(
                Question.concept_id == c.id,
                Question.question_text == q_text
            ).first()
            if not existing_q:
                q = Question(
                    concept_id=c.id,
                    question_type=q_type,
                    question_text=q_text,
                    question_options=q_opts,
                    correct_answer=c_ans,
                    evaluation_rubric=rubric,
                    difficulty_level=diff,
                    created_by_id=teacher_user.id if teacher_user else None
                )
                db.add(q)
                db.commit()
                print(f"  [+] Question seeded for {c_code}")

        print("[OK] Database successfully seeded with curriculum, graph, and questions!")
        print("   Teacher credentials: teacher@adaptive.edu / teacher123")
        print("   Student credentials: student@adaptive.edu / student123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
