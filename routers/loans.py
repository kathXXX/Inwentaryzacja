from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

import models
from database import db_dependency
from models import ItemStatus
from routers.email_service import send_loan_approved_email
from schemas import LoanApprove, LoanHistoryRead, LoanRead, LoanRequest, LoanReturn, TeacherLoan
from security import require_student, require_teacher


router = APIRouter(prefix="/loans", tags=["Wypozyczenia"])


@router.get(
    "/pending/",
    response_model=list[LoanRead],
    summary="Lista oczekujacych wnioskow [nauczyciel/admin]",
)
async def list_pending_loans(
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    loans = db.query(models.Loan).filter(models.Loan.status == ItemStatus.zarezerwowany).all()

    return [
        LoanRead(
            id=loan.id,
            item_id=loan.item_id,
            item_name=loan.item.nazwa if loan.item else None,
            status=loan.status,
            user_id=loan.user_id,
        )
        for loan in loans
    ]


@router.post(
    "/request/",
    status_code=status.HTTP_201_CREATED,
    response_model=LoanRead,
    summary="Zloz wniosek o wypozyczenie [student]",
)
async def request_loan(
    req: LoanRequest,
    db: db_dependency,
    current_user: models.User = Depends(require_student),
):
    loan = db.query(models.Loan).filter(models.Loan.item_id == req.item_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")
    if loan.status.value != ItemStatus.dostepny.value:
        raise HTTPException(status_code=400, detail=f"Przedmiot jest obecnie: {loan.status}")

    loan.status = ItemStatus.zarezerwowany
    loan.user_id = current_user.id
    db.commit()
    db.refresh(loan)
    return loan


@router.post(
    "/approve/",
    response_model=LoanRead,
    summary="Zatwierdz wniosek studenta [nauczyciel/admin]",
)
async def approve_loan(
    req: LoanApprove,
    background_tasks: BackgroundTasks,
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    loan = db.query(models.Loan).filter(models.Loan.id == req.loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Wniosek nie znaleziony")
    if loan.status.value != ItemStatus.zarezerwowany.value:
        raise HTTPException(status_code=400, detail="Mozna zatwierdzic tylko wnioski zarezerwowane")

    loan.status = ItemStatus.wypozyczony
    history = models.LoanHistory(
        item_id=loan.item_id,
        user_id=loan.user_id,
        approved_by_id=current_user.id,
    )

    db.add(history)
    db.commit()
    db.refresh(loan)

    if loan.user and loan.user.email and loan.item:
        background_tasks.add_task(
            send_loan_approved_email,
            loan.user.email,
            f"{loan.user.first_name} {loan.user.last_name}",
            loan.item.nazwa,
        )

    return loan


@router.post(
    "/teacher/",
    status_code=status.HTTP_201_CREATED,
    response_model=LoanRead,
    summary="Wypozycz sprzet dla siebie [nauczyciel/admin]",
)
async def teacher_loan(
    req: TeacherLoan,
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    loan = db.query(models.Loan).filter(models.Loan.item_id == req.item_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")
    if loan.status.value != ItemStatus.dostepny.value:
        raise HTTPException(status_code=400, detail=f"Przedmiot jest obecnie: {loan.status}")

    loan.status = ItemStatus.wypozyczony
    loan.user_id = current_user.id
    history = models.LoanHistory(
        item_id=loan.item_id,
        user_id=current_user.id,
        approved_by_id=current_user.id,
    )

    db.add(history)
    db.commit()
    db.refresh(loan)
    return loan


@router.post(
    "/return/",
    response_model=LoanRead,
    summary="Oznacz przedmiot jako zwrocony [nauczyciel/admin]",
)
async def return_loan(
    req: LoanReturn,
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    loan = db.query(models.Loan).filter(models.Loan.id == req.loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Wniosek nie znaleziony")
    if loan.status.value == ItemStatus.dostepny.value:
        raise HTTPException(status_code=400, detail="Przedmiot jest juz dostepny")

    history = (
        db.query(models.LoanHistory)
        .filter(
            models.LoanHistory.item_id == loan.item_id,
            models.LoanHistory.user_id == loan.user_id,
            models.LoanHistory.returned_at == None,
        )
        .order_by(models.LoanHistory.borrowed_at.desc())
        .first()
    )

    if history:
        history.returned_at = datetime.utcnow()
        history.returned_by_id = current_user.id
        loan.status = ItemStatus.dostepny
        loan.user_id = None

    db.commit()
    db.refresh(loan)
    return loan


@router.get(
    "/history/",
    response_model=list[LoanHistoryRead],
    summary="Historia wypozyczen [nauczyciel/admin]",
)
async def loan_history(
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    return db.query(models.LoanHistory).all()
