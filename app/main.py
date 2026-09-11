"""应用入口。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import _token_for, router
from .config import settings
from .core.hub import hub
from .db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("bambu-spool")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.mock_mode:
        logger.info("以模拟打印机模式启动，无需拓竹账号")
    await hub.start()
    logger.info("服务已就绪：http://%s:%s", settings.host, settings.port)
    try:
        yield
    finally:
        await hub.stop()


app = FastAPI(title="拓竹耗材管家", version="0.1.0", lifespan=lifespan)

# 无需鉴权即可访问的路径
OPEN_PATHS = {"/", "/index.html", "/favicon.ico", "/api/auth/login", "/api/auth/status"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if not settings.app_password:
        return await call_next(request)
    path = request.url.path
    if path in OPEN_PATHS or path.startswith("/static") or path.startswith("/docs") or path.startswith("/openapi"):
        return await call_next(request)
    cookie = request.cookies.get("bs_auth", "")
    if cookie == _token_for(settings.app_password) or request.headers.get("x-app-password") == settings.app_password:
        return await call_next(request)
    return JSONResponse({"detail": "需要登录"}, status_code=401)


app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", include_in_schema=False)
async def health():
    return {"ok": True, "mock": settings.mock_mode}
