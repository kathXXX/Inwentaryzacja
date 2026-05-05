from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Annotated, Optional
import models
from models import Base, UserRole, ItemStatus
from models import UserRole, ItemStatus
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import qrcode
from fastapi.responses import StreamingResponse
import io
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
import os
from pydantic import Field
from typing import Optional


app = FastAPI()
security = HTTPBearer()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@app.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == data.username).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Nieprawidłowe dane")

    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://web-production-53ca6.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Schematy Pydantic
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.student

    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)

    email: Optional[str] = None
    phone: Optional[str] = None

    # student
    field_of_study: Optional[str] = None
    student_index: Optional[str] = None

    # nauczyciel
    department: Optional[str] = None

class UserRead(BaseModel):
    id: int
    username: str
    role: UserRole

    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]

    field_of_study: Optional[str]
    student_index: Optional[str]
    department: Optional[str]


class ItemCreate(BaseModel):
    nazwa: str
    kategoria: str
    lokalizacja: str

class ItemRead(BaseModel):
    id: int
    nazwa: str
    kategoria: str
    lokalizacja: str
    class Config:
        from_attributes = True

class LoanRead(BaseModel):
    id: int
    item_id: int
    item_name: Optional[str] = None   # 👈 NOWE
    status: ItemStatus
    user_id: Optional[int]
    class Config:
        from_attributes = True

class LoanRequest(BaseModel):
    """Student składa wniosek o wypożyczenie."""
    item_id: int

class LoanApprove(BaseModel):
    """Nauczyciel zatwierdza wniosek (zmienia status z zarezerwowany → wypozyczony)."""
    loan_id: int

class LoanReturn(BaseModel):
    """Nauczyciel oznacza przedmiot jako zwrócony."""
    loan_id: int

class TeacherLoan(BaseModel):
    """Nauczyciel wypożycza sprzęt dla siebie bez dodatkowej autoryzacji."""
    item_id: int

class AvailabilityRead(BaseModel):
    id: int
    item_id: int
    item_name: Optional[str] = None
    kategoria: Optional[str] = None
    lokalizacja: Optional[str] = None
    status: ItemStatus

class Config:
    from_attributes = True
# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

# ---------------------------------------------------------------------------
# UŻYTKOWNICY (administrator)
# ---------------------------------------------------------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Nieprawidłowy token")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Użytkownik nie istnieje")

    return user
def require_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != UserRole.administrator:
        raise HTTPException(status_code=403, detail="Wymagana rola administrator")
    return current_user


def require_teacher(current_user: models.User = Depends(get_current_user)):
    if current_user.role not in [UserRole.nauczyciel, UserRole.administrator]:
        raise HTTPException(status_code=403, detail="Wymagana rola nauczyciel")
    return current_user


def require_student(current_user: models.User = Depends(get_current_user)):
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Wymagana rola student")
    return current_user

@app.get("/loans/pending/", response_model=list[LoanRead], tags=["Wypożyczenia"], summary="Lista oczekujących wniosków")
async def list_pending_loans(db: db_dependency, current_user: models.User = Depends(require_teacher)):
    return db.query(models.Loan).filter(models.Loan.status == ItemStatus.zarezerwowany).all()

@app.get("/items/{item_id}/qr")
def generate_qr(item_id: int):
    data = f"https://web-production-53ca6.up.railway.app/return.html?item_id={item_id}"

    qr = qrcode.make(data)

    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/users/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRead,
    tags=["Użytkownicy"],
    summary="Utwórz użytkownika [administrator]"
)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    hashed_password = pwd_context.hash(user.password)

    new_user = models.User(
        username=user.username,
        password=hashed_password,
        role=user.role,

        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,

        field_of_study=user.field_of_study,
        student_index=user.student_index,
        department=user.department)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

@app.get("/users/", response_model=list[UserRead],
         tags=["Użytkownicy"], summary="Lista użytkowników [administrator]")
