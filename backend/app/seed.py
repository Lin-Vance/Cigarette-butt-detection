"""演示数据种子。

幂等：users 表非空即跳过。`force=True` 时先清空业务表再重建。
所有数据都标注为演示数据，量级对齐修订说明 C2 的「校园试点」口径。
"""

import json
import random
import shutil
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .generator import build_event, ensure_pool
from .models import (
    AnalysisTask,
    AuditLog,
    Camera,
    CitizenReport,
    Event,
    Suggestion,
    User,
    WorkOrder,
)
from .rules import recompute_suggestions
from .security import ROLE_LABELS, hash_password
from .statemachine import REJECT_REASONS
from .timeutil import iso, iso_ms, now_cn, plus_ms

SEED_RNG = random.Random(20260927)

DEMO_PASSWORD = "123456"

SEED_USERS = [
    ("admin", "超级管理员", "admin", "13800138000"),
    ("manager", "后勤管理员", "manager", "13800138001"),
    ("worker01", "张建国", "worker", "13800138002"),
    ("worker02", "李红梅", "worker", "13800138003"),
    ("worker03", "王海军", "worker", "13800138005"),
    ("worker04", "陈小燕", "worker", "13800138006"),
    ("aidev", "AI 开发人员", "ai_dev", "13800138004"),
]

# 与前端 frontend/src/mock/engine.ts 的摄像头定义保持一致
# 2026-09-28 扩充：4 → 8 路，覆盖宿舍区 / 运动场 / 行政楼 / 校医院，
# 便于「正式使用」时先把校园主要公共空间铺满（后续按实际施工进度继续加）。
SEED_CAMERAS = [
    ("cam_001", "图书馆北门枪机", "图书馆北门", 32.148213, 114.068912, "online", 25.0, False, "histogram_eq", 99.8),
    ("cam_002", "教学楼 A 座出口球机", "教学楼 A 座出口", 32.147566, 114.071534, "online", 25.0, False, "histogram_eq", 99.2),
    ("cam_003", "学生食堂东侧枪机", "学生食堂东侧", 32.148874, 114.069217, "online", 25.0, False, "histogram_eq", 98.7),
    ("cam_004", "体育馆西广场球机", "体育馆西广场", 32.146902, 114.070648, "degraded", 15.0, True, "retinex", 92.4),
    ("cam_005", "宿舍区东门枪机", "宿舍区东门", 32.149521, 114.072801, "online", 25.0, False, "histogram_eq", 99.5),
    ("cam_006", "运动场南侧球机", "运动场南侧", 32.146113, 114.069354, "online", 25.0, True, "retinex", 97.9),
    ("cam_007", "行政楼前广场枪机", "行政楼前广场", 32.147038, 114.067155, "online", 25.0, False, "histogram_eq", 99.1),
    ("cam_008", "校医院西门球机", "校医院西门", 32.149977, 114.066230, "offline", 0.0, False, "histogram_eq", 86.3),
]

# 演示市民手机号（市民端登录时用它才能看到已种子化的上报记录）
DEMO_CITIZEN_PHONE = "13800000000"

# 每个量级生成多少条事件
# pilot 由 28 提到 42：正式启用初期先铺一批"看起来真的在跑"的历史数据
EVENT_COUNT = {"design": 48, "pilot": 42}


def _order_no(seq: int, when) -> str:
    return f"GD{when.year}{seq:06d}"


async def _is_seeded(session: AsyncSession) -> bool:
    total = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    return bool(total)


async def ensure_demo_citizen(session: AsyncSession) -> None:
    """保证本地演示账号可重复登录，不影响其他市民账号。"""
    user = (
        await session.execute(
            select(User).where(
                User.username == DEMO_CITIZEN_PHONE,
                User.role == "citizen",
            )
        )
    ).scalar_one_or_none()
    password_hash, salt = hash_password(DEMO_PASSWORD)
    if user is None:
        session.add(
            User(
                username=DEMO_CITIZEN_PHONE,
                password_hash=password_hash,
                password_salt=salt,
                real_name="演示市民",
                role="citizen",
                phone=DEMO_CITIZEN_PHONE,
                enabled=True,
                created_at=iso(now_cn()),
            )
        )
    else:
        user.password_hash = password_hash
        user.password_salt = salt
        user.enabled = True
    await session.commit()


