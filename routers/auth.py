import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import models
from database import get_db
from rate_limit import limiter
from routers.email_service import is_email_dev_mode, send_login_code_email
from schemas import ChangePasswordRequest, LoginCodeRead, LoginCodeRequest, LoginRequest, Token
from security import create_access_token, get_current_user, hash_password, verify_password


router = APIRouter(tags=["Auth"])

LOGIN_CODE_TTL_MINUTES = int(os.getenv("LOGIN_CODE_TTL_MINUTES", "10"))
LOGIN_CODE_MAX_ATTEMPTS = int(os.getenv("LOGIN_CODE_MAX_ATTEMPTS", "5"))


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return email
    if len(local) <= 2:
        hidden_local = local[0] + "***"
    else:
        hidden_local = local[0] + "***" + local[-1]
    return f"{hidden_local}@{domain}"


def generate_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


@router.post("/login", response_model=LoginCodeRead)
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == data.username).first()

    if not user or not user.password or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Nieprawidlowe dane")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Konto nie jest aktywne")

    if not user.email:
        raise HTTPException(status_code=400, detail="Uzytkownik nie ma przypisanego adresu email")

    now = datetime.utcnow()
    db.query(models.LoginCode).filter(
        models.LoginCode.user_id == user.id,
        models.LoginCode.used_at == None,
    ).update({"used_at": now})

    code = generate_login_code()
    challenge = models.LoginCode(
        challenge_id=secrets.token_urlsafe(32),
        user_id=user.id,
        code_hash=hash_password(code),
        expires_at=now + timedelta(minutes=LOGIN_CODE_TTL_MINUTES),
    )
    db.add(challenge)
    db.commit()

    try:
        await send_login_code_email(user.email, code)
    except Exception as exc:
        challenge.used_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail="Nie udalo sie wyslac kodu logowania") from exc

    return LoginCodeRead(
        challenge_id=challenge.challenge_id,
        message="Kod logowania zostal wyslany na email",
        email=mask_email(user.email),
        expires_in_seconds=LOGIN_CODE_TTL_MINUTES * 60,
        dev_code=code if is_email_dev_mode() else None,
    )


@router.post("/login/verify", response_model=Token)
@limiter.limit("10/minute")
def verify_login_code(request: Request, data: LoginCodeRequest, db: Session = Depends(get_db)):
    challenge = (
        db.query(models.LoginCode)
        .filter(models.LoginCode.challenge_id == data.challenge_id)
        .first()
    )

    if not challenge:
        raise HTTPException(status_code=400, detail="Nieprawidlowy kod lub sesja logowania")

    if challenge.used_at is not None:
        raise HTTPException(status_code=400, detail="Kod zostal juz wykorzystany")

    if challenge.expires_at < datetime.utcnow():
        challenge.used_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=400, detail="Kod wygasl")

    if challenge.attempts >= LOGIN_CODE_MAX_ATTEMPTS:
        challenge.used_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=400, detail="Przekroczono limit prob")

    if not verify_password(data.code, challenge.code_hash):
        challenge.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Nieprawidlowy kod")

    user = challenge.user
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Konto nie jest aktywne")

    challenge.used_at = datetime.utcnow()
    db.commit()

    return {"access_token": create_access_token(user), "token_type": "bearer"}


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not current_user.password or not verify_password(data.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Aktualne haslo jest nieprawidlowe")

    current_user.password = hash_password(data.new_password)
    db.commit()
    return {"message": "Haslo zostalo zmienione"}
