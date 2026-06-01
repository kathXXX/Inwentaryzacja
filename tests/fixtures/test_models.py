from datetime import datetime, timedelta

from models import User, LoginCode, Item, Loan, LoanHistory, UserRole, ItemStatus


def test_user_model_fields():
    user = User(
        username="student01",
        password="hashed-password",
        is_active=True,
        role=UserRole.student,
        first_name="Jan",
        last_name="Kowalski",
        email="jan@example.com",
    )

    assert user.username == "student01"
    assert user.is_active is True
    assert user.role == UserRole.student
    assert user.first_name == "Jan"
    assert user.last_name == "Kowalski"
    assert user.email == "jan@example.com"


def test_user_role_values():
    assert UserRole.student.value == "student"
    assert UserRole.nauczyciel.value == "nauczyciel"
    assert UserRole.administrator.value == "administrator"


def test_item_status_values():
    assert ItemStatus.dostepny.value == "dostepny"
    assert ItemStatus.wypozyczony.value == "wypozyczony"
    assert ItemStatus.zarezerwowany.value == "zarezerwowany"


def test_login_code_model_fields():
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    login_code = LoginCode(
        challenge_id="challenge123",
        user_id=1,
        code_hash="hashed-code",
        attempts=0,
        expires_at=expires_at,
    )

    assert login_code.challenge_id == "challenge123"
    assert login_code.user_id == 1
    assert login_code.code_hash == "hashed-code"
    assert login_code.attempts == 0
    assert login_code.expires_at == expires_at
    assert login_code.used_at is None


def test_item_model_fields():
    item = Item(
        nazwa="Laptop",
        kategoria="Elektronika",
        lokalizacja="Sala 101",
        qr_code="QR123",
    )

    assert item.nazwa == "Laptop"
    assert item.kategoria == "Elektronika"
    assert item.lokalizacja == "Sala 101"
    assert item.qr_code == "QR123"


def test_loan_model_available_status():
    loan = Loan(
        item_id=1,
        status=ItemStatus.dostepny,
        user_id=None,
    )

    assert loan.item_id == 1
    assert loan.status == ItemStatus.dostepny
    assert loan.user_id is None


def test_loan_model_borrowed_status():
    loan = Loan(
        item_id=1,
        status=ItemStatus.wypozyczony,
        user_id=5,
    )

    assert loan.item_id == 1
    assert loan.status == ItemStatus.wypozyczony
    assert loan.user_id == 5


def test_loan_history_model_fields():
    borrowed_at = datetime.utcnow()
    returned_at = borrowed_at + timedelta(days=1)

    history = LoanHistory(
        item_id=1,
        user_id=2,
        borrowed_at=borrowed_at,
        returned_at=returned_at,
        approved_by_id=3,
        returned_by_id=4,
    )

    assert history.item_id == 1
    assert history.user_id == 2
    assert history.borrowed_at == borrowed_at
    assert history.returned_at == returned_at
    assert history.approved_by_id == 3
    assert history.returned_by_id == 4