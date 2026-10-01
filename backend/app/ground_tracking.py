"""固定摄像头地面烟头的跨帧跟踪与新旧判定。

本模块不负责神经网络推理，只接收已经映射回原图坐标的检测框。这样跟踪逻辑可以
独立测试，也避免把“最近的人”误写成模型已经证明的责任人。人员绑定始终是
``candidate_association``，需要连续视频和人工复核。
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Iterable


BBox = tuple[float, float, float, float]


def _center(box: BBox) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def _bottom_center(box: BBox) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2.0, box[3])


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _iou(a: BBox, b: BBox) -> float:
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    if intersection <= 0:
        return 0.0
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return intersection / max(area_a + area_b - intersection, 1e-6)


@dataclass
class Track:
    track_id: str
    box: BBox
    first_seen_ms: int
    last_confirmed_ms: int
    first_frame: int
    last_frame: int
    classification: str
    confidence: float
    active: bool = True
    missed_frames: int = 0
    alert_emitted: bool = False
    associated_person_id: str | None = None
    association_distance_px: float | None = None
    association_updated_ms: int | None = None

    def public(self) -> dict:
        x, y = _center(self.box)
        return {
            "target_id": self.track_id,
            "classification": self.classification,
            "is_new": self.classification == "new",
            "first_seen_ms": self.first_seen_ms,
            "last_confirmed_ms": self.last_confirmed_ms,
            "position": {"x": round(x, 1), "y": round(y, 1)},
            "box": [round(v, 1) for v in self.box],
            "confidence": round(self.confidence, 1),
            "active": self.active,
            "missed_frames": self.missed_frames,
            "person_association": (
                {
                    "person_track_id": self.associated_person_id,
                    "distance_px": round(self.association_distance_px or 0.0, 1),
                    "updated_at_ms": self.association_updated_ms,
                    "relation": "candidate_association",
                    "notice": "仅表示时空距离最近，不等同于责任认定",
                }
                if self.associated_person_id
                else None
            ),
        }


@dataclass
class PersonObservation:
    timestamp_ms: int
    person_track_id: str
    points: list[tuple[float, float]]


@dataclass
class CameraState:
    frame_index: int = 0
    next_ground_id: int = 1
    next_person_id: int = 1
    ground_tracks: dict[str, Track] = field(default_factory=dict)
    person_tracks: dict[str, Track] = field(default_factory=dict)
    person_observations: list[PersonObservation] = field(default_factory=list)


class GroundTargetTracker:
    """轻量 ByteTrack 风格匹配器：IoU 优先，中心点距离补充小目标匹配。"""

    def __init__(
        self,
        *,
        baseline_frames: int = 30,
        max_missed_frames: int = 8,
        association_window_ms: int = 3000,
        center_distance_ratio: float = 0.045,
        remembered_distance_ratio: float = 0.025,
    ) -> None:
        self.baseline_frames = max(1, baseline_frames)
        self.max_missed_frames = max(1, max_missed_frames)
        self.association_window_ms = max(500, association_window_ms)
        self.center_distance_ratio = center_distance_ratio
        self.remembered_distance_ratio = remembered_distance_ratio
        self._states: dict[str, CameraState] = {}
        self._lock = threading.RLock()

    def reset(self, camera_id: str) -> None:
        with self._lock:
            self._states.pop(camera_id, None)

    def status(self, camera_id: str) -> dict:
        with self._lock:
            state = self._states.get(camera_id, CameraState())
            return self._status(camera_id, state)

    def process(
        self,
        camera_id: str,
        timestamp_ms: int,
        image_size: tuple[int, int],
        ground_detections: list[dict],
        person_detections: list[dict],
        hand_detections: list[dict] | None = None,
    ) -> dict:
        width, height = image_size
        diagonal = max(1.0, math.hypot(width, height))
        with self._lock:
            state = self._states.setdefault(camera_id, CameraState())
            state.frame_index += 1
            frame_index = state.frame_index

            persons = self._update_tracks(
                state,
                state.person_tracks,
                person_detections,
                timestamp_ms,
                frame_index,
                diagonal,
                prefix="P",
                classification="person",
            )
            self._remember_people(state, timestamp_ms, persons, hand_detections or [])

            baseline_ready = frame_index > self.baseline_frames
            before_ids = set(state.ground_tracks)
            grounds = self._update_tracks(
                state,
                state.ground_tracks,
                ground_detections,
                timestamp_ms,
                frame_index,
                diagonal,
                prefix="C",
                classification="new" if baseline_ready else "historical_baseline",
            )
            created = [track for track in grounds if track.track_id not in before_ids]
            alerts: list[dict] = []
            for track in created:
                if track.classification != "new":
                    continue
                self._associate_person(state, track, timestamp_ms)
                track.alert_emitted = True
                alerts.append(
                    {
                        "type": "new_ground_target",
                        "camera_id": camera_id,
                        "target": track.public(),
                        "candidate_association_only": True,
                    }
                )

            # 后 3 秒内出现的行人/手部也可更新新目标的候选关联。
            association_updates: list[dict] = []
            for track in state.ground_tracks.values():
                if track.classification == "new" and timestamp_ms - track.first_seen_ms <= self.association_window_ms:
                    previous = (track.associated_person_id, track.association_distance_px)
                    self._associate_person(state, track, timestamp_ms)
                    current = (track.associated_person_id, track.association_distance_px)
                    if current != previous and track.associated_person_id:
                        association_updates.append(
                            {
                                "target_id": track.track_id,
                                "person_association": track.public()["person_association"],
                            }
                        )

            return {
                **self._status(camera_id, state),
                "timestamp_ms": timestamp_ms,
                "targets": [track.public() for track in grounds],
                "people": [track.public() for track in persons],
                "alerts": alerts,
                "association_updates": association_updates,
                "policy": {
                    "new_target": f"冷启动 {self.baseline_frames} 帧完成后首次出现，且未匹配任何已知位置",
                    "occlusion_tolerance_frames": self.max_missed_frames,
                    "person_window_ms": self.association_window_ms,
                    "responsibility": "人员仅作候选时空关联，必须人工复核",
                },
            }

    def _status(self, camera_id: str, state: CameraState) -> dict:
        return {
            "camera_id": camera_id,
            "frame_index": state.frame_index,
            "baseline_frames": self.baseline_frames,
            "baseline_remaining": max(0, self.baseline_frames - state.frame_index),
            "baseline_ready": state.frame_index >= self.baseline_frames,
            "known_ground_targets": len(state.ground_tracks),
        }

    def _update_tracks(
        self,
        state: CameraState,
        tracks: dict[str, Track],
        detections: list[dict],
        timestamp_ms: int,
        frame_index: int,
        diagonal: float,
        *,
        prefix: str,
        classification: str,
    ) -> list[Track]:
        boxes = [tuple(float(v) for v in det["box"]) for det in detections]
        unmatched_tracks = set(tracks)
        unmatched_detections = set(range(len(boxes)))
        candidates: list[tuple[float, float, str, int]] = []
        for track_id, track in tracks.items():
            # 人员只在 ByteTrack 风格的短暂 lost buffer 内续接；不能因为后来有人
            # 走到相同位置，就复用很久以前的人员 ID。地面目标则需要长期位置记忆。
            if prefix == "P" and not track.active:
                continue
            for index, box in enumerate(boxes):
                iou = _iou(track.box, box)
                distance_ratio = _distance(_center(track.box), _center(box)) / diagonal
                limit = self.center_distance_ratio if track.active else self.remembered_distance_ratio
                if iou >= 0.05 or distance_ratio <= limit:
                    candidates.append((-iou, distance_ratio, track_id, index))
        candidates.sort()
        matched: list[Track] = []
        for _, _, track_id, index in candidates:
            if track_id not in unmatched_tracks or index not in unmatched_detections:
                continue
            track = tracks[track_id]
            track.box = boxes[index]
            track.last_confirmed_ms = timestamp_ms
            track.last_frame = frame_index
            track.confidence = float(detections[index].get("confidence", 0.0))
            track.active = True
            track.missed_frames = 0
            unmatched_tracks.remove(track_id)
            unmatched_detections.remove(index)
            matched.append(track)

        expired_people: list[str] = []
        for track_id in unmatched_tracks:
            track = tracks[track_id]
            track.missed_frames += 1
            if track.missed_frames > self.max_missed_frames:
                track.active = False
                if prefix == "P":
                    expired_people.append(track_id)

        for track_id in expired_people:
            tracks.pop(track_id, None)

        for index in sorted(unmatched_detections):
            if prefix == "C":
                number = state.next_ground_id
                state.next_ground_id += 1
            else:
                number = state.next_person_id
                state.next_person_id += 1
            track_id = f"{prefix}-{number:06d}"
            track = Track(
                track_id=track_id,
                box=boxes[index],
                first_seen_ms=timestamp_ms,
                last_confirmed_ms=timestamp_ms,
                first_frame=frame_index,
                last_frame=frame_index,
                classification=classification,
                confidence=float(detections[index].get("confidence", 0.0)),
            )
            tracks[track_id] = track
            matched.append(track)
        return sorted(matched, key=lambda item: item.track_id)

    def _remember_people(
        self,
        state: CameraState,
        timestamp_ms: int,
        people: Iterable[Track],
        hands: list[dict],
    ) -> None:
        hand_centers = [_center(tuple(float(v) for v in item["box"])) for item in hands]
        for person in people:
            x1, y1, x2, y2 = person.box
            margin_x = max(8.0, (x2 - x1) * 0.2)
            margin_y = max(8.0, (y2 - y1) * 0.15)
            points = [_bottom_center(person.box)]
            points.extend(
                point
                for point in hand_centers
                if x1 - margin_x <= point[0] <= x2 + margin_x
                and y1 - margin_y <= point[1] <= y2 + margin_y
            )
            state.person_observations.append(PersonObservation(timestamp_ms, person.track_id, points))
        cutoff = timestamp_ms - self.association_window_ms
        state.person_observations = [item for item in state.person_observations if item.timestamp_ms >= cutoff]

    def _associate_person(self, state: CameraState, target: Track, now_ms: int) -> None:
        target_point = _center(target.box)
        best: tuple[float, PersonObservation] | None = None
        for observation in state.person_observations:
            if abs(observation.timestamp_ms - target.first_seen_ms) > self.association_window_ms:
                continue
            distance = min(_distance(target_point, point) for point in observation.points)
            if best is None or distance < best[0]:
                best = (distance, observation)
        if best is None:
            return
        if target.association_distance_px is None or best[0] < target.association_distance_px:
            target.associated_person_id = best[1].person_track_id
            target.association_distance_px = best[0]
            target.association_updated_ms = now_ms


from .config import get_settings

_settings = get_settings()
ground_tracker = GroundTargetTracker(
    baseline_frames=_settings.ai_baseline_frames,
    max_missed_frames=_settings.ai_max_missed_frames,
    association_window_ms=_settings.ai_person_window_ms,
)

