from __future__ import annotations

import unittest

from app.ground_tracking import GroundTargetTracker


def detection(box, confidence=90.0):
    return {"box": list(box), "confidence": confidence}


class GroundTargetTrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = GroundTargetTracker(
            baseline_frames=3,
            max_missed_frames=2,
            association_window_ms=3000,
        )
        self.size = (1000, 600)

    def process(self, frame, cigarettes=None, people=None, hands=None):
        return self.tracker.process(
            "CAM-TEST",
            frame * 1000,
            self.size,
            cigarettes or [],
            people or [],
            hands or [],
        )

    def test_cold_start_target_is_historical_and_never_alerts(self):
        first = self.process(1, [detection((100, 400, 120, 420))])
        self.assertEqual(first["targets"][0]["classification"], "historical_baseline")
        self.assertEqual(first["alerts"], [])
        target_id = first["targets"][0]["target_id"]

        self.process(2, [detection((102, 401, 122, 421))])
        self.process(3, [])
        self.process(4, [])
        reappeared = self.process(5, [detection((103, 402, 123, 422))])
        self.assertEqual(reappeared["targets"][0]["target_id"], target_id)
        self.assertEqual(reappeared["targets"][0]["classification"], "historical_baseline")
        self.assertEqual(reappeared["alerts"], [])

    def test_new_target_after_baseline_alerts_once_and_survives_occlusion(self):
        self.process(1)
        self.process(2)
        self.process(3)
        created = self.process(4, [detection((700, 450, 720, 470))])
        self.assertTrue(created["baseline_ready"])
        self.assertEqual(len(created["alerts"]), 1)
        target_id = created["targets"][0]["target_id"]
        self.assertTrue(created["targets"][0]["is_new"])

        self.process(5)
        resumed = self.process(6, [detection((704, 452, 724, 472))])
        self.assertEqual(resumed["targets"][0]["target_id"], target_id)
        self.assertEqual(resumed["alerts"], [])

    def test_new_target_gets_nearest_person_candidate_not_responsibility(self):
        self.process(1)
        self.process(2)
        self.process(3, people=[detection((70, 100, 130, 430))])
        result = self.process(4, cigarettes=[detection((95, 435, 105, 445))])
        association = result["targets"][0]["person_association"]
        self.assertIsNotNone(association)
        self.assertEqual(association["person_track_id"], "P-000001")
        self.assertEqual(association["relation"], "candidate_association")
        self.assertIn("不等同于责任认定", association["notice"])

    def test_expired_person_id_is_not_reused_for_someone_else(self):
        first = self.process(1, people=[detection((70, 100, 130, 430))])
        self.assertEqual(first["people"][0]["target_id"], "P-000001")
        self.process(2)
        self.process(3)
        self.process(4)
        later = self.process(5, people=[detection((72, 100, 132, 430))])
        self.assertEqual(later["people"][0]["target_id"], "P-000002")


if __name__ == "__main__":
    unittest.main()

