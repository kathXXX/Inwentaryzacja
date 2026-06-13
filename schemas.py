from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models import ItemStatus, UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginCodeRead(BaseModel):
    challenge_id: str
    message: str
    email: Optional[str] = None
    expires_in_seconds: int
    dev_code: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ActivationCodeRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    code: str = Field(min_length=4, max_length=12)


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


class ItemBulkCreate(BaseModel):
    names: list[str] = Field(min_length=1, max_length=100)
    kategoria: str = Field(min_length=1, max_length=100)
    lokalizacja: str = Field(min_length=1, max_length=100)


class LocationRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    items_count: int = 0


class ItemRead(BaseModel):
    id: int
    nazwa: str
    kategoria: str
    lokalizacja: str
    location_id: Optional[int] = None
    qr_code: str

    class Config:
        from_attributes = True


class ItemQrRead(BaseModel):
    item_id: int
    nazwa: str
    kategoria: str
    lokalizacja: str
    location_id: Optional[int] = None
    qr_code: str
    loan_id: Optional[int]
    status: ItemStatus
    user_id: Optional[int] = None
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None


class LoanRead(BaseModel):
    id: int
    item_id: int
    item_name: Optional[str] = None
    status: ItemStatus
    user_id: Optional[int]
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoanRequest(BaseModel):
    item_id: int
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None


class LoanApprove(BaseModel):
    loan_id: int
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None


class LoanReturn(BaseModel):
    loan_id: int


class TeacherLoan(BaseModel):
    item_id: int
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None


class TeacherReserveForStudent(BaseModel):
    item_id: int
    user_id: int
    starts_at: Optional[datetime] = None
    due_at: datetime


class AvailabilityRead(BaseModel):
    id: int
    item_id: int
    item_name: Optional[str] = None
    kategoria: Optional[str] = None
    lokalizacja: Optional[str] = None
    status: ItemStatus
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoanHistoryRead(BaseModel):
    id: int
    item_id: int
    user_id: int
    borrowed_at: datetime
    item_name: str | None = None
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime]
    returned_at: Optional[datetime]
    approved_by_id: Optional[int]
    returned_by_id: Optional[int]

    class Config:
        from_attributes = True


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    challenge_id: str
    code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=8, max_length=128)


class LocationInventoryCheckRequest(BaseModel):
    location_id: Optional[int] = None
    location_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    qr_codes: list[str] = Field(default_factory=list, max_length=500)


class InventoryCheckItem(BaseModel):
    item_id: int
    nazwa: str
    kategoria: str
    lokalizacja: str
    location_id: Optional[int] = None
    qr_code: str
    loan_id: Optional[int] = None
    status: ItemStatus
    user_id: Optional[int] = None
    starts_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    scanned: bool = False


class WrongLocationItem(InventoryCheckItem):
    expected_location: str
    checked_location: str
    message: str


class LocationInventoryCheckRead(BaseModel):
    location: LocationRead
    scanned_count: int
    expected_count: int
    present_count: int
    missing_count: int
    wrong_location_count: int
    unknown_codes: list[str]
    present_items: list[InventoryCheckItem]
    missing_items: list[InventoryCheckItem]
    wrong_location_items: list[WrongLocationItem]


class DueReminderRequest(BaseModel):
    days: int = Field(default=1, ge=0, le=30)


class ItemReminderRequest(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=100)


class DueReminderRead(BaseModel):
    sent: int
    skipped: int
