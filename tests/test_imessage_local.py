import base64
import json
import plistlib
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.imessage_local import (
    MessagesReader, PopupBoard, StickerWatcher, build_request,
    decode_attributed_body, is_sticker_attachment, normalize_contact, panel_page,
    series_label, sticker_series,
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
        CREATE TABLE chat (ROWID INTEGER PRIMARY KEY, guid TEXT, display_name TEXT);
        CREATE TABLE chat_handle_join (chat_id INTEGER, handle_id INTEGER);
        CREATE TABLE message (ROWID INTEGER PRIMARY KEY, guid TEXT, text TEXT,
            attributedBody BLOB, handle_id INTEGER, is_from_me INTEGER, date INTEGER,
            associated_message_type INTEGER DEFAULT 0, associated_message_guid TEXT,
            cache_has_attachments INTEGER DEFAULT 0);
        CREATE TABLE chat_message_join (chat_id INTEGER, message_id INTEGER);
        CREATE TABLE attachment (ROWID INTEGER PRIMARY KEY, filename TEXT, mime_type TEXT,
            uti TEXT, transfer_state INTEGER, is_sticker INTEGER,
            sticker_user_info BLOB, attribution_info BLOB);
        CREATE TABLE message_attachment_join (message_id INTEGER, attachment_id INTEGER);
        INSERT INTO handle VALUES (1, '+15550100199'), (2, '+15550100777');
        INSERT INTO chat VALUES (1, 'direct-friend', NULL), (2, 'group', 'Family'),
            (3, 'direct-other', NULL);
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

    def sticker(self, chat, *, mine=False, handle=1, exists=True, series=None, sid=None,
                pack_name=None, info_blob=None):
        rowid = self._message(chat, "\ufffc", None, mine, handle, attachments=1)
        self.attachment += 1
        path = self.directory / ("sticker-%d.heic" % self.attachment)
        if exists:
            path.write_bytes(b"heic-placeholder")
        if info_blob is not None:
            info = info_blob
        elif series:
            info = plistlib.dumps({
                "pid": series, "sid": sid or ("sid-%d" % self.attachment), "shash": "ab",
            })
        else:
            info = None
        attribution = plistlib.dumps({"name": pack_name}) if pack_name else None
        self.db.execute(
            """INSERT INTO attachment
            (ROWID, filename, mime_type, uti, transfer_state, is_sticker, sticker_user_info, attribution_info)
            VALUES (?, ?, 'image/heic', 'public.heic', 5, 1, ?, ?)""",
            (self.attachment, str(path), info, attribution))
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
        self.extra = []

    def tearDown(self):
        for watcher in self.extra:
            watcher.close()
        self.watcher.close()
        self.fx.db.close()
        self.temp.cleanup()

    def all_chats(self):
        watcher = StickerWatcher(
            self.reader, self.vision, self.board, contact=None,
            state_path=str(Path(self.temp.name) / ("all-%d.sqlite3" % len(self.extra))),
            notifier=lambda title, body: self.notes.append((title, body)),
            converter=lambda path, workdir: self.png, workdir=self.temp.name)
        watcher.poll_once()
        self.extra.append(watcher)
        return watcher

    def test_decodes_text_from_attributed_body(self):
        self.assertEqual(decode_attributed_body(attributed("ha that got me")), "ha that got me")
        self.assertIsNone(decode_attributed_body(None))
        self.assertEqual(normalize_contact(FRIEND), normalize_contact(FRIEND_HANDLE))

    def test_recognizes_stickers_across_messages_schema_variants(self):
        base = {"is_sticker": 0, "uti": "public.heic", "filename": "/tmp/image.heic"}
        self.assertFalse(is_sticker_attachment(base))
        self.assertTrue(is_sticker_attachment({**base, "is_sticker": 1}))
        self.assertTrue(is_sticker_attachment({
            **base, "uti": "com.apple.messages.sticker",
        }))
        self.assertTrue(is_sticker_attachment({
            **base, "filename": "/Library/Messages/Stickers/item.heic",
        }))

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
        self.assertIsNone(items[0]["chat"])

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

    def test_any_chat_explains_group_other_and_own_stickers(self):
        watcher = self.all_chats()
        self.fx.sticker(2)
        self.fx.sticker(3, handle=2)
        self.fx.sticker(1, mine=True)
        summary = watcher.poll_once()
        self.assertEqual(summary["explained"], 3)
        self.assertEqual(len(self.vision.calls), 3)
        items = self.board.since(0)
        self.assertEqual([item["sender"] for item in items],
                         [FRIEND_HANDLE, "+15550100777", "You"])
        self.assertEqual(items[0]["chat"], "Family")
        self.assertIsNone(items[2]["chat"])
        self.assertEqual(self.notes[0][0], "%s in Family sent a sticker" % FRIEND_HANDLE)

    def test_popup_suggests_another_sticker_from_the_same_series(self):
        converted = []

        def convert(path, workdir):
            converted.append(Path(path).name)
            return self.png + Path(path).name.encode()

        self.fx.sticker(1, series="com.example.pack", sid="old", pack_name="Bippy")
        watcher = StickerWatcher(
            self.reader, self.vision, self.board, contact=None,
            state_path=str(Path(self.temp.name) / "series.sqlite3"),
            notifier=lambda title, body: self.notes.append((title, body)),
            converter=convert, workdir=self.temp.name)
        watcher.poll_once()
        self.extra.append(watcher)
        self.fx.sticker(2, series="com.example.pack", sid="new", pack_name="Bippy")
        watcher.poll_once()
        self.assertEqual(len(self.vision.calls), 1)
        item = self.board.since(0)[-1]
        self.assertEqual(item["suggestion_series"], "Bippy")
        self.assertEqual(item["chat"], "Family")
        self.assertEqual(item["cue"], "It follows your joke.")
        suggestion = self.board.suggestion_image(item["id"])
        self.assertTrue(suggestion.endswith(b"sticker-1.heic"))
        self.assertEqual(converted, ["sticker-2.heic", "sticker-1.heic"])

    def test_different_series_is_not_suggested(self):
        self.fx.sticker(1, series="pack-a", sid="a", pack_name="Alpha")
        watcher = self.all_chats()
        self.fx.sticker(1, series="pack-b", sid="b", pack_name="Beta")
        watcher.poll_once()
        item = self.board.since(0)[-1]
        self.assertNotIn("suggestion_image", item)
        self.assertIn("No other sticker", item["suggestion_note"])
        self.assertEqual(len(self.vision.calls), 1)

    def test_sticker_without_pack_metadata_still_explains(self):
        watcher = self.all_chats()
        self.fx.sticker(3, handle=2, info_blob=b"not-a-plist")
        watcher.poll_once()
        item = self.board.since(0)[-1]
        self.assertEqual(item["sender"], "+15550100777")
        self.assertNotIn("suggestion_image", item)
        self.assertNotIn("suggestion_note", item)
        self.assertIn("really funny", item["text"])

    def test_series_name_comes_from_pack_metadata(self):
        pack = plistlib.dumps({"pid": "com.apple.messages.genmoji", "sid": "abc"})
        self.assertEqual(sticker_series(pack, None)["label"], "Genmoji")
        named = plistlib.dumps({"name": "Bippy"})
        self.assertEqual(sticker_series(pack, named)["label"], "Bippy")
        self.assertIsNone(sticker_series(b"not-a-plist", None))
        self.assertEqual(
            series_label("com.christinat.bippy.StickerPackExtension", None), "bippy")
        page = panel_page().decode()
        self.assertIn("any Messages chat", page)
        self.assertIn("same series", page)
        self.assertIn('id="modal"', page)

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
