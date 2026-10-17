# October 17 methodology and issue update

This update revises the existing T0–T7 issues rather than creating another backlog. It preserves issue state, assignees, comments, milestones, labels, notes outside managed sections, and previously checked work.

## Agreed method

- Automatically explain every incoming sticker in an enabled conversation; no per-sticker AI request or required feedback.
- Keep longer database history and separately save an immutable context window per sticker and recipient. Use the target sticker/text plus 20–25 preceding same-chat messages, default 25, with no age cutoff, subsequent replies, or unrestricted old-history retrieval.
- Separate recipient language/length preferences, sender–recipient relationships, and scoped validation records. Initial validation storage is for evaluation only; do not automatically reuse it or infer a broad personal trait.
- Show two strongest plausible meanings only when compatible. For a rankable opposing pair, show the best-supported meaning with an uncertainty caveat; do not force a weaker third interpretation. Use an honest fallback when evidence is insufficient.
- Keep one backend/one model call in the initial path and private routing outside the model. Deduplicate source events rather than image identity.

## Progress and remaining work

A local workspace prototype implements the Jac/SQLite foundation, synthetic fixture, private outbox, and replaceable API-key model adapter. Reverification for this update passed 21 backend tests, 11 publisher tests and the publisher dry run. Those results use fake interpretations/mock HTTP and do not establish live vision accuracy or phone delivery. The local application-source estimate was 77.4% Jac under src/, excluding tests/tooling/docs/dependencies.

The review branch for this issue update publishes planning definitions and methodology/interface documentation only. Application source, test code, runtime dependencies and synthetic image assets remain in the working tree and are not included in this planning-only change. T0/T7 explicitly track publication and teammate reproduction. Do not treat local file paths as a published runnable backend.

The existing T1 verification comment reports that no live ping, native sticker media or private explanation was completed. Shared-line assignment/sender identity is still missing; dedicated group-line access was not purchased. Its two completed documentation items and original comment must remain intact. T3's current assignee must remain assigned.

## Task changes

| Task | Updated focus |
| --- | --- |
| T0 | Review v2 interfaces, scoped user context, saved-window examples and source availability. |
| T1 | Unblock beta line/sender access and collect actual sticker/private-delivery evidence. |
| T2 | Authenticated normalized beta ingress, stable identities, and private outbox transport. |
| T3 | Real model access, one-call inputs, compatible/opposing candidates and explicit uncertainty. |
| T4 | Persistent history, immutable windows, scoped profiles, evaluation-only feedback, verified routing and retries. |
| T5 | Automatic phone-to-phone flow, correct frozen context, privacy and measured delivery. |
| T6 | Matched context/personalization comparisons, semantic failures, held-out labels and cost/latency. |
| T7 | Publish/reproduce the implementation and package measured live-demo evidence. |

T6 now depends on T3 and T4 because its comparisons use the model boundary and persisted context/profile behavior. Other dependencies and the two milestones are retained. Fetch work remains an optional separate experiment; this update does not cancel or modify a teammate's Fetch branch.

The source review should be merged when ready so future runs from main use the same definitions. Live issues can be updated immediately without merging this branch. No issue is closed by this update.

## Verified publication

All eight existing issues (#1–#8) were updated and read back successfully on October 17, 2026. Existing state, assignees, labels, milestones, comments and checked work were preserved. Canonical planning/interface sources are in [draft PR #10](https://github.com/ja-dens/lahacksai/pull/10). The review does not publish application source or merge into main. Details are recorded in [methodology-update.json](methodology-update.json); issue documentation references use the immutable source commit so they survive review-branch deletion.
