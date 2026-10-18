import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.evaluate_stickers import evaluate


ROOT = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    def test_fixture_report_is_deterministic_and_not_accuracy(self):
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            first = evaluate(mode="fixture")
            second = evaluate(mode="fixture")
        self.assertEqual(first, second)
        self.assertTrue(first["all_policy_regressions_passed"])
        self.assertEqual(first["network_model_calls"], 0)
        self.assertFalse(first["fixture_output_is_model_accuracy"])
        self.assertIsNone(first["measured_model_accuracy"])
        self.assertEqual(
            set(first["pairs"]),
            {"context", "presentation", "relationship", "window_size"},
        )
        self.assertEqual({case["split"] for case in first["cases"]}, {"held_out"})

    def test_cli_fixture_report_is_machine_readable(self):
        run = subprocess.run(
            [sys.executable, "scripts/evaluate_stickers.py", "--mode", "fixture"],
            cwd=ROOT, check=False, capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)
        self.assertEqual(len(report["cases"]), 17)
        self.assertTrue(all(
            case["policy_regression_passed"] for case in report["cases"]
        ))

    @unittest.skipUnless((ROOT / "evaluation/hamster_pack.json").exists(),
                         "hamster pack is kept local-only")
    def test_every_hamster_reference_tile_reaches_the_pipeline(self):
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            report = evaluate(mode="fixture", dataset="hamster-pack")
        self.assertEqual(report["dataset"], "user-permitted-hamster-pack-reference-v1")
        self.assertEqual(len(report["cases"]), 19)
        self.assertEqual(len({case["id"] for case in report["cases"]}), 19)
        self.assertTrue(report["all_policy_regressions_passed"])
        self.assertEqual(report["network_model_calls"], 0)
        self.assertFalse(report["fixture_output_is_model_accuracy"])
        self.assertIsNone(report["measured_model_accuracy"])
        self.assertEqual({case["split"] for case in report["cases"]}, {"coverage"})


if __name__ == "__main__":
    unittest.main()
