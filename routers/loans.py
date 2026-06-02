from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

import models
from database import db_dependency
from models import ItemStatus
from routers.email_service import send_loan_approved_email, send_loan_due_reminder_email
from schemas import (
    DueReminderRead,
    DueReminderRequest,
    LoanApprove,
    LoanHistoryRead,
    LoanRead,
    LoanRequest,
    LoanReturn,
    TeacherLoan,
)
from security import require_student, require_teacher


router = APIRouter(prefix="/loans", tags=["Wypozyczenia"])


def normalize_due_at(due_at: datetime | None) -> datetime | None:
    if due_at and due_at.tzinfo:
        return due_at.astimezone(timezone.utc).replace(tzinfo=None)
    return due_at


def validate_due_at(due_at: datetime | None) -> datetime | None:
    due_at = normalize_due_at(due_at)
    if due_at and due_at <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="Termin zwrotu musi byc w przyszlosci")
    return due_at


def format_due_at(due_at: datetime | None) -> str | None:
    if not due_at:
        return None
    return due_at.strftime("%d.%m.%Y %H:%M")


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
            due_at=loan.due_at,
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
    due_at = validate_due_at(req.due_at)

    loan = db.query(models.Loan).filter(models.Loan.item_id == req.item_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")
    if loan.status.value != ItemStatus.dostepny.value:
        raise HTTPException(status_code=400, detail=f"Przedmiot jest obecnie: {loan.status}")

    loan.status = ItemStatus.zarezerwowany
    loan.user_id = current_user.id
    loan.due_at = due_at
    loan.due_reminder_sent_at = None
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

    due_at = validate_due_at(req.due_at)
    if due_at:
        loan.due_at = due_at

    loan.status = ItemStatus.wypozyczony
    history = models.LoanHistory(
        item_id=loan.item_id,
        user_id=loan.user_id,
        approved_by_id=current_user.id,
        due_at=loan.due_at,
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
            format_due_at(loan.due_at),
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
    due_at = validate_due_at(req.due_at)

    loan = db.query(models.Loan).filter(models.Loan.item_id == req.item_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")
    if loan.status.value != ItemStatus.dostepny.value:
        raise HTTPException(status_code=400, detail=f"Przedmiot jest obecnie: {loan.status}")

    loan.status = ItemStatus.wypozyczony
    loan.user_id = current_user.id
    loan.due_at = due_at
    loan.due_reminder_sent_at = None
    history = models.LoanHistory(
        item_id=loan.item_id,
        user_id=current_user.id,
        approved_by_id=current_user.id,
        due_at=loan.due_at,
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
        loan.due_at = None
        loan.due_reminder_sent_at = None

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


@router.post(
    "/reminders/due/",
    response_model=DueReminderRead,
    summary="Wyslij przypomnienia o terminie zwrotu tylko do studentow [nauczyciel/admin]",
)
async def send_due_reminders(
    req: DueReminderRequest,
    background_tasks: BackgroundTasks,
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    now = datetime.utcnow()
    until = now + timedelta(days=req.days)

    loans = (
        db.query(models.Loan)
        .join(models.User, models.Loan.user_id == models.User.id)
        .filter(
            models.Loan.status == ItemStatus.wypozyczony,
            models.Loan.due_at != None,
            models.Loan.due_at <= until,
            models.Loan.due_reminder_sent_at == None,
            models.User.role == models.UserRole.student,
        )
        .all()
    )

    sent = 0
    skipped = 0

    for loan in loans:
        if not loan.user or not loan.user.email or not loan.item or not loan.due_at:
            skipped += 1
            continue

        background_tasks.add_task(
            send_loan_due_reminder_email,
            loan.user.email,
            f"{loan.user.first_name} {loan.user.last_name}",
            loan.item.nazwa,
            format_due_at(loan.due_at) or "",
        )
        loan.due_reminder_sent_at = now
        sent += 1

    db.commit()

    return DueReminderRead(sent=sent, skipped=skipped)
