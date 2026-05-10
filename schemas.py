from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models import ItemStatus, UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.student

    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)

    email: Optional[str] = None
    phone: Optional[str] = None
    field_of_study: Optional[str] = None
    student_index: Optional[str] = None
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

    class Config:
        from_attributes = True


class ItemCreate(BaseModel):
    nazwa: str
    kategoria: str
    lokalizacja: str


class ItemRead(BaseModel):
    id: int
    nazwa: str
    kategoria: str
    lokalizacja: str
    qr_code: str

    class Config:
        from_attributes = True


class ItemQrRead(BaseModel):
    item_id: int
    nazwa: str
    kategoria: str
    lokalizacja: str
    qr_code: str
    loan_id: Optional[int]
    status: ItemStatus
    user_id: Optional[int] = None


class LoanRead(BaseModel):
    id: int
    item_id: int
    item_name: Optional[str] = None
    status: ItemStatus
    user_id: Optional[int]

    class Config:
        from_attributes = True


class LoanRequest(BaseModel):
    item_id: int


class LoanApprove(BaseModel):
    loan_id: int


class LoanReturn(BaseModel):
    loan_id: int


class TeacherLoan(BaseModel):
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


class LoanHistoryRead(BaseModel):
    id: int
    item_id: int
    user_id: int
    borrowed_at: datetime
    returned_at: Optional[datetime]
    approved_by_id: Optional[int]
    returned_by_id: Optional[int]

    class Config:
        from_attributes = True
