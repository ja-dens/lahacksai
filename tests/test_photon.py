"""T2 contract/security/transport tests. Every provider operation is fake."""

import base64
import copy
import hashlib
import hmac
import importlib.util
import json
import socket
import struct
import subprocess
import sys
import unittest
import zlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
# Load only T2's file to keep its transport tests independent of other components.
SPEC = importlib.util.spec_from_file_location("_standalone_t2_photon", ROOT / "src/adapters/photon.py")
PHOTON = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PHOTON
SPEC.loader.exec_module(PHOTON)
Attachment, HTTPResponse = PHOTON.Attachment, PHOTON.HTTPResponse
MAX_MEDIA_BYTES, MAX_WEBHOOK_BYTES = PHOTON.MAX_MEDIA_BYTES, PHOTON.MAX_WEBHOOK_BYTES
PhotonAdapter, PhotonError = PHOTON.PhotonAdapter, PHOTON.PhotonError
PhotonHTTPClient, PrivateDestination = PHOTON.PhotonHTTPClient, PHOTON.PrivateDestination
_NoRedirect, urllib_transport = PHOTON._NoRedirect, PHOTON.urllib_transport
PNG = (ROOT / "fixtures/stickers/laughing.png").read_bytes()
PROJECT, AGENT, RECIPIENT = "demo-project", "demo-agent", "demo-older-recipient"
SOURCE, PRIVATE, ATTACHMENT = "demo-family-chat", "demo-private-thread", "demo-attachment"


def message(*, kind="sticker", message_id="demo-3"):
    return {
        "id": message_id, "projectId": PROJECT, "platform": "imessage", "status": "received",
        "sentBy": {"id": "demo-younger-sender", "projectId": PROJECT, "platform": "imessage"},
        "space": {"id": SOURCE, "projectId": PROJECT, "platform": "imessage"},
        "timestamps": {"receivedAt": "2026-10-17T12:00:06-07:00"},
        "content": ({"type": "text", "format": "plain", "text": "Hello"} if kind == "text" else
                    {"type": "attachment", "attachmentId": ATTACHMENT, "metadata": {"demo": {"kind": kind}}}),
    }


def body_for(value):
    # Deliberately synthetic envelope; real beta event schemas are version-specific.
    return json.dumps({"type": "demo.message.received", "data": {"message": value}}).encode()


def signed_headers(raw):
    return {"X-Test-Signature": hmac.new(b"synthetic-test-key", raw, hashlib.sha256).hexdigest()}


def verify(raw, headers):
    return hmac.compare_digest(signed_headers(raw)["X-Test-Signature"], headers.get("X-Test-Signature", ""))


def decode(envelope):
    return envelope["data"]["message"] if envelope["type"] == "demo.message.received" else None


def destination(delivery):
    if delivery["recipient_id"] != RECIPIENT:
        raise PermissionError("not enrolled")
    return PrivateDestination(RECIPIENT, SOURCE, "imessage", PRIVATE, AGENT, RECIPIENT,
                              (AGENT, RECIPIENT), verified=True)


def delivery():
    return json.loads((ROOT / "fixtures/contracts/private_delivery.json").read_text())


class FakeProvider:
    def __init__(self):
        self.fetches, self.sends, self.accepted = [], [], {}
        self.attachment = Attachment(PNG, "image/png")
        self.fetch_error = self.send_error = None
        self.reply = None

    def fetch_attachment(self, attachment_id, **options):
        self.fetches.append((attachment_id, options))
        if self.fetch_error:
            raise self.fetch_error
        return self.attachment

    def send_message(self, body, *, idempotency_key, timeout):
        self.sends.append((copy.deepcopy(body), idempotency_key, timeout))
        if self.send_error:
            raise self.send_error
        if self.reply is not None:
            return self.reply
        if idempotency_key in self.accepted:
            old, result = self.accepted[idempotency_key]
            if old != body:
                raise PhotonError("provider_http_409")
            return result
        result = {"id": "accepted-" + str(len(self.accepted) + 1), "status": "accepted"}
        self.accepted[idempotency_key] = (copy.deepcopy(body), result)
        return result


