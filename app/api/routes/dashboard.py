from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.financial_record import FinancialRecord, RecordType
from app.models.user import UserRole
from app.schemas.dashboard import CategoryTotal, DashboardSummary, TrendPoint
from app.schemas.record import FinancialRecordRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
read_roles = [UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN]


@router.get(
    "/summary",
    response_model=DashboardSummary,
    dependencies=[Depends(require_roles(*read_roles))],
)
def get_summary(
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> DashboardSummary:
    filters = [FinancialRecord.is_deleted.is_(False)]
    if start_date:
        filters.append(FinancialRecord.record_date >= start_date)
    if end_date:
        filters.append(FinancialRecord.record_date <= end_date)

    sums = list(
        db.execute(
            select(
                FinancialRecord.record_type,
                func.coalesce(func.sum(FinancialRecord.amount), 0),
            )
            .where(*filters)
            .group_by(FinancialRecord.record_type)
        ).all()
    )

    total_income = Decimal("0")
    total_expenses = Decimal("0")
    for record_type, total in sums:
        if record_type == RecordType.INCOME:
            total_income = Decimal(total)
        else:
            total_expenses = Decimal(total)

    return DashboardSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=total_income - total_expenses,
    )


@router.get(
    "/categories",
    response_model=list[CategoryTotal],
    dependencies=[Depends(require_roles(*read_roles))],
)
def get_category_totals(
    db: Session = Depends(get_db),
    record_type: RecordType | None = Query(default=None),
) -> list[CategoryTotal]:
    filters = [FinancialRecord.is_deleted.is_(False)]
    if record_type:
        filters.append(FinancialRecord.record_type == record_type)

    rows = db.execute(
        select(FinancialRecord.category, func.coalesce(func.sum(FinancialRecord.amount), 0))
        .where(*filters)
        .group_by(FinancialRecord.category)
        .order_by(func.sum(FinancialRecord.amount).desc())
    ).all()

    return [CategoryTotal(category=category, total=Decimal(total)) for category, total in rows]


@router.get(
    "/trends",
    response_model=list[TrendPoint],
    dependencies=[Depends(require_roles(*read_roles))],
)
def get_trends(
    db: Session = Depends(get_db),
    interval: str = Query(default="monthly", pattern="^(monthly|weekly)$"),
) -> list[TrendPoint]:
    period_expr = (
        func.strftime("%Y-%m", FinancialRecord.record_date)
        if interval == "monthly"
        else func.strftime("%Y-W%W", FinancialRecord.record_date)
    )

    rows = db.execute(
        select(
            period_expr.label("period"),
            FinancialRecord.record_type,
            func.coalesce(func.sum(FinancialRecord.amount), 0).label("total"),
        )
        .where(FinancialRecord.is_deleted.is_(False))
        .group_by("period", FinancialRecord.record_type)
        .order_by("period")
    ).all()

    return [
        TrendPoint(period=period, record_type=record_type, total=Decimal(total))
        for period, record_type, total in rows
    ]


@router.get(
    "/recent",
    response_model=list[FinancialRecordRead],
    dependencies=[Depends(require_roles(*read_roles))],
)
def get_recent_activity(
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[FinancialRecord]:
    return list(
        db.scalars(
            select(FinancialRecord)
            .where(FinancialRecord.is_deleted.is_(False))
            .order_by(FinancialRecord.record_date.desc(), FinancialRecord.id.desc())
            .limit(limit)
        ).all()
    )
