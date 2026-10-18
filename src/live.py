"""Authenticated local Photon polling runtime for the sticker interpreter."""

from __future__ import annotations

import json
import logging
import os
import random
import signal
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from .adapters.assembly import Interpreter, PhotonTransport
from .adapters.photon import (
    PhotonError,
    PhotonHTTPClient,
    PrivateDestination,
)
from .adapters.vision import OpenAIVision
from .context_store import SQLiteStore
from .main import create_pipeline, load_settings, process_event, run_window

LOG = logging.getLogger("sticker_interpreter.live")


def _required(environ: dict[str, str], name: str) -> str:
    value = environ.get(name, "").strip()
    if not value:
        raise ValueError(name + " is required")
    return value


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Photon timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class LiveConfig:
    project_id: str
    api_key: str
    agent_handle: str
    allowed_sender_handle: str
    database_path: str = "local-data/live.sqlite3"
    poll_seconds: float = 2.0
    lookback_seconds: int = 0
    request_timeout: float = 15.0

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "LiveConfig":
        values = dict(os.environ if environ is None else environ)
        try:
            poll_seconds = float(values.get("PHOTON_POLL_SECONDS", "2"))
            lookback_seconds = int(values.get("PHOTON_LOOKBACK_SECONDS", "0"))
            request_timeout = float(values.get("PHOTON_TIMEOUT_SECONDS", "15"))
        except ValueError:
            raise ValueError("Photon timing settings must be numeric") from None
        if not 0.25 <= poll_seconds <= 300:
            raise ValueError("PHOTON_POLL_SECONDS must be between 0.25 and 300")
        if not 0 <= lookback_seconds <= 86_400:
            raise ValueError("PHOTON_LOOKBACK_SECONDS must be between 0 and 86400")
        if not 1 <= request_timeout <= 120:
            raise ValueError("PHOTON_TIMEOUT_SECONDS must be between 1 and 120")
        return cls(
            project_id=_required(values, "PHOTON_PROJECT_ID"),
            api_key=_required(values, "PHOTON_API_KEY"),
            agent_handle=_required(values, "PHOTON_AGENT_HANDLE"),
            allowed_sender_handle=_required(values, "PHOTON_ALLOWED_SENDER"),
            database_path=values.get("STICKER_DB_PATH", "local-data/live.sqlite3"),
            poll_seconds=poll_seconds,
            lookback_seconds=lookback_seconds,
            request_timeout=request_timeout,
        )


class DeferredOpenAIVision:
    """Construct the network client on the first sticker, not at process startup."""

    def __init__(self):
        model = os.environ.get("VISION_MODEL", "").strip() or "gpt-4.1-mini"
        self._vision = None
        self.metadata = {"provider": "openai-api-key", "model": model}
        self.last_call_metadata = None

    def __call__(self, request):
        if self._vision is None:
            self._vision = OpenAIVision(model=self.metadata["model"])
            self.metadata = dict(self._vision.metadata)
        result = self._vision(request)
        self.last_call_metadata = getattr(self._vision, "last_call_metadata", None)
        return result

    def close(self):
        if self._vision is not None and callable(getattr(self._vision, "close", None)):
            self._vision.close()