async def list_users(

    db: db_dependency,
    current_user: models.User = Depends(require_admin)
):
    if current_user.role != UserRole.administrator:
        raise HTTPException(status_code=403, detail="Brak dostępu")

    return db.query(models.User).all()

@app.get("/users/{user_id}", response_model=UserRead,
         tags=["Użytkownicy"], summary="Pobierz użytkownika [administrator]")
async def read_user(user_id: int, db: db_dependency, current_user: models.User = Depends(require_teacher)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    return user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
            tags=["Użytkownicy"], summary="Usuń użytkownika [administrator]")
async def delete_user(user_id: int, db: db_dependency, current_user: models.User = Depends(require_admin)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Nie możesz usunąć samego siebie")
    db.delete(db_user)
    db.commit()

# ---------------------------------------------------------------------------
# PRZEDMIOTY (administrator dodaje/usuwa; student i nauczyciel przeglądają)
# ---------------------------------------------------------------------------

@app.post("/items/", status_code=status.HTTP_201_CREATED, response_model=ItemRead,
          tags=["Przedmioty"], summary="Dodaj przedmiot [administrator]")
async def create_item(item: ItemCreate, db: db_dependency, current_user: models.User = Depends(require_admin)):
    db_item = models.Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    # Utwórz domyślny wpis w tabeli loans (status: dostepny)
    db_loan = models.Loan(item_id=db_item.id, status=ItemStatus.dostepny, user_id=None)
    db.add(db_loan)
    db.commit()
    return db_item

@app.get("/items/", response_model=list[ItemRead],
         tags=["Przedmioty"], summary="Lista wszystkich przedmiotów [wszyscy]")
async def list_items(db: db_dependency):
    return db.query(models.Item).all()

@app.get("/items/{item_id}", response_model=ItemRead,
         tags=["Przedmioty"], summary="Pobierz przedmiot [wszyscy]")
async def read_item(item_id: int, db: db_dependency):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")
    return item

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT,
            tags=["Przedmioty"], summary="Usuń przedmiot [administrator]")
async def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")

    db_loan = db.query(models.Loan).filter(models.Loan.item_id == item_id).first()
    if db_loan:
        db.delete(db_loan)

    db.delete(db_item)
    db.commit()

# ---------------------------------------------------------------------------
# DOSTĘPNOŚĆ — podgląd statusu (student)
# ---------------------------------------------------------------------------

@app.get("/items/{item_id}/status", response_model=AvailabilityRead,
         tags=["Dostępność"], summary="Sprawdź status przedmiotu [wszyscy]")
