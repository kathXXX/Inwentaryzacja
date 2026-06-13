from fastapi import APIRouter, Body, Depends, HTTPException, status

from sqlalchemy.exc import IntegrityError

import models
from database import db_dependency
from schemas import ActivationCodeRequest, UserCreate, UserRead
from security import hash_password, require_admin, require_teacher, verify_password

import secrets
from datetime import datetime, timedelta
from routers.email_service import send_activation_email


router = APIRouter(prefix="/users", tags=["Uzytkownicy"])


def generate_activation_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


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
    if not user.email:
        raise HTTPException(status_code=400, detail="Email jest wymagany dla konta uzytkownika")

    activation_code = generate_activation_code()
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
        activation_token=hash_password(activation_code),
        activation_token_expires_at=datetime.utcnow() + timedelta(hours=24),
    )

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Uzytkownik o takim loginie juz istnieje",
        )
    db.refresh(new_user)

    try:
        await send_activation_email(
            to_email=user.email,
            username=user.username,
            password=plain_password,
            activation_code=activation_code,
        )
    except Exception as e:
        print(f"Nie udalo sie wyslac maila aktywacyjnego: {e}")

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

    active_loans = (
        db.query(models.Loan)
        .filter(
            models.Loan.user_id == user_id,
            models.Loan.status != models.ItemStatus.dostepny,
        )
        .all()
    )
    if active_loans:
        item_ids = ", ".join(f"#{loan.item_id}" for loan in active_loans[:5])
        raise HTTPException(
            status_code=400,
            detail=(
                "Nie mozna usunac uzytkownika, bo ma aktywne wypozyczenia "
                f"lub rezerwacje: {item_ids}. Najpierw zwroc albo odrzuc te wypozyczenia."
            ),
        )

    db.query(models.LoginCode).filter(models.LoginCode.user_id == user_id).delete(
        synchronize_session=False
    )
    db.query(models.Loan).filter(models.Loan.user_id == user_id).update(
        {
            models.Loan.user_id: None,
            models.Loan.starts_at: None,
            models.Loan.due_at: None,
            models.Loan.due_reminder_sent_at: None,
        },
        synchronize_session=False,
    )
    db.query(models.LoanHistory).filter(models.LoanHistory.approved_by_id == user_id).update(
        {models.LoanHistory.approved_by_id: None},
        synchronize_session=False,
    )
    db.query(models.LoanHistory).filter(models.LoanHistory.returned_by_id == user_id).update(
        {models.LoanHistory.returned_by_id: None},
        synchronize_session=False,
    )
    db.query(models.LoanHistory).filter(models.LoanHistory.user_id == user_id).delete(
        synchronize_session=False
    )

    db.delete(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Nie mozna usunac uzytkownika, bo ma powiazane dane w systemie",
        )



@router.post("/activate", summary="Aktywuj konto")
async def activate_user(
    db: db_dependency,
    data: ActivationCodeRequest | None = Body(default=None),
    token: str | None = None,
):
    activation_by_code = data is not None

    if data:
        user = db.query(models.User).filter(models.User.username == data.username).first()
    elif token:
        user = db.query(models.User).filter(models.User.activation_token == token).first()
    else:
        raise HTTPException(status_code=400, detail="Podaj kod aktywacji")

    if not user:
        detail = "Nieprawidlowy kod aktywacji" if activation_by_code else "Nieprawidlowy token"
        raise HTTPException(status_code=400, detail=detail)

    if user.is_active:
        return {"message": "Konto jest juz aktywne"}

    if data:
        try:
            code_ok = bool(user.activation_token and verify_password(data.code, user.activation_token))
        except Exception:
            code_ok = False

        if not code_ok:
            raise HTTPException(status_code=400, detail="Nieprawidlowy kod aktywacji")

    if user.activation_token_expires_at and user.activation_token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Kod aktywacji wygasl")

    user.is_active = True
    user.activation_token = None
    user.activation_token_expires_at = None

    db.commit()

    return {"message": "Konto zostalo aktywowane"}
