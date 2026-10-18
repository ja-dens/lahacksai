"""Watch this Mac's Messages database and explain new stickers in a local popup.

The Messages database is opened read-only. Only stickers sent by one consenting
contact in a one-to-one chat are interpreted. Explanations stay on this Mac:
nothing is posted back into the conversation.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .interpreter import interpret_sticker
from .main import format_delivery

LOG = logging.getLogger("sticker_interpreter.imessage")

MESSAGES_DB = Path.home() / "Library" / "Messages" / "chat.db"
APPLE_EPOCH = 978307200
CONTEXT_LIMIT = 25
CONTEXT_BUDGET = 24000
MESSAGE_TEXT_LIMIT = 4000
STICKER_ATTEMPTS = 10
OWNER_ID = "me"
FAILURE_TEXT = {
    "api_key_not_configured": "No OpenAI key is set, so this sticker was not explained.",
    "model_authentication_failed": "OpenAI rejected the key, so this sticker was not explained.",
    "model_rate_limited": "OpenAI is out of credit or busy, so this sticker was not explained.",
    "model_timeout": "OpenAI took too long, so this sticker was not explained.",
    "model_connection_failed": "Could not reach OpenAI, so this sticker was not explained.",
}


class MessagesAccessError(RuntimeError):
    """The Messages database cannot be read, usually for lack of Full Disk Access."""


def normalize_contact(value: str) -> str:
    value = (value or "").strip()
    if "@" in value:
        return value.lower()
    digits = re.sub(r"\D", "", value)
    return digits[-10:] if len(digits) >= 10 else digits


def decode_attributed_body(blob: bytes | None) -> str | None:
    """Extract plain text from the typedstream NSAttributedString in newer macOS."""
    if not blob:
        return None
    start = blob.find(b"NSString")
    if start < 0:
        return None
    data = blob[start + len(b"NSString"):]
    marker = data.find(b"+")
    if marker < 0 or marker + 1 >= len(data):
        return None
    data = data[marker + 1:]
    length = data[0]
    offset = 1
    if length == 0x81:
        length, offset = int.from_bytes(data[1:3], "little"), 3
    elif length == 0x82:
        length, offset = int.from_bytes(data[1:4], "little"), 4
    elif length == 0x83:
        length, offset = int.from_bytes(data[1:5], "little"), 5
    text = data[offset:offset + length].decode("utf-8", errors="replace")
    return text or None


def apple_time(value) -> str:
    value = int(value or 0)
    seconds = value / 1_000_000_000 if value > 10_000_000_000 else value
    return datetime.fromtimestamp(APPLE_EPOCH + seconds, timezone.utc).isoformat(
        timespec="microseconds")


def open_messages_db(path: Path = MESSAGES_DB) -> sqlite3.Connection:
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("SELECT 1 FROM message LIMIT 1").fetchall()
        return db
    except sqlite3.Error as error:
        raise MessagesAccessError(
            "Cannot read the Messages database. Give Cursor (or your terminal) "
            "Full Disk Access in System Settings > Privacy & Security, then restart it."
        ) from error


def _columns(db, table):
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}


class MessagesReader:
    """Read-only queries against the Messages schema."""

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.has_sticker_flag = "is_sticker" in _columns(db, "attachment")
        self.has_body = "attributedBody" in _columns(db, "message")

    def max_rowid(self) -> int:
        return int(self.db.execute("SELECT COALESCE(MAX(ROWID), 0) FROM message").fetchone()[0])

    def direct_chat(self, chat_id: int, contact: str) -> bool:
        members = self.db.execute(
            """SELECT h.id FROM chat_handle_join j JOIN handle h ON h.ROWID = j.handle_id
            WHERE j.chat_id = ?""", (chat_id,)).fetchall()
        return len(members) == 1 and normalize_contact(members[0]["id"]) == contact

    def new_messages(self, after_rowid: int):
        body = "m.attributedBody" if self.has_body else "NULL"
        return self.db.execute(
            f"""SELECT m.ROWID AS rowid, m.guid, m.text, {body} AS body, m.is_from_me,
                m.date, m.associated_message_type, m.associated_message_guid,
                h.id AS handle, j.chat_id
            FROM message m
            LEFT JOIN handle h ON h.ROWID = m.handle_id
            JOIN chat_message_join j ON j.message_id = m.ROWID
            WHERE m.ROWID > ? ORDER BY m.ROWID""", (after_rowid,)).fetchall()

    def attachments(self, message_rowid: int):
        flag = "a.is_sticker" if self.has_sticker_flag else "0"
        return self.db.execute(
            f"""SELECT a.ROWID AS rowid, a.filename, a.mime_type, a.uti, a.transfer_state,
                {flag} AS is_sticker
            FROM message_attachment_join j JOIN attachment a ON a.ROWID = j.attachment_id
            WHERE j.message_id = ?""", (message_rowid,)).fetchall()

    def earlier_in_chat(self, chat_id: int, before_rowid: int, limit: int):
        body = "m.attributedBody" if self.has_body else "NULL"
        rows = self.db.execute(
            f"""SELECT m.ROWID AS rowid, m.guid, m.text, {body} AS body, m.is_from_me,
                m.date, m.associated_message_type, m.cache_has_attachments,
                h.id AS handle
            FROM message m
            JOIN chat_message_join j ON j.message_id = m.ROWID
            LEFT JOIN handle h ON h.ROWID = m.handle_id
            WHERE j.chat_id = ? AND m.ROWID < ? AND m.associated_message_type = 0
            ORDER BY m.date DESC, m.ROWID DESC LIMIT ?""",
            (chat_id, before_rowid, limit)).fetchall()
        return list(reversed(rows))


def message_text(row) -> str | None:
    text = row["text"]
    if text:
        text = text.replace("\ufffc", "").strip()
    if not text:
        text = decode_attributed_body(row["body"])
        if text:
            text = text.replace("\ufffc", "").strip()
    return text or None


def sender_label(row) -> str:
    return OWNER_ID if row["is_from_me"] else (row["handle"] or "unknown")


def attachment_kind(reader, row) -> str:
    if not row["cache_has_attachments"]:
        return "text"
    kinds = set()
    for item in reader.attachments(row["rowid"]):
        if item["is_sticker"]:
            kinds.add("sticker")
        elif (item["mime_type"] or "").startswith("image/"):
            kinds.add("image")
        elif (item["mime_type"] or "").startswith("audio/"):
            kinds.add("audio")
        else:
            kinds.add("other")
    for kind in ("sticker", "image", "audio", "other"):
        if kind in kinds:
            return kind
    return "text"


def sticker_png(path: Path, workdir: Path) -> bytes:
    """Convert a sticker file (often HEIC) to a static PNG capped at 1024 px."""
    output = workdir / (hashlib.sha256(str(path).encode()).hexdigest()[:16] + ".png")
    result = subprocess.run(
        ["sips", "-s", "format", "png", "-Z", "1024", str(path), "--out", str(output)],
        capture_output=True, timeout=30,
    )
    if result.returncode != 0 or not output.exists():
        raise ValueError("sticker_conversion_failed")
    data = output.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) > 5_000_000:
        raise ValueError("sticker_conversion_failed")
    return data


def build_request(reader, message, png: bytes, relationship: str | None) -> dict:
    earlier = reader.earlier_in_chat(message["chat_id"], message["rowid"], CONTEXT_LIMIT)
    remaining = CONTEXT_BUDGET
    recent = []
    for row in reversed(earlier):
        text = message_text(row)
        kind = attachment_kind(reader, row)
        if text is not None:
            clipped = text[:min(MESSAGE_TEXT_LIMIT, remaining)]
            remaining -= len(clipped)
        else:
            clipped = None
        recent.append({
            "message_id": row["guid"], "sender_id": sender_label(row),
            "sent_at": apple_time(row["date"]), "text": clipped,
            "text_truncated": text is not None and clipped != text,
            "kind": kind, "media_not_interpreted": kind != "text",
            "reply_to_message_id": None,
        })
    recent.reverse()
    sent_at = apple_time(message["date"])
    for item in recent:
        if item["sent_at"] > sent_at:
            item["sent_at"] = sent_at
    target_text = message_text(message)
    return {
        "schema_version": 2, "policy_version": "context-v1",
        "source_message_id": message["guid"], "platform": "imessage-local",
        "conversation_id": "chat-" + str(message["chat_id"]),
        "sender_id": sender_label(message), "recipient_id": OWNER_ID,
        "sent_at": sent_at,
        "target_text": target_text[:MESSAGE_TEXT_LIMIT] if target_text else None,
        "target_text_truncated": bool(target_text and len(target_text) > MESSAGE_TEXT_LIMIT),
        "reply_to_message_id": message["associated_message_guid"] or None,
        "sticker": {"mime_type": "image/png",
                    "data_base64": base64.b64encode(png).decode("ascii"),
                    "sha256": hashlib.sha256(png).hexdigest()},
        "recent_messages": recent,
        "context_message_limit": CONTEXT_LIMIT,
        "context_text_character_budget": CONTEXT_BUDGET,
        "context_age_limit": None,
        "user_context": {
            "preferences": {"language": "en", "explanation_length": "short"},
            "preferences_source": "default",
            "relationship": relationship,
            "relationship_source": "recipient_declared" if relationship else None,
        },
    }


class PopupBoard:
    """In-memory list of explanations for the local popup page."""

    def __init__(self):
        self._lock = threading.Lock()
        self._items = []
        self._images = {}

    def add(self, item: dict, png: bytes | None = None) -> dict:
        with self._lock:
            item = dict(item, id=len(self._items) + 1)
            if png is not None:
                self._images[item["id"]] = png
                item["image"] = "/sticker/%d.png" % item["id"]
            self._items.append(item)
            return item

    def since(self, last_id: int):
        with self._lock:
            return [item for item in self._items if item["id"] > last_id]

    def image(self, item_id: int):
        with self._lock:
            return self._images.get(item_id)


def notify(title: str, body: str) -> None:
    script = ["osascript", "-e", "on run argv",
              "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
              "-e", "end run", title, body[:240]]
    try:
        subprocess.Popen(script, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        LOG.warning("Notification could not be shown")


class StickerWatcher:
    """Poll the Messages database and interpret new stickers from one contact."""

    def __init__(self, reader, vision, board, *, contact, state_path,
                 relationship=None, include_mine=False, include_photos=False,
                 notifier=notify, converter=sticker_png, workdir=None):
        self.reader = reader
        self.vision = vision
        self.board = board
        self.contact = normalize_contact(contact)
        if not self.contact:
            raise ValueError("A contact phone number or email is required")
        self.relationship = relationship
        self.include_mine = include_mine
        self.include_photos = include_photos
        self.notifier = notifier
        self.converter = converter
        self.workdir = Path(workdir or tempfile.mkdtemp(prefix="sticker-popup-"))
        Path(state_path).parent.mkdir(parents=True, exist_ok=True)
        self.state = sqlite3.connect(state_path, check_same_thread=False)
        self.state.executescript("""
            CREATE TABLE IF NOT EXISTS watcher_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS watcher_results (
                message_guid TEXT PRIMARY KEY, status TEXT NOT NULL,
                explanation TEXT, recorded_at TEXT NOT NULL);
        """)
        self.pending = {}
        self.attempts = {}

    def close(self):
        self.state.close()

    def cursor(self) -> int:
        row = self.state.execute(
            "SELECT value FROM watcher_state WHERE key='last_rowid'").fetchone()
        if row:
            return int(row[0])
        latest = self.reader.max_rowid()
        self._save_cursor(latest)
        return latest

    def _save_cursor(self, value: int):
        self.state.execute(
            """INSERT INTO watcher_state(key, value) VALUES ('last_rowid', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (str(value),))
        self.state.commit()

    def _done(self, guid) -> bool:
        return self.state.execute(
            "SELECT 1 FROM watcher_results WHERE message_guid=?", (guid,)).fetchone() is not None

    def _record(self, guid, status, explanation=None):
        self.state.execute(
            "INSERT OR REPLACE INTO watcher_results VALUES (?, ?, ?, ?)",
            (guid, status, explanation, datetime.now(timezone.utc).isoformat()))
        self.state.commit()

    def _sticker_file(self, message):
        for item in self.reader.attachments(message["rowid"]):
            mime = item["mime_type"] or ""
            if item["is_sticker"] or (self.include_photos and mime.startswith("image/")):
                if not item["filename"]:
                    return None, True
                path = Path(os.path.expanduser(item["filename"]))
                return (path, False) if path.exists() else (None, True)
        return None, False

    def _eligible(self, message) -> bool:
        if message["is_from_me"] and not self.include_mine:
            return False
        if not message["is_from_me"] and normalize_contact(message["handle"] or "") != self.contact:
            return False
        return self.reader.direct_chat(message["chat_id"], self.contact)

    def poll_once(self) -> dict:
        summary = {"seen": 0, "stickers": 0, "explained": 0, "waiting": 0}
        cursor = self.cursor()
        rows = list(self.reader.new_messages(cursor)) + list(self.pending.values())
        for message in rows:
            summary["seen"] += 1
            cursor = max(cursor, int(message["rowid"]))
            guid = message["guid"]
            if self._done(guid) or not self._eligible(message):
                self.pending.pop(guid, None)
                continue
            path, waiting = self._sticker_file(message)
            if path is None:
                if waiting:
                    self.attempts[guid] = self.attempts.get(guid, 0) + 1
                    if self.attempts[guid] < STICKER_ATTEMPTS:
                        self.pending[guid] = message
                        summary["waiting"] += 1
                    else:
                        self.pending.pop(guid, None)
                        self._record(guid, "sticker_file_unavailable")
                continue
            self.pending.pop(guid, None)
            summary["stickers"] += 1
            self._explain(message, path)
            summary["explained"] += 1
        self._save_cursor(cursor)
        return summary

    def _explain(self, message, path):
        guid = message["guid"]
        sender = "You" if message["is_from_me"] else "Your friend"
        try:
            png = self.converter(path, self.workdir)
        except (ValueError, OSError, subprocess.SubprocessError):
            self._record(guid, "sticker_conversion_failed")
            self.board.add({"status": "error", "sender": sender,
                            "text": "This sticker could not be opened for an explanation."})
            return
        try:
            request = build_request(self.reader, message, png, self.relationship)
            result = interpret_sticker(request, self.vision)
            text = format_delivery(request, result)["text"]
            status = result["status"]
        except Exception as error:  # Operational failures never become a meaning.
            code = getattr(error, "code", None) or type(error).__name__
            LOG.warning("Sticker interpretation failed code=%s", code)
            self._record(guid, "failed_" + str(code))
            text = FAILURE_TEXT.get(str(code), "Could not explain this sticker (%s)." % code)
            self.board.add({"status": "error", "sender": sender, "text": text}, png)
            return
        self._record(guid, status, text)
        self.board.add({"status": status, "sender": sender, "text": text,
                        "cue": result.get("context_cue") or ""}, png)
        self.notifier("%s sent a sticker" % sender, text)


