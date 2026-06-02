import pytest
from pydantic import ValidationError

from schemas import LoginRequest, ChangePasswordRequest, UserCreate
from models import UserRole


def test_login_request_valid():
    data = LoginRequest(username="admin", password="password123")

    assert data.username == "admin"
    assert data.password == "password123"


def test_change_password_valid():
    data = ChangePasswordRequest(
        current_password="oldpassword",
        new_password="newpassword123",
    )

    assert data.current_password == "oldpassword"
    assert data.new_password == "newpassword123"


def test_change_password_new_password_too_short():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(
            current_password="oldpassword",
            new_password="short",
        )


def test_user_create_valid_student():
    data = UserCreate(
        username="student01",
        password="password123",
        role=UserRole.student,
        first_name="Jan",
        last_name="Kowalski",
        email="jan@example.com",
    )

    assert data.username == "student01"
    assert data.role == UserRole.student
    assert data.first_name == "Jan"


def test_user_create_username_too_short():
    with pytest.raises(ValidationError):
        UserCreate(
            username="ab",
            password="password123",
            role=UserRole.student,
            first_name="Jan",
            last_name="Kowalski",
        )


def test_user_create_password_too_short():
    with pytest.raises(ValidationError):
        UserCreate(
            username="student01",
            password="short",
            role=UserRole.student,
            first_name="Jan",
            last_name="Kowalski",
        )


def test_user_create_first_name_too_short():
    with pytest.raises(ValidationError):
        UserCreate(
            username="student01",
            password="password123",
            role=UserRole.student,
            first_name="J",
            last_name="Kowalski",
        )
