from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.financial_record import FinancialRecord, RecordType
from app.models.user import User, UserRole
from app.schemas.record import (
    FinancialRecordCreate,
    FinancialRecordListResponse,
    FinancialRecordRead,
    FinancialRecordUpdate,
)

router = APIRouter(prefix="/records", tags=["records"])
read_roles = [UserRole.VIEWER, UserRole.ANALYST, UserRole.ADMIN]


@router.post(
    "",
    response_model=FinancialRecordRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def create_record(
    payload: FinancialRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialRecord:
    record = FinancialRecord(
        amount=payload.amount,
        record_type=payload.record_type,
        category=payload.category.strip(),
        record_date=payload.record_date,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get(
    "",
    response_model=FinancialRecordListResponse,
    dependencies=[Depends(require_roles(*read_roles))],
)
def list_records(
    db: Session = Depends(get_db),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    category: str | None = Query(default=None),
    record_type: RecordType | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> FinancialRecordListResponse:
    filters = [FinancialRecord.is_deleted.is_(False)]

    if start_date:
        filters.append(FinancialRecord.record_date >= start_date)
    if end_date:
        filters.append(FinancialRecord.record_date <= end_date)
    if category:
        filters.append(FinancialRecord.category == category)
    if record_type:
        filters.append(FinancialRecord.record_type == record_type)
    if search:
        token = f"%{search}%"
        filters.append(
            or_(
                FinancialRecord.category.ilike(token),
                FinancialRecord.notes.ilike(token),
            )
        )

    base_query = select(FinancialRecord).where(and_(*filters))
    count_query = select(func.count()).select_from(FinancialRecord).where(and_(*filters))

    total = db.scalar(count_query) or 0
    items = list(
        db.scalars(
            base_query.order_by(FinancialRecord.record_date.desc(), FinancialRecord.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return FinancialRecordListResponse(total=total, items=items)


@router.get(
    "/{record_id}",
    response_model=FinancialRecordRead,
    dependencies=[Depends(require_roles(*read_roles))],
)
def get_record(record_id: int, db: Session = Depends(get_db)) -> FinancialRecord:
    record = db.get(FinancialRecord, record_id)
    if record is None or record.is_deleted:
        raise HTTPException(status_code=404, detail="Record not found.")
    return record


@router.put(
    "/{record_id}",
    response_model=FinancialRecordRead,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def update_record(record_id: int, payload: FinancialRecordUpdate, db: Session = Depends(get_db)) -> FinancialRecord:
    record = db.get(FinancialRecord, record_id)
    if record is None or record.is_deleted:
        raise HTTPException(status_code=404, detail="Record not found.")

    updates = payload.model_dump(exclude_unset=True)
    if "category" in updates and updates["category"] is not None:
        updates["category"] = updates["category"].strip()

    for field, value in updates.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def delete_record(record_id: int, db: Session = Depends(get_db)) -> None:
    record = db.get(FinancialRecord, record_id)
    if record is None or record.is_deleted:
        raise HTTPException(status_code=404, detail="Record not found.")
    record.is_deleted = True
    db.commit()
