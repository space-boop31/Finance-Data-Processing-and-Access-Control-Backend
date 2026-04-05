from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.session import Base, get_db
from app.main import app
from app.models.user import User, UserRole


def _build_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session_local


def _create_user(session_local: sessionmaker, username: str, password: str, role: UserRole) -> None:
    db = session_local()
    db.add(
        User(
            username=username,
            full_name=username.title(),
            hashed_password=get_password_hash(password),
            role=role,
            is_active=True,
        )
    )
    db.commit()
    db.close()


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_auth_login_success() -> None:
    client, session_local = _build_client()
    _create_user(session_local, "admin", "adminpass", UserRole.ADMIN)

    token = _login(client, "admin", "adminpass")
    assert token

    app.dependency_overrides.clear()


def test_viewer_cannot_create_record() -> None:
    client, session_local = _build_client()
    _create_user(session_local, "viewer1", "viewerpass", UserRole.VIEWER)
    token = _login(client, "viewer1", "viewerpass")

    response = client.post(
        "/records",
        json={
            "amount": "1200.50",
            "record_type": "income",
            "category": "Salary",
            "record_date": "2026-04-01",
            "notes": "Monthly salary",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403

    app.dependency_overrides.clear()


def test_admin_records_and_dashboard_summary() -> None:
    client, session_local = _build_client()
    _create_user(session_local, "admin2", "adminpass", UserRole.ADMIN)
    token = _login(client, "admin2", "adminpass")
    headers = {"Authorization": f"Bearer {token}"}

    income_response = client.post(
        "/records",
        json={
            "amount": "1000.00",
            "record_type": "income",
            "category": "Salary",
            "record_date": "2026-04-01",
            "notes": "Salary credit",
        },
        headers=headers,
    )
    assert income_response.status_code == 201

    expense_response = client.post(
        "/records",
        json={
            "amount": "250.00",
            "record_type": "expense",
            "category": "Food",
            "record_date": "2026-04-02",
            "notes": "Groceries",
        },
        headers=headers,
    )
    assert expense_response.status_code == 201

    list_response = client.get("/records", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 2

    summary_response = client.get("/dashboard/summary", headers=headers)
    assert summary_response.status_code == 200
    body = summary_response.json()
    assert float(body["total_income"]) == 1000.0
    assert float(body["total_expenses"]) == 250.0
    assert float(body["net_balance"]) == 750.0

    app.dependency_overrides.clear()
