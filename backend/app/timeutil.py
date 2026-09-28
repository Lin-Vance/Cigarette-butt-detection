"""时间工具。

修订说明 C3 要求：统一使用 ISO 8601 **带时区** 格式。
PRD 示例为 `2026-08-07T22:10:35.123+08:00`，即固定东八区。

这里用固定 `timezone(timedelta(hours=8))` 而非 `ZoneInfo("Asia/Shanghai")`：
Windows 上 `zoneinfo` 依赖 `tzdata` 包才能拿到 IANA 数据库，固定偏移零依赖且
本项目部署级别不跨时区（校园试点），不会踩夏令时问题。
"""

from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))

# 采样率口径：100 fps（10 ms/帧）。与前端首屏装置、§03 证据链保持一致。
FPS = 100
MS_PER_FRAME = 1000 // FPS


def now_cn() -> datetime:
    return datetime.now(CST)


def iso(dt: datetime | None = None) -> str:
    """输出 ISO 8601 带 +08:00 的字符串。"""
    return (dt or now_cn()).astimezone(CST).isoformat()


def iso_ms(dt: datetime | None = None) -> str:
    """毫秒精度版本，事件时间戳用这个。"""
    d = (dt or now_cn()).astimezone(CST)
    return d.isoformat(timespec="milliseconds")


def parse_iso(value: str) -> datetime:
    """解析 ISO 8601；无时区的按东八区处理（兼容历史数据）。"""
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=CST)


def frame_no(dt: datetime) -> int:
    """按 100 fps 口径换算帧号（F-0000 形式的前缀由调用方拼）。"""
    return int(round(dt.timestamp() * FPS))


def frame_code(n: int) -> str:
    return f"F-{n % 10000:04d}"


def plus_ms(dt: datetime, ms: int) -> datetime:
    return dt + timedelta(milliseconds=ms)
