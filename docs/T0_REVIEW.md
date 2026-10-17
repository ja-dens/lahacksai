# T0 baseline review and handoff

Date: October 17, 2026. The user reported no requested field changes and directed use of the current v2 contract. No IncomingMessage, InterpretationRequest, InterpretationResult or DeliveryRequest field was added, removed or renamed by this review. This is a technical review of each module boundary, not a claim that the three human owners signed off.

## Reproduce from this repository

```sh
python3 -I -S scripts/check_contract_fixtures.py
python3 -S -m unittest discover -s checks -p 'test_contract_fixtures.py' -v
node --test .github/scripts/sync-planning.test.cjs
node .github/scripts/sync-planning.cjs --dry-run
```

The Python commands use the standard library with site packages disabled. They require no application imports, Photon/model accounts, credentials or network calls. The negative tests deny socket creation and clear process configuration for the baseline check. Synthetic outputs are fixed fixtures, not measured model predictions.

## Complete exchange to inspect

1. [IncomingMessage](../fixtures/contracts/incoming_message.json): normalized sticker event demo-3 and its actual synthetic PNG bytes.
2. [InterpretationRequest](../fixtures/contracts/interpretation_request.json): target image/text, two available preceding messages, default cap 25, no age cutoff, and separately declared preferences/relationship.
3. [InterpretationResult](../fixtures/contracts/interpretation_result.json): fixed likely meaning, context cue and uncertainty; no routing fields.
4. [DeliveryRequest](../fixtures/contracts/private_delivery.json): application-selected recipient/source and formatted text. The trusted enrollment resolver supplies the private destination separately.
5. [Saved window](../fixtures/contracts/saved_exchange.json): matching request/hash/result; status pending and delivered=false. This is an example, not a running database.
6. [Feedback](../fixtures/contracts/feedback.json): voluntary first-choice recipient judgment, scoped to that window. The [Fetch requests](../fixtures/contracts/fetch_requests.json) use the same synthetic identity/window, outside automatic inference.

Alternative fixtures cover compatible, opposing and unsupported model/policy outputs. A compatible pair retains both meanings; a rankable opposing pair retains one with a caveat. The checker verifies the examples, not the model's ability to rank or classify them correctly.

## Technical review by boundary

| Owner perspective | Reviewed handoff | Finding and disposition |
| --- | --- | --- |
| A — messaging, T1/T2 | Native event → IncomingMessage; DeliveryRequest → private transport | No native Photon sticker payload is verified. Keep application fields; T1 supplies sanitized observed mappings later. Documented a trusted destination resolver because private destination is intentionally absent from DeliveryRequest. |
| B — interpretation, T3 | Frozen request/image → candidate response → InterpretationResult | Complete image/hash and labeled context/settings are present. Output has no destination/recipient. Added missing/extra-field and compatible/opposing examples to the executable review; no second model request is introduced. |
| C — context/routing, T4/T5 | Authorized history/settings → snapshot → private outbox; feedback → evaluation only | Count, chronology, truncation budgets, source IDs and hashes are checked. Added wrong-recipient, source-chat, future-message, snapshot and feedback checks. Persisted immutability and real authorization remain implementation requirements. |

## Current decisions traced to evidence

| Decisions | Contract/fixture evidence |
| --- | --- |
| D01 automatic per-sticker | Incoming demo-3 identifies a sticker; T2/T4/T5 trigger behavior remains their implementation, not proved by fixture validation. |
| D02/D03 compatible pair / opposing single+caveat | candidate_compatible/result_compatible and candidate_opposing/result_opposing; regression rejects an opposing alternative. |
| D04/D05 voluntary scoped validation | Feedback references one saved window and recipient_judgment; second choice must have been shown. |
| D06 declared personalization | Separate language/length preferences and sender relationship; priority is not an intent-weighting rule. |
| D07 maintained records | PRODUCT_SPEC.md, PLANS.md and ERROR_LOG.md; canonical task Markdown is synced from main. |
| D08 bounded preceding context | Default 25 within 20–25; source window, size bounds and future-message rejection checked. |
| D09/D10 separate records / evaluation-only feedback | Exact user-context shape excludes validation retrieval; feedback remains outside the saved model request. |
| D11/D12 history/snapshots / no age cutoff | Separate saved-window fixture and hash; a regression accepts old preceding text. Runtime persistence/immutability belongs to T4. |
| D13 optional Fetch tools | Saved-result read or scoped feedback write only; synthetic Fetch fixtures do not alter the automatic path. |

## Shared-file ownership

T0 is the contract/configuration steward for the baseline in this PR. [CONFIGURATION.md](CONFIGURATION.md) names accountable tasks and the change procedure. T1 and T4 retain their implementation ownership. GitHub usernames are not guessed, assignments are not moved, and no teammate is messaged by this review.

## Human review and later corrections

| Acknowledgment | Current evidence |
| --- | --- |
| Project owner baseline choice | Confirmed in this chat: no changes reported; use current v2. |
| A — messaging owner | No acknowledgment recorded. Existing T1 evidence is a platform-access report, not contract approval. |
| B — interpreter owner | No acknowledgment recorded; an issue assignment is not approval. |
| C — context owner | No acknowledgment recorded. T4 implementation is in progress according to the user. |

The focused PR provides the concrete review surface. No owner field corrections have been supplied; future corrections use CONFIGURATION.md's change procedure and stay versioned. Do not check the original three-owner review/feedback items or close T0 until that human evidence exists. The technical standalone deliverable is usable now and does not block T1/T4 or any mocked module work.

## T1 provider status

The [existing T1 report](https://github.com/ja-dens/lahacksai/issues/2#issuecomment-6242039867) did not obtain a verified sender/line, sticker event or private send. No new verified provider payload or correction is available for this review. No vendor fields, supported sticker formats, group operations or delivery guarantees were invented. T1 can supply a later sanitized normalization example without changing current app fields; a genuinely breaking change needs a new version.
