from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from database import get_db
from main import app
from security import require_teacher


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_locations.db"

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


def setup_function():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_teacher] = fake_teacher_user
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)


def teardown_function():
    models.Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


def create_item(db, name, location, qr_code):
    loc = models.Location(name=location)
    db.add(loc)
    db.flush()

    item = models.Item(
        nazwa=name,
        kategoria="Elektronika",
        lokalizacja=location,
        location_id=loc.id,
        qr_code=qr_code,
    )
    db.add(item)
    db.flush()

    db.add(models.Loan(item_id=item.id, status=models.ItemStatus.dostepny))
    return item


def test_inventory_check_reports_missing_and_wrong_location():
    db = TestingSessionLocal()
    expected = create_item(db, "Laptop", "Sala 101", "QR_EXPECTED")
    wrong = create_item(db, "Projektor", "Sala 202", "QR_WRONG")
    expected_id = expected.id
    wrong_id = wrong.id
    db.commit()
    db.close()

    response = client.post(
        "/locations/inventory-check/",
        json={
            "location_name": "Sala 101",
            "qr_codes": ["QR_WRONG", "QR_UNKNOWN"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["location"]["name"] == "Sala 101"
    assert data["missing_count"] == 1
    assert data["missing_items"][0]["item_id"] == expected_id
    assert data["wrong_location_count"] == 1
    assert data["wrong_location_items"][0]["item_id"] == wrong_id
    assert data["wrong_location_items"][0]["expected_location"] == "Sala 202"
    assert data["unknown_codes"] == ["QR_UNKNOWN"]
