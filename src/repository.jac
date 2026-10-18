"""Persistent history, immutable request snapshots, and a local private outbox."""
import json;
import sqlite3;
import from sqlite3 { Connection }
import from pathlib { Path }
import from .contracts { canonical, digest, now }

def connect(path: str) -> Connection {
    if path != ":memory:" { Path(path).parent.mkdir(parents=True, exist_ok=True); }
    db = sqlite3.connect(path);
    db.row_factory = sqlite3.Row;
    db.execute("PRAGMA foreign_keys = ON");
    db.executescript("""
        CREATE TABLE IF NOT EXISTS enrollments (
            platform TEXT, conversation_id TEXT, recipient_id TEXT,
            destination TEXT NOT NULL, members_json TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            source_kind TEXT NOT NULL DEFAULT 'group',
            source_verified INTEGER NOT NULL DEFAULT 0,
            assistant_id TEXT,
            PRIMARY KEY (platform, conversation_id, recipient_id)
        );
        CREATE TABLE IF NOT EXISTS preferences (
            platform TEXT, recipient_id TEXT, settings_json TEXT NOT NULL,
            updated_at TEXT NOT NULL, PRIMARY KEY (platform, recipient_id)
        );
        CREATE TABLE IF NOT EXISTS relationships (
            platform TEXT, recipient_id TEXT, sender_id TEXT,
            relationship TEXT NOT NULL, updated_at TEXT NOT NULL,
            PRIMARY KEY (platform, recipient_id, sender_id)
        );
        CREATE TABLE IF NOT EXISTS messages (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL, conversation_id TEXT NOT NULL,
            message_id TEXT NOT NULL, sent_at TEXT NOT NULL,
            event_json TEXT NOT NULL, event_sha256 TEXT NOT NULL,
            UNIQUE (platform, conversation_id, message_id)
        );
        CREATE INDEX IF NOT EXISTS message_order
            ON messages(platform, conversation_id, sent_at, sequence);
        CREATE TABLE IF NOT EXISTS context_windows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL, conversation_id TEXT NOT NULL,
            source_message_id TEXT NOT NULL, recipient_id TEXT NOT NULL,
            request_json TEXT NOT NULL, request_sha256 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (platform, conversation_id, source_message_id, recipient_id)
        );
        CREATE TRIGGER IF NOT EXISTS immutable_context_window
            BEFORE UPDATE ON context_windows
            BEGIN SELECT RAISE(ABORT, 'context snapshots are immutable'); END;
        CREATE TABLE IF NOT EXISTS interpretation_runs (
            window_id INTEGER PRIMARY KEY REFERENCES context_windows(id) ON DELETE CASCADE,
            status TEXT NOT NULL, result_json TEXT, error_code TEXT
        );
        CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            window_id INTEGER NOT NULL UNIQUE REFERENCES context_windows(id) ON DELETE CASCADE,
            recipient_id TEXT NOT NULL, destination TEXT NOT NULL,
            text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            window_id INTEGER NOT NULL REFERENCES context_windows(id) ON DELETE CASCADE,
            recipient_id TEXT NOT NULL, selection TEXT NOT NULL,
            note TEXT, provenance TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """);
    columns = [row["name"] for row in db.execute("PRAGMA table_info(enrollments)").fetchall()];
    for (column, definition) in [("source_kind", "TEXT NOT NULL DEFAULT 'group'"),
                                 ("source_verified", "INTEGER NOT NULL DEFAULT 0"),
                                 ("assistant_id", "TEXT")] {
        if column not in columns { db.execute("ALTER TABLE enrollments ADD COLUMN " + column + " " + definition); }
    }
    db.commit();
    return db;
}

