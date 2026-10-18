"""Durable T5 ports over T4 history, frozen requests and a private outbox."""
import json;
import from sqlite3 { Connection }
import from .contracts { canonical, digest, normalize_event, now }
import from .context { build_request }
import from .repository { active_enrollments, record_message, snapshot, load_snapshot, save_feedback }
import from .routing { verified_direct }

def initialize(db: Connection) {
    db.executescript("""
        CREATE TABLE IF NOT EXISTS pipeline_jobs (
            window_id INTEGER PRIMARY KEY REFERENCES context_windows(id) ON DELETE CASCADE,
            state TEXT NOT NULL DEFAULT 'pending', idempotency_key TEXT NOT NULL UNIQUE,
            errors_json TEXT NOT NULL DEFAULT '[]', receipt_json TEXT
        );
    """);
    columns = [row["name"] for row in db.execute("PRAGMA table_info(outbox)").fetchall()];
    if "receipt_json" not in columns { db.execute("ALTER TABLE outbox ADD COLUMN receipt_json TEXT"); }
    # Preserve jobs/results from the earlier local T4 schema without repeating inference.
    rows = db.execute("""SELECT w.*, r.status AS run_status, r.result_json FROM context_windows w
        JOIN interpretation_runs r ON r.window_id=w.id LEFT JOIN pipeline_jobs j ON j.window_id=w.id
        WHERE j.window_id IS NULL""").fetchall();
    for row in rows {
        state = "interpreted" if row["result_json"] else "pending";
        if row["run_status"] == "failed" { state = "interpretation_failed"; }
        key = digest([row["platform"], row["conversation_id"], row["source_message_id"], row["recipient_id"]]);
        db.execute("INSERT INTO pipeline_jobs(window_id, state, idempotency_key) VALUES (?, ?, ?)", (row["id"], state, key));
    }
    db.commit();
}

def observe(db: Connection, raw: dict, settings: dict) -> list[int] {
    event = normalize_event(raw);
    if event["from_assistant"] { return []; }
    enrollments = active_enrollments(db, event);
    if not enrollments { return []; }
    ids = [];
    with db {
        target = record_message(db, event, commit=False);
        if event["kind"] == "sticker" {
            for enrollment in enrollments {
                trusted = dict(enrollment);
                trusted["members"] = json.loads(str(trusted["members_json"]));
                trusted["source_verified"] = bool(trusted["source_verified"]);
                direct = verified_direct(trusted);
                if enrollment["recipient_id"] == event["sender_id"] and not direct { continue; }
                recipient = str(enrollment["recipient_id"]);
                for setting in ["context_message_limit", "context_text_character_budget", "message_text_character_limit", "target_text_character_limit"] {
                    if type(settings.get(setting)) is not int or settings[setting] < 1 { raise ValueError("Invalid context limit"); }
                }
                request = build_request(db, target, event, recipient,
                    int(settings["context_message_limit"]), int(settings["context_text_character_budget"]),
                    int(settings["message_text_character_limit"]), int(settings["target_text_character_limit"]));
                (window, created) = snapshot(db, event, recipient, request, commit=False);
                key = digest([event["platform"], event["conversation_id"], event["message_id"], recipient]);
                db.execute("INSERT OR IGNORE INTO pipeline_jobs(window_id, idempotency_key) VALUES (?, ?)",
                    (window["id"], key));
                ids.append(int(window["id"]));
            }
        }
    }
    return ids;
}

def load_job(db: Connection, window_id: int) -> dict {
    window = load_snapshot(db, window_id);
    row = db.execute("SELECT * FROM pipeline_jobs WHERE window_id=?", (window_id,)).fetchone();
    if row is None { raise ValueError("Unknown pipeline job"); }
    run = db.execute("SELECT result_json FROM interpretation_runs WHERE window_id=?", (window_id,)).fetchone();
    return {"window_id": window_id, "request": window["request"],
        "request_sha256": window["request_sha256"], "state": row["state"],
        "result": json.loads(str(run["result_json"])) if run and run["result_json"] else None,
        "idempotency_key": row["idempotency_key"], "errors": json.loads(str(row["errors_json"])),
        "receipt": json.loads(str(row["receipt_json"])) if row["receipt_json"] else None};
}

def resolve_route(db: Connection, window_id: int) -> dict {
    window = load_snapshot(db, window_id);
    row = db.execute("""SELECT * FROM enrollments WHERE platform=?
        AND conversation_id=? AND recipient_id=?""",
        (window["platform"], window["conversation_id"], window["recipient_id"])).fetchone();
    if row is None { raise PermissionError("Enrollment unavailable"); }
    route = dict(row);
    route["members"] = json.loads(str(route.pop("members_json")));
    route["enabled"] = bool(route["enabled"]);
    route["source_verified"] = bool(route["source_verified"]);
    return route;
}

