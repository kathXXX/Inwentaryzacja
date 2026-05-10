import io
import os
import secrets
from urllib.parse import urlencode

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import models
from database import db_dependency
from models import ItemStatus
from schemas import ItemCreate, ItemQrRead, ItemRead
from security import require_admin


router = APIRouter(prefix="/items", tags=["Przedmioty"])


def generate_qr_code() -> str:
    return secrets.token_urlsafe(18)


def generate_unique_qr_code(db: Session) -> str:
    while True:
        qr_code = generate_qr_code()
        exists = db.query(models.Item).filter(models.Item.qr_code == qr_code).first()
        if not exists:
            return qr_code


def get_public_frontend_url() -> str:
    return os.getenv(
        "PUBLIC_FRONTEND_URL",
        "https://web-production-53ca6.up.railway.app",
    ).rstrip("/")


def build_qr_target_url(qr_code: str) -> str:
    return f"{get_public_frontend_url()}/?{urlencode({'qr': qr_code})}"


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ItemRead,
    summary="Dodaj przedmiot [administrator]",
)
async def create_item(
    item: ItemCreate,
    db: db_dependency,
    current_user: models.User = Depends(require_admin),
):
    db_item = models.Item(**item.model_dump(), qr_code=generate_unique_qr_code(db))
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    db_loan = models.Loan(item_id=db_item.id, status=ItemStatus.dostepny, user_id=None)
    db.add(db_loan)
    db.commit()

    return db_item


@router.get("/", response_model=list[ItemRead], summary="Lista wszystkich przedmiotow")
async def list_items(db: db_dependency):
    return db.query(models.Item).all()


@router.get(
    "/qr/{qr_code}",
    response_model=ItemQrRead,
    summary="Znajdz przedmiot po kodzie QR",
)
async def read_item_by_qr(qr_code: str, db: db_dependency):
    item = db.query(models.Item).filter(models.Item.qr_code == qr_code).first()
    if not item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")

    loan = item.loan
    if not loan:
        raise HTTPException(status_code=404, detail="Brak rekordu dostepnosci dla tego przedmiotu")

    return ItemQrRead(
        item_id=item.id,
        nazwa=item.nazwa,
        kategoria=item.kategoria,
        lokalizacja=item.lokalizacja,
        qr_code=item.qr_code,
        loan_id=loan.id,
        status=loan.status,
    )


@router.get("/{item_id}/qr")
def generate_qr(item_id: int, db: db_dependency):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")

    data = build_qr_target_url(item.qr_code)

    qr = qrcode.make(data)

    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@router.get("/{item_id}", response_model=ItemRead, summary="Pobierz przedmiot")
async def read_item(item_id: int, db: db_dependency):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")
    return item


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Usun przedmiot [administrator]",
)
async def delete_item(
    item_id: int,
    db: db_dependency,
    current_user: models.User = Depends(require_admin),
):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")

    db_loan = db.query(models.Loan).filter(models.Loan.item_id == item_id).first()
    if db_loan:
        db.delete(db_loan)

    db.delete(db_item)
    db.commit()
