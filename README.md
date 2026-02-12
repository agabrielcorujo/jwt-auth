# jwt-auth

FastAPI authentication package using JWT access tokens, Redis refresh tokens, and PostgreSQL.

## What Exists In This Repo

```text
jwt_auth/
├── __init__.py
├── auth_routes.py
├── controllers/
│   └── auth_controller.py
├── services/
│   └── auth_services.py
├── schemas/
│   └── auth_schema.py
└── db/
    ├── db.py
    └── redis.py
```

`example_app.py` shows minimal mounting/import usage.

## Install

```bash
pip install git+https://github.com/agabrielcorujo/jwt-auth.git
```

or in `requirements.txt`:

```txt
jwt-auth @ git+https://github.com/agabrielcorujo/jwt-auth.git
```

## Quick Integration

```python
from fastapi import FastAPI
from jwt_auth.auth_routes import router as auth_router

app = FastAPI()
app.include_router(auth_router)
```

Bearer decode helper:

```python
from jwt_auth.services.auth_services import decode_access_token
```

## API Endpoints

Base prefix: `/auth`

1. `POST /auth/register`
2. `POST /auth/login`
3. `POST /auth/refresh`
4. `POST /auth/logout`
5. `PATCH /auth/password-reset-request`
6. `PATCH /auth/validate-password-reset-request`

### Request Schemas

`POST /auth/login`

```json
{
  "email": "user@example.com",
  "password": "plain-text-password"
}
```

`POST /auth/register`

```json
{
  "email": "user@example.com",
  "password": "plain-text-password",
  "phone": "optional, defaults to n/a",
  "first_name": "optional, defaults to n/a",
  "last_name": "optional, defaults to n/a",
  "city": "optional, defaults to n/a",
  "street": "optional, defaults to n/a",
  "state": "optional, defaults to n/a",
  "zip_code": "optional, defaults to n/a"
}
```

`POST /auth/refresh` and `POST /auth/logout`
- No JSON body required for token input.
- They read `refresh_token` from cookie.

`PATCH /auth/password-reset-request`

```json
{
  "email": "user@example.com"
}
```

`PATCH /auth/validate-password-reset-request`

```json
{
  "email": "user@example.com",
  "code": "1234",
  "password": "new-password"
}
```

### Response Shape (Current Behavior)

- Login returns:
  - `access_token`
  - `role`
  - `first_name`
  - `last_name`
  - `status`
- Register returns:
  - `created`
  - `user_id`
- Refresh returns:
  - `access_token`
  - `token_type`
- Logout returns:
  - `status`

## Cookie Behavior

On login, refresh cookie is set with:
- `key="refresh_token"`
- `httponly=True`
- `secure=True`
- `samesite="lax"`
- `path="/auth"`
- `domain=os.getenv("DOMAIN")`

On logout, cookie is deleted with matching `path="/auth"` and `domain=os.getenv("DOMAIN")`.

## Environment Variables

Required for app startup:

```env
DB_HOST=...
DB_PORT=...
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
JWT_KEY=...
```

Redis:

```env
REDIS_URL={redis url from whatever hosted provider you are using (not docker)}
```

If `REDIS_URL` is missing (eg you are using docker), code defaults to `redis://redis:6379`.

Cookie domain (optional):

```env
DOMAIN=.{your domain}.com or whatever
```

Twilio (optional, password reset SMS endpoints):

```env
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE=...
```

## Important Runtime Notes

- DB pool is initialized at import time in `jwt_auth/db/db.py`.
- Redis client is initialized at import time in `jwt_auth/db/redis.py`.
- If DB env vars are missing, DB connection fails, or Redis is unreachable, imports that depend on these modules will fail early.

## Database Schema Requirements

Your PostgreSQL database **must** contain a `users` table with the following schema:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    role TEXT NOT NULL,
    city TEXT NOT NULL,
    street TEXT NOT NULL,
    state TEXT NOT NULL,
    zip_code TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
);
```

Required columns (in this order):
- id - Primary key (UUID, auto-generated with gen_random_uuid())
- email - Unique user email
- password_hash - Hashed password (never plaintext)
- first_name - User's first name
- last_name - User's last name
- phone - User's phone number
- role - Application role (e.g. user, admin)
- city - City
- street - Street address
- state - State
- zip_code - ZIP / postal code
- created_at - Account creation timestamp

