from fastapi import FastAPI,Depends
from fastapi.security import OAuth2PasswordBearer
from auth_router import router as auth_router
from jwt_auth import decode_access_token

app = FastAPI()

# Mount auth routes
app.include_router(auth_router)

# ------------------------------------------------------------------------------
# OAuth2 Bearer token extractor
# ------------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ------------------------------------------------------------------------------
# Example protected endpoint
# ------------------------------------------------------------------------------

@app.get("/example")
def example(token: str = Depends(oauth2_scheme)):
    """
    Example protected endpoint.

    Requires:
    - Authorization: Bearer <access_token>

    Flow:
    1. FastAPI extracts the Bearer token
    2. Token is decoded and validated
    3. User ID is extracted
    4. User-specific data is returned
    """
    user_id = decode_access_token(token)

    return {
        "response":"some data"
        }