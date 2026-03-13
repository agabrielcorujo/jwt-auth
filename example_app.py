from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.security import OAuth2PasswordBearer
from jwt_auth.auth_routes import router as auth_router
from jwt_auth.db.db import close_pool, init_pool
from jwt_auth.db.redis import close_cache, init_cache


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_pool()
    await init_cache()
    try:
        yield
    finally:
        await close_cache()
        await close_pool()


app = FastAPI(lifespan=lifespan)

# Mount auth routes
app.include_router(auth_router)

# ------------------------------------------------------------------------------
# OAuth2 Bearer token extractor
# ------------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


