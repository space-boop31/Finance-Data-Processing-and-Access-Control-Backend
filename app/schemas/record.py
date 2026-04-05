from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.financial_record import RecordType


class FinancialRecordBase(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    record_type: RecordType
    category: str = Field(min_length=2, max_length=100)
    record_date: date
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return value.strip()


class FinancialRecordCreate(FinancialRecordBase):
    pass


class FinancialRecordUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    record_type: RecordType | None = None
    category: str | None = Field(default=None, min_length=2, max_length=100)
    record_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class FinancialRecordRead(BaseModel):
    id: int
    amount: Decimal
    record_type: RecordType
    category: str
    record_date: date
    notes: str | None
    created_by: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FinancialRecordListResponse(BaseModel):
    total: int
    items: list[FinancialRecordRead]
