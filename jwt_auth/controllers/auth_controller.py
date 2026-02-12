from fastapi import HTTPException
import jwt_auth.services.auth_services as services
import jwt_auth.schemas.auth_schema as schema
from fastapi import Response
import os 

def login_controller(credentials:schema.LoginRequest,response: Response):

    try:

        user = services.check_user_by_email(credentials.email)

        if not user or not services.pwd_context.verify(credentials.password, user["pass_hash"]):
            raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
        
    except services.AuthError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )

    access_token = services.create_access_token(user["id"],user["role"])
    refresh_token = services.create_refresh_token()

    services.store_refresh_token(refresh_token, user["id"])

    # Store refresh token as an HttpOnly cookie to prevent JS access
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/auth",
        domain=os.getenv("DOMAIN")
    )

    return {
        "access_token": access_token,
        "role":user["role"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "status": "logged in"
    }

def register_controller(request:schema.RegisterRequest):

    try: 
        result = services.create_user(request.email,request.phone,request.password,request.first_name,request.last_name,request.street,request.city,request.state,request.zip_code)
    
    except services.AuthError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.message
        )

    return result

def logout_controller(response: Response,refresh_token: str):

    if refresh_token:

        services.remove_from_cache(f"refresh:{refresh_token}")

        response.delete_cookie("refresh_token")

    return {"status": "logged out"}

def refresh_controller(refresh_token:str):

    if not refresh_token:
        
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
    
        result = services.refresh(refresh_token)
    
    except services.AuthError as error:

        raise HTTPException(status_code=error.status_code, detail=error.message)
    
    return result

def reset_pass_request_controller(request:schema.PasswordChangeRequest):

    return services.change_password_request(request.email)

def validate_password_change_request_controller(request:schema.PasswordChangeRequestVerify):

    return services.validate_password_change_request(request.code,request.email,request.password)