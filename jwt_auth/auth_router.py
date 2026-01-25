"""
auth_router.py

FastAPI router responsible for authentication-related endpoints.

This module exposes routes for:
- User login
- User registration
- Logout
- Access token refresh

Authentication design:
- Access tokens are short-lived JWTs returned in responses
- Refresh tokens are long-lived, stored in Redis, and sent via HttpOnly cookies
"""

from fastapi import APIRouter, HTTPException, Response, Cookie

from jwt_auth.jwt_auth import (
    create_access_token,
    create_refresh_token,
    store_refresh_token,
    get_id_from_token,
)

from jwt_auth.user_auth import (
    verify_password,
    check_user_by_email,
    LoginRequest,
    RegisterRequest,
    create_user,
    UserAlreadyExistsError,
    DatabaseOperationError,
    InvalidCredentialsError
)

from jwt_auth.redis_server.client import cache

from jwt_auth.db import safe_query


# ------------------------------------------------------------------------------
# Router configuration
# ------------------------------------------------------------------------------

"""
Authentication router mounted under the /auth prefix.
"""
router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


# ------------------------------------------------------------------------------
# Login endpoint
# ------------------------------------------------------------------------------

@router.post("/login")
def login(credentials: LoginRequest, response: Response):
    """
    Authenticate a user and issue access + refresh tokens.

    Flow:
    1. Look up user by email
    2. Verify password against stored hash
    3. Issue a short-lived JWT access token
    4. Generate and store a refresh token in Redis
    5. Send refresh token as an HttpOnly cookie

    Args:
        credentials (LoginRequest): Validated login credentials
        response (Response): FastAPI response object used to set cookies

    Returns:
        dict: Access token and basic user metadata

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    try:
        user = check_user_by_email(credentials.email)

        if not user or not verify_password(credentials.password, user["pass_hash"]):
            raise InvalidCredentialsError()
        
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(user["id"],user["role"])
    refresh_token = create_refresh_token()

    store_refresh_token(cache, refresh_token, user["id"])

    # Store refresh token as an HttpOnly cookie to prevent JS access
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/auth"
    )

    return {
        "access_token": access_token,
        "role":user["role"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "status": "logged in"
    }


# ------------------------------------------------------------------------------
# Registration endpoint
# ------------------------------------------------------------------------------

@router.post("/register")
def register(credentials: RegisterRequest):
    """
    Register a new user account.

    Flow:
    - Hash password
    - Insert user into database
    - Reject duplicate email addresses

    Args:
        credentials (RegisterRequest): Validated registration data

    Returns:
        dict: Confirmation message

    Raises:
        HTTPException: 409 if the user already exists
    """
    try: 
        result = create_user(credentials)
    
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )
    
    except DatabaseOperationError:
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

    return {"status": "user created"}


# ------------------------------------------------------------------------------
# Logout endpoint
# ------------------------------------------------------------------------------

@router.post("/logout")
def logout(response: Response, refresh_token: str = Cookie(None)):
    """
    Log out the current user by invalidating their refresh token.

    Flow:
    - Delete refresh token from Redis
    - Remove refresh token cookie from the client

    Args:
        response (Response): FastAPI response object
        refresh_token (str, optional): Refresh token from HttpOnly cookie

    Returns:
        dict: Logout confirmation message
    """
    if refresh_token:
        cache.delete(f"refresh:{refresh_token}")
        response.delete_cookie("refresh_token")

    return {"status": "logged out"}


# ------------------------------------------------------------------------------
# Refresh endpoint
# ------------------------------------------------------------------------------

@router.post("/refresh")
def refresh(refresh_token: str = Cookie(None)):
    """
    Issue a new access token using a valid refresh token.

    Flow:
    - Read refresh token from HttpOnly cookie
    - Validate token against Redis
    - Issue a new JWT access token

    Args:
        refresh_token (str, optional): Refresh token from HttpOnly cookie

    Returns:
        dict: New access token and token type

    Raises:
        HTTPException:
            - 401 if refresh token is missing
            - 401 if refresh token is invalid or expired
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_id = get_id_from_token(cache, refresh_token)

    role = safe_query("SELECT role FROM users where id = %s",(user_id,),fetch="one")

    if not user_id or not role:
        raise HTTPException(status_code=401, detail="Authentication required")

    access_token = create_access_token(user_id,role)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