class LiveRuntime:
    """One project, one verified direct space, one model adapter."""

    def __init__(self, config: LiveConfig, *, client=None, vision=None, store=None,
                 sleep=time.sleep, clock=_utc_now):
        self.config = config
        self.client = client or PhotonHTTPClient(
            project_id=config.project_id, api_key=config.api_key,
        )
        self.vision = vision or DeferredOpenAIVision()
        self.store = store or SQLiteStore(config.database_path)
        self._owns_vision = vision is None
        self._owns_store = store is None
        self._sleep = sleep
        self._clock = clock
        self._stop = threading.Event()
        self.transport = None
        self.pipeline = None
        self.identity = None
        self._initialize_runtime_tables()

    def _initialize_runtime_tables(self):
        self.store.db.executescript("""
            CREATE TABLE IF NOT EXISTS live_state (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS live_receipts (
                message_id TEXT PRIMARY KEY, status TEXT NOT NULL,
                processed_at TEXT NOT NULL, window_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS live_delivery_status (
                provider_message_id TEXT PRIMARY KEY, status TEXT NOT NULL,
                checked_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS live_attachments (
                source_message_id TEXT PRIMARY KEY, mime_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS live_model_calls (
                source_message_id TEXT PRIMARY KEY, metadata_json TEXT NOT NULL,
                recorded_at TEXT NOT NULL
            );
        """)
        receipt_columns = {
            row["name"]
            for row in self.store.db.execute("PRAGMA table_info(live_receipts)")
        }
        if "window_id" not in receipt_columns:
            self.store.db.execute("ALTER TABLE live_receipts ADD COLUMN window_id INTEGER")
        self.store.db.commit()

    def close(self):
        if self._owns_vision and callable(getattr(self.vision, "close", None)):
            self.vision.close()
        if self._owns_store:
            self.store.close()

    def stop(self, *_args):
        self._stop.set()

    def _list_all(self, *, created_since=None, order="asc"):
        token = None
        messages = []
        seen_tokens = set()
        for _ in range(100):
            page = self.client.list_messages(
                created_since=created_since, page_token=token, page_size=100,
                platform="imessage", direction="received", order=order,
                timeout=self.config.request_timeout,
            )
            messages.extend(page["items"])
            token = page.get("nextPageToken")
            if token is None:
                return messages
            if token in seen_tokens:
                raise PhotonError("pagination_cycle")
            seen_tokens.add(token)
        raise PhotonError("pagination_limit")

    def _message_identity(self, message):
        if message.get("platform") != "imessage" or message.get("status") != "received":
            raise PhotonError("source_scope_mismatch")
        sender = message.get("sentBy")
        agent = message.get("receivedBy")
        space = message.get("space")
        if not all(isinstance(item, dict) for item in (sender, agent, space)):
            raise PhotonError("invalid_provider_response")
        if (sender.get("kind") != "human"
                or sender.get("handle") != self.config.allowed_sender_handle):
            raise PhotonError("unauthorized_sender")
        if (agent.get("kind") != "agent"
                or agent.get("handle") != self.config.agent_handle):
            raise PhotonError("unauthorized_agent")
        sender_id, agent_id, space_id = sender.get("id"), agent.get("id"), space.get("id")
        participants = space.get("participantIds")
        if (space.get("kind") != "direct" or not all(
                isinstance(value, str) and value for value in (sender_id, agent_id, space_id))
                or not isinstance(participants, list)
                or set(participants) != {sender_id, agent_id} or len(participants) != 2):
            raise PhotonError("unauthorized_space")
        return {
            "sender_id": sender_id, "agent_id": agent_id, "space_id": space_id,
            "participants": tuple(participants),
        }

    def _scoped_message(self, message):
        scoped = json.loads(json.dumps(message))
        scoped["projectId"] = self.config.project_id
        for key in ("sentBy", "receivedBy", "space"):
            scoped[key]["projectId"] = self.config.project_id
            scoped[key]["platform"] = "imessage"
        timestamps = scoped.setdefault("timestamps", {})
        if "receivedAt" not in timestamps:
            timestamps["receivedAt"] = scoped.get("createdAt")
        return scoped

    def bootstrap(self):
        candidates = self._list_all(order="desc")
        identity = None
        for message in candidates:
            try:
                identity = self._message_identity(message)
                break
            except PhotonError:
                continue
        if identity is None:
            raise PhotonError("verified_direct_space_not_found")
        self.identity = identity
        self.store.enroll(
            "imessage", identity["space_id"], identity["sender_id"],
            identity["space_id"], list(identity["participants"]),
            source_kind="direct", source_verified=True,
            assistant_id=identity["agent_id"],
        )

        def resolve_private(delivery, route):
            return PrivateDestination(
                recipient_id=delivery["recipient_id"],
                source_conversation_id=delivery["source_conversation_id"],
                platform="imessage", space_id=route["destination"],
                sender_id=identity["agent_id"],
                recipient_user_id=identity["sender_id"],
                participant_ids=identity["participants"],
                verified=True,
            )

        self.transport = PhotonTransport(
            self.store, project_id=self.config.project_id, platform="imessage",
            assistant_ids={identity["agent_id"]}, client=self.client,
            verify_event=lambda _body, _headers: False,
            decode_event=lambda _envelope: None,
            resolve_private=resolve_private,
            # Photon does not expose native sticker events. In the verified direct
            # test space, an image attachment is the explicit photo-button fallback.
            classify_attachment=lambda _message, _part: "sticker",
        )
        self.pipeline = create_pipeline(
            self.store, Interpreter(self.vision), self.transport,
            load_settings(os.environ),
        )
        return dict(identity)

    def _cursor(self):
        row = self.store.db.execute(
            "SELECT value FROM live_state WHERE key='received_cursor'"
        ).fetchone()
        if row:
            return _parse_time(row["value"])
        if self.config.lookback_seconds == 0:
            return None
        return self._clock() - timedelta(seconds=self.config.lookback_seconds)

    def _save_cursor(self, value):
        stamp = value.astimezone(timezone.utc).isoformat(timespec="microseconds")
        self.store.db.execute(
            """INSERT INTO live_state(key, value) VALUES ('received_cursor', ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value""", (stamp,),
        )
        self.store.db.commit()

    def _was_processed(self, message_id):
        return self.store.db.execute(
            "SELECT 1 FROM live_receipts WHERE message_id=?", (message_id,),
        ).fetchone() is not None

    def _mark_processed(self, message_id, status, window_id=None):
        self.store.db.execute(
            """INSERT INTO live_receipts(message_id, status, processed_at, window_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                status=excluded.status, processed_at=excluded.processed_at,
                window_id=COALESCE(excluded.window_id, live_receipts.window_id)""",
            (message_id, status, self._clock().isoformat(), window_id),
        )
        self.store.db.commit()

    def _model_configured(self):
        return bool(
            os.environ.get("OPENAI_API_KEY", "").strip()
            or os.environ.get("VISION_API_KEY", "").strip()
        )

    def _retry_saved_configuration_failures(self):
        if not self._model_configured():
            return 0
        rows = self.store.db.execute(
            """SELECT r.window_id FROM live_receipts r
            JOIN interpretation_runs i ON i.window_id = r.window_id
            WHERE r.window_id IS NOT NULL AND i.status = 'interpretation_failed'
            AND i.error_code IN ('api_key_not_configured', 'model_not_configured')"""
        ).fetchall()
        for row in rows:
            outcome = run_window(self.pipeline, int(row["window_id"]), retry=True)
            self._mark_processed(
                self.store.db.execute(
                    "SELECT message_id FROM live_receipts WHERE window_id=?",
                    (row["window_id"],),
                ).fetchone()["message_id"],
                str(outcome.get("status", "processed")),
                int(row["window_id"]),
            )
        return len(rows)

    def _matches_bootstrap(self, identity):
        return all(identity[key] == self.identity[key] for key in (
            "sender_id", "agent_id", "space_id",
        ))

    def reconcile_deliveries(self):
        rows = self.store.db.execute(
            """SELECT receipt_json FROM pipeline_jobs
            WHERE state='accepted' AND receipt_json IS NOT NULL"""
        ).fetchall()
        counts = {"delivered": 0, "pending": 0}
        for row in rows:
            receipt = json.loads(row["receipt_json"])
            message_id = receipt.get("provider_message_id")
            if not message_id:
                continue
            try:
                message = self.client.get_message(
                    message_id, timeout=self.config.request_timeout,
                )
                status = str(message.get("status", "unknown"))
            except PhotonError as error:
                if not error.retryable and error.code != "provider_http_404":
                    raise
                status = "temporarily_unavailable"
            self.store.db.execute(
                "INSERT OR REPLACE INTO live_delivery_status VALUES (?, ?, ?)",
                (message_id, status, self._clock().isoformat()),
            )
            counts["delivered" if status == "delivered" else "pending"] += 1
        self.store.db.commit()
        return counts

    def poll_once(self):
        load_dotenv(override=True)
        if self.pipeline is None:
            self.bootstrap()
        retried = self._retry_saved_configuration_failures()
        cursor = self._cursor()
        # A bounded overlap prevents equal-timestamp and commit-boundary misses.
        since = None if cursor is None else (cursor - timedelta(seconds=5)).isoformat()
        messages = self._list_all(created_since=since, order="asc")
        messages.sort(key=lambda item: (
            item.get("timestamps", {}).get("receivedAt") or item.get("createdAt") or "",
            item.get("id") or "",
        ))
        result = {"seen": len(messages), "processed": 0, "duplicates": 0,
                  "history_only": 0, "sticker": 0, "ignored": 0, "retried": retried}
        latest = cursor or datetime.min.replace(tzinfo=timezone.utc)
        for message in messages:
            message_id = message.get("id")
            if not isinstance(message_id, str) or not message_id:
                raise PhotonError("invalid_provider_response")
            received = _parse_time(
                message.get("timestamps", {}).get("receivedAt")
                or message.get("createdAt")
            )
            window_id = None
            if self._was_processed(message_id):
                result["duplicates"] += 1
                latest = max(latest, received)
                continue
            try:
                identity = self._message_identity(message)
                if not self._matches_bootstrap(identity):
                    self._mark_processed(message_id, "ignored_other_space")
                    result["ignored"] += 1
                    latest = max(latest, received)
                    continue
                normalized = self.transport.adapter.normalize_message(
                    self._scoped_message(message)
                )
            except PhotonError as error:
                if error.retryable:
                    raise
                self._mark_processed(message_id, "rejected_" + error.code)
                result["ignored"] += 1
                latest = max(latest, received)
                continue
            if normalized.event is None:
                status = "ignored"
                result["ignored"] += 1
            else:
                sticker = normalized.event.get("sticker")
                if isinstance(sticker, dict):
                    import base64
                    size = len(base64.b64decode(sticker["data_base64"], validate=True))
                    self.store.db.execute(
                        "INSERT OR IGNORE INTO live_attachments VALUES (?, ?, ?, ?, ?)",
                        (message_id, sticker["mime_type"], size, sticker["sha256"],
                         self._clock().isoformat()),
                    )
                    self.store.db.commit()
                outcomes = process_event(
                    self.pipeline, normalized.event, authenticated=True,
                )
                status = str(outcomes[0].get("status", "processed"))
                window_id = outcomes[0].get("window_id")
                model_metadata = getattr(self.vision, "last_call_metadata", None)
                if normalized.event["kind"] == "sticker" and isinstance(model_metadata, dict):
                    self.store.db.execute(
                        "INSERT OR IGNORE INTO live_model_calls VALUES (?, ?, ?)",
                        (message_id, json.dumps(model_metadata, sort_keys=True),
                         self._clock().isoformat()),
                    )
                    self.store.db.commit()
                result["sticker" if normalized.event["kind"] == "sticker"
                       else "history_only"] += 1
            self._mark_processed(message_id, status, window_id)
            result["processed"] += 1
            latest = max(latest, received)
        if latest == datetime.min.replace(tzinfo=timezone.utc):
            latest = self._clock()
        self._save_cursor(latest)
        result["delivery"] = self.reconcile_deliveries()
        return result

    def run(self):
        delay = self.config.poll_seconds
        while not self._stop.is_set():
            try:
                summary = self.poll_once()
                LOG.info(
                    "poll complete seen=%d processed=%d stickers=%d",
                    summary["seen"], summary["processed"], summary["sticker"],
                )
                delay = self.config.poll_seconds
            except PhotonError as error:
                LOG.warning(
                    "Photon operation failed code=%s retryable=%s",
                    error.code, error.retryable,
                )
                if not error.retryable:
                    raise
                delay = min(max(delay * 2, 1.0), 60.0)
            except Exception:
                LOG.exception("Live poll failed")
                delay = min(max(delay * 2, 1.0), 60.0)
            self._stop.wait(delay + random.uniform(0, min(delay * 0.1, 1.0)))


def run_live(*, once=False):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    load_dotenv()
    config = LiveConfig.from_env()
    runtime = LiveRuntime(config)
    previous = {}
    try:
        if not once:
            for name in (signal.SIGINT, signal.SIGTERM):
                previous[name] = signal.signal(name, runtime.stop)
        return runtime.poll_once() if once else runtime.run()
    finally:
        for name, handler in previous.items():
            signal.signal(name, handler)
        runtime.close()