def panel_page() -> bytes:
    return Path(__file__).with_name("imessage_panel.html").read_bytes()


def serve_panel(board: PopupBoard, port: int):
    page = panel_page()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body, content_type):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                return self._send(page, "text/html; charset=utf-8")
            if url.path == "/events":
                try:
                    last = int(parse_qs(url.query).get("after", ["0"])[0])
                except ValueError:
                    last = 0
                body = json.dumps(board.since(last), ensure_ascii=False).encode()
                return self._send(body, "application/json")
            match = re.fullmatch(r"/sticker/(\d+)\.png", url.path)
            if match:
                png = board.image(int(match.group(1)))
                if png is not None:
                    return self._send(png, "image/png")
            self.send_error(404)

        def log_message(self, *_args):
            pass

    server = None
    for candidate in range(port, port + 10):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate), Handler)
            break
        except OSError:
            continue
    if server is None:
        raise OSError("No free local port for the popup panel")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d/" % server.server_address[1]


def open_panel(url: str) -> None:
    chrome = Path("/Applications/Google Chrome.app")
    if chrome.exists():
        command = ["open", "-na", str(chrome), "--args", "--app=" + url,
                   "--window-size=380,560", "--window-position=40,60"]
    else:
        command = ["open", url]
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        LOG.warning("Open %s to see the popup panel", url)


