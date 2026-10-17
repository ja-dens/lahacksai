"""Regression checks for the shared planning/fixture verifier, not the application."""

import copy
import hashlib
import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fixture_checker", ROOT / "scripts/check_contract_fixtures.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class ContractFixturesTest(unittest.TestCase):
    def setUp(self):
        self.inputs = copy.deepcopy(checker.load_inputs())
        self.bundle, self.defaults, self.env, self.image, self.chat = self.inputs

    def test_baseline_works_without_credentials_packages_or_network(self):
        with patch.dict(os.environ, {}, clear=True), patch("socket.socket", side_effect=AssertionError("Unexpected network")):
            checker.validate_bundle(*self.inputs)

    def test_environment_drift_is_rejected(self):
        self.inputs = (*self.inputs[:2], self.env.replace("CONTEXT_MESSAGE_LIMIT=25", "CONTEXT_MESSAGE_LIMIT=8"), *self.inputs[3:])
        with self.assertRaisesRegex(ValueError, "context limit differs"):
            checker.validate_bundle(*self.inputs)

    def test_credential_in_template_is_rejected(self):
        self.inputs = (*self.inputs[:2], self.env.replace("PHOTON_API_KEY=", "PHOTON_API_KEY=synthetic-test-secret"), *self.inputs[3:])
        with self.assertRaisesRegex(ValueError, "placeholders empty"):
            checker.validate_bundle(*self.inputs)

    def test_missing_id_wrong_type_and_extra_routing_field_are_rejected(self):
        for record, key, value, delete in (
            ("incoming_message", "message_id", None, True),
            ("interpretation_request", "context_message_limit", True, False),
            ("interpretation_request", "destination", "another-thread", False),
            ("interpretation_result", "recipient_id", "another-recipient", False),
        ):
            with self.subTest(record=record, key=key):
                inputs = copy.deepcopy(self.inputs)
                if delete:
                    del inputs[0][record][key]
                else:
                    inputs[0][record][key] = value
                with self.assertRaisesRegex(ValueError, "missing required|wrong type|unknown fields"):
                    checker.validate_bundle(*inputs)

    def test_naive_and_future_context_timestamps_are_rejected(self):
        for value, error in (("2026-10-17T19:00:00", "timezone"), ("2026-10-18T19:00:00+00:00", "future message")):
            with self.subTest(value=value):
                inputs = copy.deepcopy(self.inputs)
                inputs[0]["interpretation_request"]["recent_messages"][0]["sent_at"] = value
                with self.assertRaisesRegex(ValueError, error):
                    checker.validate_bundle(*inputs)

    def test_old_context_is_accepted_without_an_age_cutoff(self):
        request = self.bundle["interpretation_request"]
        value = "2020-01-01T00:00:00+00:00"
        request["recent_messages"][0]["sent_at"] = value
        self.chat["messages"][0]["sent_at"] = value
        self.bundle["saved_exchange"]["request"] = copy.deepcopy(request)
        canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        self.bundle["saved_exchange"]["request_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        checker.validate_bundle(*self.inputs)

    def test_context_count_text_size_and_profile_feedback_are_rejected(self):
        mutations = (
            lambda r: r.update(context_message_limit=19),
            lambda r: r["recent_messages"][0].update(text="x" * 4001),
            lambda r: r["user_context"].update(validated_exchanges=["past-feedback"]),
            lambda r: r.update(target_text="x" * 4001),
            lambda r: r["recent_messages"].append(copy.deepcopy(r["recent_messages"][0])),
        )
        for mutation in mutations:
            inputs = copy.deepcopy(self.inputs)
            mutation(inputs[0]["interpretation_request"])
            with self.subTest(mutation=mutations.index(mutation)), self.assertRaises(ValueError):
                checker.validate_bundle(*inputs)

    def test_altered_image_or_saved_snapshot_is_rejected(self):
        for target, key, value, error in (
            ("interpretation_request", "sticker", {"data_base64": "YQ==", "mime_type": "image/png", "sha256": "invalid"}, "Image fixture mismatch"),
            ("saved_exchange", "request_sha256", "altered", "Request digest mismatch"),
            ("saved_exchange", "delivered", True, "Fixture labeled as live"),
        ):
            inputs = copy.deepcopy(self.inputs)
            inputs[0][target][key] = value
            with self.subTest(target=target, key=key), self.assertRaisesRegex(ValueError, error):
                checker.validate_bundle(*inputs)

    def test_opposing_pair_and_duplicate_candidates_are_rejected(self):
        self.bundle["result_opposing"]["alternative"] = self.bundle["candidate_opposing"]["candidates"][1]
        with self.assertRaisesRegex(ValueError, "Opposing policy mismatch"):
            checker.validate_bundle(*self.inputs)
        self.setUp()
        self.bundle["candidate_compatible"]["candidates"][1] = self.bundle["candidate_compatible"]["candidates"][0]
        with self.assertRaisesRegex(ValueError, "Duplicate candidate"):
            checker.validate_bundle(*self.inputs)

    def test_forged_recipient_and_invalid_feedback_are_rejected(self):
        for target, key, value, error in (
            ("private_delivery", "recipient_id", "another-recipient", "Recipient mismatch"),
            ("private_delivery", "source_conversation_id", "another-chat", "Delivery source mismatch"),
            ("feedback", "selection", "second", "Second feedback choice was not shown"),
            ("feedback", "provenance", "sender_confirmed", "wrongly labeled sender confirmation"),
        ):
            inputs = copy.deepcopy(self.inputs)
            inputs[0][target][key] = value
            with self.subTest(target=target, key=key), self.assertRaisesRegex(ValueError, error):
                checker.validate_bundle(*inputs)


if __name__ == "__main__":
    unittest.main()
