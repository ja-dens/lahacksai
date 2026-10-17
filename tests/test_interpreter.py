import base64
from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import unittest

import httpx
from openai import APIStatusError, APITimeoutError, OpenAI
from PIL import Image

from src import interpreter
from src.adapters.vision import VisionAdapter

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures/contracts"


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


class InterpreterTests(unittest.TestCase):
    def setUp(self):
        self.request = fixture("interpretation_request")
        self.sent = []
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()

    def adapter(self, candidate=None, raw=None, status="completed", failure=None):
        candidate = fixture("candidate_single") if candidate is None else candidate

        def transport(request):
            self.sent.append(json.loads(request.content))
            if failure == "timeout":
                raise httpx.ReadTimeout("test timeout", request=request)
            if failure == "server":
                return httpx.Response(500, json={"error": {"message": "test error"}})
            return httpx.Response(200, json={
                "id": "resp_test", "object": "response", "created_at": 0,
                "status": status, "model": "test-vision",
                "output": [{"id": "msg_test", "type": "message", "role": "assistant", "status": "completed",
                            "content": [{"type": "output_text", "text": json.dumps(candidate) if raw is None else raw,
                                         "annotations": []}]}],
            })

        client = OpenAI(api_key="test-not-a-real-key", base_url="https://example.invalid/v1",
                        http_client=httpx.Client(transport=httpx.MockTransport(transport)))
        self.clients.append(client)
        return VisionAdapter(client, "test-vision")

    def assert_failed(self, adapter, snapshot, calls):
        self.assertEqual(len(self.sent), calls)
        self.assertEqual(adapter.last_run["status"], "failed")
        self.assertEqual(adapter.last_run["snapshot"], snapshot)
        self.assertIsNone(adapter.last_run["result"])
        self.assertIn("error_type", adapter.last_run)

    def test_all_published_policy_fixtures(self):
        for case in ("single", "compatible", "opposing", "unsupported"):
            with self.subTest(case=case):
                expected = fixture("interpretation_result" if case == "single" else f"result_{case}")
                self.assertEqual(interpreter.apply_candidate_policy("demo-3", fixture(f"candidate_{case}")), expected)

    def test_unrankable_candidates_abstain(self):
        for case in ("single", "compatible", "opposing"):
            candidate = fixture(f"candidate_{case}")
            candidate["rankable"] = False
            result = interpreter.apply_candidate_policy("demo-3", candidate)
            self.assertEqual(result["status"], "unsupported")
            self.assertEqual(result["meaning"], "")
            self.assertIsNone(result["alternative"])

    def test_reject_invalid_candidate_schema_and_policy(self):
        good = fixture("candidate_single")
        cases = [
            {**good, "candidates": ["one", "two", "three"]},
            {**good, "candidates": ["same", " SAME  "], "candidate_relation": "compatible"},
            {**good, "candidates": [""]}, {**good, "candidates": [1]},
            {**good, "candidate_relation": "made-up"}, {**good, "candidate_relation": []},
            {**good, "rankable": 1}, {**good, "rankable": "true"},
            {**good, "uncertainty_caveat": ""}, {**good, "context_cue": None},
            {**good, "candidates": ["x" * 1001]}, {**good, "recipient_id": "model-chosen"},
            {key: value for key, value in good.items() if key != "rankable"},
            {**fixture("candidate_unsupported"), "rankable": True},
        ]
        for candidate in cases:
            with self.subTest(candidate=candidate):
                with self.assertRaises(ValueError):
                    interpreter.apply_candidate_policy("demo-3", candidate)

    def test_one_serialized_request_contains_real_image_and_context(self):
        self.request["target_text"] = "Here is my reaction."
        before = deepcopy(self.request)
        adapter = self.adapter()
        self.assertEqual(adapter.interpret(self.request), fixture("interpretation_result"))
        self.assertEqual(self.request, before)
        self.assertEqual(len(self.sent), 1)
        payload = self.sent[0]
        self.assertFalse(payload["store"])
        self.assertNotIn("previous_response_id", payload)
        self.assertNotIn("tools", payload)
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertTrue(payload["text"]["format"]["strict"])
        text_part, image_part = payload["input"][0]["content"]
        actual_png = base64.b64decode(image_part["image_url"].split(",", 1)[1])
        self.assertEqual(actual_png, (ROOT / "fixtures/stickers/hamster_tongue_out.png").read_bytes())
        context = json.loads(text_part["text"])
        for key in ("recent_messages", "target_text", "target_text_truncated", "context_message_limit",
                    "context_text_character_budget", "context_age_limit", "user_context"):
            self.assertEqual(context[key], self.request[key])
        self.assertEqual(adapter.last_run["snapshot"], before)
        self.assertEqual(adapter.last_run["status"], "completed")

    def test_context_projection_excludes_history_feedback_and_routing(self):
        self.request.update(feedback="feedback-canary", older_history="history-canary",
                            private_delivery="destination-canary", api_key="secret-canary")
        self.request["user_context"]["feedback"] = "profile-feedback-canary"
        self.request["recent_messages"][0]["outside_window_reply"] = "reply-canary"
        self.adapter().interpret(self.request)
        text = json.dumps(self.sent[0])
        for canary in ("feedback-canary", "history-canary", "destination-canary", "secret-canary", "reply-canary"):
            self.assertNotIn(canary, text)
        context = json.loads(self.sent[0]["input"][0]["content"][0]["text"])
        self.assertNotIn("recipient_id", context)

    def test_old_messages_remain_and_unknown_relationship_is_allowed(self):
        self.request["recent_messages"][0]["sent_at"] = "2020-01-01T00:00:00+00:00"
        self.request["user_context"].update(relationship=None, relationship_source=None)
        self.adapter().interpret(self.request)
        context = json.loads(self.sent[0]["input"][0]["content"][0]["text"])
        self.assertEqual(context["recent_messages"][0]["sent_at"], "2020-01-01T00:00:00+00:00")

    def test_invalid_requests_fail_before_sdk(self):
        cases = []
        for key, value in (("schema_version", 1), ("schema_version", True), ("context_message_limit", 8),
                           ("context_age_limit", 3600), ("context_text_character_budget", 1),
                           ("target_text", "x" * 4001), ("target_text_truncated", "false"),
                           ("sent_at", "2026-10-17T19:00:06"), ("recent_messages", {})):
            request = deepcopy(self.request)
            request[key] = value
            cases.append(request)
        request = deepcopy(self.request)
        request["recent_messages"].reverse()
        cases.append(request)
        for key, value in (("text", "x" * 4001), ("sent_at", "2026-10-18T19:00:00+00:00"),
                           ("message_id", "demo-3"), ("kind", "unknown"), ("text_truncated", 1)):
            request = deepcopy(self.request)
            request["recent_messages"][0][key] = value
            cases.append(request)
        request = deepcopy(self.request)
        request["recent_messages"].append(deepcopy(request["recent_messages"][1]))
        cases.append(request)
        for request in cases:
            with self.subTest(request=request):
                adapter = self.adapter()
                with self.assertRaises(ValueError):
                    adapter.interpret(request)
                self.assert_failed(adapter, request, 0)

    def test_corrupt_and_unsupported_images_never_reach_sdk(self):
        media_cases = [
            {**self.request["sticker"], "mime_type": "image/gif"},
            {**self.request["sticker"], "sha256": "wrong"},
            {**self.request["sticker"], "data_base64": "not-base64!"},
        ]
        for data in (b"not a PNG", b"\x89PNG\r\n\x1a\n", b"x" * 5_000_001):
            media_cases.append({"data_base64": base64.b64encode(data).decode(), "mime_type": "image/png",
                                "sha256": hashlib.sha256(data).hexdigest()})
        animated = BytesIO()
        Image.new("RGB", (2, 2), "red").save(animated, format="PNG", save_all=True,
                                               append_images=[Image.new("RGB", (2, 2), "blue")], duration=100)
        data = animated.getvalue()
        media_cases.append({"data_base64": base64.b64encode(data).decode(), "mime_type": "image/png",
                            "sha256": hashlib.sha256(data).hexdigest()})
        for media in media_cases:
            with self.subTest(mime=media["mime_type"]):
                request = deepcopy(self.request)
                request["sticker"] = media
                adapter = self.adapter()
                with self.assertRaises((ValueError, OSError)):
                    adapter.interpret(request)
                self.assert_failed(adapter, request, 0)

    def test_invalid_json_schema_incomplete_or_refused_output_preserves_failure(self):
        for raw, status in (("not JSON", "completed"), ("[]", "completed"), ("{}", "completed"),
                            ('{"rankable":true,"rankable":false}', "completed"),
                            ("", "completed"), ("{}", "incomplete")):
            with self.subTest(raw=raw, status=status):
                self.sent.clear()
                adapter = self.adapter(raw=raw, status=status)
                with self.assertRaises(ValueError):
                    adapter.interpret(self.request)
                self.assert_failed(adapter, self.request, 1)

    def test_timeouts_and_server_errors_are_not_retried_or_interpreted(self):
        for failure, expected in (("timeout", APITimeoutError), ("server", APIStatusError)):
            with self.subTest(failure=failure):
                self.sent.clear()
                adapter = self.adapter(failure=failure)
                with self.assertRaises(expected):
                    adapter.interpret(self.request)
                self.assert_failed(adapter, self.request, 1)

    def test_semantic_unsupported_result_is_completed_not_an_operational_failure(self):
        adapter = self.adapter(candidate=fixture("candidate_unsupported"))
        self.assertEqual(adapter.interpret(self.request), fixture("result_unsupported"))
        self.assertEqual(adapter.last_run["status"], "completed")
        self.assertEqual(len(self.sent), 1)


if __name__ == "__main__":
    unittest.main()
