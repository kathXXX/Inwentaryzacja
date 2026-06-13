from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

import models
from database import db_dependency
from models import ItemStatus, UserRole
from routers.email_service import send_loan_approved_email, send_loan_due_reminder_email
from schemas import (
    DueReminderRead,
    DueReminderRequest,
    ItemReminderRequest,
    LoanApprove,
    LoanHistoryRead,
    LoanRead,
    LoanRequest,
    LoanReturn,
    TeacherLoan,
    TeacherReserveForStudent,
)
from security import require_student, require_teacher


router = APIRouter(prefix="/loans", tags=["Wypozyczenia"])


def normalize_datetime(value: datetime | None) -> datetime | None:
    if value and value.tzinfo:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def resolve_loan_period(
    starts_at: datetime | None,
    due_at: datetime | None,
    *,
    existing_starts_at: datetime | None = None,
    existing_due_at: datetime | None = None,
    require_due_at: bool = True,
) -> tuple[datetime, datetime | None]:
    start = normalize_datetime(starts_at) or existing_starts_at or datetime.utcnow()
    due = normalize_datetime(due_at) or existing_due_at

    if require_due_at and not due:
        raise HTTPException(status_code=400, detail="Podaj date zwrotu")

    if due and due <= start:
        raise HTTPException(status_code=400, detail="Data zwrotu musi byc po dacie rozpoczecia")

    return start, due


