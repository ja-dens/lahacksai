# Product architecture and feasibility checks

> Publication scope: planning and synthetic fixtures only. References to the local backend describe separate workspace work; its application source is not included in this revision.

Approved conversation → Photon adapter → context/enrollment checks → multimodal interpreter → validated explanation → private Photon delivery.

Read [PRODUCT_SPEC.md](PRODUCT_SPEC.md) for the current user decisions, including the interpretation-pair policy, uncertainty fallback, personalization in settings, and limits on feedback generalization. It separates confirmed behavior from proposed implementation details.

One backend owns this flow. GitHub stores source and tasks; a laptop or hosting service runs the backend. The user selected longer database history with separate context-window instances and no age cutoff. The local implementation uses SQLite and defaults to 25 preceding messages, with a configurable 20–25 cap. It stores all permitted observed messages, freezes a per-sticker/per-recipient request and hash, and keeps results/feedback/outbox records separate. New messages or profile changes do not alter a saved window. A longer archive does not expand the live model window or require semantic search.

The CLI exercises normalized event ingestion with synthetic fixtures. No public server or Photon connection is running. The local database is unencrypted development storage in ignored local-data/; real-chat authentication, permissions, deletion/retention policy, provider access, retries and deployment remain live-integration work. Explicit conversation purge cascades to snapshots, runs, feedback, and outbox; account-scoped preferences and relationships are separate records.

## Platform checks

Verify a real text exchange, actual static-sticker media, stable conversation/message identifiers, incoming direction, and private delivery to an enrolled recipient. For iMessage groups, confirm dedicated-line access with Photon. If the initial channel is blocked, investigate another Photon-supported channel and document which operation works. A replayed JSON fixture is not proof of native sticker support.

Private delivery in an assistant thread is the candidate MVP. An invisible inline annotation inside someone else's native chat interface is a separate unverified capability.

## Interpretation

Pass the actual sticker image plus the bounded preceding-message window to one multimodal model. Include recipient language/length preferences and their declared relationship to the sender once their interfaces are agreed. Store situation-specific validations separately for evaluation; do not include those historical examples in first-version live requests (PRODUCT_SPEC.md D09/D10). Explain likely use concisely. Show two plausible meanings only when they are compatible; when the strongest candidates oppose one another and a best-supported candidate can be ranked, show that interpretation with an uncertainty caveat. The no-defensible-candidate response remains an open product decision. Handle unfamiliar imagery, invalid results, and provider timeouts honestly. No special training pipeline is part of the initial plan.

## User experience

Process each supported incoming sticker in an explicitly enabled conversation automatically and send explanations only to the enrolled recipient. Provide personalization settings and pause controls in the chosen interface; no separate interpretation request or feedback response is required for each sticker. Later validation is voluntary and remains tied to the particular exchange. State that selected context and sticker media are processed by the chosen providers; private delivery does not make all processing on-device.

## Evaluation

Compare image-only and image-plus-context calls using the same model and examples. Reserve some examples until final evaluation. Measure delivery time, comprehension, and confidently wrong interpretations; record sample count and limitations.

## Optional Fetch entry point

D13 adds a separate ASI:One saved-explanation lookup and voluntary-feedback adapter. It reads a saved result or writes an exchange-specific evaluation record through an authorized backend boundary; it does not reinterpret the sticker or enter the automatic Photon path. T8 can implement and test this against a fake backend while T4 supplies real scoped operations later. See [DELEGATION.md](DELEGATION.md) for independent file ownership and final integration.
