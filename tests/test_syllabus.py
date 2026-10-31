from fastapi.testclient import TestClient
from app.models.syllabus import DifficultyLevel


def test_create_subject_teacher_authorized(teacher_client: TestClient):
    payload = {
        "code": "MATH101",
        "name": "Calculus I",
        "description": "Differential and Integral Calculus"
    }
    response = teacher_client.post("/api/v1/subjects", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "MATH101"
    assert data["name"] == "Calculus I"
    assert data["id"] is not None


def test_create_subject_student_forbidden(student_client: TestClient):
    payload = {
        "code": "PHYS101",
        "name": "Classical Mechanics",
        "description": "Newtonian physics"
    }
    response = student_client.post("/api/v1/subjects", json=payload)
    assert response.status_code == 403
    assert "Operation not permitted" in response.json()["detail"]


def test_duplicate_subject_code_rejected(teacher_client: TestClient):
    payload = {"code": "CHEM101", "name": "General Chemistry"}
    res1 = teacher_client.post("/api/v1/subjects", json=payload)
    assert res1.status_code == 201

    res2 = teacher_client.post("/api/v1/subjects", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_list_and_get_subject(student_client: TestClient, teacher_client: TestClient):
    # Teacher creates
    teacher_client.post("/api/v1/subjects", json={"code": "BIO101", "name": "General Biology"})

    # Student can read
    list_res = student_client.get("/api/v1/subjects")
    assert list_res.status_code == 200
    subjects = list_res.json()
    assert len(subjects) >= 1
    bio = next(s for s in subjects if s["code"] == "BIO101")

    get_res = student_client.get(f"/api/v1/subjects/{bio['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "General Biology"


def test_chapter_crud_workflow(teacher_client: TestClient, student_client: TestClient):
    # 1. Create subject
    subj_res = teacher_client.post(
        "/api/v1/subjects",
        json={"code": "CS101", "name": "Computer Science"}
    )
    subj_id = subj_res.json()["id"]

    # 2. Student cannot create chapter
    forbidden_res = student_client.post(
        "/api/v1/chapters",
        json={"subject_id": subj_id, "chapter_number": 1, "title": "Intro"}
    )
    assert forbidden_res.status_code == 403

    # 3. Teacher creates chapter
    ch1_res = teacher_client.post(
        "/api/v1/chapters",
        json={"subject_id": subj_id, "chapter_number": 1, "title": "Algorithms & Flowcharts"}
    )
    assert ch1_res.status_code == 201
    ch1_id = ch1_res.json()["id"]

    # 4. Duplicate chapter number in same subject fails
    dup_res = teacher_client.post(
        "/api/v1/chapters",
        json={"subject_id": subj_id, "chapter_number": 1, "title": "Duplicate"}
    )
    assert dup_res.status_code == 409

    # 5. Teacher creates chapter 2
    ch2_res = teacher_client.post(
        "/api/v1/chapters",
        json={"subject_id": subj_id, "chapter_number": 2, "title": "Data Structures"}
    )
    assert ch2_res.status_code == 201

    # 6. List chapters filtered by subject_id
    chapters_res = student_client.get(f"/api/v1/chapters?subject_id={subj_id}")
    assert chapters_res.status_code == 200
    assert len(chapters_res.json()) == 2


def test_concept_crud_and_filters(teacher_client: TestClient, student_client: TestClient):
    # Setup Subject and Chapter
    subj = teacher_client.post("/api/v1/subjects", json={"code": "MATH201", "name": "Linear Algebra"}).json()
    ch = teacher_client.post(
        "/api/v1/chapters",
        json={"subject_id": subj["id"], "chapter_number": 1, "title": "Vectors & Matrices"}
    ).json()

    # Teacher creates beginner concept
    c1_payload = {
        "concept_code": "VEC_INTRO_01",
        "subject_id": subj["id"],
        "chapter_id": ch["id"],
        "name": "Vector Operations",
        "description": "Addition, scalar multiplication and dot product of vectors in R^n.",
        "difficulty_level": DifficultyLevel.BEGINNER.value,
        "learning_objectives": ["Compute vector dot product", "Perform vector scalar multiplication"]
    }
    c1_res = teacher_client.post("/api/v1/concepts", json=c1_payload)
    assert c1_res.status_code == 201
    c1_data = c1_res.json()
    assert c1_data["concept_code"] == "VEC_INTRO_01"
    assert len(c1_data["learning_objectives"]) == 2

    # Teacher creates advanced concept
    c2_payload = {
        "concept_code": "EIGEN_01",
        "subject_id": subj["id"],
        "chapter_id": ch["id"],
        "name": "Eigenvalues & Eigenvectors",
        "description": "Characteristic polynomials and eigenspaces.",
        "difficulty_level": DifficultyLevel.ADVANCED.value,
        "learning_objectives": ["Find eigenvalues of 2x2 and 3x3 matrices"]
    }
    c2_res = teacher_client.post("/api/v1/concepts", json=c2_payload)
    assert c2_res.status_code == 201

    # Filter concepts by difficulty
    filtered = student_client.get(f"/api/v1/concepts?difficulty_level={DifficultyLevel.ADVANCED.value}")
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["concept_code"] == "EIGEN_01"

    # Get detail of concept 1
    detail_res = student_client.get(f"/api/v1/concepts/{c1_data['id']}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "prerequisites" in detail
    assert "dependents" in detail


def test_cascade_delete_subject(teacher_client: TestClient):
    # Create Subject -> Chapter -> Concept
    s = teacher_client.post("/api/v1/subjects", json={"code": "TEMP101", "name": "Temporary Subject"}).json()
    ch = teacher_client.post("/api/v1/chapters", json={"subject_id": s["id"], "chapter_number": 1, "title": "Temp Ch"}).json()
    c = teacher_client.post("/api/v1/concepts", json={
        "concept_code": "TEMP_CON_01",
        "subject_id": s["id"],
        "chapter_id": ch["id"],
        "name": "Temp Concept",
        "description": "Testing cascading delete behavior",
        "difficulty_level": DifficultyLevel.BEGINNER.value,
        "learning_objectives": ["Understand cascading deletes"]
    }).json()

    # Delete subject
    del_res = teacher_client.delete(f"/api/v1/subjects/{s['id']}")
    assert del_res.status_code == 204

    # Verify chapter and concept are cleanly gone
    assert teacher_client.get(f"/api/v1/chapters/{ch['id']}").status_code == 404
    assert teacher_client.get(f"/api/v1/concepts/{c['id']}").status_code == 404
