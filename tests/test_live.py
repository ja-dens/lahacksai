import json
import tempfile
import unittest
from pathlib import Path

from src.adapters.photon import Attachment, PhotonError
from src.adapters.vision import FixtureVision
from src.context_store import SQLiteStore
from src.live import LiveConfig, LiveRuntime


ROOT = Path(__file__).resolve().parents[1]


def message(message_id, content, created="2026-10-17T23:19:28.938Z"):
    human = "pho_usr_human"
    agent = "pho_usr_agent"
    return {
        "id": message_id,
        "platform": "imessage",
        "status": "received",
        "createdAt": created,
        "sentBy": {"kind": "human", "handle": "+15555550123", "id": human},
        "receivedBy": {
            "kind": "agent", "handle": "+15555550188", "id": agent,
            "details": {"type": "shared"},
        },
        "space": {
            "kind": "direct", "id": "pho_spc_direct", "platform": "imessage",
            "participantIds": [human, agent],
        },
        "content": content,
    }


class FakePhoton:
    def __init__(self, messages):
        self.messages = messages
        self.sent = []
        self.list_calls = []

    def list_messages(self, **kwargs):
        self.list_calls.append(kwargs)
        items = list(self.messages)
        if kwargs.get("order") == "desc":
            items.reverse()
        return {"items": items, "nextPageToken": None}

    def fetch_attachment(self, attachment_id, **_kwargs):
        if attachment_id != "pho_att_image":
            raise PhotonError("provider_http_404")
        return Attachment(
            (ROOT / "fixtures/stickers/laughing.png").read_bytes(), "image/png",
        )

    def send_message(self, body, **_kwargs):
        self.sent.append(body)
        return {
            "id": "pho_msg_outbound", "projectId": "pho_prj_test",
            "status": "accepted", "space": {"id": body["spaceId"]},
            "sentBy": {"id": body["senderId"]},
        }

    def get_message(self, message_id, **_kwargs):
        return {
            "id": message_id, "projectId": "pho_prj_test", "status": "delivered",
        }


class CountingVision(FixtureVision):
    def __init__(self):
        result = json.loads(
            (ROOT / "fixtures/contracts/candidate_single.json").read_text()
        )
        super().__init__(result)
        self.calls = 0

    def __call__(self, request):
        self.calls += 1
        return super().__call__(request)


class LiveConfigTests(unittest.TestCase):
    def test_requires_verified_sender_configuration(self):
        base = {
            "PHOTON_PROJECT_ID": "pho_prj_test",
            "PHOTON_API_KEY": "secret",
            "PHOTON_AGENT_HANDLE": "+15555550188",
        }
        with self.assertRaisesRegex(ValueError, "PHOTON_ALLOWED_SENDER"):
            LiveConfig.from_env(base)


class LiveRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "live.sqlite3")
        self.config = LiveConfig(
            project_id="pho_prj_test", api_key="secret",
            agent_handle="+15555550188",
            allowed_sender_handle="+15555550123",
            database_path=self.db_path,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_text_then_photo_is_interpreted_delivered_and_deduplicated(self):
        messages = [
            message("pho_msg_text", {"type": "text", "format": "plain", "text": "hi"}),
            message(
                "pho_msg_photo",
                {"type": "attachment", "attachmentId": "pho_att_image"},
                "2026-10-17T23:20:28.938Z",
            ),
        ]
        client = FakePhoton(messages)
        vision = CountingVision()
        runtime = LiveRuntime(
            self.config, client=client, vision=vision,
            store=SQLiteStore(self.db_path),
        )
        try:
            first = runtime.poll_once()
            second = runtime.poll_once()
        finally:
            runtime.store.close()
        self.assertEqual(first["history_only"], 1)
        self.assertEqual(first["sticker"], 1)
        self.assertEqual(first["delivery"]["delivered"], 1)
        self.assertEqual(second["duplicates"], 2)
        self.assertEqual(vision.calls, 1)
        self.assertEqual(len(client.sent), 1)
        self.assertNotIn("parentMessageId", client.sent[0])
        db = SQLiteStore(self.db_path)
        try:
            attachment = db.db.execute("SELECT * FROM live_attachments").fetchone()
            delivery = db.db.execute("SELECT * FROM live_delivery_status").fetchone()
        finally:
            db.close()
        self.assertEqual(attachment["mime_type"], "image/png")
        self.assertEqual(delivery["status"], "delivered")

    def test_restart_uses_durable_receipts(self):
        messages = [message(
            "pho_msg_text", {"type": "text", "format": "plain", "text": "hi"},
        )]
        client = FakePhoton(messages)
        first_store = SQLiteStore(self.db_path)
        first = LiveRuntime(
            self.config, client=client, vision=CountingVision(), store=first_store,
        )
        first.poll_once()
        first_store.close()

        second_store = SQLiteStore(self.db_path)
        second = LiveRuntime(
            self.config, client=client, vision=CountingVision(), store=second_store,
        )
        try:
            result = second.poll_once()
        finally:
            second_store.close()
        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["duplicates"], 1)

    def test_rejects_message_from_other_sender(self):
        unauthorized = message(
            "pho_msg_bad", {"type": "text", "format": "plain", "text": "hi"},
        )
        unauthorized["sentBy"]["handle"] = "+15555550999"
        client = FakePhoton([unauthorized])
        store = SQLiteStore(self.db_path)
        runtime = LiveRuntime(
            self.config, client=client, vision=CountingVision(), store=store,
        )
        try:
            with self.assertRaisesRegex(PhotonError, "verified_direct_space_not_found"):
                runtime.poll_once()
        finally:
            store.close()

    def test_pagination_is_followed_and_repeated_tokens_are_rejected(self):
        class PaginatedPhoton(FakePhoton):
            def list_messages(self, **kwargs):
                if kwargs.get("order") == "desc":
                    return {"items": self.messages, "nextPageToken": None}
                token = kwargs.get("page_token")
                if token is None:
                    return {"items": [self.messages[0]], "nextPageToken": "second"}
                return {"items": [self.messages[1]], "nextPageToken": None}

        client = PaginatedPhoton([
            message("first", {"type": "text", "text": "one"}),
            message("second", {"type": "text", "text": "two"},
                    "2026-10-17T23:20:28.938Z"),
        ])
        store = SQLiteStore(self.db_path)
        runtime = LiveRuntime(
            self.config, client=client, vision=CountingVision(), store=store,
        )
        try:
            self.assertEqual(runtime.poll_once()["processed"], 2)
        finally:
            store.close()

    def test_stop_before_run_is_graceful(self):
        client = FakePhoton([message(
            "one", {"type": "text", "format": "plain", "text": "hi"},
        )])
        store = SQLiteStore(self.db_path)
        runtime = LiveRuntime(
            self.config, client=client, vision=CountingVision(), store=store,
        )
        try:
            runtime.stop()
            self.assertIsNone(runtime.run())
            self.assertEqual(client.list_calls, [])
        finally:
            store.close()
