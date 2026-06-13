from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from database import get_db
from main import app
from security import require_admin, require_teacher


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_users.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def fake_admin_user():
    return models.User(
        id=999,
        username="admin",
        role=models.UserRole.administrator,
        first_name="Admin",
        last_name="User",
        is_active=True,
    )


def fake_teacher_user():
    return models.User(
        id=2,
        username="teacher",
        role=models.UserRole.nauczyciel,
        first_name="Anna",
        last_name="Nowak",
        is_active=True,
    )


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_admin] = fake_admin_user
    app.dependency_overrides[require_teacher] = fake_teacher_user

    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)

    yield

    models.Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


def create_test_user(username="student01"):
    db = TestingSessionLocal()
    user = models.User(
        username=username,
        password="hashed-password",
        role=models.UserRole.student,
        first_name="Jan",
        last_name="Kowalski",
        email=f"{username}@example.com",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user.id


def test_list_users_empty():
    response = client.get("/users/")

    assert response.status_code == 200
    assert response.json() == []


def test_read_user_existing():
    user_id = create_test_user()

    response = client.get(f"/users/{user_id}")

    assert response.status_code == 200
    assert response.json()["username"] == "student01"
    assert response.json()["email"] == "student01@example.com"


def test_read_user_not_found():
    response = client.get("/users/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Uzytkownik nie znaleziony"


def test_delete_user_existing():
    user_id = create_test_user("student_to_delete")

    response = client.delete(f"/users/{user_id}")

    assert response.status_code == 204

    check_response = client.get(f"/users/{user_id}")
    assert check_response.status_code == 404


def test_delete_user_with_history_and_login_code():
    user_id = create_test_user("student_with_history")

    db = TestingSessionLocal()
    item = models.Item(
        nazwa="Laptop",
        kategoria="Elektronika",
        lokalizacja="Sala 101",
        qr_code="QR-HISTORY",
    )
    db.add(item)
    db.flush()
    history = models.LoanHistory(item_id=item.id, user_id=user_id)
    login_code = models.LoginCode(
        challenge_id="challenge-history",
        user_id=user_id,
        code_hash="hash",
        expires_at=datetime(2099, 1, 1),
    )
    db.add_all([history, login_code])
    db.commit()
    db.close()

    response = client.delete(f"/users/{user_id}")

    assert response.status_code == 204

    db = TestingSessionLocal()
    assert db.query(models.User).filter(models.User.id == user_id).first() is None
    assert db.query(models.LoanHistory).filter(models.LoanHistory.user_id == user_id).count() == 0
    assert db.query(models.LoginCode).filter(models.LoginCode.user_id == user_id).count() == 0
    db.close()


def test_delete_user_with_active_loan_is_blocked():
    user_id = create_test_user("student_with_loan")

    db = TestingSessionLocal()
    item = models.Item(
        nazwa="Projektor",
        kategoria="Elektronika",
        lokalizacja="Sala 102",
        qr_code="QR-ACTIVE",
    )
    db.add(item)
    db.flush()
    db.add(
        models.Loan(
            item_id=item.id,
            status=models.ItemStatus.wypozyczony,
            user_id=user_id,
        )
    )
    db.commit()
    db.close()

    response = client.delete(f"/users/{user_id}")

    assert response.status_code == 400
    assert "aktywne wypozyczenia" in response.json()["detail"]


def test_delete_user_not_found():
    response = client.delete("/users/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Uzytkownik nie znaleziony"


def test_activate_user_invalid_token():
    response = client.post("/users/activate?token=wrong-token")

    assert response.status_code == 400
    assert response.json()["detail"] == "Nieprawidlowy token"
