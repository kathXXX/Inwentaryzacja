from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import models
from database import get_db
from rate_limit import limiter
from schemas import LoginRequest, Token
from security import create_access_token, verify_password


router = APIRouter(tags=["Auth"])


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == data.username).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Nieprawidlowe dane")

    return {"access_token": create_access_token(user), "token_type": "bearer"}
