from fastapi import APIRouter, Depends, HTTPException, status

import models
from database import db_dependency
from schemas import UserCreate, UserRead
from security import hash_password, require_admin, require_teacher

import os
import secrets
from datetime import datetime, timedelta
from routers.email_service import send_activation_email


router = APIRouter(prefix="/users", tags=["Uzytkownicy"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRead,
    summary="Utworz uzytkownika [administrator]",
)
async def create_user(
    user: UserCreate,
    db: db_dependency,
    current_user: models.User = Depends(require_admin),

):
    activation_token = secrets.token_urlsafe(32)
    plain_password = user.password

    new_user = models.User(
        username=user.username,
        password=hash_password(plain_password),

        role=user.role,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        field_of_study=user.field_of_study,
        student_index=user.student_index,
        department=user.department,
        is_active=False,
        activation_token=activation_token,
        activation_token_expires_at=datetime.utcnow() + timedelta(hours=24),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    activation_link = f"{os.getenv('FRONTEND_URL')}/activate?token={activation_token}"

    await send_activation_email(
        to_email=user.email,
        username=user.username,
        password=user.password,
        activation_link=activation_link,
    )

    return new_user


@router.get(
    "/",
    response_model=list[UserRead],
    summary="Lista uzytkownikow [administrator]",
)
async def list_users(
    db: db_dependency,
    current_user: models.User = Depends(require_admin),
):
    return db.query(models.User).all()


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Pobierz uzytkownika [nauczyciel/admin]",
)
async def read_user(
    user_id: int,
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Uzytkownik nie znaleziony")
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Usun uzytkownika [administrator]",
)
async def delete_user(
    user_id: int,
    db: db_dependency,
    current_user: models.User = Depends(require_admin),
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Uzytkownik nie znaleziony")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Nie mozesz usunac samego siebie")

    db.delete(db_user)
    db.commit()



    @router.post("/activate", summary="Aktywuj konto")
    async def activate_user(
        token: str,
        db: db_dependency,
    ):
        user = db.query(models.User).filter(
            models.User.activation_token == token
        ).first()

        if not user:
            raise HTTPException(status_code=400, detail="Nieprawidlowy token")

        if user.activation_token_expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Token wygasl")

        user.is_active = True
        user.activation_token = None
        user.activation_token_expires_at = None

        db.commit()

        return {"message": "Konto zostalo aktywowane"}