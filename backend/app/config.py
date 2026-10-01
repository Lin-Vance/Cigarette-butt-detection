"""FastAPI 服务的集中配置。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "烟踪智治 · 后端服务"
    api_prefix: str = "/api/v1"
    version: str = "0.1.0"
    environment: str = "development"

    # 正式运行统一使用 MySQL；SQLite 只作为迁移前的只读历史备份。
    database_url: str = "mysql+aiomysql://yanzong:yanzong-dev-only@127.0.0.1:3306/yanzong?charset=utf8mb4"
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_key_prefix: str = "yanzong"

    # JWT（演示用固定密钥，生产必须换）
    jwt_secret: str = "yanzong-development-only-secret-change-before-production-2026"
    jwt_algorithm: str = "HS256"
    access_token_ttl_sec: int = 7200
    refresh_token_ttl_sec: int = 14 * 24 * 3600
    # 仅本地演示时把动态验证码回显给前端；部署时必须设为 false 并接短信网关。
    expose_demo_codes: bool = True

    # 证据文件本地目录（替代 MinIO）
    storage_dir: Path = BACKEND_DIR / "storage"
    evidence_dir_name: str = "evidence"

    # 首帧素材来源：复用主站已归档的设计稿实景图作为演示证据帧。
    # 首次启动时会把候选图片复制进 storage/evidence/_pool/，
    # 之后即使本目录不存在也能独立运行（找不到时退化为生成 SVG 帧）。
    asset_source_dir: Path = BACKEND_DIR.parent / "frontend" / "public" / "media"

    # 启动时灌入演示数据（幂等：已有数据则跳过）
    seed_on_startup: bool = True
    # 演示数据量级：design（设计稿量级）/ pilot（2-4 路摄像头试点量级）
    default_scale_mode: str = "pilot"

    # 启动时预热 cigarette-detector.pt（torch 导入 + 首次前向）。
    #
    # ⚠️ 实测代价很大（2026-09-28）：CPU 环境下这段预热要 **约 80 秒**，
    # 期间进程内存涨到约 0.5–1GB，而且因为它持有 GIL，
    # **事件循环会被饿死——端口已经在监听，但任何请求（含 /healthz）都不回应**。
    # 前端对此有兜底：存活探测 1.2 秒超时 → 判"后端离线" → 回退本地模拟数据，
    # 预热完成后 5 秒内自动切回后端；登录同样会回退本地演示账号。
    #
    #   AI_WARMUP=0  启动更快（秒级），但**市民第一次上传素材**要等模型加载（约 80 秒），
    #                而前端预检超时是 3.5 秒 → 会退回本地预检，看不到真实模型结果。
    #   AI_WARMUP=1  启动慢约 1 分钟，但之后每次上传都在 1 秒内返回真实检测结果。**演示建议保持 1**。
    ai_warmup: bool = True

    cors_origins: list[str] = [
        "http://127.0.0.1:5180",
        "http://localhost:5180",
        "http://127.0.0.1:5190",
        "http://localhost:5190",
    ]
    # 前端 dev server 端口，允许任意本机端口调试
    cors_origin_regex: str = r"http://(127\.0\.0\.1|localhost):\d+"

    @property
    def evidence_dir(self) -> Path:
        return self.storage_dir / self.evidence_dir_name

    @property
    def pool_dir(self) -> Path:
        return self.evidence_dir / "_pool"


@lru_cache
def get_settings() -> Settings:
    return Settings()
