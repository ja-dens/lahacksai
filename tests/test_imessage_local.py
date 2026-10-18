import base64
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.imessage_local import (
    MessagesReader, PopupBoard, StickerWatcher, build_request,
    decode_attributed_body, normalize_contact,
)
from src.interpreter import prepare_request

ROOT = Path(__file__).resolve().parents[1]
FRIEND = "+1 (555) 010-0199"
FRIEND_HANDLE = "+15550100199"
NS = 1_000_000_000


def sticker_bytes():
    request = json.loads((ROOT / "fixtures/contracts/interpretation_request.json").read_text())
    return base64.b64decode(request["sticker"]["data_base64"])


def attributed(text):
    encoded = text.encode()
    return b"\x04\x0bstreamtyped\x81\xe8\x03\x84\x01@\x84\x84\x84\x12NSAttributedString" \
        b"\x00\x84\x84\x08NSObject\x00\x85\x92\x84\x84\x84\x08NSString\x01\x94\x84\x01+" \
        + bytes([len(encoded)]) + encoded + b"\x86\x84\x02iI"


def messages_db(path):
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT);
        CREATE TABLE chat (ROWID INTEGER PRIMARY KEY, guid TEXT);
        CREATE TABLE chat_handle_join (chat_id INTEGER, handle_id INTEGER);
        CREATE TABLE message (ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT,
            attributedBody BLOB, handle_id INTEGER, is_from_me INTEGER, date INTEGER,
            associated_message_type INTEGER DEFAULT 0, associated_message_guid TEXT,
            cache_has_attachments INTEGER DEFAULT 0);
        CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER);
        CREATE TABLE attachment (ROWID INTEGER PRIMARY KEY, filename TEXT, mime_type TEXT,
            uti TEXT, transfer_state INTEGER, is_sticker INTEGER);
        CREATE TABLE message_attachment_join (message_id INTEGER, attachment_id INTEGER);
        INSERT INTO handle VALUES (1, '+15550100199'), (2, '+15550100777');
        INSERT INTO chat VALUES (1, 'direct-friend'), (2, 'group'), (3, 'direct-other');
        INSERT INTO chat_handle_join VALUES (1, 1), (2, 1), (2, 2), (3, 2);
    """)
    return db


class Fixture:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.db = messages_db(self.directory / "chat.db")
        self.db.row_factory = sqlite3.Row
        self.rowid = 0
        self.attachment = 0
        self.time = 800_000_000 * NS

    def text(self, chat, text, *, mine=False, handle=1, body=False):
        return self._message(chat, None if body else text, attributed(text) if body else None,
                             mine, handle)

    def sticker(self, chat, *, mine=False, handle=1, exists=True):
        rowid = self._message(chat, "\ufffc", None, mine, handle, attachments=1)
        self.attachment += 1
        path = self.directory / ("sticker-%d.heic" % self.attachment)
        if exists:
            path.write_bytes(b"heic-placeholder")
        self.db.execute("INSERT INTO attachment VALUES (?, ?, 'image/heic', 'public.heic', 5, 1)",
                        (self.attachment, str(path)))
        self.db.execute("INSERT INTO message_attachment_join VALUES (?, ?)", (rowid, self.attachment))
        self.db.commit()
        return rowid, path

    def _message(self, chat, text, body, mine, handle, attachments=0):
        self.rowid += 1
        self.time += 5 * NS
        self.db.execute(
            "INSERT INTO message VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)",
            (self.rowid, "guid-%d" % self.rowid, text, body, 0 if mine else handle,
             1 if mine else 0, self.time, attachments))
        self.db.execute("INSERT INTO chat_message_join VALUES (?, ?)", (chat, self.rowid))
        self.db.commit()
        return self.rowid


class FakeVision:
    def __init__(self):
        self.calls = []

    def __call__(self, request):
        self.calls.append(request)
        return {"candidates": ["They found your joke really funny."],
                "candidate_relation": "single", "rankable": True,
                "context_cue": "It follows your joke.",
                "uncertainty_caveat": "This is a likely meaning, not confirmed."}


class IMessageLocalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.temp.name)
        self.fx.text(1, "old message before the watcher started")
        self.reader = MessagesReader(self.fx.db)
        self.vision = FakeVision()
        self.board = PopupBoard()
        self.notes = []
        self.png = sticker_bytes()
        self.watcher = StickerWatcher(
            self.reader, self.vision, self.board, contact=FRIEND,
            state_path=str(Path(self.temp.name) / "state.sqlite3"), relationship="friend",
            notifier=lambda title, body: self.notes.append((title, body)),
            converter=lambda path, workdir: self.png, workdir=self.temp.name)
        self.watcher.poll_once()

    def tearDown(self):
        self.watcher.close()
        self.fx.db.close()
        self.temp.cleanup()

    def test_decodes_text_from_attributed_body(self):
        self.assertEqual(decode_attributed_body(attributed("ha that got me")), "ha that got me")
        self.assertIsNone(decode_attributed_body(None))
        self.assertEqual(normalize_contact(FRIEND), normalize_contact(FRIEND_HANDLE))

    def test_friend_sticker_shows_popup_with_one_model_call(self):
        self.fx.text(1, "I tried to catch fog. I mist.", mine=True)
        self.fx.text(1, "that joke got me", body=True)
        self.fx.sticker(1)
        summary = self.watcher.poll_once()
        self.assertEqual(summary["explained"], 1)
        self.assertEqual(len(self.vision.calls), 1)
        items = self.board.since(0)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["sender"], "Your friend")
        self.assertIn("really funny", items[0]["text"])
        self.assertIn("not confirmed", items[0]["text"])
        self.assertEqual(self.board.image(items[0]["id"]), self.png)
        self.assertEqual(self.notes[0][0], "Your friend sent a sticker")
        request = self.vision.calls[0]
        prepare_request(request)
        texts = [m["text"] for m in request["recent_messages"]]
        self.assertEqual(texts[-2:], ["I tried to catch fog. I mist.", "that joke got me"])
        self.assertEqual(request["recent_messages"][-2]["sender_id"], "me")
        self.assertEqual(request["user_context"]["relationship"], "friend")
        self.assertEqual(request["recipient_id"], "me")

    def test_history_before_start_is_not_interpreted(self):
        self.watcher.close()
        self.fx.sticker(1)
        state = Path(self.temp.name) / "fresh.sqlite3"
        fresh = StickerWatcher(self.reader, self.vision, self.board, contact=FRIEND,
                               state_path=str(state), converter=lambda p, w: self.png,
                               notifier=lambda *a: None, workdir=self.temp.name)
        fresh.poll_once()
        self.assertEqual(self.vision.calls, [])
        self.watcher = fresh

    def test_ignores_group_other_contacts_and_own_stickers(self):
        self.fx.sticker(2)
        self.fx.sticker(3, handle=2)
        self.fx.sticker(1, mine=True)
        self.watcher.poll_once()
        self.assertEqual(self.vision.calls, [])
        self.assertEqual(self.board.since(0), [])

    def test_same_sticker_message_is_explained_once(self):
        self.fx.sticker(1)
        self.watcher.poll_once()
        self.watcher.state.execute("DELETE FROM watcher_state")
        self.watcher.state.commit()
        self.watcher.poll_once()
        self.assertEqual(len(self.vision.calls), 1)

    def test_waits_for_sticker_download(self):
        _, path = self.fx.sticker(1, exists=False)
        self.assertEqual(self.watcher.poll_once()["waiting"], 1)
        self.assertEqual(self.vision.calls, [])
        path.write_bytes(b"downloaded")
        self.watcher.poll_once()
        self.assertEqual(len(self.vision.calls), 1)

    def test_model_failure_never_invents_a_meaning(self):
        def broken(request):
            error = RuntimeError("down")
            error.code = "model_timeout"
            raise error
        self.watcher.vision = broken
        self.fx.sticker(1)
        self.watcher.poll_once()
        item = self.board.since(0)[0]
        self.assertEqual(item["status"], "error")
        self.assertIn("took too long", item["text"])
        self.assertEqual(self.notes, [])

    def test_request_window_is_bounded(self):
        for index in range(30):
            self.fx.text(1, "message %d" % index)
        rowid, _ = self.fx.sticker(1)
        row = self.reader.new_messages(rowid - 1)[0]
        request = build_request(self.reader, row, self.png, None)
        self.assertEqual(len(request["recent_messages"]), 25)
        self.assertEqual(request["recent_messages"][-1]["text"], "message 29")
        self.assertIsNone(request["user_context"]["relationship_source"])
        prepare_request(request)


if __name__ == "__main__":
    unittest.main()
