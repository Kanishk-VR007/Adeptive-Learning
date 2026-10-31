from fastapi.testclient import TestClient
from app.models.user import UserRole


def test_register_student(client: TestClient):
    payload = {
        "email": "newstudent@adaptive.edu",
        "password": "securepassword123",
        "full_name": "Carl Friedrich Gauss",
        "role": UserRole.STUDENT.value
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newstudent@adaptive.edu"
    assert data["full_name"] == "Carl Friedrich Gauss"
    assert data["role"] == UserRole.STUDENT.value
    assert "hashed_password" not in data


def test_register_teacher(client: TestClient):
    payload = {
        "email": "newteacher@adaptive.edu",
        "password": "teachersecurepassword",
        "full_name": "Isaac Newton",
        "role": UserRole.TEACHER.value
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == UserRole.TEACHER.value


def test_register_duplicate_email(client: TestClient, student_user):
    payload = {
        "email": student_user.email,
        "password": "anotherpassword",
        "full_name": "Imposter",
        "role": UserRole.STUDENT.value
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_login_oauth2_form_success(client: TestClient, student_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": student_user.email, "password": "student123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == student_user.email


def test_login_json_success(client: TestClient, teacher_user):
    response = client.post(
        "/api/v1/auth/login/json",
        json={"email": teacher_user.email, "password": "teacher123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == UserRole.TEACHER.value


def test_login_invalid_password(client: TestClient, student_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": student_user.email, "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_nonexistent_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@adaptive.edu", "password": "somepassword"}
    )
    assert response.status_code == 401


def test_read_me_authenticated(student_client: TestClient, student_user):
    response = student_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == student_user.email
    assert data["role"] == UserRole.STUDENT.value


def test_read_me_unauthenticated(client: TestClient):
    client.headers = {}
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
