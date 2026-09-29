"""应用入口。

启动：
    uvicorn app.main:app --reload --port 8000
或直接用根目录 start.bat / start.sh。
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import BACKEND_DIR, get_settings
from .db import get_session_factory, init_db
from .generator import ensure_pool
from .deps import require_roles
from .models import User
from .routers import audit, auth, camera, decision, event, inference, report, stats, workorder
from .routers import activity as activity_router
from .routers import ws as ws_router
from .seed import ensure_demo_citizen, seed_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("yanzong")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment.lower() == "production" and (
        settings.jwt_secret == "yanzong-development-only-secret-change-before-production-2026"
        or len(settings.jwt_secret) < 32
    ):
        raise RuntimeError("生产环境必须配置至少 32 位的随机 JWT_SECRET")
    await init_db()
    ensure_pool()
    if settings.seed_on_startup:
        async with get_session_factory()() as session:
            result = await seed_all(session)
            if result.get("skipped"):
                logger.info("演示数据已存在，跳过种子化")
            else:
                logger.info("演示数据已灌入：%s", result)
            if settings.environment.lower() == "development":
                await ensure_demo_citizen(session)
    logger.info("证据目录：%s", settings.evidence_dir)
    logger.info("数据库：%s", settings.database_url.split("@")[-1])

    # 预热 cigarette-detector.pt：把 torch 导入与首次前向的耗时挪到启动阶段，
    # 否则会全部落在市民第一次上传上（超过前端 3.5s 预检超时）。失败不影响服务启动。
    #
    # ⚠️ 必须放到**后台线程**（2026-09-28 复核新发现 D-23）：
    # 原先这里是同步调用，会阻塞 lifespan；而 uvicorn 是**先绑定端口、再跑 lifespan**，
    # 于是出现"端口已在监听，但任何请求都挂着"的窗口——实测 `/healthz` 挂起 14.6 秒、
    # python 进程内存涨到 1.06GB。后果有两个：
    #   1. 前端存活探测（1.2s 超时）在这段时间一律判"后端离线"；
    #   2. 若浏览器此时发起登录，请求要等到 axios 15 秒超时才失败。
    # 移出主流程后服务立即可用；预热未完成时 `/public/ai/inspect` 首次调用会稍慢，
    # 前端本来就有 3.5s 超时 + 本地预检兜底，不会拖垮整站。
    async def _warm_model() -> None:
        warm = await asyncio.to_thread(inference.warmup)
        if warm.get("ok"):
            logger.info("AI 预检已预热：cigarette-detector.pt · device=%s", warm.get("device"))
        else:
            logger.warning(
                "AI 预检未就绪：%s（上传接口会返回 503，前端将回退本地预检）", warm.get("reason")
            )

    warm_task: asyncio.Task | None = None
    if settings.ai_warmup:
        warm_task = asyncio.create_task(_warm_model())
    else:
        logger.info("已按配置跳过模型预热（ai_warmup=0）：启动更快，首次上传会慢")
    try:
        yield
    finally:
        if warm_task is not None and not warm_task.done():
            warm_task.cancel()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "烟踪智治后端服务 · FastAPI 单体。\n\n"
        "**重要声明**：AI 行为识别管道（三段式状态机 / ByteTrack / 光流法 / 抛物线拟合）"
        "尚未实现，本服务内置**合规事件生成器**产出演示事件，全部数据均标注为演示数据，"
        "不代表真实识别结果。"
    ),
    lifespan=lifespan,
    docs_url=None if settings.environment.lower() == "production" else "/docs",
    redoc_url=None if settings.environment.lower() == "production" else "/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 证据文件（替代 MinIO）
settings.storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(settings.storage_dir)), name="storage")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith(api) else "no-cache"
    return response


# ---------------- 统一错误响应 ----------------


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "error_code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": "SYS_HTTP_ERROR", "message": str(detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "SYS_VALIDATION_ERROR",
            "message": f"参数校验失败：{loc} {first.get('msg', '')}".strip(),
            "errors": [
                {"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()[:8]
            ],
        },
    )


# ---------------- 路由注册 ----------------

api = settings.api_prefix
app.include_router(auth.router, prefix=api)
app.include_router(auth.users_router, prefix=api)
app.include_router(camera.router, prefix=api)
app.include_router(camera.ai_router, prefix=api)
app.include_router(event.router, prefix=api)
app.include_router(workorder.router, prefix=api)
app.include_router(report.citizen_router, prefix=api)
app.include_router(report.public_router, prefix=api)
app.include_router(report.admin_router, prefix=api)
app.include_router(stats.router, prefix=api)
app.include_router(decision.router, prefix=api)
app.include_router(audit.router, prefix=api)
app.include_router(activity_router.router, prefix=api)
app.include_router(inference.router, prefix=api)
app.include_router(ws_router.router)


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "api_prefix": api,
        "ws": ["/ws/alerts", "/ws/workorders"],
        "demo_notice": "全部数据为演示数据；AI 行为识别管道未实现。",
    }


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict:
    return {"status": "ok"}


@app.post(api + "/admin/reseed", tags=["meta"])
async def reseed(
    force: bool = True,
    _: User = Depends(require_roles("admin")),
) -> dict:
    """重建演示数据（答辩前重置现场用）。"""
    async with get_session_factory()() as session:
        result = await seed_all(session, force=force)
    return {"status": "ok", "result": result, "backend_dir": str(BACKEND_DIR)}
