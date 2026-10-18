# Backend architecture and evidence

One backend joins authenticated Photon normalization, persistent same-chat context, one image interpretation call, validated candidate policy and private delivery. See [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md) for module roles and [CONTEXT_STORE.md](CONTEXT_STORE.md) for SQLite/job guarantees.

The default context window is 25 preceding messages, configurable from 20–25, with no age cutoff. Longer history and per-sticker/per-recipient frozen inputs are distinct from model context. Declared settings/relationships remain separate; saved feedback is evaluation-only.

The local Photon 2.0 beta runtime polls project-scoped received messages and
accepts only the configured human handle, assigned agent handle, and discovered
two-participant direct space. It stores a cursor with overlap, durable source
receipts, attachment metadata, model-call metadata, provider acknowledgments,
and reconciled delivery status. Routing is resolved from that frozen enrollment;
message text and model output cannot supply a destination. Group-source support
remains a separate dedicated-line path.

The offline demo exercises the same modules over synthetic provider I/O.
Photon did not emit a Message or Attachment for a native sticker bubble in the
tested shared thread. The live runtime therefore treats a static image sent with
the photo button as the explicit trigger only after direct-space identity
verification. [T1-verification.md](T1-verification.md) preserves that evidence.
Live OpenAI quality and a complete photo-to-phone round trip remain unverified.

Python implements the backend, including validation, routing, SQLite transactions, SDK adapters and coordination. These modules use no graph/walker features; the language migration preserves the v2 boundaries and database schema while removing Jac and LLVM runtime dependencies. See [PYTHON_MIGRATION.md](PYTHON_MIGRATION.md).
