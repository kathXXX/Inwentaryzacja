from fastapi import APIRouter, Depends, HTTPException, status

import models
from database import db_dependency
from schemas import UserCreate, UserRead
from security import hash_password, require_admin, require_teacher


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
    new_user = models.User(
        username=user.username,
        password=hash_password(user.password),
        role=user.role,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        field_of_study=user.field_of_study,
        student_index=user.student_index,
        department=user.department,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

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
