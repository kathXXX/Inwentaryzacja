from jose import jwt
from fastapi import HTTPException

from models import User, UserRole
from security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    hash_password,
    verify_password,
    require_admin,
    require_teacher,
    require_student,
)


def test_hash_password_returns_different_value():
    hashed = hash_password("password123")

    assert hashed != "password123"
    assert isinstance(hashed, str)


def test_verify_password_correct_password():
    hashed = hash_password("password123")

    assert verify_password("password123", hashed) is True


def test_verify_password_wrong_password():
    hashed = hash_password("password123")

    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token_contains_user_id_and_role():
    user = User(
        id=1,
        username="admin",
        role=UserRole.administrator,
        first_name="Admin",
        last_name="User",
        is_active=True,
    )

    token = create_access_token(user)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["sub"] == "1"
    assert payload["role"] == "administrator"
    assert "exp" in payload


def test_require_admin_allows_admin():
    user = User(
        id=1,
        username="admin",
        role=UserRole.administrator,
        first_name="Admin",
        last_name="User",
    )

    assert require_admin(user) == user


def test_require_admin_blocks_student():
    user = User(
        id=2,
        username="student",
        role=UserRole.student,
        first_name="Jan",
        last_name="Kowalski",
    )

    try:
        require_admin(user)
        assert False
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Wymagana rola administrator"


def test_require_teacher_allows_teacher():
    user = User(
        id=3,
        username="teacher",
        role=UserRole.nauczyciel,
        first_name="Anna",
        last_name="Nowak",
    )

    assert require_teacher(user) == user


def test_require_teacher_allows_admin():
    user = User(
        id=4,
        username="admin",
        role=UserRole.administrator,
        first_name="Admin",
        last_name="User",
    )

    assert require_teacher(user) == user


def test_require_teacher_blocks_student():
    user = User(
        id=5,
        username="student",
        role=UserRole.student,
        first_name="Jan",
        last_name="Kowalski",
    )

    try:
        require_teacher(user)
        assert False
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Wymagana rola nauczyciel"


def test_require_student_allows_student():
    user = User(
        id=6,
        username="student",
        role=UserRole.student,
        first_name="Jan",
        last_name="Kowalski",
    )

    assert require_student(user) == user


def test_require_student_blocks_teacher():
    user = User(
        id=7,
        username="teacher",
        role=UserRole.nauczyciel,
        first_name="Anna",
        last_name="Nowak",
    )

    try:
        require_student(user)
        assert False
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "Wymagana rola student"