from fastapi.testclient import TestClient
from app.models.assessment import QuestionType
from app.models.syllabus import DifficultyLevel


def test_question_crud_and_student_sanitization(teacher_client: TestClient, student_client: TestClient):
    # Setup subject, chapter, concept
    s = teacher_client.post("/api/v1/subjects", json={"code": "PHY101", "name": "Physics I"}).json()
    ch = teacher_client.post("/api/v1/chapters", json={"subject_id": s["id"], "chapter_number": 1, "title": "Kinematics"}).json()
    c = teacher_client.post("/api/v1/concepts", json={
        "concept_code": "KIN_VEL_01",
        "subject_id": s["id"],
        "chapter_id": ch["id"],
        "name": "Velocity & Acceleration",
        "description": "Rate of change of displacement and velocity",
        "difficulty_level": DifficultyLevel.BEGINNER.value,
        "learning_objectives": ["Differentiate displacement to find velocity"]
    }).json()

    # 1. Student cannot create question
    forbidden_res = student_client.post("/api/v1/questions", json={
        "concept_id": c["id"],
        "question_text": "What is acceleration?",
        "correct_answer": "dv/dt"
    })
    assert forbidden_res.status_code == 403

    # 2. Teacher creates question
    q_payload = {
        "concept_id": c["id"],
        "question_type": QuestionType.MCQ.value,
        "question_text": "If s(t) = 3t^2, what is the velocity v(t) at t = 2?",
        "question_options": [
            {"id": "A", "text": "6"},
            {"id": "B", "text": "12"},
            {"id": "C", "text": "18"},
            {"id": "D", "text": "24"}
        ],
        "correct_answer": "B",
        "evaluation_rubric": {"explanation": "v(t) = s'(t) = 6t. At t=2, v(2) = 12."},
        "difficulty_level": DifficultyLevel.BEGINNER.value
    }
    create_res = teacher_client.post("/api/v1/questions", json=q_payload)
    assert create_res.status_code == 201
    q_data = create_res.json()
    assert q_data["id"] is not None
    assert q_data["correct_answer"] == "B"

    # 3. Student views question: correct_answer must be sanitized/omitted
    student_view_res = student_client.get(f"/api/v1/questions/{q_data['id']}")
    assert student_view_res.status_code == 200
    student_view = student_view_res.json()
    assert "correct_answer" not in student_view
    assert "evaluation_rubric" not in student_view
    assert student_view["question_text"] == q_payload["question_text"]

    # 4. Teacher views question: sees full rubric and answer
    teacher_view_res = teacher_client.get(f"/api/v1/questions/{q_data['id']}")
    assert teacher_view_res.status_code == 200
    assert teacher_view_res.json()["correct_answer"] == "B"
    assert "explanation" in teacher_view_res.json()["evaluation_rubric"]


def test_session_creation_and_answer_evaluation(teacher_client: TestClient, student_client: TestClient):
    # Setup
    s = teacher_client.post("/api/v1/subjects", json={"code": "CHEM201", "name": "Organic Chemistry"}).json()
    ch = teacher_client.post("/api/v1/chapters", json={"subject_id": s["id"], "chapter_number": 1, "title": "Alkanes"}).json()
    c = teacher_client.post("/api/v1/concepts", json={
        "concept_code": "ORG_ALK_01",
        "subject_id": s["id"],
        "chapter_id": ch["id"],
        "name": "Alkane Nomenclature",
        "description": "IUPAC naming rules for branched alkanes",
        "difficulty_level": DifficultyLevel.BEGINNER.value,
        "learning_objectives": ["Identify parent carbon chain"]
    }).json()

    # Create 2 questions
    q1 = teacher_client.post("/api/v1/questions", json={
        "concept_id": c["id"],
        "question_type": QuestionType.MCQ.value,
        "question_text": "What is the molecular formula of propane?",
        "question_options": [
            {"id": "A", "text": "CH4"},
            {"id": "B", "text": "C2H6"},
            {"id": "C", "text": "C3H8"},
            {"id": "D", "text": "C4H10"}
        ],
        "correct_answer": "C",
        "evaluation_rubric": {"explanation": "Propane has 3 carbons: C3H(2*3+2) = C3H8."}
    }).json()

    q2 = teacher_client.post("/api/v1/questions", json={
        "concept_id": c["id"],
        "question_type": QuestionType.NUMERIC.value,
        "question_text": "How many carbon atoms are in butane?",
        "correct_answer": "4",
        "evaluation_rubric": {"explanation": "Butane contains 4 carbons."}
    }).json()

    # 1. Student starts practice session
    session_res = student_client.post("/api/v1/assessments/sessions", json={
        "subject_id": s["id"],
        "session_type": "ADAPTIVE_PRACTICE",
        "target_concept_id": c["id"],
        "question_count": 5
    })
    assert session_res.status_code == 201
    session_data = session_res.json()
    assert session_data["id"] is not None
    assert len(session_data["questions"]) == 2

    # 2. Student submits CORRECT answer to q1
    sub1_res = student_client.post("/api/v1/assessments/submit", json={
        "question_id": q1["id"],
        "session_id": session_data["id"],
        "response_text": "C",
        "confidence_score": 0.9,
        "time_spent_ms": 3500
    })
    assert sub1_res.status_code == 200
    sub1_data = sub1_res.json()
    assert sub1_data["is_correct"] is True
    assert sub1_data["new_mastery_probability"] > sub1_data["previous_mastery_probability"]
    assert sub1_data["practice_count"] == 1

    # 3. Student submits INCORRECT answer to q2
    sub2_res = student_client.post("/api/v1/assessments/submit", json={
        "question_id": q2["id"],
        "session_id": session_data["id"],
        "response_text": "5",
        "confidence_score": 0.4,
        "time_spent_ms": 5000
    })
    assert sub2_res.status_code == 200
    sub2_data = sub2_res.json()
    assert sub2_data["is_correct"] is False
    assert sub2_data["ai_feedback"] == "Butane contains 4 carbons."

    # 4. Check learner history
    hist_res = student_client.get("/api/v1/assessments/history?limit=10")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 2
    assert history[0]["question_id"] in [q1["id"], q2["id"]]
