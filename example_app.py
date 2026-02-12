from fastapi import FastAPI,Depends
from fastapi.security import OAuth2PasswordBearer
from jwt_auth.auth_routes import router as auth_router
from jwt_auth.services.auth_services import decode_access_token

app = FastAPI()

# Mount auth routes
app.include_router(auth_router)

# ------------------------------------------------------------------------------
# OAuth2 Bearer token extractor
# ------------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


