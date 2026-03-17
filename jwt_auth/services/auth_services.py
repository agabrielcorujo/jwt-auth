import asyncio
import logging
import os
import random,resend
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict

from passlib.context import CryptContext
from twilio.rest import Client

from jwt_auth.db.db import DBError, safe_query
from jwt_auth.db.redis import cache

resend.api_key = os.getenv("RESEND_API_KEY")

class AuthError(Exception):
    def __init__(self, message: str, status_code: int):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

logging.basicConfig(
    level=logging.INFO,  # minimum level to log
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)

JWT_KEY = os.getenv("JWT_KEY")

if not JWT_KEY:
    raise AuthError("Server Configuration Error", 500)

REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 14

def create_access_token(user_id: str, role: str) -> str:

    payload: Dict = {
        "sub": user_id,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "type": "access",
    }

    return jwt.encode(payload, JWT_KEY, algorithm="HS256")

def decode_access_token(token: str, role: bool = False) -> str:

    try:

        payload = jwt.decode(
            token,
            JWT_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
  
    except jwt.ExpiredSignatureError:
        raise AuthError("Expired access token", 401)

    except jwt.InvalidTokenError:
        raise AuthError("Invalid access token", 401)
    
    user_id = payload.get("sub")
    user_role = payload.get("role")

    if not user_id or not user_role:
        raise AuthError("Invalid access token", 401)

    if role:
        return user_role

    return user_id

def create_refresh_token() -> str:

    return secrets.token_urlsafe(32)

async def store_refresh_token(refresh_token: str, user_id: str) -> None:
    await cache.setex(f"refresh:{refresh_token}", REFRESH_TOKEN_TTL_SECONDS, user_id)


async def check_user_by_email(email: str) -> dict | None:
    query = "SELECT id, email, password_hash, first_name, last_name, phone, role, twofa FROM users WHERE email = $1"

    try:
        result = await safe_query(query, (email,), fetch="one")

    except DBError as error:
        raise AuthError(message=error.message, status_code=error.status_code)

    if not result:
        return None

    user = {
        "id": result[0],
        "email": result[1],
        "pass_hash": result[2],
        "first_name": result[3],
        "last_name": result[4],
        "phone": result[5],
        "role": result[6],
        "twofa":result[7],
    }

    return user

async def create_user(email, phone, password, firstname, lastname, street, city, state, zipcode,twofa):

    query = """
                INSERT INTO users (
                email,
                phone,
                password_hash,
                first_name,
                last_name,
                created_at,
                role,
                street,
                city,
                state,
                zip_code,
                twofa
                )
                VALUES ($1, $2, $3, $4, $5, NOW(), 'client', $6, $7, $8, $9,$10)
                ON CONFLICT (email) DO NOTHING
                RETURNING id;
                """
    try:
        result = await safe_query(
            query,
            (
                email,
                phone,
                pwd_context.hash(password),
                firstname,
                lastname,
                street,
                city,
                state,
                zipcode,
                twofa
            ),
            fetch="one"
        )

    except DBError as error:
        raise AuthError(message=error.message, status_code=error.status_code)


    if not result:
        raise AuthError("User already exists", 409)

    return {
        "created": True,
        "user_id": result[0],
    }

async def change_password_request(email: str,project:str) -> dict:

    user = await check_user_by_email(email)

    if not user:
        return {}

    code = random.randint(100000, 999999)

    try:

        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": os.getenv("RESEND_FROM_EMAIL"),
                "to": email,
                "subject": f"{project} Password Reset Code",
                "html": f"""
                        <h2>Password Reset</h2>
                        <p>Your {project} password reset code is:</p>
                        <h1>{code}</h1>
                        <p>This code expires in 2 minutes.</p>
                        """
            }
        )

        await cache.setex(f"{email}:pass_reset_code", 120, str(code))

    except Exception as e:
        logger.error(f"Error sending reset email: {e}")
        return {}

    return {
        "status": "sent"
    }

async def validate_password_change_request(code: str, email: str, password: str):

    cached_code = await cache.get(f"{email}:pass_reset_code")

    if not cached_code or cached_code != code:
        return {}

    pass_hash = pwd_context.hash(password)

    query = """
    UPDATE users
    SET password_hash = $1
    WHERE email = $2
    RETURNING id
    """

    try:
        result = await safe_query(query, (pass_hash, email), fetch="one")

    except DBError as error:
        raise AuthError(message=error.message, status_code=error.status_code)

    if not result:
        return {}

    # remove code so it can't be reused
    await cache.delete(f"{email}:pass_reset_code")

    return {"status": "password_changed"}

async def remove_from_cache(item: str):
    return await cache.delete(item)

async def refresh(refresh_token: str):

    user_id = await cache.get(f"refresh:{refresh_token}")

    if not user_id:

        raise AuthError("Authentication required", 401)

    try:
        row = await safe_query("SELECT role FROM users WHERE id = $1", (user_id,), fetch="one")
        if not row:
            raise AuthError("Authentication required", 401)
        role = row[0]

    except DBError as error:
        raise AuthError(error.message, error.status_code)

    access_token = create_access_token(user_id,role)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

async def create_twofa_attempt(email:str):
    project = os.getenv("PROJECT_NAME", "Project")
    code = random.randint(100000, 999999)
    
    try:

        await asyncio.to_thread(                                                                                                                                              
            resend.Emails.send,
            {
                "from": os.getenv("RESEND_FROM_EMAIL"),
                "to": email,
                "subject": f"{project} 2 Factor Authentication Code",
                "html": f"""
                        <h2>2FA</h2>
                        <p>Your {project} login verification code is:</p>
                        <h1>{code}</h1>
                        <p>This code expires in 2 minutes.</p>
                        """
            }
        )

        await cache.setex(f"{email}:twofa_code", 120, str(code))

    except Exception as e:
        logger.error(f"Error sending twofa code email: {e}")
        raise AuthError("Unable to send verification code", 500)

    return {"status":"code sent to email"}

async def validate_twofa_attempt(email:str,code:str):
    cached_code = await cache.get(f"{email}:twofa_code")
    
    if not cached_code:
        raise AuthError(message = "Expired or invalid code entered",status_code = 401)

    if cached_code != code:
        await cache.delete(f"{email}:twofa_code")

        raise AuthError(message = "Invalid code entered",status_code = 401)

    await cache.delete(f"{email}:twofa_code")

    return {"status":"verified"}











