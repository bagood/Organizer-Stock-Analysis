import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import SessionFactory
from app.routers.auth_router import router as auth_router
from app.routers.chat_history_router import router as chat_history_router
from app.routers.chat_quota_router import router as chat_quota_router
from app.routers.portfolio_router import public_router
from app.routers.portfolio_router import router as portfolio_router
from app.services.chat_history_housekeeping import run_chat_history_housekeeping


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    stop_event = asyncio.Event()
    housekeeping_task = asyncio.create_task(
        run_chat_history_housekeeping(stop_event), name="chat-history-housekeeping"
    )
    try:
        yield
    finally:
        stop_event.set()
        housekeeping_task.cancel()
        with suppress(asyncio.CancelledError):
            await housekeeping_task


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(chat_quota_router)
app.include_router(chat_history_router)
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
