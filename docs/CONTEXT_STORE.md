# Persistent context and coordinator storage

## What issue #5 does

This is the app's persistent memory. For each sticker it keeps a frozen copy of
the relevant conversation, the explanation that was produced, and the work still
waiting to be sent. A snapshot is that frozen copy: later conversation or profile
changes cannot rewrite what the model originally saw.

| Stored record | Why it exists |
| --- | --- |
| Conversation messages | Keep observed history, separately from the bounded model input. |
| Recipient settings and relationships | Load that recipient's declared language, length and sender relationship. |
| Context window | Freeze the target and preceding 20–25 messages for one sticker and recipient. |
| Interpretation result | Retrieve the original explanation later without another model call. |
| Private outbox | Track a queued reply and its acknowledgment, independently of inference. |
| Feedback and command receipt | Save an exchange-specific judgment and recognize the same command on retry. |

SQLite stores these records in one local file, with no separate database server.
Its transactions let related updates succeed together or roll back together.
Image interpretation belongs to #4; provider sending and final wiring belong to
the Photon adapter and #6. This module records state rather than verifying real
platform identities or claiming that a phone displayed a message.

## Interfaces and state

`src.context_store.SQLiteStore(path)` exposes T5's store ports over standard-library Python SQLite logic. Core source was retained from the local T4 prototype; scheduling, claims, results, acknowledgment state and lookup/feedback operations are now integrated.

The store preserves longer per-platform/conversation history. Each sticker/recipient gets an immutable v2 snapshot with up to 25 preceding messages, configurable from 20–25, no age cutoff and explicit text budgets. Later messages, preferences and feedback do not alter it. Feedback stays evaluation-only. Existing prototype snapshots/results migrate without another inference call.

`observe`, `load_job`, `resolve_route`, `claim`, `save_result`, `mark_failure` and `mark_accepted` implement the coordinator ports. Result persistence creates a pending private outbox entry; `accepted` requires a provider message ID and never asserts visual phone receipt. Claims use conditional SQLite updates. Source replays and process restarts do not resend accepted jobs. Interrupted interpreting/sending claims and unknown acknowledgments require reconciliation; there is no distributed exactly-once guarantee or automatic billed retry.

| State | Meaning and next action |
| --- | --- |
| pending outbox | Explanation saved and queued; no send is implied. |
| sending | A send has been claimed; an interrupted process must reconcile before retrying. |
| accepted | Provider acknowledgment and message ID were saved. Replays do not resend; phone receipt remains separate evidence. |
| send_failed | Provider definitively rejected the send. An explicit retry reuses the saved result and send key. |
| delivery_unknown | Acceptance is uncertain. Stop for reconciliation rather than blindly resending. |
| interpretation_failed / blocked | Keep the frozen input and error category. Correct the problem and explicitly retry; reuse any existing valid result. |

Trusted setup uses `enroll`, `set_preferences` and `set_relationship`. These calls record supplied configuration; they do not independently verify platform identity. Ordinary group mode requires a separate destination and skips recipient-authored stickers. A shared direct assistant thread is allowed only when enrollment explicitly supplies `source_kind="direct"`, `source_verified=True`, an `assistant_id` and exactly that assistant plus recipient as members. The transport setup must establish that binding; fields in an incoming message cannot authorize direct mode. Assistant echoes remain ignored.

`get_explanation(window_id, authenticated_recipient_id)` returns only the saved output fields. `save_feedback(window_id, authenticated_recipient_id, selection, note=None)` checks ownership, choices actually shown and note size. The trusted transport/session supplies identity. Missing and other-recipient windows use the same lookup denial. No history or image is returned by these operations.

For commands arriving through Fetch, `SQLiteStore.execute_command(tool, arguments,
authenticated_recipient_id, command_id)` adds durable replay handling without
changing those two backend method signatures or the v2 records. `FetchTools`
automatically uses this method when the injected backend supplies it. The command
ID must come from the trusted transport (currently sender plus ACP message UUID),
not the model or user text.

SQLite stores a command fingerprint and response under `(recipient_id,
command_id)`. An immediate transaction serializes competing connections and
commits the feedback row and receipt together. Replaying identical arguments
returns the original receipt after an agent/database restart; changed arguments
under the same identity are rejected. Authorization is checked before returning
any stored response. An insertion failure rolls back both records. These are
local database guarantees, not exactly-once network delivery guarantees.

Calling `save_feedback` directly represents a new judgment each time. Callers
handling retries should use `execute_command` through `FetchTools`. Receipts are
created for commands first executed with this version; older feedback without a
command ID cannot be retroactively deduplicated. Conversation purge cascades to
these receipts as well as the feedback rows. FakeBackend remains in-memory.

Run the database checks with `python -S -m unittest discover -s tests -p 'test_context_store.py'`. They use only the standard library, temporary real SQLite files and denied socket creation. Coverage includes restart, frozen windows, long/old history, time ordering, deduplication, multiple recipients, direct/group routing, rollback, competing claims, explicit retries, uncertain sends, scoped feedback, legacy queued results and durable Fetch feedback receipts.

`src.repository.purge_conversation(db, platform, conversation)` explicitly deletes that conversation's history, windows, jobs, outbox, feedback and enrollment through foreign-key cascades. Account-level preferences/relationships remain separately scoped settings. Keep database files in ignored `local-data/` with operating-system account access; real-data retention and deployment account authentication require a separate operational policy.

Local retention is explicit: no automatic expiry is enabled; records remain until
the conversation is purged or the local database is removed. Purging the database
does not promise deletion from external providers, independent exports or backups.
Do not treat this local policy as production retention or account authentication.

## Verified local acceptance

All 32 database tests pass with site packages disabled; all 187 application tests
pass in the development venv. The database tests deny network sockets. They cover
restart persistence, frozen snapshots, scoped preferences/history, exact 20/25
message bounds, timestamp ties, prior uninterpreted media, paused enrollment,
separate windows for reused images, authorized feedback and pending unsent replies.
Command-receipt checks include restart, concurrent connections, rollback, invalid
choices, purge and upgrading a database that lacks the new receipt table.

Reproduce the offline combined demo after installing the application dependencies:

```sh
python -m src demo --db local-data/t4-context-demo.sqlite3 --replay
```

Observed with a fresh file: one fixed-fixture interpretation and one synthetic
provider send. Running it again in a new process with the same file produced zero
new interpretation/send calls and retained the same snapshot hash. The file is
ignored by Git. These are simulated provider/model operations and zero network
calls, not live accuracy or phone-delivery evidence. Unlike the database tests,
the combined demo imports the optional image adapter and needs Pillow; do not
disable site packages with `-S` for this command.
