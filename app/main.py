from fastapi import FastAPI
from sqlalchemy import select

from app.api.router import api_router
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import Base, SessionLocal, engine
from app.models.user import User, UserRole

app = FastAPI(title=settings.APP_NAME)
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_default_admin()


def seed_default_admin() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.username == settings.DEFAULT_ADMIN_USERNAME))
        if existing:
            return
        admin = User(
            username=settings.DEFAULT_ADMIN_USERNAME,
            full_name="System Admin",
            hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()
