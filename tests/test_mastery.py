from fastapi.testclient import TestClient
from app.models.syllabus import DifficultyLevel


def test_bkt_mastery_progression(teacher_client: TestClient, student_client: TestClient, student_user):
    # Setup Subject and 2 Concepts
    s = teacher_client.post("/api/v1/subjects", json={"code": "STATS101", "name": "Statistics"}).json()
    ch = teacher_client.post("/api/v1/chapters", json={"subject_id": s["id"], "chapter_number": 1, "title": "Probability"}).json()

    c1 = teacher_client.post("/api/v1/concepts", json={
        "concept_code": "PROB_BAYES_01",
        "subject_id": s["id"],
        "chapter_id": ch["id"],
        "name": "Bayes Theorem",
        "description": "Conditional probability and Bayes rule",
        "difficulty_level": DifficultyLevel.INTERMEDIATE.value,
        "learning_objectives": ["Compute posterior probability"]
    }).json()

    c2 = teacher_client.post("/api/v1/concepts", json={
        "concept_code": "PROB_COMB_01",
        "subject_id": s["id"],
        "chapter_id": ch["id"],
        "name": "Combinatorics",
        "description": "Permutations and combinations",
        "difficulty_level": DifficultyLevel.BEGINNER.value,
        "learning_objectives": ["Calculate nCr and nPr"]
    }).json()

    # Create questions for c1
    q1 = teacher_client.post("/api/v1/questions", json={
        "concept_id": c1["id"],
        "question_text": "What does P(A|B) denote?",
        "correct_answer": "Conditional probability"
    }).json()

    # 1. Prior check: before practice, mastery is NOT_STARTED (0.1)
    summary_before = student_client.get(f"/api/v1/mastery/me/subject/{s['id']}").json()
    assert summary_before["total_concepts"] == 2
    assert summary_before["not_started_count"] == 2
    assert summary_before["mastered_count"] == 0

    # 2. Practice: student answers correctly 3 times consecutively
    # First correct answer
    res1 = student_client.post("/api/v1/assessments/submit", json={
        "question_id": q1["id"],
        "response_text": "Conditional probability"
    }).json()
    p1 = res1["new_mastery_probability"]
    assert p1 > 0.1
    assert res1["practice_count"] == 1

    # Second correct answer
    res2 = student_client.post("/api/v1/assessments/submit", json={
        "question_id": q1["id"],
        "response_text": "Conditional probability"
    }).json()
    p2 = res2["new_mastery_probability"]
    assert p2 > p1
    assert res2["practice_count"] == 2

    # Third correct answer
    res3 = student_client.post("/api/v1/assessments/submit", json={
        "question_id": q1["id"],
        "response_text": "Conditional probability"
    }).json()
    p3 = res3["new_mastery_probability"]
    assert p3 > p2
    assert res3["practice_count"] == 3
    # P(L) should reach or exceed 0.85 (mastered)
    assert p3 >= 0.85

    # 3. Check subject summary now reflects mastered concept
    summary_after = student_client.get(f"/api/v1/mastery/me/subject/{s['id']}").json()
    assert summary_after["mastered_count"] == 1
    assert summary_after["not_started_count"] == 1
    c1_stat = next(c for c in summary_after["concepts"] if c["concept_id"] == c1["id"])
    assert c1_stat["status"] == "MASTERED"
    assert c1_stat["practice_count"] == 3

    # 4. Teacher views student mastery
    teacher_view = teacher_client.get(f"/api/v1/mastery/user/{student_user.id}/subject/{s['id']}")
    assert teacher_view.status_code == 200
    assert teacher_view.json()["mastered_count"] == 1

    # 5. Student cannot access teacher endpoint for other users
    forbidden_view = student_client.get(f"/api/v1/mastery/user/{student_user.id}/subject/{s['id']}")
    assert forbidden_view.status_code == 403
