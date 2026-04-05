# Finance Backend (FastAPI + SQLite)

Role-based backend for a finance dashboard with JWT auth, record management, and summary analytics.

## Tech Stack

- FastAPI
- SQLite + SQLAlchemy
- JWT (`python-jose`)
- Password hashing (`passlib[bcrypt]`)

## Project Layout

```text
finance-backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    main.py
  tests/
  requirements.txt
```

## Setup

1. Create virtual environment and install dependencies:
   - `pip install -r requirements.txt`
2. Optional environment variables (`.env`):
   - `DATABASE_URL=sqlite:///./finance.db`
   - `JWT_SECRET_KEY=replace-me`
   - `ACCESS_TOKEN_EXPIRE_MINUTES=60`
   - `DEFAULT_ADMIN_USERNAME=admin`
   - `DEFAULT_ADMIN_PASSWORD=admin123`
3. Run API (manual by you):
   - `uvicorn app.main:app --reload`

FastAPI docs:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Default Roles

- `viewer`: read records + dashboard
- `analyst`: read records + dashboard
- `admin`: full user and record management

## Access Matrix

- `POST /auth/login` -> public
- `GET /users/me` -> authenticated user
- `POST /users`, `GET /users`, `PATCH /users/{id}` -> admin
- `GET /records`, `GET /records/{id}` -> viewer/analyst/admin
- `POST /records`, `PUT /records/{id}`, `DELETE /records/{id}` -> admin
- `GET /dashboard/*` -> viewer/analyst/admin

## Example cURL

Login:

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Create record (admin token required):

```bash
curl -X POST "http://127.0.0.1:8000/records" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "1499.00",
    "record_type": "income",
    "category": "Salary",
    "record_date": "2026-04-01",
    "notes": "Monthly salary"
  }'
```

Dashboard summary:

```bash
curl -X GET "http://127.0.0.1:8000/dashboard/summary" \
  -H "Authorization: Bearer <TOKEN>"
```

## Filtering and Pagination

`GET /records` supports:
- `start_date`, `end_date`
- `category`
- `record_type` (`income` or `expense`)
- `search` (category or notes)
- `limit` and `offset`

## Notes

- Soft delete is enabled for records (`is_deleted`).
- Database tables and default admin user are created on startup.
- Change `DEFAULT_ADMIN_PASSWORD` immediately in non-local usage.