def claim(db: Connection, window_id: int, phase: str) -> bool {
    if phase not in ["interpreting", "sending"] { raise ValueError("Unknown claim phase"); }
    states = ["pending", "interpretation_failed", "blocked"] if phase == "interpreting" else ["interpreted", "send_failed", "blocked"];
    # A single conditional UPDATE gives competing SQLite connections one winner.
    condition = "IS NULL" if phase == "interpreting" else "IS NOT NULL";
    with db {
        cursor = db.execute("""UPDATE pipeline_jobs SET state=? WHERE window_id=?
            AND state IN (?, ?, ?) AND (SELECT result_json FROM interpretation_runs
                WHERE window_id=pipeline_jobs.window_id) """ + condition,
            (phase, window_id, states[0], states[1], states[2]));
        if cursor.rowcount == 1 and phase == "sending" {
            db.execute("UPDATE outbox SET status='sending' WHERE window_id=?", (window_id,));
        }
    }
    return cursor.rowcount == 1;
}

def save_result(db: Connection, window_id: int, result: dict, text: str) {
    window = load_snapshot(db, window_id);
    if result.get("source_message_id") != window["source_message_id"] {
        raise ValueError("Result does not belong to this window");
    }
    route = resolve_route(db, window_id);
    with db {
        cursor = db.execute("UPDATE pipeline_jobs SET state='interpreted' WHERE window_id=? AND state='interpreting'", (window_id,));
        if cursor.rowcount != 1 { raise ValueError("Interpretation must own a claim"); }
        db.execute("UPDATE interpretation_runs SET status='interpreted', result_json=?, error_code=NULL WHERE window_id=?",
            (canonical(result), window_id));
        db.execute("""INSERT INTO outbox(window_id, recipient_id, destination, text, created_at)
            VALUES (?, ?, ?, ?, ?)""", (window_id, window["recipient_id"], route["destination"], text, now()));
    }
}

def mark_failure(db: Connection, window_id: int, state: str, error_code: str) {
    if state not in ["blocked", "interpretation_failed", "send_failed", "delivery_unknown"] {
        raise ValueError("Unknown failure state");
    }
    with db {
        row = db.execute("SELECT state, errors_json FROM pipeline_jobs WHERE window_id=?", (window_id,)).fetchone();
        if row is None { raise ValueError("Unknown pipeline job"); }
        if row["state"] == "accepted" { return; }
        errors = list(json.loads(str(row["errors_json"])));
        errors.append(error_code);
        db.execute("UPDATE pipeline_jobs SET state=?, errors_json=? WHERE window_id=?", (state, canonical(errors), window_id));
        db.execute("UPDATE interpretation_runs SET status=?, error_code=? WHERE window_id=?", (state, error_code, window_id));
        db.execute("UPDATE outbox SET status=? WHERE window_id=?", (state, window_id));
    }
}

def mark_accepted(db: Connection, window_id: int, receipt: dict) {
    if receipt.get("status") != "accepted" or not receipt.get("provider_message_id") {
        raise ValueError("Definitive provider acknowledgment required");
    }
    with db {
        cursor = db.execute("""UPDATE pipeline_jobs SET state='accepted', receipt_json=?
            WHERE window_id=? AND state='sending'""", (canonical(receipt), window_id));
        if cursor.rowcount != 1 { raise ValueError("Delivery must own a send claim"); }
        db.execute("UPDATE outbox SET status='accepted', receipt_json=? WHERE window_id=?", (canonical(receipt), window_id));
        db.execute("UPDATE interpretation_runs SET status='accepted', error_code=NULL WHERE window_id=?", (window_id,));
    }
}

def get_explanation(db: Connection, window_id: int, recipient: str) -> dict {
    # Missing and other-recipient records deliberately have the same response.
    if type(window_id) is not int or window_id < 1 or not recipient { raise PermissionError("Saved exchange unavailable."); }
    row = db.execute("""SELECT w.source_message_id, r.result_json FROM context_windows w
        JOIN interpretation_runs r ON r.window_id=w.id WHERE w.id=? AND w.recipient_id=?""",
        (window_id, recipient)).fetchone();
    if row is None or not row["result_json"] {
        raise PermissionError("Saved exchange unavailable.");
    }
    result = dict(json.loads(str(row["result_json"])));
    return {"ok": True, "window_id": window_id, "source_message_id": row["source_message_id"],
        "status": result["status"], "meaning": result["meaning"], "alternative": result["alternative"],
        "context_cue": result["context_cue"], "uncertainty_caveat": result["uncertainty_caveat"],
        "candidate_relation": result["candidate_relation"]};
}

def feedback(db: Connection, window_id: int, recipient: str, selection: str,
             note: str | None = None) -> dict {
    get_explanation(db, window_id, recipient);
    feedback_id = save_feedback(db, window_id, recipient, selection, note);
    record = dict(db.execute("SELECT * FROM feedback WHERE id=?", (feedback_id,)).fetchone());
    record["feedback_id"] = record.pop("id");
    return {"ok": True, "feedback": record};
}
