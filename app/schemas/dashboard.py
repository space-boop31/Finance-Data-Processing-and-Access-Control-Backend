from decimal import Decimal

from pydantic import BaseModel

from app.models.financial_record import RecordType


class DashboardSummary(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_balance: Decimal


class CategoryTotal(BaseModel):
    category: str
    total: Decimal


class TrendPoint(BaseModel):
    period: str
    record_type: RecordType
    total: Decimal
