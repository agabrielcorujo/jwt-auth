"""
user_auth.py

Authentication and user management utilities.

This module handles:
- Password hashing and verification
- Pydantic request schemas for login and registration
- Database helpers for user lookup and creation

All database interactions are performed through the `safe_query`
helper to ensure pooled connections and parameterized queries.
"""

from passlib.context import CryptContext
from jwt_auth.db import safe_query
from pydantic import BaseModel, EmailStr


# ------------------------------------------------------------------------------
# Password hashing configuration
# ------------------------------------------------------------------------------

"""
Password hashing context using Argon2.

- Argon2 is a memory-hard hashing algorithm suitable for password storage
- `deprecated="auto"` allows future algorithm upgrades if needed
"""
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)


# ------------------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """
    Schema for user login requests.

    Attributes:
        email (EmailStr): User email address
        password (str): Plaintext password submitted by the user
    """
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    """
    Schema for user registration requests.

    Attributes:
        email (str): User email address
        password (str): Plaintext password to be hashed and stored
        first_name (str): User's first name
        last_name (str): User's last name
    """
    email: str
    phone: str
    password: str
    first_name: str
    last_name: str
    city: str
    street: str
    state: str
    zip_code: str

class AuthValidationError(Exception):
    """Raised when auth input is invalid."""

class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user with an existing email."""

class DatabaseOperationError(Exception):
    """Raised when a database operation fails unexpectedly."""

class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""
    
# ------------------------------------------------------------------------------
# Password utilities
# ------------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using Argon2.

    Args:
        password (str): Plaintext password

    Returns:
        str: Securely hashed password

    Raises:
        ValueError: If the password is empty or None
    """
    if not password:
        raise AuthValidationError("Password cannot be empty")

    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Args:
        password (str): Plaintext password provided by the user
        hashed_password (str): Stored password hash from the database

    Returns:
        bool: True if the password matches the hash, False otherwise

    Raises:
        ValueError: If either argument is missing
    """
    if not password or not hashed_password:
        raise AuthValidationError("Password verification inputs missing")

    return pwd_context.verify(password, hashed_password)


# ------------------------------------------------------------------------------
# Database helpers
# ------------------------------------------------------------------------------

def check_user_by_email(email: str) -> dict | None:
    """
    Retrieve a user record by email address.

    Args:
        email (str): Email address to search for

    Returns:
        dict | None:
            - Dictionary containing user fields if found
            - None if no user exists with the given email
    """
    result = safe_query(
        "SELECT id,email,password_hash,first_name,last_name,phone,role FROM users WHERE email = %s",
        (email,),
        fetch="one"
    )

    if result:
        user = {
            "id": result[0],
            "email": result[1],
            "pass_hash": result[2],
            "first_name": result[3],
            "last_name": result[4],
            "phone":result[5],
            "role":result[6]
        }
        return user

    return None


def create_user(credentials: RegisterRequest) -> dict:
    """
    Create a new user in the database if the email does not already exist.

    This function:
    - Hashes the user's password
    - Inserts a new row into the users table
    - Uses ON CONFLICT to prevent duplicate emails
    - Returns the created user's ID if successful

    Args:
        credentials (RegisterRequest): Validated registration data

    Returns:
        dict:
            - created (bool): Whether the user was successfully created
            - user_id (str | None): UUID of the created user, if applicable
    """

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
    zip_code
    )
    VALUES (%s, %s, %s, %s, %s, NOW(),'client',%s,%s,%s,%s)
    ON CONFLICT (email) DO NOTHING
    RETURNING id;
    """

    try:

        row = safe_query(
            query,
            (
                credentials.email,
                credentials.phone,
                hash_password(credentials.password),
                credentials.first_name,
                credentials.last_name,
                credentials.street,
                credentials.city,
                credentials.state,
                credentials.zip_code,
            ),
            fetch="one",
            insert=True
        )

    except Exception as e:
        # this should be logged, not printed
        raise DatabaseOperationError("Failed to create user") from e

    if not row:
        raise UserAlreadyExistsError("User with this email already exists")
    
    return {
        "created": True,
        "user_id": row[0],
    }

