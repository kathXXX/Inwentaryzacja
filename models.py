from sqlalchemy import Integer, String, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from typing import Optional
import enum
from datetime import datetime

class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    student = "student"
    nauczyciel = "nauczyciel"
    administrator = "administrator"


class ItemStatus(str, enum.Enum):
    dostepny = "dostepny"
    wypozyczony = "wypozyczony"
    zarezerwowany = "zarezerwowany"


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activation_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    activation_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student, nullable=False)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # tylko student
    field_of_study: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    student_index: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # tylko nauczyciel
    department: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    loans: Mapped[list["Loan"]] = relationship("Loan", back_populates="user", foreign_keys="Loan.user_id")
    loan_history: Mapped[list["LoanHistory"]] = relationship("LoanHistory", back_populates="user", foreign_keys="LoanHistory.user_id")


class LoginCode(Base):
    __tablename__ = "login_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    challenge_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    items: Mapped[list["Item"]] = relationship("Item", back_populates="location")


class Item(Base):
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nazwa: Mapped[str] = mapped_column(String(100), nullable=False)
    kategoria: Mapped[str] = mapped_column(String(100), nullable=False)
    lokalizacja: Mapped[str] = mapped_column(String(100), nullable=False)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id"), nullable=True)
    qr_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="items")
    loan: Mapped[Optional["Loan"]] = relationship("Loan", back_populates="item", uselist=False)


class Loan(Base):
    __tablename__ = 'loans'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey('items.id'), unique=True)
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus), default=ItemStatus.dostepny)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    due_reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    item: Mapped["Item"] = relationship("Item", back_populates="loan")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="loans", foreign_keys=[user_id])


class LoanHistory(Base):
    __tablename__ = "loan_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    borrowed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    approved_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    returned_by_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    item: Mapped["Item"] = relationship("Item")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
