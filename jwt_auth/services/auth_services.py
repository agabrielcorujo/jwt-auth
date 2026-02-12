import jwt
from datetime import datetime, timedelta, timezone
import os
import secrets
from typing import Dict
from jwt_auth.db.db import safe_query,DBError
from jwt_auth.db.redis import cache
from passlib.context import CryptContext
from twilio.rest import Client
import os
import random
import logging

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
    raise AuthError("Server Configuration Error",500)

REFRESH_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 14

def create_access_token(user_id: str,role:str) -> str:

    payload: Dict = {
        "sub": user_id,
        "role":role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "type": "access"
    }

    return jwt.encode(payload, JWT_KEY, algorithm="HS256")

def decode_access_token(token: str,role:bool = False) -> str:

    try:

        payload = jwt.decode(
            token,
            JWT_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
  
    except jwt.ExpiredSignatureError:
        raise AuthError("Expired access token",401)
    
    except jwt.InvalidTokenError:
        raise AuthError("Invalid access token",401)
    
    user_id = payload.get("sub")
    user_role = payload.get("role")

    if not user_id or not user_role:
        raise AuthError("Invalid access token",401)
    
    if role:
        return user_role
        
    return user_id

def create_refresh_token() -> str:

    return secrets.token_urlsafe(32)

def store_refresh_token(refresh_token: str, user_id: str) -> None:

    return cache.setex(f"refresh:{refresh_token}",REFRESH_TOKEN_TTL_SECONDS,user_id,)

def check_user_by_email(email: str) -> dict | None:

    query = "SELECT id,email,password_hash,first_name,last_name,phone,role FROM users WHERE email = %s"

    try:

        result = safe_query(query,(email,),fetch="one")

    except DBError as error:

        raise AuthError(message=error.message,status_code=error.status_code)

    if not result:
        return None
    
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

def create_user(email,phone,password,firstname,lastname,street,city,state,zipcode):
        
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
        result = safe_query(
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
                zipcode
            ),
            fetch="one",
            insert=True
        )

    except DBError as error: 

        raise AuthError(message=error.message,status_code=error.status_code)


    if not result:

        raise AuthError("User already exists",409)
    
    return {
        "created": True,
        "user_id": result[0],
    }

def change_password_request(email:str) -> dict:

    user = check_user_by_email(email)

    if not user:
        return {}

    phone = f'+1{user["phone"]}'

    code = random.randint(1000,10000)

    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )

    try:
        client.messages.create(
            body=f"{code} is your OffClutter Storage code.",
            from_=os.getenv("TWILIO_PHONE"),
            to=phone
        )
        cache.setex(f"{email}:pass_reset_code",120,code)

    except Exception as e:
        logger.error(f"Error in sending twilio message: {e}")
        return {}

    return {
        "status":"sent"
    }

def validate_password_change_request(code:str,email:str,password:str):
    
    cached_code = cache.get(f"{email}:pass_reset_code")

    if not cached_code or cached_code != code:
        return {}
    
    pass_hash = pwd_context.hash(password)

    query = "UPDATE users SET password_hash = %s WHERE email = %s RETURNING id"

    try:

        result = safe_query(query,(pass_hash,email),insert=True,fetch="one")

    except DBError as error:

        raise AuthError(message=error.message,status_code=error.status_code)

    if not result:
        return {}

    return {"status":"password_changed"}

def remove_from_cache(item:str):
    cache.delete(item)

def refresh(refresh_token:str):

    user_id = cache.get(f"refresh:{refresh_token}")

    if not user_id:

        raise AuthError("Authentication required",401)
    
    try:
    
        role = safe_query("SELECT role FROM users where id = %s",(user_id,),fetch="one")[0]
    
    except DBError as error:

        raise AuthError(error.message,error.status_code)

    access_token = create_access_token(user_id,role)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }