from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "e000-calibration-terminal-observation-v0.schema.json"
RECORD_PATH = (
    ROOT / "experiments" / "e-000" / "artifacts" / "calibration-terminal-observation-v0.json"
)


class CalibrationTerminalObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

    def codes(self, value: dict) -> list[str]:
        return [error.message for error in self.validator.iter_errors(value)]

    def test_retained_terminal_observation_accepts(self) -> None:
        self.assertEqual([], self.codes(self.record))

    def test_success_laundering_rejects(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["calibration_succeeded"] = True
        self.assertTrue(self.codes(changed))

    def test_retry_laundering_rejects(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["first_attempt"]["retry_count"] = 1
        self.assertTrue(self.codes(changed))

    def test_second_capture_laundering_rejects(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["remaining_actions"]["second_capture"] = "succeeded"
        self.assertTrue(self.codes(changed))

    def test_tier_laundering_rejects(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["tier_assignment"] = "T1"
        self.assertTrue(self.codes(changed))

    def test_candidate_inspection_rejects(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["candidate_inspected"] = True
        self.assertTrue(self.codes(changed))

    def test_unknown_fields_reject(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["private_command"] = "not public"
        self.assertTrue(self.codes(changed))


if __name__ == "__main__":
    unittest.main()
