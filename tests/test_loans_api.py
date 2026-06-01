from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from database import get_db
from main import app
from security import require_student, require_teacher
import pytest

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_loans.db"

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


def fake_student_user():
    return models.User(
        id=1,
        username="student",
        role=models.UserRole.student,
        first_name="Jan",
        last_name="Kowalski",
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
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_student] = fake_student_user
    app.dependency_overrides[require_teacher] = fake_teacher_user

    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)

    yield

    models.Base.metadata.drop_all(bind=engine)


def setup_function():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)


def create_item_and_loan(status=models.ItemStatus.dostepny, user_id=None):
    db = TestingSessionLocal()

    item = models.Item(
        nazwa="Laptop",
        kategoria="Elektronika",
        lokalizacja="Sala 101",
        qr_code="QR123",
    )
    db.add(item)
    db.flush()

    loan = models.Loan(
        item_id=item.id,
        status=status,
        user_id=user_id,
    )
    db.add(loan)
    db.commit()
    db.refresh(item)
    db.refresh(loan)

    db.close()
    return item.id, loan.id


def test_request_loan_success():
    item_id, loan_id = create_item_and_loan()

    response = client.post("/loans/request/", json={"item_id": item_id})

    assert response.status_code == 201
    assert response.json()["item_id"] == item_id
    assert response.json()["status"] == "zarezerwowany"
    assert response.json()["user_id"] == 1


def test_request_loan_item_not_found():
    response = client.post("/loans/request/", json={"item_id": 999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Przedmiot nie znaleziony"


def test_request_loan_item_not_available():
    item_id, loan_id = create_item_and_loan(
        status=models.ItemStatus.wypozyczony,
        user_id=2,
    )

    response = client.post("/loans/request/", json={"item_id": item_id})

    assert response.status_code == 400
    assert "Przedmiot jest obecnie" in response.json()["detail"]


def test_list_pending_loans_empty():
    response = client.get("/loans/pending/")

    assert response.status_code == 200
    assert response.json() == []


def test_list_pending_loans_after_request():
    item_id, loan_id = create_item_and_loan()

    client.post("/loans/request/", json={"item_id": item_id})
    response = client.get("/loans/pending/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "zarezerwowany"


def test_approve_loan_success():
    item_id, loan_id = create_item_and_loan(
        status=models.ItemStatus.zarezerwowany,
        user_id=1,
    )

    response = client.post("/loans/approve/", json={"loan_id": loan_id})

    assert response.status_code == 200
    assert response.json()["status"] == "wypozyczony"
    assert response.json()["user_id"] == 1


def test_approve_loan_not_found():
    response = client.post("/loans/approve/", json={"loan_id": 999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Wniosek nie znaleziony"


def test_approve_loan_wrong_status():
    item_id, loan_id = create_item_and_loan(
        status=models.ItemStatus.dostepny,
        user_id=None,
    )

    response = client.post("/loans/approve/", json={"loan_id": loan_id})

    assert response.status_code == 400
    assert response.json()["detail"] == "Mozna zatwierdzic tylko wnioski zarezerwowane"


def test_teacher_loan_success():
    item_id, loan_id = create_item_and_loan()

    response = client.post("/loans/teacher/", json={"item_id": item_id})

    assert response.status_code == 201
    assert response.json()["status"] == "wypozyczony"
    assert response.json()["user_id"] == 2


def test_teacher_loan_item_not_found():
    response = client.post("/loans/teacher/", json={"item_id": 999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Przedmiot nie znaleziony"


def test_return_loan_success():
    item_id, loan_id = create_item_and_loan(
        status=models.ItemStatus.wypozyczony,
        user_id=1,
    )

    db = TestingSessionLocal()
    history = models.LoanHistory(
        item_id=item_id,
        user_id=1,
        approved_by_id=2,
    )
    db.add(history)
    db.commit()
    db.close()

    response = client.post("/loans/return/", json={"loan_id": loan_id})

    assert response.status_code == 200
    assert response.json()["status"] == "dostepny"
    assert response.json()["user_id"] is None


def test_return_loan_not_found():
    response = client.post("/loans/return/", json={"loan_id": 999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Wniosek nie znaleziony"


def test_return_loan_already_available():
    item_id, loan_id = create_item_and_loan(
        status=models.ItemStatus.dostepny,
        user_id=None,
    )

    response = client.post("/loans/return/", json={"loan_id": loan_id})

    assert response.status_code == 400
    assert response.json()["detail"] == "Przedmiot jest juz dostepny"


def test_loan_history_empty():
    response = client.get("/loans/history/")

    assert response.status_code == 200
    assert response.json() == []