def enroll(db: Connection, platform: str, conversation: str, recipient: str,
           destination: str, members: list[str], enabled: bool = True,
           source_kind: str = "group", source_verified: bool = False,
           assistant_id: str | None = None) -> None {
    direct = source_kind == "direct" and source_verified is True;
    if source_kind not in ["group", "direct"] or type(source_verified) is not bool or type(enabled) is not bool {
        raise ValueError("Invalid enrollment mode");
    }
    if direct and (not assistant_id or assistant_id == recipient or set(members) != {recipient, assistant_id}) {
        raise ValueError("Verified direct mode requires exactly the recipient and assistant");
    }
    if recipient not in members or not destination or (destination == conversation and not direct) {
        raise ValueError("Private destination and source membership are required");
    }
    db.execute("""INSERT INTO enrollments
        (platform, conversation_id, recipient_id, destination, members_json, enabled,
         source_kind, source_verified, assistant_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(platform, conversation_id, recipient_id) DO UPDATE SET
        destination=excluded.destination, members_json=excluded.members_json,
        enabled=excluded.enabled, source_kind=excluded.source_kind,
        source_verified=excluded.source_verified, assistant_id=excluded.assistant_id""",
        (platform, conversation, recipient, destination, canonical(members), int(enabled),
         source_kind, int(source_verified), assistant_id));
    db.commit();
}

def active_enrollments(db: Connection, event: dict) -> list[dict] {
    rows = db.execute("""SELECT * FROM enrollments WHERE platform=?
        AND conversation_id=? AND enabled=1""",
        (event["platform"], event["conversation_id"])).fetchall();
    return [dict(row) for row in rows if event["sender_id"] in json.loads(str(row["members_json"]))];
}

def set_preferences(db: Connection, platform: str, recipient: str, language: str,
                    length: str) -> None {
    if not language.strip() or length not in ["short", "detailed"] {
        raise ValueError("Language and a supported explanation length are required");
    }
    settings = {"language": language, "explanation_length": length};
    db.execute("""INSERT INTO preferences VALUES (?, ?, ?, ?)
        ON CONFLICT(platform, recipient_id) DO UPDATE SET
        settings_json=excluded.settings_json, updated_at=excluded.updated_at""",
        (platform, recipient, canonical(settings), now()));
    db.commit();
}

def set_relationship(db: Connection, platform: str, recipient: str, sender: str,
                     relationship: str) -> None {
    if not relationship.strip() { raise ValueError("Relationship must not be empty"); }
    db.execute("""INSERT INTO relationships VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(platform, recipient_id, sender_id) DO UPDATE SET
        relationship=excluded.relationship, updated_at=excluded.updated_at""",
        (platform, recipient, sender, relationship, now()));
    db.commit();
}

def user_context(db: Connection, event: dict, recipient: str) -> dict {
    prefs = db.execute("SELECT * FROM preferences WHERE platform=? AND recipient_id=?",
        (event["platform"], recipient)).fetchone();
    relation = db.execute("""SELECT * FROM relationships WHERE platform=?
        AND recipient_id=? AND sender_id=?""",
        (event["platform"], recipient, event["sender_id"])).fetchone();
    return {
        "preferences": json.loads(str(prefs["settings_json"])) if prefs else {
            "language": "en", "explanation_length": "short"
        },
        "preferences_source": "user_declared" if prefs else "implementation_default",
        "relationship": relation["relationship"] if relation else None,
        "relationship_source": "recipient_declared" if relation else None
    };
}

def record_message(db: Connection, event: dict, commit: bool = True) -> dict {
    key = (event["platform"], event["conversation_id"], event["message_id"]);
    existing = db.execute("""SELECT * FROM messages WHERE platform=?
        AND conversation_id=? AND message_id=?""", key).fetchone();
    if existing {
        if existing["event_sha256"] != digest(event) {
            raise ValueError("Source message identity was reused with changed content");
        }
        return dict(existing);
    }
    db.execute("""INSERT INTO messages
        (platform, conversation_id, message_id, sent_at, event_json, event_sha256)
        VALUES (?, ?, ?, ?, ?, ?)""",
        key + (event["sent_at"], canonical(event), digest(event)));
    if commit { db.commit(); }
    return dict(db.execute("""SELECT * FROM messages WHERE platform=?
        AND conversation_id=? AND message_id=?""", key).fetchone());
}

