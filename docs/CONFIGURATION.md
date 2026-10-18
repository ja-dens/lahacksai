# Shared configuration ownership and v2 defaults

[config/defaults.v2.json](../config/defaults.v2.json) records the existing engineering defaults in PRODUCT_SPEC.md and CONTRACTS.md. It is a reference for module owners, not a claim that an unpublished application automatically reads this file. Application owners must wire and test their configuration loaders. It changes no v2 message/result fields.

| Setting | v2 baseline | Meaning |
| --- | --- | --- |
| Preceding messages | Default 25; configurable 20–25 | Immediately preceding same-chat messages, plus target text/image. |
| Age cutoff | null | Preserve the selected window across long gaps. |
| Recent text | 24,000 characters total; 4,000 per message | Spend budget newest first, restore chronology, mark truncation, retain original history separately. |
| Target text | 4,000 characters | Separate from preceding-text budget. |
| Initial image | image/png; at most 5,000,000 bytes | Prototype target support; not a claim about native Photon formats. A signature check alone does not prove a complete valid image. |
| Language / length | en / short; short or detailed | Presentation defaults; not inferred sender intent. |
| Feedback | first / second / neither / not_sure | Second requires a displayed alternative; provenance is recipient_judgment. |
| Live feedback retrieval | false | Store for evaluation only; do not add feedback to model requests. |

.env.example is a credential-free template. Its CONTEXT_MESSAGE_LIMIT and EXPLANATION_LANGUAGE must match this baseline; keys/model names remain blank. Copying a template does not load it into a process. Each application owner documents the actual loader and command; do not assume a dotenv package exists. Model selection, vendor credentials, line/sender identity, deployment, production retention and identity verification are not supplied defaults.

## Ownership by task

| Shared surface | Accountable task | Other owners' action |
| --- | --- | --- |
| docs/PRODUCT_SPEC.md, docs/CONTRACTS.md, shared JSON fixtures and checker | T0 contract steward | Propose a focused PR; preserve existing v2 fields until a versioned change is agreed. |
| config/defaults.v2.json, .env.example, src/contracts.py and dependency manifests when introduced | T0 coordinates shared changes | T2/T3/T4/T5/T8 supply required settings/dependencies; avoid competing edits to the same file. |
| Photon vendor normalization/evidence | T1 evidence, T2 implementation | Provide sanitized observed fields and limitations; do not rename app fields to match unverified SDK examples. |
| Profile/history/context/outbox implementation | T4 | Consume shared defaults; own persistence and trusted enrollment. |
| Vision/prompt/policy implementation | T3 | Consume frozen requests and return the existing result shape. |
| Assembly/configuration loader/deployment | T5 | Validate configured bounds and inject provider clients; coordinate shared-file edits through T0. |

This establishes responsibility by task, not an invented GitHub username or a claim that teammates have acknowledged it. Current human assignments remain authoritative. T0's steward is handling this repository change at the user's request; it does not take ownership of the T1/T4 teammates' implementation files.

## Change procedure

1. Link the proposing task and include the current field/default, proposed change, evidence and affected consumers.
2. Keep keys private. Put any new variable name with an empty placeholder in .env.example and explain its loader.
3. Update contracts, examples/defaults, checker and affected consumer tests together. Breaking field changes require a new contract version rather than silently mutating v2.
4. Run the fixture and planning checks. Merge through a focused PR; main then syncs canonical issue text.
