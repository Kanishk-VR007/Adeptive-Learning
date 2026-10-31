import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token

# In-memory SQLite database specifically for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create an unauthenticated TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def teacher_user(db_session: Session) -> User:
    """Create a sample teacher user in the test database."""
    teacher = User(
        email="teacher@adaptive.edu",
        hashed_password=get_password_hash("teacher123"),
        full_name="Prof. Alan Turing",
        role=UserRole.TEACHER,
        is_active=True
    )
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)
    return teacher


@pytest.fixture(scope="function")
def student_user(db_session: Session) -> User:
    """Create a sample student user in the test database."""
    student = User(
        email="student@adaptive.edu",
        hashed_password=get_password_hash("student123"),
        full_name="Ada Lovelace",
        role=UserRole.STUDENT,
        is_active=True
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture(scope="function")
def teacher_token(teacher_user: User) -> str:
    """Generate JWT token for the teacher user."""
    return create_access_token(
        subject=teacher_user.id,
        extra_claims={"role": teacher_user.role.value, "email": teacher_user.email}
    )


@pytest.fixture(scope="function")
def student_token(student_user: User) -> str:
    """Generate JWT token for the student user."""
    return create_access_token(
        subject=student_user.id,
        extra_claims={"role": student_user.role.value, "email": student_user.email}
    )


@pytest.fixture(scope="function")
def teacher_client(db_session: Session, teacher_token: str) -> Generator[TestClient, None, None]:
    """TestClient pre-authenticated as a Teacher with dedicated client instance."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers={"Authorization": f"Bearer {teacher_token}"}) as client_instance:
        yield client_instance
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def student_client(db_session: Session, student_token: str) -> Generator[TestClient, None, None]:
    """TestClient pre-authenticated as a Student with dedicated client instance."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, headers={"Authorization": f"Bearer {student_token}"}) as client_instance:
        yield client_instance
    app.dependency_overrides.clear()
