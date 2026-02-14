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
    email: EmailStr
    password: str

    phone: Optional[str] = Field(default="")
    first_name: Optional[str] = Field(default="")
    last_name: Optional[str] = Field(default="")
    city: Optional[str] = Field(default="")
    street: Optional[str] = Field(default="")
    state: Optional[str] = Field(default="")
    zip_code: Optional[str] = Field(default="")

class PasswordChangeRequest(BaseModel):
    email:EmailStr

class PasswordChangeRequestVerify(BaseModel):
    email:EmailStr
    code:str
    password:str  

