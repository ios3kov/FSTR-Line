"""Definition consistency only; these tests do not attach to or execute AE."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2] / "research/ae-notifications"


class CompletionTargetTests(unittest.TestCase):
    def test_exact_identity_matches_existing_control(self):
        target = json.loads((ROOT / "completion_targets.json").read_text())
        control = json.loads((ROOT / "context_targets.json").read_text())
        for key in ("aeBundleId", "aeShortVersion", "aeBundleVersion"):
            self.assertEqual(target[key], control[key])
        self.assertEqual(target["modules"]["BEE"], control["modules"]["BEE"])
        self.assertEqual(target["SYNC-001"], "NOT RUN")

    def test_edge_and_call_sites_are_separate_and_bounded(self):
        target = json.loads((ROOT / "completion_targets.json").read_text())
        points = target["breakpoints"]
        self.assertEqual(len(points), 8)
        self.assertEqual(len({p["label"] for p in points}), 8)
        self.assertEqual(len({p["fileAddress"] for p in points}), 8)
        for name in ("command", "group", "undo", "redo"):
            edge = next(p for p in points if p["label"] == name + "-completion-edge")
            call = next(p for p in points if p["label"] == name + "-signal-call")
            self.assertEqual(edge["role"], "activity-edge-candidate")
            self.assertEqual(call["role"], "signal-call-candidate")
            self.assertLess(int(edge["fileAddress"], 16), int(call["fileAddress"], 16))
        for point in points:
            self.assertEqual(point["module"], "BEE")
            self.assertEqual((point["minLocations"], point["maxLocations"]), (1, 1))


if __name__ == "__main__":
    unittest.main()
