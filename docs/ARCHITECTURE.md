# Backend architecture and evidence

One backend joins authenticated Photon normalization, persistent same-chat context, one image interpretation call, validated candidate policy and private delivery. See [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md) for module roles and [CONTEXT_STORE.md](CONTEXT_STORE.md) for SQLite/job guarantees.

The default context window is 25 preceding messages, configurable from 20–25, with no age cutoff. Longer history and per-sticker/per-recipient frozen inputs are distinct from model context. Declared settings/relationships remain separate; saved feedback is evaluation-only.

The T1 branch proposed a shared iMessage direct-thread demonstration. The integrated routing supports an explicitly verified two-participant direct source and preserves separate private destinations for group sources. A direct assistant thread exposes only its own context, not an unrelated family chat. Real source/destination verification must be provided externally.

The offline demo exercises the real modules over synthetic provider I/O. The source verifier/decoder/classifier used there must not be deployed as Photon authentication. [T1-verification.md](T1-verification.md) preserves earlier evidence and links the newer native-sticker blocker. Live model quality and phone receipt remain unverified. No paid line, channel change or live send was performed by this integration.

Python implements the backend, including validation, routing, SQLite transactions, SDK adapters and coordination. These modules use no graph/walker features; the language migration preserves the v2 boundaries and database schema while removing Jac and LLVM runtime dependencies. See [PYTHON_MIGRATION.md](PYTHON_MIGRATION.md).