def check_access() -> dict:
    db = open_messages_db()
    try:
        reader = MessagesReader(db)
        return {"messages_database_readable": True,
                "sticker_flag_available": reader.has_sticker_flag,
                "message_count": reader.max_rowid()}
    finally:
        db.close()


def run_imessage(contact, *, relationship=None, include_mine=False, include_photos=False,
                 port=8766, open_window=True, poll_seconds=1.5,
                 state_path="local-data/imessage-local.sqlite3"):
    from dotenv import load_dotenv
    from .adapters.vision import OpenAIVision

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    load_dotenv()
    if not shutil.which("sips"):
        raise RuntimeError("macOS sips is required to convert stickers")
    db = open_messages_db()
    reader = MessagesReader(db)
    vision = OpenAIVision(model=os.environ.get("VISION_MODEL") or "gpt-4.1-mini")
    board = PopupBoard()
    watcher = StickerWatcher(reader, vision, board, contact=contact, state_path=state_path,
                             relationship=relationship, include_mine=include_mine,
                             include_photos=include_photos)
    server, url = serve_panel(board, port)
    print("Sticker popup panel: " + url, flush=True)
    print("Watching new stickers from the chosen contact. Press Ctrl+C to stop.", flush=True)
    if open_window:
        open_panel(url)
    try:
        while True:
            try:
                summary = watcher.poll_once()
                if summary["stickers"]:
                    LOG.info("explained %d sticker(s)", summary["explained"])
            except sqlite3.Error:
                LOG.warning("Messages database busy; retrying")
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        watcher.close()
        vision.close()
        db.close()