class NoNetworkTests(unittest.TestCase):
    def setUp(self):
        self.socket_guard = patch.object(socket, "socket", side_effect=AssertionError("Network forbidden in T2 tests"))
        self.connection_guard = patch.object(socket, "create_connection", side_effect=AssertionError("Network forbidden in T2 tests"))
        self.socket_guard.start()
        self.connection_guard.start()
        self.addCleanup(self.socket_guard.stop)
        self.addCleanup(self.connection_guard.stop)
        self.provider, self.seen = FakeProvider(), []
        self.adapter = self.make_adapter()

    def make_adapter(self, **overrides):
        options = dict(project_id=PROJECT, platform="imessage", assistant_ids={AGENT}, client=self.provider,
                       verify_event=verify, decode_event=decode, resolve_destination=destination,
                       classify_attachment=lambda msg, part: part.get("metadata", {}).get("demo", {}).get("kind", "other"))
        return PhotonAdapter(**dict(options, **overrides))

    def receive(self, value, *, adapter=None):
        raw = body_for(value)
        return (adapter or self.adapter).receive_webhook(raw, signed_headers(raw), self.seen.append)


class IncomingTests(NoNetworkTests):
    def test_sticker_matches_v2_shape_and_actual_media(self):
        result = self.receive(message())
        expected = json.loads((ROOT / "fixtures/contracts/incoming_message.json").read_text())
        self.assertEqual(result.status, "forwarded")
        self.assertEqual(result.trigger, "interpret_sticker")
        self.assertEqual(set(result.event), set(expected))
        self.assertEqual(result.event["sent_at"], "2026-10-17T19:00:06.000000+00:00")
        self.assertEqual(base64.b64decode(result.event["sticker"]["data_base64"]), PNG)
        self.assertEqual(result.event["sticker"]["sha256"], hashlib.sha256(PNG).hexdigest())
        self.assertEqual(self.provider.fetches[0][1], {"max_bytes": MAX_MEDIA_BYTES, "timeout": 10.0})
        self.assertEqual(self.seen, [result.event])

    def test_text_only_updates_history_without_media_access(self):
        result = self.receive(message(kind="text"))
        self.assertEqual(result.trigger, "history_only")
        self.assertEqual(result.event["text"], "Hello")
        self.assertEqual(result.event["kind"], "text")
        self.assertIsNone(result.event["sticker"])
        self.assertEqual(self.provider.fetches, [])

    def test_absent_text_and_reply_reference_are_preserved(self):
        value = message(); value["parentMessageId"] = "earlier-source-message"
        result = self.receive(value)
        self.assertIsNone(result.event["text"])
        self.assertEqual(result.event["reply_to_message_id"], "earlier-source-message")

    def test_grouped_text_and_sticker_are_one_source_event(self):
        value = message(); attachment = value["content"]
        value["content"] = {"type": "group", "parts": [{"type": "text", "text": "Nice!"}, attachment]}
        result = self.receive(value)
        self.assertEqual(result.event["text"], "Nice!")
        self.assertEqual(result.event["message_id"], "demo-3")
        self.assertEqual(result.trigger, "interpret_sticker")
        self.assertEqual(len(self.seen), 1)

    def test_ordinary_photo_is_history_only_and_not_downloaded(self):
        result = self.receive(message(kind="image"))
        self.assertEqual(result.trigger, "history_only")
        self.assertEqual(result.event["kind"], "image")
        self.assertIsNone(result.event["sticker"])
        self.assertEqual(self.provider.fetches, [])

    def test_no_default_sticker_classifier(self):
        result = self.receive(message(), adapter=self.make_adapter(classify_attachment=None))
        self.assertEqual(result.event["kind"], "other")
        self.assertEqual(self.provider.fetches, [])

    def test_audio_is_prior_media_not_a_sticker(self):
        result = self.receive(message(kind="audio"))
        self.assertEqual(result.event["kind"], "audio")
        self.assertEqual(result.trigger, "history_only")
        self.assertEqual(self.provider.fetches, [])

    def test_multiple_attachments_take_automatic_unsupported_path(self):
        value = message(); value["content"] = {"type": "group", "parts": [value["content"], copy.deepcopy(value["content"])]}
        result = self.receive(value)
        self.assertEqual(result.event["kind"], "sticker")
        self.assertIsNone(result.event["sticker"])
        self.assertEqual(result.trigger, "interpret_sticker")
        self.assertEqual(result.warning, "multiple_media_unsupported")
        self.assertEqual(self.provider.fetches, [])

    def test_outbound_and_own_agent_echo_events_are_ignored(self):
        for change in ("status", "sender"):
            with self.subTest(change=change):
                value = message()
                if change == "status": value["status"] = "dispatched"
                else: value["sentBy"]["id"] = AGENT
                self.assertEqual(self.receive(value).status, "ignored")
        self.assertEqual(self.seen, [])
        self.assertEqual(self.provider.fetches, [])

    def test_read_and_typing_events_do_not_pollute_history(self):
        for kind in ("message.read", "space.typing.update", "reaction"):
            value = message(); value["content"] = {"type": kind}
            self.assertEqual(self.receive(value).status, "ignored")
        self.assertEqual(self.seen, [])

    def test_source_scope_mismatches_are_rejected(self):
        for parent, key in ((None, "projectId"), (None, "platform"), ("space", "projectId"), ("sentBy", "platform")):
            value = message(); (value if parent is None else value[parent])[key] = "another-scope"
            result = self.receive(value)
            self.assertEqual(result.error_code, "source_scope_mismatch")
        self.assertEqual(self.seen, [])

    def test_naive_or_invalid_timestamps_are_rejected(self):
        for stamp in (None, "not-a-time", "2026-10-17T12:00:00"):
            value = message(); value["timestamps"]["receivedAt"] = stamp
            self.assertEqual(self.receive(value).error_code, "invalid_timestamp")
        self.assertEqual(self.seen, [])

    def test_invalid_source_records_are_rejected(self):
        for edit in (lambda m: m.update(id=""), lambda m: m.update(space=None),
                     lambda m: m.update(parentMessageId=9), lambda m: m.update(content={"type": "text", "text": 9}),
                     lambda m: m.update(content={"type": "group", "parts": []})):
            value = message(); edit(value)
            self.assertEqual(self.receive(value).status, "rejected")
        self.assertEqual(self.seen, [])

    def test_bad_classifier_is_rejected(self):
        result = self.receive(message(), adapter=self.make_adapter(classify_attachment=lambda m, p: "guess"))
        self.assertEqual(result.error_code, "invalid_media_classification")

    def test_replays_keep_identity_and_reach_coordinator_ledger(self):
        first, second = self.receive(message()), self.receive(message())
        self.assertEqual(first.event, second.event)
        self.assertEqual(len(self.seen), 2)  # Adapter does not silently own a second dedup ledger.

    def test_identical_images_in_distinct_messages_are_both_forwarded(self):
        first, second = self.receive(message()), self.receive(message(message_id="demo-4"))
        self.assertNotEqual(first.event["message_id"], second.event["message_id"])
        self.assertEqual(first.event["sticker"]["sha256"], second.event["sticker"]["sha256"])
        self.assertEqual(len(self.seen), 2)

    def test_old_and_out_of_order_source_times_are_preserved(self):
        value = message(); value["timestamps"]["receivedAt"] = "2020-01-01T00:00:00Z"
        current = self.receive(message()); old = self.receive(value)
        self.assertEqual(old.event["sent_at"], "2020-01-01T00:00:00.000000+00:00")
        self.assertEqual([x["sent_at"] for x in self.seen], [current.event["sent_at"], old.event["sent_at"]])