def format_date(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.strftime("%d.%m.%Y %H:%M")


def loan_to_read(loan: models.Loan) -> LoanRead:
    return LoanRead(
        id=loan.id,
        item_id=loan.item_id,
        item_name=loan.item.nazwa if loan.item else None,
        status=loan.status,
        user_id=loan.user_id,
        starts_at=loan.starts_at,
        due_at=loan.due_at,
    )


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
    return [loan_to_read(loan) for loan in loans]


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

    starts_at, due_at = resolve_loan_period(req.starts_at, req.due_at)

    loan.status = ItemStatus.zarezerwowany
    loan.user_id = current_user.id
    loan.starts_at = starts_at
    loan.due_at = due_at
    loan.due_reminder_sent_at = None

    db.commit()
    db.refresh(loan)
    return loan_to_read(loan)


@router.post(
    "/reserve-for-student/",
    status_code=status.HTTP_201_CREATED,
    response_model=LoanRead,
    summary="Zarezerwuj sprzet dla studenta [nauczyciel/admin]",
)
async def reserve_for_student(
    req: TeacherReserveForStudent,
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    student = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student nie znaleziony")
    if student.role != UserRole.student:
        raise HTTPException(status_code=400, detail="Rezerwacje mozna zrobic tylko dla studenta")

    loan = db.query(models.Loan).filter(models.Loan.item_id == req.item_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")
    if loan.status.value != ItemStatus.dostepny.value:
        raise HTTPException(status_code=400, detail=f"Przedmiot jest obecnie: {loan.status}")

    starts_at, due_at = resolve_loan_period(req.starts_at, req.due_at)

    loan.status = ItemStatus.zarezerwowany
    loan.user_id = student.id
    loan.starts_at = starts_at
    loan.due_at = due_at
    loan.due_reminder_sent_at = None

    db.commit()
    db.refresh(loan)
    return loan_to_read(loan)


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
    if not loan.user_id:
        raise HTTPException(status_code=400, detail="Wniosek nie ma przypisanego uzytkownika")

    starts_at, due_at = resolve_loan_period(
        req.starts_at,
        req.due_at,
        existing_starts_at=loan.starts_at,
        existing_due_at=loan.due_at,
    )

    loan.starts_at = starts_at
    loan.due_at = due_at
    loan.status = ItemStatus.wypozyczony

    history = models.LoanHistory(
        item_id=loan.item_id,
        user_id=loan.user_id,
        starts_at=loan.starts_at,
        due_at=loan.due_at,
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
            format_date(loan.starts_at),
            format_date(loan.due_at),
        )

    return loan_to_read(loan)


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

    starts_at, due_at = resolve_loan_period(req.starts_at, req.due_at)

    loan.status = ItemStatus.wypozyczony
    loan.user_id = current_user.id
    loan.starts_at = starts_at
    loan.due_at = due_at
    loan.due_reminder_sent_at = None

    history = models.LoanHistory(
        item_id=loan.item_id,
        user_id=current_user.id,
        starts_at=loan.starts_at,
        due_at=loan.due_at,
        approved_by_id=current_user.id,
    )

    db.add(history)
    db.commit()
    db.refresh(loan)
    return loan_to_read(loan)


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
    if not loan.user_id:
        raise HTTPException(status_code=400, detail="Wypozyczenie nie ma przypisanego uzytkownika")

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

    now = datetime.utcnow()
    if history:
        history.returned_at = now
        history.returned_by_id = current_user.id
    else:
        history = models.LoanHistory(
            item_id=loan.item_id,
            user_id=loan.user_id,
            borrowed_at=now,
            starts_at=loan.starts_at,
            due_at=loan.due_at,
            returned_at=now,
            returned_by_id=current_user.id,
        )
        db.add(history)

    loan.status = ItemStatus.dostepny
    loan.user_id = None
    loan.starts_at = None
    loan.due_at = None
    loan.due_reminder_sent_at = None

    db.commit()
    db.refresh(loan)
    return loan_to_read(loan)


@router.get(
    "/history/",
    response_model=list[LoanHistoryRead],
    summary="Historia wypozyczen [nauczyciel/admin]",
)
async def loan_history(
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    histories = db.query(models.LoanHistory).order_by(models.LoanHistory.borrowed_at.desc()).all()
    return [
        LoanHistoryRead(
            id=h.id,
            item_id=h.item_id,
            item_name=h.item.nazwa if h.item else None,
            user_id=h.user_id,
            borrowed_at=h.borrowed_at,
            starts_at=h.starts_at,
            due_at=h.due_at,
            returned_at=h.returned_at,
            approved_by_id=h.approved_by_id,
            returned_by_id=h.returned_by_id,
        )
        for h in histories
    ]


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
            models.User.role == UserRole.student,
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
            format_date(loan.starts_at),
            format_date(loan.due_at) or "",
        )
        loan.due_reminder_sent_at = now
        sent += 1

    db.commit()
    return DueReminderRead(sent=sent, skipped=skipped)


@router.post(
    "/reminders/items/",
    response_model=DueReminderRead,
    summary="Wyslij przypomnienia dla zaznaczonych przedmiotow [nauczyciel/admin]",
)
async def send_item_reminders(
    req: ItemReminderRequest,
    background_tasks: BackgroundTasks,
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    item_ids = list(dict.fromkeys(req.item_ids))
    loans = (
        db.query(models.Loan)
        .join(models.User, models.Loan.user_id == models.User.id)
        .filter(
            models.Loan.item_id.in_(item_ids),
            models.Loan.status == ItemStatus.wypozyczony,
            models.User.role == UserRole.student,
        )
        .all()
    )

    now = datetime.utcnow()
    sent = 0
    skipped = len(item_ids) - len({loan.item_id for loan in loans})

    for loan in loans:
        if not loan.user or not loan.user.email or not loan.item:
            skipped += 1
            continue

        background_tasks.add_task(
            send_loan_due_reminder_email,
            loan.user.email,
            f"{loan.user.first_name} {loan.user.last_name}",
            loan.item.nazwa,
            format_date(loan.starts_at),
            format_date(loan.due_at) or "",
        )
        loan.due_reminder_sent_at = now
        sent += 1

    db.commit()
    return DueReminderRead(sent=sent, skipped=skipped)


@router.post("/reject/")
async def reject_loan(
    req: LoanApprove,
    db: db_dependency,
    current_user: models.User = Depends(require_teacher),
):
    loan = db.query(models.Loan).filter(models.Loan.id == req.loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Wniosek nie istnieje")
    if loan.status != ItemStatus.zarezerwowany:
        raise HTTPException(status_code=400, detail="Mozna odrzucic tylko wniosek oczekujacy")

    loan.status = ItemStatus.dostepny
    loan.user_id = None
    loan.starts_at = None
    loan.due_at = None
    loan.due_reminder_sent_at = None

    db.commit()
    db.refresh(loan)
    return {"message": "Wniosek odrzucony"}