async def _clear(session: AsyncSession) -> None:
    from sqlalchemy import delete

    for model in (AuditLog, Suggestion, AnalysisTask, CitizenReport, WorkOrder, Event, Camera, User):
        await session.execute(delete(model))
    await session.flush()

    settings = get_settings()
    for child in settings.evidence_dir.iterdir() if settings.evidence_dir.exists() else []:
        if child.name == "_pool":
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)


async def seed_all(session: AsyncSession, *, force: bool = False) -> dict[str, int]:
    settings = get_settings()
    if await _is_seeded(session) and not force:
        return {"skipped": 1}
    if force:
        await _clear(session)

    rng = SEED_RNG
    now = now_cn()
    pool = ensure_pool()

    # ---- 账号 ----
    users: list[User] = []
    for username, real_name, role, phone in SEED_USERS:
        password_hash, salt = hash_password(DEMO_PASSWORD)
        user = User(
            username=username,
            password_hash=password_hash,
            password_salt=salt,
            real_name=real_name,
            role=role,
            phone=phone,
            enabled=True,
            created_at=iso(now),
        )
        session.add(user)
        users.append(user)

    # ---- 摄像头 ----
    cameras: list[Camera] = []
    for cid, name, loc, lat, lon, status, fps, pre, algo, rate in SEED_CAMERAS:
        cam = Camera(
            camera_id=cid,
            name=name,
            location_name=loc,
            latitude=lat,
            longitude=lon,
            status=status,
            fps=fps,
            preprocess_enabled=pre,
            preprocess_algorithm=algo,
            online_rate=rate,
            rtsp_url=f"rtsp://192.168.1.{100 + len(cameras)}:554/stream1",
            roi_polygon=[[100, 100], [800, 100], [800, 600], [100, 600]],
            created_at=iso(now),
        )
        session.add(cam)
        cameras.append(cam)

    await session.flush()

    # ---- 事件 + 工单 ----
    mode = settings.default_scale_mode if settings.default_scale_mode in EVENT_COUNT else "pilot"
    count = EVENT_COUNT[mode]
    workers = [u for u in users if u.role == "worker"]

    events: list[Event] = []
    for i in range(count):
        # 越靠前越新；时间落在最近 7 天内，供 7 天趋势与时段分布使用
        at = plus_ms(now, -int((i * 5.6 + rng.random() * 3) * 3600 * 1000))
        # 让事件集中在午间与傍晚，便于规则引擎产出「时段峰值」建议
        hour_bias = at.hour
        if i % 3 == 0:
            at = at.replace(hour=12, minute=rng.randint(0, 59))
        elif i % 3 == 1:
            at = at.replace(hour=18, minute=rng.randint(0, 59))
        cam = cameras[i % len(cameras)]
        ev = build_event(cam, at=at, rng=rng, pool=pool)
        # 状态分布：确认多数，少量待复核与误报
        roll = i % 10
        if roll in (0, 1):
            ev.status = "pending_review"
        elif roll == 2:
            ev.status = "false_alarm"
            ev.review_note = "复核判定为手部误触，未发生抛掷"
        else:
            ev.status = "confirmed"
        events.append(ev)
        session.add(ev)
        _ = hour_bias

    await session.flush()

    orders: list[WorkOrder] = []
    seq = 0
    open_statuses = ["pending", "pending", "pending", "accepted", "processing", "verifying"]
    for i, ev in enumerate(events):
        if ev.status not in ("confirmed", "closed", "referred"):
            ev.has_workorder = False
            continue

        seq += 1
        created = ev.event_timestamp
        # 前 3 条**实际生成的工单**保持待接单，给「调度任务池」留出可操作数据。
        #
        # ⚠️ 2026-09-28 缺陷复核新发现 D-19，这里原先有两个连带问题，导致
        #    「种子数据永远产不出一张待接单工单」：
        #   1) 判定用的是**事件下标** `i < 3`，而 events[0..2] 的状态分别是
        #      pending_review / pending_review / false_alarm，都在上面的
        #      `continue` 里被跳过了 → pending 分支是**死代码**；
        #   2) created_at 沿用事件时间（几小时乃至几天前），而超时扫描
        #      （orders.is_overdue，30 分钟 SLA）会在任何人第一次打开任务池时
        #      把陈旧的 pending 直接升级为 timeout。
        #    外部症状：API 模式下环卫端「可接单」列表恒为空，
        #    「接单 → 到场 → 提交验收」整条闭环演示不出来。
        #    故这里改用**工单序号** seq 判定，并把 created_at 拉回 25 分钟内。
        if seq <= 3:
            status = "pending"
            created = iso_ms(plus_ms(now, -int(rng.randint(2, 25)) * 60 * 1000))
        elif seq <= 5:
            status = "processing"
        elif seq == 6:
            status = "timeout"
        else:
            status = open_statuses[seq % len(open_statuses)] if seq % 4 else "closed"

        assigned = rng.choice(workers)
        accepted_at = None
        started_at = None
        verified_at = None
        completed_at = None
        response = None

        if status != "pending":
            accepted_at = iso_ms(plus_ms(now, -int(rng.randint(60, 3000)) * 1000))
            response = rng.randint(180, 2400)
        if status in ("processing", "verifying", "closed"):
            started_at = iso_ms(plus_ms(now, -int(rng.randint(30, 1500)) * 1000))
        if status == "closed":
            verified_at = completed_at = iso_ms(plus_ms(now, -int(rng.randint(10, 600)) * 1000))

        order = WorkOrder(
            order_no=_order_no(seq, now),
            event_id=ev.event_id,
            camera_id=ev.camera_id,
            location_name=next((c.location_name for c in cameras if c.camera_id == ev.camera_id), ""),
            latitude=next((c.latitude for c in cameras if c.camera_id == ev.camera_id), 0.0),
            longitude=next((c.longitude for c in cameras if c.camera_id == ev.camera_id), 0.0),
            status=status,
            assigned_to=assigned.real_name if status != "pending" else "待派发",
            assigned_to_id=assigned.id if status != "pending" else None,
            priority="high" if ev.confidence >= 0.9 else "normal",
            created_at=created,
            accepted_at=accepted_at,
            started_at=started_at,
            verified_at=verified_at,
            completed_at=completed_at,
            response_time_sec=response,
            escalated=status == "timeout",
            completion_submitted=status == "closed",
            completion_note="已完成清理并拍照留档" if status == "closed" else "",
        )
        orders.append(order)
        ev.has_workorder = True
        session.add(order)

    await session.flush()

    # ---- 市民上报 + 分析任务 ----
    await _seed_reports(session, rng, now, cameras, workers)

    # ---- 审计日志 ----
    for u in users:
        session.add(
            AuditLog(
                ts=iso(plus_ms(now, -int(rng.randint(600, 9000)) * 1000)),
                actor_id=u.id,
                actor=u.username,
                role=u.role,
                action="AUTH_LOGIN",
                target=f"user:{u.username}",
                detail=f"角色 {ROLE_LABELS.get(u.role, u.role)} 登录成功",
                result="success",
                ip="127.0.0.1",
            )
        )

    await session.flush()

    # ---- 调度建议（规则引擎真实计算）----
    await recompute_suggestions(session)

    await session.commit()
    return {
        "users": len(users),
        "cameras": len(cameras),
        "events": len(events),
        "workorders": len(orders),
        "scale_mode": mode,
    }


