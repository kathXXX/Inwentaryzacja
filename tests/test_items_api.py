from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from database import get_db
from main import app
from security import require_admin
import pytest

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_items.db"

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
        id=1,
        username="admin",
        role=models.UserRole.administrator,
        first_name="Admin",
        last_name="User",
        is_active=True,
    )

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_database():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_admin] = fake_admin_user

    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)

    yield

    models.Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


def test_create_item():
    response = client.post(
        "/items/",
        json={
            "nazwa": "Laptop",
            "kategoria": "Elektronika",
            "lokalizacja": "Sala 101",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["nazwa"] == "Laptop"
    assert data["kategoria"] == "Elektronika"
    assert data["lokalizacja"] == "Sala 101"
    assert "qr_code" in data


def test_list_items_empty():
    response = client.get("/items/")

    assert response.status_code == 200
    assert response.json() == []


def test_list_items_after_create():
    client.post(
        "/items/",
        json={
            "nazwa": "Projektor",
            "kategoria": "Elektronika",
            "lokalizacja": "Sala 202",
        },
    )

    response = client.get("/items/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["nazwa"] == "Projektor"


def test_read_item_existing():
    create_response = client.post(
        "/items/",
        json={
            "nazwa": "Kamera",
            "kategoria": "Elektronika",
            "lokalizacja": "Studio",
        },
    )
    item_id = create_response.json()["id"]

    response = client.get(f"/items/{item_id}")

    assert response.status_code == 200
    assert response.json()["nazwa"] == "Kamera"


def test_read_item_not_found():
    response = client.get("/items/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Przedmiot nie znaleziony"


def test_delete_item_existing():
    create_response = client.post(
        "/items/",
        json={
            "nazwa": "Tablet",
            "kategoria": "Elektronika",
            "lokalizacja": "Sala 303",
        },
    )
    item_id = create_response.json()["id"]

    response = client.delete(f"/items/{item_id}")

    assert response.status_code == 204

    check_response = client.get(f"/items/{item_id}")
    assert check_response.status_code == 404


def test_delete_item_not_found():
    response = client.delete("/items/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Przedmiot nie znaleziony"