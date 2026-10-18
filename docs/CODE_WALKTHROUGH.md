# How the sticker interpreter works

The backend turns an incoming sticker into a private explanation. The model interprets meaning; application code chooses context and recipients.

```mermaid
flowchart LR
    A[Photon event] --> B[Authenticate and normalize]
    B --> C[Freeze context in SQLite]
    C --> D[One image model call]
    D --> E[Validate interpretation]
    E --> F[Save result and outbox]
    F --> G[Private delivery]
    F --> H[Optional lookup and feedback]
```

1. **Receive:** `src/adapters/photon.py` authenticates raw events through a supplied verifier, normalizes native fields, retrieves classified sticker media and sends text to verified private destinations. Real event decoding and native sticker classification depend on the Photon setup.
2. **Coordinate:** `src/main.py` controls the workflow. Text updates history. A sticker creates one job per enrolled recipient. Assistant echoes and paused/unapproved conversations do not trigger interpretation.
3. **Freeze context:** `src/repository.py`, `context.py` and `store.py` keep SQLite history and immutable requests. Each contains the target image/text, up to 25 preceding same-chat messages, character limits and declared preferences/relationship. There is no age cutoff. Later replies and saved feedback are excluded.
4. **Interpret once:** `src/adapters/vision.py` sends the actual image and permitted text to the model. `src/interpreter.py` validates candidate output and applies policy: compatible meanings can both appear; opposing meanings produce one best guess with uncertainty; insufficient evidence produces an unsupported result. The assembly adapter composes this policy exactly once.
5. **Save before sending:** results and outbox entries are persisted before delivery. Job states record pending, interpreting, interpreted, sending and accepted work. Replays reuse existing jobs. Interrupted claims or unclear acknowledgments require reconciliation, since an automatic retry could duplicate a charge or message.
6. **Route outside the model:** enrollment determines recipients and private destinations. Groups require separate private threads. A verified direct source can reply in the same thread, with exactly the configured assistant and recipient. Message/model fields cannot grant this permission.
7. **Offer optional feedback:** `src/fetch_tools.py` and `src/adapters/fetch_agent.py` retrieve saved explanations or record exchange-specific choices without reinterpreting the image. The public demo uses fictional records and process-local command deduplication. SQLiteStore supplies scoped persistent result/feedback operations for an injected trusted backend.

`src/context_store.py` is a thin object adapter over Python database functions. `src/adapters/assembly.py` joins the different component APIs and translates send receipts. `src/demo.py` connects the real components to synthetic provider I/O and fixed model candidates. `python -m src demo` exercises real normalization, policy and durable storage without network calls. `python -m src mock-demo` preserves the earlier fully mocked harness.

## Why Python is used now

The original 40% Jac policy caused ordinary workflow, validation, routing and storage code to be written in Jac. The user removed that policy and requested a language review. All ten former Jac modules used conventional functions, dictionaries and Python libraries; none used nodes, edges, walkers or another Jac-specific facility. Photon and the model API do not require Jac.

The backend now uses Python throughout. This keeps the existing SDKs, SQLite library, CLI and core functions in one runtime, allows normal imports and debugging, and removes the Jac/LLVM installation and compilation layer. Module names, v2 JSON fields, interpretation policy, SQLite schema and persisted job states are preserved. No database conversion is needed. The mock coordinator and SQLite store run without installed packages; the image decoder and optional SDKs keep their existing dependencies.

[PYTHON_MIGRATION.md](PYTHON_MIGRATION.md) records the review, regression checks and a local startup comparison. Historical error logs retain the earlier Jac checkpoints.

The offline checks establish compatibility, validation, routing and persistence with synthetic data. Fixed model candidates do not measure accuracy, and provider acceptance does not establish phone receipt. Live native sticker ingestion, real identity/destination verification and the complete phone demonstration remain separate evidence to collect.
