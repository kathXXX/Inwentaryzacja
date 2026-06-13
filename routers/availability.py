from fastapi import APIRouter, Depends, HTTPException

import models
from database import db_dependency
from schemas import AvailabilityRead, LoanRead
from security import require_teacher


router = APIRouter(tags=["Dostepnosc"])


@router.get(
    "/items/{item_id}/status",
    response_model=AvailabilityRead,
    summary="Sprawdz status przedmiotu",
)
async def get_item_status(item_id: int, db: db_dependency):
    loan = db.query(models.Loan).filter(models.Loan.item_id == item_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Brak rekordu dostepnosci dla tego przedmiotu")

    return AvailabilityRead(
        id=loan.id,
        item_id=loan.item_id,
        item_name=loan.item.nazwa if loan.item else None,
        kategoria=loan.item.kategoria if loan.item else None,
        lokalizacja=loan.item.lokalizacja if loan.item else None,
        status=loan.status,
        starts_at=loan.starts_at,
        due_at=loan.due_at,
    )


@router.get(
    "/availability/",
    response_model=list[AvailabilityRead],
    summary="Lista dostepnosci",
)
async def list_availability(db: db_dependency):
    loans = db.query(models.Loan).all()

    return [
        AvailabilityRead(
            id=loan.id,
            item_id=loan.item_id,
            item_name=loan.item.nazwa if loan.item else None,
            kategoria=loan.item.kategoria if loan.item else None,
            lokalizacja=loan.item.lokalizacja if loan.item else None,
            status=loan.status,
            starts_at=loan.starts_at,
            due_at=loan.due_at,
        )
        for loan in loans
    ]


@router.get(
    "/availability/details/",
    response_model=list[LoanRead],
    summary="Lista statusow z uzytkownikami [nauczyciel/admin]",
)
async def list_availability_details(
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    loans = db.query(models.Loan).all()

    return [
        LoanRead(
            id=loan.id,
            item_id=loan.item_id,
            item_name=loan.item.nazwa if loan.item else None,
            status=loan.status,
            user_id=loan.user_id,
            starts_at=loan.starts_at,
            due_at=loan.due_at,
        )
        for loan in loans
    ]