class AuthenticationTests(NoNetworkTests):
    def test_standalone_import_never_initializes_other_application_modules(self):
        script = '''
import importlib.abc, importlib.util, socket, sys, urllib.request
from pathlib import Path
def deny_network(*args, **kwargs):
    raise RuntimeError("Network forbidden")
socket.socket = deny_network
socket.create_connection = deny_network
class DenyApplication(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "src" or fullname.startswith("src."):
            raise RuntimeError("Application import forbidden")
sys.meta_path.insert(0, DenyApplication())
spec = importlib.util.spec_from_file_location("_isolated_photon", Path("src/adapters/photon.py"))
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
assert module.PhotonAdapter is not None
'''
        result = subprocess.run([sys.executable, "-S", "-c", script], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_authentication_uses_exact_raw_bytes_before_decoder(self):
        calls = []
        adapter = self.make_adapter(verify_event=lambda raw, headers: calls.append(raw) or False,
                                    decode_event=lambda event: self.fail("Decoded unauthenticated bytes"))
        raw = b"invalid JSON containing a fake secret"
        self.assertEqual(adapter.receive_webhook(raw, {}, self.seen.append).error_code, "authentication_failed")
        self.assertEqual(calls, [raw])
        self.assertEqual(self.seen, [])

    def test_tampered_body_and_missing_signature_are_rejected(self):
        raw = body_for(message())
        for body, headers in ((raw, {}), (raw + b" ", signed_headers(raw))):
            self.assertEqual(self.adapter.receive_webhook(body, headers, self.seen.append).status, "rejected")
        self.assertEqual(self.provider.fetches, [])

    def test_verifier_error_or_truthy_non_boolean_fails_closed(self):
        def broken(raw, headers): raise RuntimeError("fake-key-must-not-leak")
        for verifier in (broken, lambda raw, headers: "yes", lambda raw, headers: 1):
            adapter = self.make_adapter(verify_event=verifier)
            result = self.receive(message(), adapter=adapter)
            self.assertEqual(result.error_code, "authentication_failed")
            self.assertNotIn("fake-key", repr(result))

    def test_missing_authentication_callback_is_not_allowed(self):
        with self.assertRaises(ValueError): self.make_adapter(verify_event=None)

    def test_constructor_rejects_missing_identity_and_non_finite_timeout(self):
        for changes in ({"assistant_ids": AGENT}, {"assistant_ids": set()}, {"timeout": 0},
                        {"timeout": float("nan")}, {"timeout": float("inf")}, {"timeout": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.make_adapter(**changes)

    def test_malformed_duplicate_key_and_non_finite_json_are_rejected(self):
        for raw in (b'{', b'[]', b'{"type":"first","type":"second"}', b'{"value":NaN}'):
            result = self.adapter.receive_webhook(raw, signed_headers(raw), self.seen.append)
            self.assertEqual(result.status, "rejected")
        self.assertEqual(self.seen, [])

    def test_webhook_size_cap_precedes_parsing_and_media_access(self):
        result = self.adapter.receive_webhook(b"x" * (MAX_WEBHOOK_BYTES + 1), {}, self.seen.append)
        self.assertEqual(result.error_code, "invalid_webhook_size")
        self.assertEqual(self.provider.fetches, [])

    def test_unknown_event_is_ignored_by_injected_decoder(self):
        raw = b'{"type":"demo.unrelated"}'
        self.assertEqual(self.adapter.receive_webhook(raw, signed_headers(raw), self.seen.append).status, "ignored")

    def test_coordinator_failure_is_retryable_without_leaking_error(self):
        def broken(event): raise RuntimeError("fake-key-and-chat-text")
        raw = body_for(message(kind="text"))
        result = self.adapter.receive_webhook(raw, signed_headers(raw), broken)
        self.assertEqual(result.error_code, "coordinator_failed")
        self.assertTrue(result.retryable)
        self.assertNotIn("fake-key", repr(result))


class MediaTests(NoNetworkTests):
    def test_media_limit_matches_shared_v2_configuration(self):
        defaults = json.loads((ROOT / "config/defaults.v2.json").read_text())
        self.assertEqual(MAX_MEDIA_BYTES, defaults["target_sticker_max_bytes"])
        self.assertEqual(defaults["target_sticker_mime_types"], ["image/png"])

    def test_unavailable_attachment_keeps_automatic_abstention_path(self):
        self.provider.fetch_error = PhotonError("provider_http_404")
        result = self.receive(message())
        self.assertEqual(result.warning, "provider_http_404")
        self.assertEqual(result.trigger, "interpret_sticker")
        self.assertIsNone(result.event["sticker"])

    def test_transient_timeout_does_not_persist_empty_media_as_final_input(self):
        self.provider.fetch_error = TimeoutError("fake-key")
        result = self.receive(message())
        self.assertEqual(result.error_code, "media_timeout")
        self.assertTrue(result.retryable)
        self.assertEqual(self.seen, [])
        self.assertNotIn("fake-key", repr(result))

    def test_transient_provider_failure_is_safe_and_retryable(self):
        self.provider.fetch_error = PhotonError("provider_http_503", retryable=True)
        result = self.receive(message())
        self.assertTrue(result.retryable)
        self.assertEqual(self.seen, [])
        self.provider.fetch_error = RuntimeError("fake-key")
        self.assertEqual(self.receive(message()).error_code, "media_fetch_failed")

    def test_bad_credentials_or_cross_project_media_are_operational_errors(self):
        for code in ("provider_http_401", "provider_http_403", "media_scope_mismatch"):
            self.provider.fetch_error = PhotonError(code)
            result = self.receive(message())
            self.assertEqual(result.status, "rejected")
            self.assertEqual(result.error_code, code)
            self.assertIsNone(result.event)
        self.assertEqual(self.seen, [])

    def test_unsupported_mime_and_oversized_bytes_are_not_sent_to_coordinator_as_media(self):
        for attachment, warning in ((Attachment(PNG, "image/webp"), "unsupported_media"),
                                    (Attachment(b"x" * (MAX_MEDIA_BYTES + 1), "image/png"), "media_too_large")):
            self.provider.attachment = attachment
            result = self.receive(message())
            self.assertEqual(result.warning, warning)
            self.assertIsNone(result.event["sticker"])

    def test_truncated_and_bad_crc_png_are_rejected(self):
        for data in (PNG[:8], PNG[:-1], PNG[:30] + bytes([PNG[30] ^ 1]) + PNG[31:], b"not png"):
            self.provider.attachment = Attachment(data, "image/png")
            result = self.receive(message())
            self.assertIn(result.warning, ("invalid_png", "unsupported_media"))
            self.assertIsNone(result.event["sticker"])

    def test_apng_is_an_explicit_unsupported_static_format(self):
        payload = struct.pack(">II", 2, 0)
        chunk = struct.pack(">I", len(payload)) + b"acTL" + payload + struct.pack(">I", zlib.crc32(b"acTL" + payload))
        self.provider.attachment = Attachment(PNG[:33] + chunk + PNG[33:], "image/png")
        self.assertEqual(self.receive(message()).warning, "animated_media_unsupported")


class DeliveryTests(NoNetworkTests):
    def test_send_uses_only_verified_private_destination_and_plain_text(self):
        result = self.adapter.send_private_explanation(delivery())
        body, key, timeout = self.provider.sends[0]
        self.assertEqual(result.status, "accepted")
        self.assertEqual(body, {"spaceId": PRIVATE, "senderId": AGENT,
                                "content": {"type": "text", "format": "plain", "text": delivery()["text"]}})
        self.assertNotIn("parentMessageId", body)
        self.assertNotEqual(body["spaceId"], SOURCE)
        self.assertEqual(result.idempotency_key, key)
        self.assertFalse(result.delivered)

    def test_retry_same_logical_delivery_has_same_key_and_provider_message(self):
        first = self.adapter.send_private_explanation(delivery())
        second = self.adapter.send_private_explanation(delivery())
        self.assertEqual(first.idempotency_key, second.idempotency_key)
        self.assertEqual(first.provider_message_id, second.provider_message_id)
        self.assertEqual(len(self.provider.accepted), 1)

    def test_distinct_sticker_messages_have_distinct_send_keys(self):
        first = self.adapter.send_private_explanation(delivery())
        other = dict(delivery(), source_message_id="demo-4")
        self.assertNotEqual(first.idempotency_key, self.adapter.send_private_explanation(other).idempotency_key)
        self.assertEqual(len(self.provider.accepted), 2)

    def test_changed_retry_text_uses_original_identity_and_surfaces_conflict(self):
        first = self.adapter.send_private_explanation(delivery())
        second = self.adapter.send_private_explanation(dict(delivery(), text="changed text"))
        self.assertEqual(first.idempotency_key, second.idempotency_key)
        self.assertEqual(second.error_code, "provider_http_409")
        self.assertEqual(len(self.provider.accepted), 1)

    def test_group_extra_participant_and_unverified_routes_are_rejected(self):
        base = destination(delivery())
        for route in (replace(base, kind="group"), replace(base, participant_ids=(AGENT, RECIPIENT, "someone-else")), replace(base, verified=False)):
            result = self.make_adapter(resolve_destination=lambda value, route=route: route).send_private_explanation(delivery())
            self.assertEqual(result.status, "error")
        self.assertEqual(self.provider.sends, [])

    def test_route_must_match_enrollment_source_platform_and_recipient(self):
        base = destination(delivery())
        for change in ({"recipient_id": "other"}, {"source_conversation_id": "other"},
                       {"platform": "telegram"}, {"sender_id": "other-agent"}):
            route = replace(base, **change)
            result = self.make_adapter(resolve_destination=lambda value, route=route: route).send_private_explanation(delivery())
            self.assertEqual(result.error_code, "destination_binding_mismatch")
        self.assertEqual(self.provider.sends, [])

    def test_delivery_cannot_supply_destination_or_other_model_fields(self):
        for field in ("destination", "spaceId", "senderId", "alternative", "command"):
            self.assertEqual(self.adapter.send_private_explanation(dict(delivery(), **{field: "source-group"})).error_code, "invalid_delivery")
        self.assertEqual(self.provider.sends, [])

    def test_denied_recipient_is_not_treated_as_a_retryable_send(self):
        result = self.adapter.send_private_explanation(dict(delivery(), recipient_id="not-enrolled"))
        self.assertEqual(result.error_code, "unauthorized_destination")
        self.assertFalse(result.retryable)
        self.assertEqual(self.provider.sends, [])

    def test_empty_and_invalid_delivery_fields_are_rejected(self):
        for item in ({}, [], dict(delivery(), text=""), dict(delivery(), recipient_id=None)):
            self.assertEqual(self.adapter.send_private_explanation(item).status, "error")
        self.assertEqual(self.provider.sends, [])

    def test_send_timeout_returns_stable_key_and_unknown_delivery(self):
        self.provider.send_error = TimeoutError("fake-api-key")
        first = self.adapter.send_private_explanation(delivery())
        second = self.adapter.send_private_explanation(delivery())
        self.assertEqual(first.error_code, "send_timeout")
        self.assertTrue(first.retryable)
        self.assertEqual(first.idempotency_key, second.idempotency_key)
        self.assertFalse(first.delivered)
        self.assertNotIn("fake-api-key", repr(first))

    def test_provider_errors_and_bad_acknowledgments_never_claim_acceptance(self):
        self.provider.send_error = RuntimeError("fake-api-key")
        self.assertEqual(self.adapter.send_private_explanation(delivery()).error_code, "send_failed")
        self.provider.send_error = None
        for reply in ({}, {"id": "id", "status": "failed"}, [], {"id": "", "status": "accepted"}):
            self.provider.reply = reply
            self.assertEqual(self.adapter.send_private_explanation(delivery()).status, "error")

    def test_even_provider_delivered_status_is_not_claimed_as_observed_phone_receipt(self):
        self.provider.reply = {"id": "id", "status": "delivered"}
        result = self.adapter.send_private_explanation(delivery())
        self.assertEqual(result.provider_status, "delivered")
        self.assertFalse(result.delivered)


class HTTPClientTests(NoNetworkTests):
    def setUp(self):
        super().setUp()
        self.calls, self.responses = [], []
        self.client = PhotonHTTPClient(project_id=PROJECT, api_key="synthetic-placeholder", transport=self.transport)

    def transport(self, method, url, **options):
        self.calls.append((method, url, options))
        response = self.responses.pop(0)
        if isinstance(response, Exception): raise response
        return response

    def test_documented_send_path_headers_and_body(self):
        ack = {"id": "provider-message", "status": "accepted", "projectId": PROJECT,
               "space": {"id": PRIVATE}, "sentBy": {"id": AGENT}}
        self.responses = [HTTPResponse(202, json.dumps(ack).encode(), {})]
        body = {"spaceId": PRIVATE, "senderId": AGENT, "content": {"type": "text", "format": "plain", "text": "Hi"}}
        result = self.client.send_message(body, idempotency_key="stable-test-key", timeout=3)
        method, url, options = self.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://api.photon.codes/v1/projects/demo-project/messages")
        self.assertEqual(options["headers"]["idempotency-key"], "stable-test-key")
        self.assertEqual(options["headers"]["Authorization"], "Bearer synthetic-placeholder")
        self.assertEqual(json.loads(options["body"]), body)
        self.assertEqual(options["timeout"], 3)
        self.assertEqual(result["id"], "provider-message")

    def test_acknowledgment_must_match_requested_project_space_and_sender(self):
        ack = {"id": "provider-message", "status": "accepted", "projectId": PROJECT,
               "space": {"id": PRIVATE}, "sentBy": {"id": AGENT}}
        body = {"spaceId": PRIVATE, "senderId": AGENT, "content": {}}
        for change in ({"projectId": "other"}, {"space": {"id": SOURCE}}, {"sentBy": {"id": "other"}}):
            self.responses = [HTTPResponse(202, json.dumps(dict(ack, **change)).encode(), {})]
            with self.assertRaisesRegex(PhotonError, "send_scope_mismatch"):
                self.client.send_message(body, idempotency_key="key", timeout=3)

    def test_rest_send_requires_documented_202_status(self):
        self.responses = [HTTPResponse(200, b'{}', {})]
        with self.assertRaisesRegex(PhotonError, "provider_http_200"):
            self.client.send_message({}, idempotency_key="key", timeout=3)

    def test_documented_attachment_metadata_then_bounded_content(self):
        metadata = {"id": ATTACHMENT, "projectId": PROJECT, "contentType": "image/png", "sizeBytes": len(PNG)}
        self.responses = [HTTPResponse(200, json.dumps(metadata).encode(), {}), HTTPResponse(200, PNG, {"Content-Type": "image/png"})]
        result = self.client.fetch_attachment(ATTACHMENT, max_bytes=MAX_MEDIA_BYTES, timeout=3)
        self.assertEqual(result, Attachment(PNG, "image/png"))
        self.assertTrue(self.calls[1][1].endswith("/attachments/demo-attachment/content"))
        self.assertEqual(self.calls[1][2]["max_bytes"], MAX_MEDIA_BYTES)

    def test_metadata_prevents_oversized_unsupported_or_cross_project_download(self):
        base = {"id": ATTACHMENT, "projectId": PROJECT, "contentType": "image/png", "sizeBytes": len(PNG)}
        for change in ({"projectId": "other"}, {"id": "other"}, {"sizeBytes": MAX_MEDIA_BYTES + 1}, {"sizeBytes": True}, {"contentType": "image/gif"}):
            self.responses = [HTTPResponse(200, json.dumps(dict(base, **change)).encode(), {})]
            self.calls.clear()
            with self.assertRaises(PhotonError): self.client.fetch_attachment(ATTACHMENT, max_bytes=MAX_MEDIA_BYTES, timeout=3)
            self.assertEqual(len(self.calls), 1)

    def test_content_mime_and_actual_length_must_match_metadata(self):
        metadata = {"id": ATTACHMENT, "projectId": PROJECT, "contentType": "image/png", "sizeBytes": len(PNG)}
        for raw, mime in ((PNG[:-1], "image/png"), (PNG, "text/html")):
            self.responses = [HTTPResponse(200, json.dumps(metadata).encode(), {}), HTTPResponse(200, raw, {"content-type": mime})]
            with self.assertRaisesRegex(PhotonError, "invalid_media_response"):
                self.client.fetch_attachment(ATTACHMENT, max_bytes=MAX_MEDIA_BYTES, timeout=3)

    def test_http_errors_are_sanitized_and_retryable_only_when_appropriate(self):
        for status in (301, 401, 404, 409, 429, 500, 503, 504):
            self.responses = [HTTPResponse(status, b"fake-api-key-in-body", {})]
            with self.assertRaises(PhotonError) as raised:
                self.client.send_message({}, idempotency_key="key", timeout=3)
            self.assertEqual(raised.exception.retryable, status in (429, 500, 503, 504))
            self.assertNotIn("fake-api-key", str(raised.exception))

    def test_transports_and_malformed_acknowledgments_are_sanitized(self):
        for response in (RuntimeError("fake-api-key"), HTTPResponse(202, b"bad json", {})):
            self.responses = [response]
            with self.assertRaises(PhotonError) as raised:
                self.client.send_message({}, idempotency_key="key", timeout=3)
            self.assertNotIn("fake-api-key", str(raised.exception))

    def test_malformed_media_metadata_is_sanitized(self):
        self.responses = [HTTPResponse(200, b"not json", {})]
        with self.assertRaisesRegex(PhotonError, "invalid_media_response"):
            self.client.fetch_attachment(ATTACHMENT, max_bytes=MAX_MEDIA_BYTES, timeout=3)

    def test_actual_byte_limit_is_checked_even_for_injected_transport(self):
        self.responses = [HTTPResponse(202, b"x" * 128_001, {})]
        with self.assertRaisesRegex(PhotonError, "response_too_large"):
            self.client.send_message({}, idempotency_key="key", timeout=3)

    def test_redirect_handler_will_not_forward_authorization(self):
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://another-host.invalid"))

    def test_live_transport_reads_at_most_limit_plus_one(self):
        class Response:
            status, headers = 200, {"Content-Type": "image/png"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, count):
                self.count = count
                return b"x" * count
        response = Response()
        with patch.object(PHOTON, "build_opener") as opener:
            opener.return_value.open.return_value = response
            with self.assertRaisesRegex(PhotonError, "response_too_large"):
                urllib_transport("GET", "https://api.photon.codes/test", headers={}, body=None, max_bytes=10, timeout=3)
        self.assertEqual(response.count, 11)

    def test_live_transport_http_and_network_errors_are_safe(self):
        for error in (HTTPError("https://api.photon.codes/test", 401, "fake-api-key", {}, None), URLError("fake-api-key")):
            with patch.object(PHOTON, "build_opener") as opener:
                opener.return_value.open.side_effect = error
                if isinstance(error, HTTPError):
                    self.assertEqual(urllib_transport("GET", "https://api.photon.codes/test", headers={}, body=None, max_bytes=10, timeout=3).status, 401)
                else:
                    with self.assertRaisesRegex(PhotonError, "provider_unavailable"):
                        urllib_transport("GET", "https://api.photon.codes/test", headers={}, body=None, max_bytes=10, timeout=3)


if __name__ == "__main__":
    unittest.main()
