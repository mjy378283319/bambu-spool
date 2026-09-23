"""应用入口：生命周期、访问控制中间件、安全响应头。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import auth
from .api.routes import router
from .auth import is_https
from .config import settings
from .core.hub import hub
from .db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger("bambu-spool")

STATIC_DIR = Path(__file__).parent / "static"

# 无需登录即可访问的路径。前端外壳（HTML/CSS/JS）必须开放，
# 否则用户连登录页都加载不出来；壳里不含任何数据。
OPEN_EXACT = {"/", "/index.html", "/favicon.ico", "/health"}
OPEN_PREFIX = ("/static/", "/api/auth/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.mock_mode:
        logger.info("以模拟打印机模式启动，无需拓竹账号")

    auth.bootstrap_admin_from_env()
    if auth.user_count() == 0:
        logger.warning(
            "尚未创建任何账号。请立刻打开网页完成管理员初始化；"
            "初始化接口已限制为仅内网直连可访问（要放开请设 ALLOW_PUBLIC_SETUP=1）。"
        )
    if not settings.trust_proxy:
        logger.info("TRUST_PROXY 已关闭，反向代理传来的 X-Forwarded-* 将被忽略")

    await hub.start()
    logger.info("服务已就绪：http://%s:%s", settings.host, settings.port)
    try:
        yield
    finally:
        await hub.stop()


app = FastAPI(
    title="拓竹耗材管家",
    version="0.12.35",
    lifespan=lifespan,
    # 挂了鉴权就别把接口文档公开（会泄露接口结构，给扫描器省事）
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# 会话 Cookie 只含随机令牌，配合 SameSite=Lax 已能挡住跨站表单提交；
# 这里再对「改数据的请求」做一次 Origin 校验，纵深防御。
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _origin_allowed(request: Request) -> bool:
    origin = request.headers.get("origin", "").strip().rstrip("/")
    if not origin:
        # 非浏览器客户端（curl / 脚本）不带 Origin，放行
        return True
    if settings.allowed_origins:
        return origin in settings.allowed_origins
    # 默认与当前 Host 比对；反代下 Host 通常是外部域名
    host = request.headers.get("x-forwarded-host", "") or request.headers.get("host", "")
    if not host:
        return True
    return origin.endswith("//" + host.split(",")[0].strip())


@app.middleware("http")
async def access_control(request: Request, call_next):
    path = request.url.path

    # 1) 强制 HTTPS（仅在反代已告知外部协议时生效）
    if settings.require_https and not is_https(request) and path != "/health":
        target = "https://" + (request.headers.get("host", "") + path)
        if request.url.query:
            target += "?" + request.url.query
        return RedirectResponse(target, status_code=308)

    # 2) 放行前端外壳与登录接口
    if path in OPEN_EXACT or path.startswith(OPEN_PREFIX):
        return _harden(await call_next(request), path)

    # 3) 跨站写操作拦截
    if request.method in UNSAFE_METHODS and not _origin_allowed(request):
        return JSONResponse({"detail": "跨站请求已被拒绝"}, status_code=403)

    # 4) 会话校验
    if auth.current_user(request) is None:
        return JSONResponse(
            {"detail": "未登录", "code": "unauthenticated"}, status_code=401
        )

    return _harden(await call_next(request), path)


def _harden(response, path: str = ""):
    """给所有响应加上基础安全头（以及前端外壳的缓存策略）。"""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    # 相机必须允许「本站自己」：手机扫码走的是 getUserMedia，受这个头管辖。
    # ⚠️ 别改成 camera=()：空括号 = 对**所有来源**（含本站）禁用相机，
    #    浏览器会直接以 NotAllowedError 拒掉、**连权限弹窗都不弹**，
    #    表现和「手机没给相机权限」一模一样 —— 用户改手机设置永远改不好。
    #    2026-09-16 踩过：两台手机 + 两个浏览器（安卓 Edge / 鸿蒙浏览器）全开不了相机。
    # 麦克风、定位本应用用不到，继续关掉。
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=(), camera=(self)"
    )
    # 前端是单页原生实现，用到内联事件处理器，因此 style/script 需要 unsafe-inline
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "connect-src 'self' ws: wss:; frame-ancestors 'none'; base-uri 'none'",
    )
    # 前端外壳必须每次都回源校验：
    #   StaticFiles 只发 ETag / Last-Modified、**不发 Cache-Control**，浏览器于是按启发式
    #   规则缓存（Last-Modified 起 10% 时长内直接复用、不校验）。后果是「镜像已经拉到新
    #   版本，页面里的 JS 还是旧的」——面板上少控件、少按钮，看着像功能根本没做。
    #   2026-09-21 真实踩坑：0.12.25 新增的两个时间旋钮在面板上找不到，白排查一轮。
    #   局域网自用，多一次 304 的开销可以忽略，所以直接 no-cache。
    if path.startswith("/static/") or path in ("/", "/index.html"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


# 图标：index.html 用 icon.svg，但浏览器/抓取器仍会按惯例请求 /favicon.ico。
# 没有这条路由时它落在鉴权中间件之后 → 401（或 404），控制台一直报错、书签栏空白。
# OPEN_EXACT 里已放行 /favicon.ico，这里只要把文件吐出去即可。
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    ico = STATIC_DIR / "favicon.ico"
    if not ico.exists():
        # 兜底：没生成 ico 就退 SVG（浏览器认 type）
        return FileResponse(STATIC_DIR / "icon.svg", media_type="image/svg+xml")
    return FileResponse(ico, media_type="image/x-icon")


@app.get("/health", include_in_schema=False)
async def health():
    return {"ok": True, "mock": settings.mock_mode}
