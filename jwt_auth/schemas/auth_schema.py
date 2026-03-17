from typing import Optional
import re
from pydantic import BaseModel, EmailStr, Field, field_validator
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
    twofa: Optional[str] = None

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
    twofa: Optional[bool] = Field(default=False)

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v):
        if not v:
            return v
            
        digits = re.sub(r"\D", "", v)

        # Remove leading 1 if it's a US number (11 digits total)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]

        return digits

class PasswordChangeRequest(BaseModel):
    email:EmailStr

class PasswordChangeRequestVerify(BaseModel):
    email:EmailStr
    code:str
    password:str  

