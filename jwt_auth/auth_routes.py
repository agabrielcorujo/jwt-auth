from fastapi import APIRouter,Response,Cookie
import jwt_auth.schemas.auth_schema as schema
import jwt_auth.controllers.auth_controller as auth_controller

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
def login(credentials: schema.LoginRequest, response: Response):

    return auth_controller.login_controller(credentials,response)

# ------------------------------------------------------------------------------
# Registration endpoint
# ------------------------------------------------------------------------------

@router.post("/register")
def register(credentials: schema.RegisterRequest):

    return auth_controller.register_controller(credentials)

# ------------------------------------------------------------------------------
# Logout endpoint
# ------------------------------------------------------------------------------

@router.post("/logout")
def logout(response: Response, refresh_token: str | None = Cookie(None)):

    return auth_controller.logout_controller(response,refresh_token)

# ------------------------------------------------------------------------------
# Refresh endpoint
# ------------------------------------------------------------------------------

@router.post("/refresh")
def refresh(refresh_token:str | None = Cookie(None)):

    return auth_controller.refresh_controller(refresh_token)

@router.patch("/password-reset-request")
def reset_pass_request(request:schema.PasswordChangeRequest):

    return  auth_controller.reset_pass_request_controller(request)

@router.patch("/validate-password-reset-request")
def validate_pass_request(request:schema.PasswordChangeRequestVerify):

    return auth_controller.validate_password_change_request_controller(request)