async def get_item_status(item_id: int, db: db_dependency):
    loan = db.query(models.Loan).filter(models.Loan.item_id == item_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Brak rekordu dostępności dla tego przedmiotu")
    return loan

@app.get("/availability/", response_model=list[AvailabilityRead],
         tags=["Dostępność"], summary="Lista dostępności [wszyscy]")
async def list_availability(db: Session = Depends(get_db)):
    loans = db.query(models.Loan).all()

    result = []
    for loan in loans:
        result.append(AvailabilityRead(
            id=loan.id,
            item_id=loan.item_id,
            item_name=loan.item.nazwa if loan.item else None,
            status=loan.status
        ))

    return result
# ---------------------------------------------------------------------------
# DOSTĘPNOŚĆ — podgląd statusu (administrator i nauczyciel)
# ---------------------------------------------------------------------------
@app.get("/availability/details/", response_model=list[LoanRead],
         tags=["Dostępność"], summary="Lista statusów z użytkownikami [nauczyciel/admin]")
async def list_availability_details(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    loans = db.query(models.Loan).all()

    result = []
    for loan in loans:
        result.append(LoanRead(
            id=loan.id,
            item_id=loan.item_id,
            item_name=loan.item.nazwa,
            status=loan.status,
            user_id=loan.user_id
        ))

    return result
# ---------------------------------------------------------------------------
# WYPOŻYCZENIA — akcje według ról
# ---------------------------------------------------------------------------

@app.post("/loans/request/", status_code=status.HTTP_201_CREATED, response_model=LoanRead,
          tags=["Wypożyczenia"], summary="Złóż wniosek o wypożyczenie [student]")
async def request_loan(req: LoanRequest, db: db_dependency, current_user: models.User = Depends(require_student)):
    """Student rezerwuje przedmiot — status zmienia się na 'zarezerwowany'."""
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

@app.post("/loans/approve/", response_model=LoanRead,
          tags=["Wypożyczenia"], summary="Zatwierdź wniosek studenta [nauczyciel]")
async def approve_loan(req: LoanApprove, db: db_dependency, current_user: models.User = Depends(require_teacher)):
    """Nauczyciel zatwierdza rezerwację — status zmienia się na 'wypozyczony'."""
    loan = db.query(models.Loan).filter(models.Loan.id == req.loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Wniosek nie znaleziony")
    if loan.status.value != ItemStatus.zarezerwowany.value:
        raise HTTPException(status_code=400, detail="Można zatwierdzić tylko wnioski ze statusem 'zarezerwowany'")
    loan.status = ItemStatus.wypozyczony
    
    history = models.LoanHistory(
        item_id=loan.item_id,
        user_id=loan.user_id,
        approved_by_id=current_user.id)   
    
    loan.status = ItemStatus.wypozyczony
    
    db.add(history)
    db.commit()
    db.refresh(loan)
    return loan

@app.post("/loans/teacher/", status_code=status.HTTP_201_CREATED, response_model=LoanRead,
          tags=["Wypożyczenia"], summary="Wypożycz sprzęt (nauczyciel, bez autoryzacji) [nauczyciel]")
async def teacher_loan(req: TeacherLoan, db: db_dependency,current_user: models.User = Depends(require_teacher)):
    """Nauczyciel wypożycza przedmiot bezpośrednio — pomija etap rezerwacji."""
    loan = db.query(models.Loan).filter(models.Loan.item_id == req.item_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Przedmiot nie znaleziony")
    if loan.status.value != ItemStatus.dostepny.value:
        raise HTTPException(status_code=400, detail=f"Przedmiot jest obecnie: {loan.status}")
    loan.status = ItemStatus.wypozyczony
    loan.user_id = current_user.id
    history = models.LoanHistory(item_id=loan.item_id, user_id=current_user.id, approved_by_id=current_user.id)

    db.add(history)
    db.commit()
    db.refresh(loan)
    return loan

@app.post("/loans/return/", response_model=LoanRead,
          tags=["Wypożyczenia"], summary="Oznacz przedmiot jako zwrócony [nauczyciel]")
async def return_loan(req: LoanReturn, db: db_dependency, current_user: models.User = Depends(require_teacher)):
    """Nauczyciel oznacza przedmiot jako zwrócony — status wraca do 'dostepny'."""
    loan = db.query(models.Loan).filter(models.Loan.id == req.loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Wniosek nie znaleziony")
    if loan.status.value == ItemStatus.dostepny.value:
        raise HTTPException(status_code=400, detail="Przedmiot jest już dostępny")
    
    history = db.query(models.LoanHistory).filter(
        models.LoanHistory.item_id == loan.item_id,
        models.LoanHistory.user_id == loan.user_id,
        models.LoanHistory.returned_at == None).order_by(models.LoanHistory.borrowed_at.desc()).first()

    if history:
        history.returned_at = datetime.utcnow()
        history.returned_by_id = current_user.id
        loan.status = ItemStatus.dostepny
        loan.user_id = None
    
    db.commit()
    db.refresh(loan)
    return loan

@app.get("/loans/history/", tags=["Historia"], summary="Historia wypożyczeń [nauczyciel/admin]")
async def loan_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher)
):
    return db.query(models.LoanHistory).all()

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")