def _ai_snapshot(verdict: str) -> dict:
    """构造与 `routers/inference.py::_build_report` **同结构**的 AI 报告快照。

    种子数据不走模型推理（否则启动要多等一分钟），但结构必须与线上一致，
    管理端与市民端才能用同一套渲染逻辑展示历史记录。
    """
    hit = verdict == "candidate"
    top = 88.4 if hit else (52.1 if verdict == "low" else 0.0)
    label = {
        "candidate": "疑似烟头目标",
        "low": "烟头信号较弱 · 建议人工判断",
        "scene": "未检出烟头目标",
    }[verdict]
    return {
        "engine": "cigarette-detector.pt · Ultralytics YOLO（cigarette / hand / person）",
        "demo": True,
        "detected": hit,
        "confidence": top,
        "count": 1 if hit else 0,
        "verdict": verdict,
        "verdict_label": label,
        "verdict_tone": "ok" if hit else ("warn" if verdict == "low" else "muted"),
        "summary": (
            "模型检出 1 个烟头目标，最高置信度 88.4%。可作为候选线索进入人工复核；"
            "单张图片只能说明现场状态，不能证明完整抛掷动作。"
            if hit
            else "模型未检出 cigarette / hand / person 中的相关目标。若画面确实是公共空间卫生问题，仍可提交为环境线索。"
        ),
        "stages": [
            {"key": "holding", "label": "持烟 · 点燃", "state": "hit" if hit else "miss", "note": "检出烟头目标" if hit else "未检出烟头目标"},
            {"key": "throw", "label": "抛掷动作", "state": "unknown", "note": "静态图片无法判定动作过程，需连续视频与时间码"},
            {"key": "landing", "label": "落地 · 现场状态", "state": "hit" if hit else "unknown", "note": "画面中存在烟头落地痕迹" if hit else "未见明确落地目标"},
        ],
        "evidence": {
            "frames": 1,
            "chain": "不完整",
            "note": "本次素材为单张图片：可记录现场状态，不足以证明完整抛掷动作。",
        },
        "notice": "模型结果仅生成候选线索，不会自动认定违规或触发处罚；判定需授权人员人工复核。",
    }


