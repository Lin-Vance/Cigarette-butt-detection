"""序列化、审计与展示辅助。"""

import json
from typing import Any, Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuditLog, CitizenReport, Event, Suggestion, User, WorkOrder
from .statemachine import EVENT_LABELS, REPORT_LABELS, WORKORDER_LABELS
from .timeutil import frame_code, iso, now_cn

STORAGE_URL_PREFIX = "/storage"


def loads_json(raw: str | None) -> dict[str, Any] | None:
    """把库里存的 JSON 字符串还原成对象；空值或脏数据一律返回 None（不抛异常）。"""
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def url(rel_path: str | None) -> str:
    """把库里的相对路径转成可访问 URL。空路径返回空字符串（表示暂无该素材）。"""
    if not rel_path:
        return ""
    return f"{STORAGE_URL_PREFIX}/{rel_path.lstrip('/')}"


def mask_phone(phone: str) -> str:
    if len(phone) != 11:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def paged(items: Sequence[Any], total: int, page: int, size: int) -> dict[str, Any]:
    return {"items": list(items), "total": total, "page": page, "size": size}


def total_pages(total: int, size: int) -> int:
    return max(1, (total + size - 1) // size) if size else 1


# ---------------- 序列化 ----------------


def event_dict(ev: Event, workorder: WorkOrder | None = None) -> dict[str, Any]:
    """事件详情。字段是「FDD §9.3 接口 + 前端 ViolationEvent 类型」的超集，
    两边都能直接消费，避免维护两套序列化。"""
    frames = sorted(ev.frames or [], key=lambda f: f.frame_ts)
    return {
        "id": ev.id,
        "event_id": ev.event_id,
        "camera_id": ev.camera_id,
        "camera_name": ev.camera_name,
        "track_id": ev.track_id,
        "stage": ev.stage,
        "confidence": round(ev.confidence, 3),
        "bbox": ev.bbox or [],
        "trajectory": ev.trajectory or [],
        "event_timestamp": ev.event_timestamp,
        "status": ev.status,
        "status_label": EVENT_LABELS.get(ev.status, ev.status),
        "evidence_count": len(frames),
        "evidence_frames": [
            {
                "frame_ts": f.frame_ts,
                "type": f.type,
                "path": url(f.path),
                "frame_no": f.frame_no,
                "frame_code": frame_code(f.frame_no),
            }
            for f in frames
        ],
        "evidence": {
            "video_clip": url(ev.video_clip_path),
            "frames": {f.type: url(f.path) for f in frames},
        },
        "video_clip_path": url(ev.video_clip_path),
        "has_workorder": ev.has_workorder,
        "review_note": ev.review_note,
        "reviewed_by": ev.reviewed_by,
        "source": ev.source,
        "report_no": ev.report_no,
        "workorder": None
        if workorder is None
        else {"order_no": workorder.order_no, "status": workorder.status},
        "created_at": ev.created_at,
    }


def workorder_dict(wo: WorkOrder) -> dict[str, Any]:
    return {
        "id": wo.id,
        "order_no": wo.order_no,
        "event_id": wo.event_id,
        "camera_id": wo.camera_id,
        "location_name": wo.location_name,
        "latitude": wo.latitude,
        "longitude": wo.longitude,
        "status": wo.status,
        "status_label": WORKORDER_LABELS.get(wo.status, wo.status),
        "assigned_to": wo.assigned_to,
        "assigned_to_id": wo.assigned_to_id,
        "priority": wo.priority,
        "created_at": wo.created_at,
        "accepted_at": wo.accepted_at,
        "started_at": wo.started_at,
        "verified_at": wo.verified_at,
        "completed_at": wo.completed_at,
        "response_time_sec": wo.response_time_sec,
        "escalated": wo.escalated,
        "closure_photo": url(wo.closure_photo_path),
        "completion_note": wo.completion_note,
        "completion_submitted": wo.completion_submitted,
    }


def report_dict(r: CitizenReport, include_phone: bool = False) -> dict[str, Any]:
    """市民上报。默认脱敏手机号（三端架构 §5.6：不展示可能导致报复的信息）。"""
    timeline = [
        {"key": "submitted", "label": REPORT_LABELS["submitted"], "ts": r.submitted_at},
        {"key": "accepted", "label": REPORT_LABELS["accepted"], "ts": r.accepted_at},
        {"key": "processing", "label": REPORT_LABELS["processing"], "ts": r.started_at},
        {"key": "finished", "label": REPORT_LABELS["finished"], "ts": r.finished_at},
        {"key": "rejected", "label": REPORT_LABELS["rejected"], "ts": r.rejected_at},
    ]
    return {
        "id": r.id,
        "report_no": r.report_no,
        "phone": r.phone if include_phone else mask_phone(r.phone),
        "kind": r.kind,
        "kind_label": "行为视频线索" if r.kind == "video" else "现场卫生照片",
        "media_name": r.media_name,
        "media_path": url(r.media_path),
        "location": r.location,
        "description": r.description,
        "status": r.status,
        "status_label": REPORT_LABELS.get(r.status, r.status),
        "submitted_at": r.submitted_at,
        "accepted_at": r.accepted_at,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "rejected_at": r.rejected_at,
        "reject_reason": r.reject_reason,
        "public_reply": r.public_reply,
        "result_photo": url(r.result_photo_path),
        "event_id": r.event_id,
        "task_id": r.task_id,
        "appeal_note": r.appeal_note,
        "risk_flag": r.risk_flag,
        # AI 报告快照 + 市民反馈（管理端复核时对照用）
        "ai_report": loads_json(r.ai_report),
        "ai_feedback": loads_json(r.ai_feedback),
        "ai_feedback_at": r.ai_feedback_at,
        "timeline": [t for t in timeline if t["ts"]],
    }


def suggestion_dict(s: Suggestion) -> dict[str, Any]:
    return {
        "id": s.id,
        "type": s.type,
        "type_label": {
            "add_facility": "增设设施",
            "adjust_schedule": "调整班次",
            "treatment_effective": "治理有效",
            "warning": "复发预警",
        }.get(s.type, s.type),
        "area_name": s.area_name,
        "time_range": s.time_range,
        "content": s.content,
        "frequency_data": s.frequency_data or {},
        "status": s.status,
        "created_at": s.created_at,
        "feedback_note": s.feedback_note,
        "resolved_at": s.resolved_at,
    }


def audit_dict(a: AuditLog) -> dict[str, Any]:
    return {
        "id": a.id,
        "ts": a.ts,
        "actor_id": a.actor_id,
        "actor": a.actor,
        "role": a.role,
        "action": a.action,
        "target": a.target,
        "detail": a.detail,
        "result": a.result,
        "ip": a.ip,
    }


# ---------------- 审计 ----------------


async def write_audit(
    session: AsyncSession,
    action: str,
    *,
    actor: User | None = None,
    actor_name: str = "",
    role: str = "",
    target: str = "",
    detail: str = "",
    result: str = "success",
    ip: str = "",
) -> AuditLog:
    """写一条审计日志。审计表只增不改不删（对齐页面 18 的只读约束）。"""
    log = AuditLog(
        ts=iso(now_cn()),
        actor_id=actor.id if actor else None,
        actor=actor.username if actor else actor_name,
        role=actor.role if actor else role,
        action=action,
        target=target,
        detail=detail,
        result=result,
        ip=ip,
    )
    session.add(log)
    return log


def client_ip(request) -> str:
    try:
        return request.client.host if request.client else ""
    except Exception:  # noqa: BLE001
        return ""


def tail(items: Iterable[Any], n: int) -> list[Any]:
    seq = list(items)
    return seq[:n]
