import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.models.syllabus import Subject
from app.core.security import get_password_hash, create_access_token

# client is provided by conftest.py fixture


@pytest.fixture
def teacher_auth_headers(db_session: Session):
    teacher = User(
        email="teacher_classes@adeptlearn.org",
        hashed_password=get_password_hash("Secret123"),
        full_name="Prof. Archimedes",
        role=UserRole.TEACHER,
        is_active=True,
    )
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)

    token = create_access_token(subject=str(teacher.id), extra_claims={"role": teacher.role.value})
    return {"Authorization": f"Bearer {token}", "teacher": teacher}


@pytest.fixture
def student_auth_headers(db_session: Session):
    student = User(
        email="student_classes@adeptlearn.org",
        hashed_password=get_password_hash("Secret123"),
        full_name="Galileo Galilei",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    token = create_access_token(subject=str(student.id), extra_claims={"role": student.role.value})
    return {"Authorization": f"Bearer {token}", "student": student}


@pytest.fixture
def sample_subject(db_session: Session):
    sub = Subject(
        code="PHYS-101",
        name="Classical Mechanics",
        description="Foundations of motion and forces",
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


def test_teacher_create_class(client, teacher_auth_headers, sample_subject):
    """Teacher can successfully create a new class linked to a subject."""
    headers = {"Authorization": teacher_auth_headers["Authorization"]}
    payload = {
        "name": "Physics Honours Section A",
        "description": "Advanced Newtonian dynamics",
        "subject_id": sample_subject.id,
    }
    res = client.post("/api/v1/teachers/classes", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Physics Honours Section A"
    assert data["subject_id"] == sample_subject.id
    assert len(data["enrollment_code"]) >= 6
    assert data["enrolled_count"] == 0


def test_student_cannot_create_class(client, student_auth_headers, sample_subject):
    """Students are strictly forbidden from creating classes (RBAC enforcement)."""
    headers = {"Authorization": student_auth_headers["Authorization"]}
    payload = {
        "name": "Unauthorized Class",
        "subject_id": sample_subject.id,
    }
    res = client.post("/api/v1/teachers/classes", json=payload, headers=headers)
    assert res.status_code == 403


def test_student_enroll_via_code_and_roster(client, teacher_auth_headers, student_auth_headers, sample_subject):
    """Complete enrollment lifecycle: Teacher creates class -> Student joins via code -> Teacher views roster."""
    t_headers = {"Authorization": teacher_auth_headers["Authorization"]}
    s_headers = {"Authorization": student_auth_headers["Authorization"]}

    # 1. Create class
    create_res = client.post(
        "/api/v1/teachers/classes",
        json={"name": "AP Physics 1", "subject_id": sample_subject.id},
        headers=t_headers,
    )
    assert create_res.status_code == 201
    class_data = create_res.json()
    code = class_data["enrollment_code"]
    class_id = class_data["id"]

    # 2. Student joins via code
    join_res = client.post("/api/v1/teachers/join", json={"enrollment_code": code}, headers=s_headers)
    assert join_res.status_code == 200
    join_data = join_res.json()
    assert join_data["class_id"] == class_id
    assert join_data["class_name"] == "AP Physics 1"

    # 3. Student views their enrolled classes
    my_classes_res = client.get("/api/v1/teachers/my-enrolled-classes", headers=s_headers)
    assert my_classes_res.status_code == 200
    my_classes = my_classes_res.json()
    assert len(my_classes) == 1
    assert my_classes[0]["class_id"] == class_id

    # 4. Teacher views roster
    roster_res = client.get(f"/api/v1/teachers/classes/{class_id}/roster", headers=t_headers)
    assert roster_res.status_code == 200
    roster = roster_res.json()
    assert len(roster) == 1
    assert roster[0]["student_id"] == student_auth_headers["student"].id
    assert roster[0]["student_name"] == "Galileo Galilei"


def test_cross_teacher_class_access_forbidden(client, teacher_auth_headers, sample_subject, db_session):
    """Teacher cannot view or manage another teacher's class."""
    # Create second teacher
    teacher2 = User(
        email="teacher2@adeptlearn.org",
        hashed_password=get_password_hash("Secret123"),
        full_name="Prof. Bohr",
        role=UserRole.TEACHER,
        is_active=True,
    )
    db_session.add(teacher2)
    db_session.commit()
    t2_token = create_access_token(subject=str(teacher2.id), extra_claims={"role": teacher2.role.value})
    t2_headers = {"Authorization": f"Bearer {t2_token}"}

    # Teacher 1 creates class
    t1_headers = {"Authorization": teacher_auth_headers["Authorization"]}
    create_res = client.post(
        "/api/v1/teachers/classes",
        json={"name": "Teacher 1 Exclusive Class", "subject_id": sample_subject.id},
        headers=t1_headers,
    )
    class_id = create_res.json()["id"]

    # Teacher 2 attempts access
    roster_res = client.get(f"/api/v1/teachers/classes/{class_id}/roster", headers=t2_headers)
    assert roster_res.status_code == 403
