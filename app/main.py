from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import SessionFactory
from app.routers.auth_router import router as auth_router
from app.routers.portfolio_router import public_router
from app.routers.portfolio_router import router as portfolio_router

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(public_router)
app.include_router(portfolio_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> dict[str, str]:
    async with SessionFactory() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}
