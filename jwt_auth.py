"""
jwt_auth.py

JWT authentication utilities for access and refresh token handling.

This module:
- Creates and validates short-lived JWT access tokens
- Generates cryptographically secure refresh tokens
- Stores and retrieves refresh tokens using Redis
- Raises FastAPI-compatible HTTP exceptions on auth failure

Access tokens are stateless JWTs.
Refresh tokens are stateful and stored server-side in Redis.
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict
from fastapi import HTTPException, status
import secrets
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

"""
Secret key used to sign and verify JWTs.
This value must remain private and consistent across services.
"""
JWT_KEY = os.getenv("JWT_KEY")

"""
Access token lifetime in minutes.
Short-lived tokens reduce blast radius if compromised.
"""
ACCESS_TOKEN_EXPIRE_MINUTES = 15

"""
Refresh token time-to-live (TTL) in seconds.
Current value: 14 days.
"""
REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 14


# ------------------------------------------------------------------------------
# Access token helpers
# ------------------------------------------------------------------------------

def create_access_token(user_id: str) -> str:
    """
    Create a signed JWT access token for a user.

    The token payload includes:
    - sub: user identifier
    - iat: issued-at timestamp
    - exp: expiration timestamp
    - type: token type ("access")

    Args:
        user_id (str): Unique identifier for the authenticated user

    Returns:
        str: Encoded JWT access token
    """
    payload: Dict = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access"
    }

    return jwt.encode(payload, JWT_KEY, algorithm="HS256")


def decode_access_token(token: str) -> str:
    """
    Decode and validate a JWT access token.

    This function:
    - Verifies the token signature
    - Verifies expiration
    - Extracts and returns the user ID

    Args:
        token (str): Encoded JWT access token

    Returns:
        str: User ID extracted from the token

    Raises:
        HTTPException:
            - 401 if the token is expired
            - 401 if the token is invalid or malformed
    """
    try:
        payload = jwt.decode(
            token,
            JWT_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token"
            )

        return user_id

    except jwt.ExpiredSignatureError:
        # Frontend uses this signal to trigger refresh flow
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )


# ------------------------------------------------------------------------------
# Refresh token helpers
# ------------------------------------------------------------------------------

def create_refresh_token() -> str:
    """
    Generate a cryptographically secure refresh token.

    Refresh tokens are opaque, random strings and are not JWTs.

    Returns:
        str: URL-safe refresh token string
    """
    return secrets.token_urlsafe(32)


def store_refresh_token(redis_client, refresh_token: str, user_id: str) -> None:
    """
    Store a refresh token in Redis with an expiration time.

    The token is only stored if it does not already exist.

    Redis key format:
        refresh:<refresh_token> -> user_id

    Args:
        redis_client: Initialized Redis client
        refresh_token (str): Generated refresh token
        user_id (str): User ID associated with the token
    """
    if not redis_client.get(f"refresh:{refresh_token}"):
        redis_client.setex(
            f"refresh:{refresh_token}",
            REFRESH_TOKEN_TTL_SECONDS,
            user_id
        )


def get_id_from_token(redis_client, refresh_token: str) -> str:
    """
    Retrieve a user ID associated with a refresh token.

    Args:
        redis_client: Initialized Redis client
        refresh_token (str): Refresh token provided by the client

    Returns:
        str | None: User ID if the token exists, otherwise None
    """
    return redis_client.get(f"refresh:{refresh_token}")
