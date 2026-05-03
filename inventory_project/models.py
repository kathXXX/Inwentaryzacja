from sqlalchemy import Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from typing import Optional
import enum


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
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student, nullable=False)

    loans: Mapped[list["Loan"]] = relationship("Loan", back_populates="user")


class Item(Base):
    __tablename__ = 'items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nazwa: Mapped[str] = mapped_column(String(100), nullable=False)
    kategoria: Mapped[str] = mapped_column(String(100), nullable=False)
    lokalizacja: Mapped[str] = mapped_column(String(100), nullable=False)

    loan: Mapped[Optional["Loan"]] = relationship("Loan", back_populates="item", uselist=False)


class Loan(Base):
    __tablename__ = 'loans'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey('items.id'), unique=True)
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus), default=ItemStatus.dostepny)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'), nullable=True)

    item: Mapped["Item"] = relationship("Item", back_populates="loan")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="loans")