"""端到端黄金路径验收。

依据《竞赛风险逐项解决规划》§5.1 黄金路径 与 §5.4 验收门槛，逐条给出可验证证据：

  市民上传 → 分析任务 → 事件候选 → 审核员确认 → 生成工单
  → 移动工作台接单并上传清理后照片 → 审核员确认闭环 → 市民端收到完成通知

运行（需后端已在 127.0.0.1:8000 启动）：
    python tests/test_golden_path.py
"""

from __future__ import annotations

import asyncio
import io
import json
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"
DEMO_PHONE = "13800000000"

results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> bool:
    results.append((ok, name, detail))
    flag = "PASS" if ok else "FAIL"
    print(f"[{flag}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def main() -> int:
    async with httpx.AsyncClient(timeout=30.0) as c:
        # ---------- 0. 服务存活 ----------
        r = await c.get(f"{BASE}/healthz")
        check(r.status_code == 200, "服务存活", f"/healthz {r.status_code}")

        # ---------- 1. 三角色登录，菜单/数据范围不同 ----------
        tokens: dict[str, str] = {}
        pages: dict[str, list[str]] = {}
        for username in ("admin", "worker01", "aidev"):
            r = await c.post(f"{API}/auth/login", json={"username": username, "password": "123456"})
            if r.status_code != 200:
                check(False, f"{username} 登录", f"{r.status_code} {r.text[:160]}")
                continue
            body = r.json()
            tokens[username] = body["access_token"]
            pages[username] = body["user"]["allowed_pages"]
            check(True, f"{username} 登录", f"角色 {body['user']['role_label']}，可见 {len(pages[username])} 个页面")

        check(
            bool(pages.get("admin")) and set(pages.get("worker", [])) < set(pages.get("admin", [])),
            "三角色菜单范围不同",
            f"admin {len(pages.get('admin', []))} 页 / worker01 {len(pages.get('worker01', []))} 页",
        )
        check(
            pages.get("worker01") == ["dispatch-pool", "dispatch-records"],
            "环卫工人仅见移动工作台",
            str(pages.get("worker01")),
        )

        # ---------- 2. 错误口令 → 401 + 统一错误码 ----------
        r = await c.post(f"{API}/auth/login", json={"username": "admin", "password": "wrong"})
        check(
            r.status_code == 401 and r.json().get("error_code") == "AUTH_INVALID_CREDENTIALS",
            "错误口令返回统一错误码",
            f"{r.status_code} {r.json().get('error_code')}",
        )

        admin = auth(tokens["admin"])
        worker = auth(tokens["worker01"])

        # ---------- 3. 权限不足：worker 访问账号管理 → 403 ----------
        r = await c.get(f"{API}/users", headers=worker)
        check(
            r.status_code == 403 and r.json().get("error_code") == "AUTH_PERMISSION_DENIED",
            "权限不足有明确错误态",
            f"{r.status_code} {r.json().get('error_code')}",
        )

        # ---------- 4. 统计基线 ----------
        r = await c.get(f"{API}/stats/overview", headers=admin)
        check(r.status_code == 200, "统计总览可用", json.dumps(r.json()["metrics"], ensure_ascii=False)[:150])
        before = r.json()["metrics"]

        # ---------- 5. WebSocket 订阅 ----------
        await _ws_case(c, admin, before)

        # ---------- 6. 一键演示一次违规 ----------
        r = await c.post(f"{API}/events/simulate", headers=admin, json={"create_workorder": True})
        ok = r.status_code == 201
        sim = r.json() if ok else {}
        check(
            ok and sim.get("order_no"),
            "一键演示一次违规（事件 + 自动建单）",
            f"事件 {sim.get('event', {}).get('event_id', '')[:8]} / 工单 {sim.get('order_no')}",
        )
        if ok:
            frames = sim["event"]["evidence_frames"]
            check(
                len(frames) == 3 and all(f["path"] for f in frames),
                "证据链三帧齐全且 path 非空",
                " / ".join(f"{f['type']}:{f['frame_code']}" for f in frames),
            )
            ts = [f["frame_ts"] for f in frames]
            check(ts[0] < ts[1] < ts[2], "三段式时间戳严格递增", " < ".join(t[11:23] for t in ts))
            check(
                all(t.endswith("+08:00") for t in ts),
                "时间戳带 +08:00 时区",
                ts[0],
            )
            check(
                len(sim["event"]["trajectory"]) >= 5,
                "轨迹点 ≥ 5",
                f"{len(sim['event']['trajectory'])} 个点",
            )

        # ---------- 7. 市民端登录 + 提交 ----------
        code_res = await c.post(
            f"{API}/auth/code/send", json={"target": DEMO_PHONE, "role": "citizen"}
        )
        demo_code = code_res.json().get("demo_code", "")
        r = await c.post(
            f"{API}/auth/citizen/login",
            json={"phone": DEMO_PHONE, "code": demo_code, "method": "code", "mode": "login"},
        )
        check(r.status_code == 200, "市民端登录", f"{r.status_code}")
        citizen = auth(r.json()["access_token"])

        r = await c.post(
            f"{API}/citizen/reports",
            headers=citizen,
            json={"kind": "video", "media_name": "clip.mp4", "location": "浉河区 · 演示点", "safe_confirmed": False},
        )
        check(
            r.status_code == 422 and r.json().get("error_code") == "RPT_SAFETY_NOT_CONFIRMED",
            "未勾选安全确认被拦下",
            f"{r.status_code} {r.json().get('error_code')}",
        )

        r = await c.post(
            f"{API}/citizen/reports",
            headers=citizen,
            json={
                "kind": "video",
                "media_name": "golden-path.mp4",
                "location": "浉河区 · 黄金路径演示点",
                "description": "端到端验收用上报",
                "safe_confirmed": True,
            },
        )
        check(r.status_code == 201, "市民提交线索", f"{r.status_code} {r.json().get('report_no') if r.status_code == 201 else r.text[:120]}")
        report_no = r.json()["report_no"]
        check(r.json()["status"] == "submitted", "上报初始状态为「已提交」", r.json()["status_label"])

        # 市民用管理员令牌访问 → 必须无效（令牌类型隔离）
        r = await c.get(f"{API}/citizen/reports", headers=admin)
        check(r.status_code == 401, "管理员令牌不能当市民令牌用", f"{r.status_code}")

        # ---------- 8. 管理端分析 → 待复核 ----------
        r = await c.post(f"{API}/reports/{report_no}/analyze", headers=admin)
        ok = r.status_code == 200
        check(
            ok and r.json()["report"]["status"] == "pending_review",
            "分析任务推进并派生候选事件",
            f"{r.status_code} 事件 {r.json().get('event_id', '')[:8] if ok else r.text[:120]}",
        )

        r = await c.get(f"{API}/citizen/reports/{report_no}", headers=citizen)
        check(
            r.json()["status"] == "pending_review",
            "市民端同步看到「待复核」",
            r.json()["status_label"],
        )

        # ---------- 9. 受理 → 自动建单 ----------
        r = await c.post(f"{API}/reports/{report_no}/accept", headers=admin)
        ok = r.status_code == 200
        order_no = r.json().get("order_no") if ok else None
        check(ok and order_no, "受理上报并自动生成工单", f"{r.status_code} {order_no}")

        r = await c.get(f"{API}/workorders", headers=admin, params={"size": 200})
        order = next((o for o in r.json()["items"] if o["order_no"] == order_no), None)
        check(order is not None and order["status"] == "pending", "工单进入调度任务池（待派发）", f"{order_no} / {order['status_label'] if order else '未找到'}")

        # ---------- 10. 作业端接单 → 市民端变「处理中」 ----------
        r = await c.post(f"{API}/workorders/{order['id']}/accept", headers=worker)
        check(r.status_code == 200 and r.json()["status"] == "accepted", "作业端接单", f"{r.status_code} {r.json().get('assigned_to', '')}")

        r = await c.get(f"{API}/citizen/reports/{report_no}", headers=citizen)
        check(
            r.json()["status"] == "processing",
            "一端操作、另一端可见（接单 → 市民端处理中）",
            r.json()["status_label"],
        )

        r = await c.post(f"{API}/workorders/{order['id']}/start", headers=worker)
        check(r.status_code == 200, "作业端开始处理", r.json().get("status_label", ""))

        # ---------- 11. 上传清理后照片 ----------
        photo = io.BytesIO(_tiny_png())
        r = await c.post(
            f"{API}/workorders/{order['id']}/complete",
            headers=worker,
            files={"photo": ("closure.png", photo.getvalue(), "image/png")},
            data={"note": "已完成清理"},
        )
        ok = r.status_code == 200
        check(ok and r.json()["status"] == "verifying", "上传清理后照片 → 待验收", f"{r.status_code} {r.json().get('closure_photo', '') if ok else r.text[:140]}")

        # ---------- 12. 重复提交拦截 ----------
        r = await c.post(
            f"{API}/workorders/{order['id']}/complete",
            headers=worker,
            files={"photo": ("closure.png", _tiny_png(), "image/png")},
            data={"note": "重复提交"},
        )
        check(
            r.status_code == 409 and r.json().get("error_code") == "WO_DUPLICATE_SUBMISSION",
            "重复提交被拦截",
            f"{r.status_code} {r.json().get('error_code')}",
        )

        # ---------- 13. 作业端无验收权 ----------
        r = await c.post(f"{API}/workorders/{order['id']}/verify", headers=worker, data={"passed": "true"})
        check(r.status_code == 403, "验收权限仅管理端", f"{r.status_code} {r.json().get('error_code')}")

        # ---------- 14. 管理端验收 → 闭环；市民端 → 已完成 ----------
        r = await c.post(f"{API}/workorders/{order['id']}/verify", headers=admin, data={"passed": "true", "note": "现场复核通过"})
        ok = r.status_code == 200
        check(ok and r.json()["status"] == "closed", "管理端验收通过 → 已闭环", f"{r.status_code} {r.json().get('status_label', '') if ok else r.text[:140]}")

        r = await c.get(f"{API}/citizen/reports/{report_no}", headers=citizen)
        body = r.json()
        check(
            body["status"] == "finished" and body["public_reply"],
            "市民端收到完成通知与公开回复",
            f"{body['status_label']} · {body['public_reply'][:28]}",
        )

        # ---------- 15. 免登录公开查询 ----------
        r = await c.get(f"{API}/public/cases/{report_no}")
        body = r.json() if r.status_code == 200 else {}
        check(
            r.status_code == 200 and "****" in body.get("phone", ""),
            "公开查询脱敏（不暴露实名信息）",
            f"{r.status_code} phone={body.get('phone')}",
        )

        # ---------- 16. 非法流转被拒 ----------
        r = await c.post(f"{API}/workorders/{order['id']}/accept", headers=worker)
        check(
            r.status_code == 409 and r.json().get("error_code") == "WO_CONFLICT",
            "已闭环工单不能再次接单（状态机拦截）",
            f"{r.status_code} {r.json().get('error_code')}",
        )

        # ---------- 17. 刷新后状态不回到初始值 ----------
        r1 = await c.get(f"{API}/workorders/stats", headers=admin)
        r2 = await c.get(f"{API}/workorders/stats", headers=admin)
        check(
            r1.json() == r2.json() and r1.json()["total"] > 0,
            "状态持久化（重复查询一致，非每次重建）",
            f"工单 {r1.json()['total']} 单 / 闭环率 {r1.json()['completion_rate']}%",
        )

        # ---------- 18. 审计日志留痕 ----------
        r = await c.get(f"{API}/audit/logs", headers=admin, params={"size": 200})
        actions = {x["action"] for x in r.json()["items"]}
        need = {"AUTH_LOGIN", "REPORT_SUBMIT", "REPORT_ACCEPT", "WORKORDER_ACCEPT", "WORKORDER_COMPLETE", "WORKORDER_VERIFY"}
        check(
            need <= actions,
            "关键操作全部留痕",
            f"共 {r.json()['total']} 条，覆盖 {len(need & actions)}/{len(need)} 类动作",
        )

        # ---------- 19. 建议由规则算出 ----------
        r = await c.get(f"{API}/suggestions", headers=admin)
        items = r.json()["items"]
        check(
            len(items) > 0 and all(i["content"] for i in items),
            "调度建议由规则引擎算出",
            f"{len(items)} 条：" + "、".join(i["type_label"] for i in items[:4]),
        )

        # ---------- 20. 事件证据链回读一致 ----------
        r = await c.get(f"{API}/events", headers=admin, params={"size": 5})
        first = r.json()["items"][0]
        r = await c.get(f"{API}/events/{first['event_id']}", headers=admin)
        detail = r.json()
        check(
            len(detail["evidence_frames"]) == 3
            and all(f["path"].startswith("/storage/") for f in detail["evidence_frames"]),
            "证据帧路径可访问",
            detail["evidence_frames"][0]["path"],
        )
        r = await c.get(f"{BASE}{detail['evidence_frames'][0]['path']}")
        check(r.status_code == 200 and int(r.headers.get("content-length", 0)) > 0, "证据帧文件真实存在", f"{r.status_code} {len(r.content)} bytes")

    failed = [x for x in results if not x[0]]
    print("\n=================== 黄金路径验收 ===================")
    print(f"通过 {len(results) - len(failed)} / {len(results)}")
    if failed:
        print("失败项：")
        for _, name, detail in failed:
            print(f"  - {name} {detail}")
    return 1 if failed else 0


async def _ws_case(c: httpx.AsyncClient, admin: dict, before: dict) -> None:
    """WebSocket 推送：订阅 /ws/alerts 后触发演示违规，应收到 event.created。"""
    try:
        import websockets
    except ImportError:
        check(False, "WebSocket 推送", "未安装 websockets 客户端库")
        return

    received: list[dict] = []
    try:
        token = admin["Authorization"].removeprefix("Bearer ")
        async with websockets.connect(f"ws://127.0.0.1:8000/ws/alerts?token={token}") as ws:
            hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            check(hello.get("type") == "connected", "WebSocket 连接", hello.get("channel", ""))

            await c.post(f"{API}/events/simulate", headers=admin, json={"create_workorder": False})
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=6))
                received.append(msg)
            except asyncio.TimeoutError:
                pass
    except Exception as exc:  # noqa: BLE001
        check(False, "WebSocket 推送", f"{type(exc).__name__}: {exc}")
        return

    check(
        bool(received) and received[0].get("type") == "event.created" and received[0].get("thumbnail_url"),
        "实时推送（事件 + 缩略图）",
        f"{received[0].get('event_id', '')[:8]} / {received[0].get('thumbnail_url', '')}" if received else "未收到推送",
    )


def _tiny_png() -> bytes:
    """1x1 PNG，用作闭环照片。"""
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c6300010000050001" + "0d0a2db40000000049454e44ae426082"
    )


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.exit(asyncio.run(main()))
