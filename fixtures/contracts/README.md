# Shared synthetic boundaries

Run `python3 scripts/check_contract_fixtures.py` from the repository root. This uses Python's standard library only; no vendor packages, model key, Photon line, running application or network is needed.

All identities and conversation text are synthetic. The user-provided demo PNG is in ../stickers/hamster_tongue_out.png. Its authorship is not asserted here; the synthetic label applies to the fictional exchange, not the image. Base64 image data is included in the JSON boundary so a module owner can exercise the real request shape. Fixed candidate/result files are interface examples, not measured model predictions or proof of sender intent.

| Files | Consumer and purpose |
| --- | --- |
| incoming_message.json | Photon adapter output / context-store input. |
| interpretation_request.json | Context-store output / interpreter input, with actual image data and separate user context. |
| candidate_*.json | Mock model responses for single, compatible, opposing and unsupported cases. |
| interpretation_result.json, result_*.json | Expected policy outputs for those synthetic responses. |
| saved_exchange.json | Immutable synthetic window plus fixed result for lookup; delivery remains pending/false. |
| private_delivery.json | Application-selected recipient and formatted explanation; a send request is not a delivery receipt. |
| feedback.json | Voluntary recipient judgment tied to window 1; excluded from live model requests. |
| fetch_requests.json | Approved ASI:One prompts and trusted **test-only** identity for a fake backend. |

See ../../docs/CONTRACTS.md for field semantics and ../../docs/DELEGATION.md for file ownership. Real integrations must obtain caller identity from a verified transport/session, not a model-provided recipient ID. The main backend and vendor adapters are separate implementation work; passing this check does not establish their availability or correctness.