def preceding_messages(db: Connection, target: dict, limit: int) -> list[dict] {
    rows = db.execute("""SELECT event_json FROM messages
        WHERE platform=? AND conversation_id=? AND sequence < ? AND sent_at <= ?
        ORDER BY sent_at DESC, sequence DESC LIMIT ?""",
        (target["platform"], target["conversation_id"], target["sequence"],
         target["sent_at"], limit)).fetchall();
    return [dict(json.loads(str(row["event_json"]))) for row in reversed(rows)];
}

def snapshot(db: Connection, event: dict, recipient: str, request: dict,
             commit: bool = True) -> tuple[dict, bool] {
    key = (event["platform"], event["conversation_id"], event["message_id"], recipient);
    old = db.execute("""SELECT * FROM context_windows WHERE platform=?
        AND conversation_id=? AND source_message_id=? AND recipient_id=?""", key).fetchone();
    if old { return (dict(old), False); }
    cursor = db.execute("""INSERT INTO context_windows
        (platform, conversation_id, source_message_id, recipient_id,
         request_json, request_sha256, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        key + (canonical(request), digest(request), now()));
    window_id = cursor.lastrowid;
    db.execute("INSERT INTO interpretation_runs(window_id, status) VALUES (?, 'prepared')",
        (window_id,));
    if commit { db.commit(); }
    return (dict(db.execute("SELECT * FROM context_windows WHERE id=?", (window_id,)).fetchone()), True);
}

def load_snapshot(db: Connection, window_id: int) -> dict {
    row = db.execute("SELECT * FROM context_windows WHERE id=?", (window_id,)).fetchone();
    if row is None { raise ValueError("Unknown context window"); }
    saved = dict(row);
    saved["request"] = json.loads(str(saved.pop("request_json")));
    return saved;
}

def save_feedback(db: Connection, window_id: int, recipient: str, selection: str,
                  note: str | None = None, commit: bool = True) -> int {
    window = load_snapshot(db, window_id);
    if window["recipient_id"] != recipient {
        raise ValueError("Feedback recipient does not own this context window");
    }
    if selection not in ["first", "second", "neither", "not_sure"] {
        raise ValueError("Unknown feedback selection");
    }
    run = db.execute("SELECT result_json FROM interpretation_runs WHERE window_id=?",
        (window_id,)).fetchone();
    if not run or not run["result_json"] { raise ValueError("No interpretation to validate"); }
    result = json.loads(str(run["result_json"]));
    if note is not None and (not isinstance(note, str) or len(note) > 2000) {
        raise ValueError("Feedback note must contain at most 2000 characters");
    }
    if selection == "first" and (result["status"] == "unsupported" or not result["meaning"]) {
        raise ValueError("No first interpretation was shown");
    }
    if selection == "second" and not result.get("alternative") {
        raise ValueError("This exchange did not show a second interpretation");
    }
    cursor = db.execute("""INSERT INTO feedback
        (window_id, recipient_id, selection, note, provenance, created_at)
        VALUES (?, ?, ?, ?, 'recipient_judgment', ?)""",
        (window_id, recipient, selection, note, now()));
    if commit { db.commit(); }
    return int(cursor.lastrowid);
}

def purge_conversation(db: Connection, platform: str, conversation: str) -> None {
    # Explicit local deletion; cascading removes windows, runs, feedback and outbox.
    with db {
        db.execute("DELETE FROM context_windows WHERE platform=? AND conversation_id=?",
            (platform, conversation));
        db.execute("DELETE FROM messages WHERE platform=? AND conversation_id=?",
            (platform, conversation));
        db.execute("DELETE FROM enrollments WHERE platform=? AND conversation_id=?",
            (platform, conversation));
    }
}
