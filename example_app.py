from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends
from fastapi.security import OAuth2PasswordBearer
from jwt_auth.auth_routes import router as auth_router
from jwt_auth.db.db import close_pool, init_pool
from jwt_auth.db.redis import close_cache, init_cache
from jwt_auth.controllers.auth_controller import decode_access_token_controller as decode_access_token


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

@app.post("/some-endpoint")
async def some_function(token: str = Depends(oauth2_scheme)):
    id = decode_access_token(token) #this raises 401 automatically if invalid token. 
    
    return #something based on the id and data wanted or provided. 