async def _seed_reports(session: AsyncSession, rng: random.Random, now, cameras, workers) -> None:
    """造几条覆盖不同状态的市民上报，让三端都有可看的数据。"""
    cam_by_id = {c.camera_id: c for c in cameras}
    blueprints = [
        # (状态, 类型, 地点, 说明, 公开回复, 不予受理原因)
        (
            "finished",
            "video",
            "浉河区 · 人民路步行街东口",
            "看到有人把烟头丢进绿化带，录了一小段。",
            "已核实并完成清理，现场已恢复整洁。感谢你的安全上报。",
            "",
        ),
        (
            "processing",
            "video",
            "羊山新区 · 社区公园北入口",
            "傍晚锻炼时看到地面上有多枚烟头，位置在长椅旁。",
            "",
            "",
        ),
        (
            "accepted",
            "photo",
            "平桥区 · 交通枢纽公交站台",
            "站台地面有烟头堆积，烟蒂桶似乎满溢。",
            "",
            "",
        ),
        (
            "rejected",
            "video",
            "浉河区 · 未标注路段",
            "拍到了地上的烟头。",
            "",
            REJECT_REASONS[0],
        ),
        (
            "submitted",
            "video",
            "浉河区 · 浉河公园西门",
            "刚提交，等待系统分析。",
            "",
            "",
        ),
        (
            "pending_review",
            "photo",
            "平桥区 · 南京大道东站广场",
            "站前广场地面有不少烟头，旁边就是烟蒂桶。",
            "",
            "",
        ),
        (
            "appealing",
            "photo",
            "羊山新区 · 新五大道与新六大街交叉口",
            "拍到的是设施满溢，不是有人乱扔，希望重新核对。",
            "该线索已受理，现场设施已清运。",
            "",
        ),
    ]

    # 每条上报都带一份「上传时当场产出的 AI 报告快照」，
    # 管理端复核时能看到当时的模型结论（结构与 /public/ai/inspect 一致）。
    AI_VERDICTS = [
        "candidate",
        "candidate",
        "scene",
        "candidate",
        "low",
        "candidate",
        "scene",
        "candidate",
        "candidate",
    ]
    DISAGREE_AT = 2  # 第 3 条演示「市民对 AI 判断提出异议」

    for idx, (status, kind, location, desc, reply, reason) in enumerate(blueprints):
        submitted = plus_ms(now, -int(rng.randint(120, 8000)) * 1000)
        report_no = f"SB{now.year}{idx + 1:05d}"
        task_id = f"TK{now.year}{idx + 1:05d}"
        event_id = ""

        # 受理过的上报派生出关联事件，实现「上报 → 事件 → 工单」贯通
        if status in ("accepted", "processing", "finished"):
            cam = cameras[idx % len(cameras)]
            ev = build_event(cam, at=submitted, rng=rng, source="citizen", report_no=report_no)
            ev.status = "confirmed"
            ev.has_workorder = True
            session.add(ev)
            await session.flush()
            event_id = ev.event_id
            workers_pick = workers[idx % len(workers)] if workers else None
            order = WorkOrder(
                order_no=f"GD{now.year}9{idx + 1:05d}",
                event_id=ev.event_id,
                camera_id=cam.camera_id,
                location_name=cam.location_name,
                latitude=cam.latitude,
                longitude=cam.longitude,
                status={"accepted": "accepted", "processing": "processing", "finished": "closed"}[status],
                assigned_to=workers_pick.real_name if workers_pick else "待派发",
                assigned_to_id=workers_pick.id if workers_pick else None,
                priority="normal",
                created_at=ev.event_timestamp,
                accepted_at=iso_ms(plus_ms(submitted, 900_000)),
                started_at=iso_ms(plus_ms(submitted, 1_500_000)),
                verified_at=iso_ms(plus_ms(submitted, 7_200_000)) if status == "finished" else None,
                completed_at=iso_ms(plus_ms(submitted, 7_200_000)) if status == "finished" else None,
                response_time_sec=900,
                completion_submitted=status == "finished",
                completion_note="已完成清理并拍照留档" if status == "finished" else "",
                closure_photo_path=ev.frames[-1].path if status == "finished" and ev.frames else "",
            )
            session.add(order)

        report = CitizenReport(
            report_no=report_no,
            phone=DEMO_CITIZEN_PHONE,
            kind=kind,
            media_name="demo-clip.mp4" if kind == "video" else "demo-photo.jpg",
            media_path="",
            location=location,
            description=desc,
            status=status,
            submitted_at=iso_ms(submitted),
            accepted_at=iso_ms(plus_ms(submitted, 900_000)) if status in ("accepted", "processing", "finished") else None,
            started_at=iso_ms(plus_ms(submitted, 1_500_000)) if status in ("processing", "finished") else None,
            finished_at=iso_ms(plus_ms(submitted, 7_200_000)) if status == "finished" else None,
            rejected_at=iso_ms(plus_ms(submitted, 600_000)) if status == "rejected" else None,
            reject_reason=reason,
            public_reply=reply,
            event_id=event_id,
            task_id=task_id,
            risk_flag=False,
            ai_report=json.dumps(_ai_snapshot(AI_VERDICTS[idx % len(AI_VERDICTS)]), ensure_ascii=False),
            ai_feedback=(
                json.dumps(
                    {
                        "agree": False,
                        "reason": "画面里只是路边的烟蒂收集桶溢出来了，并没有看到抛掷动作",
                        "expect": "希望按「设施满溢」派单处理，而不是计入违规行为",
                    },
                    ensure_ascii=False,
                )
                if idx == DISAGREE_AT
                else ""
            ),
            ai_feedback_at=iso_ms(plus_ms(submitted, 1_200_000)) if idx == DISAGREE_AT else "",
        )
        session.add(report)

        task_status = {
            "submitted": "queued",
            "accepted": "pending_review",
            "processing": "finished",
            "finished": "finished",
            "rejected": "finished",
        }.get(status, "queued")
        session.add(
            AnalysisTask(
                task_id=task_id,
                report_no=report_no,
                status=task_status,
                progress=100 if task_status == "finished" else 30,
                stage_detail="演示任务（算法管道未实现）",
                event_id=event_id,
                created_at=iso_ms(submitted),
                finished_at=iso_ms(plus_ms(submitted, 300_000)) if task_status == "finished" else None,
            )
        )

    _ = cam_by_id
    await session.flush()
