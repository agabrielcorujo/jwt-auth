from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from fastapi import Cookie

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
    email: str
    password: str

    phone: Optional[str] = Field(default="n/a")
    first_name: Optional[str] = Field(default="n/a")
    last_name: Optional[str] = Field(default="n/a")
    city: Optional[str] = Field(default="n/a")
    street: Optional[str] = Field(default="n/a")
    state: Optional[str] = Field(default="n/a")
    zip_code: Optional[str] = Field(default="n/a")

class PasswordChangeRequest(BaseModel):
    email:EmailStr

class PasswordChangeRequestVerify(BaseModel):
    email:EmailStr
    code:str
    password:str  

