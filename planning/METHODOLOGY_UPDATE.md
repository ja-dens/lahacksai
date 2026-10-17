# October 17 parallel-task and methodology update

The source of truth is docs/PRODUCT_SPEC.md plus planning/backlog.json and planning/issues/. The parent-folder STICKER_PROJECT_PLAN.md contributes the original project/module structure; later confirmed D01–D13 supersede its rolling-only buffer, simplified output policy and older dependencies. This update retains existing issues T0–T7 (#1–#8) and adds one optional T8, rather than replacing the backlog.

## Method carried from the planning discussion

- Explain every incoming sticker automatically in enabled conversations, with one backend and one multimodal request per sticker/recipient. No per-sticker user query or mandatory feedback.
- Keep longer database history and freeze a separate immutable snapshot per sticker/recipient. Select target image/text plus up to 20–25 preceding same-chat messages, default 25, without an age cutoff, later replies or broad old-history retrieval.
- Load declared language/length preferences and sender–recipient relationship separately. Store voluntary exchange-specific feedback for evaluation only; do not infer a broad trait or treat recipient judgment as sender confirmation.
- Show the strongest two meanings only when compatible. For rankable opposing meanings show the best-supported one with an uncertainty caveat. Do not manufacture a weaker third choice.
- D13 adds an optional ASI:One prompt to retrieve a saved explanation or record scoped feedback. It does not enter automatic Photon processing or call the sticker interpreter again.

## Independent work and final handoff

Every task states inputs, outputs, owned files, mock strategy, standalone command, done criteria and integration handoff. Only T5's final live completion requires finished components. Other tasks can complete their local deliverables with the published synthetic examples and substitutes.

| Task | Independent deliverable | Later live handoff |
| --- | --- | --- |
| T0 | Versioned contract/fixture stewardship | Provider corrections coordinated after evidence |
| T1 | Photon operation report, even if blocked | Required operations must pass before T5 claims support |
| T2 | Mock-tested receive/private-send adapter | Replace provisional provider fields after T1 |
| T3 | One-call adapter and candidate policy with mock SDK | T5 live inference, T6 semantic evaluation |
| T4 | Persistent snapshots/profiles/outbox and authorized lookup/feedback | T5 real transport/identity, T8 real backend |
| T5 | Assembly may start with mocks; final completion requires T2/T3/T4 and live access | Actual automatic phone explanation evidence |
| T6 | Held-out cases, rubric and fixture-capable evaluation harness | Live comparisons after T3/T4 |
| T7 | Reproducible fixture/setup and demo package with explicit pending evidence | Add T5/T6 observed results later |
| T8 | Optional Fetch stored-result/feedback adapter with fake backend | Actual ASI:One discovery/query and T4 binding verified separately |

backlog.json separates hard `depends_on` prerequisites from nonblocking `integration_depends_on` handoffs. The publisher renders both, validates their combined graph and preserves human content/checked work. The workflow tests PRs without writing issues and publishes only from main, reducing the risk of an old feature branch reverting the live backlog.

## Verification boundaries

This revision publishes planning/methodology documentation, publisher tooling and synthetic contract/image fixtures. It does not publish the local application backend, runtime dependencies or application test suite. A local workspace previously passed 21 backend tests and six Jac module checks with a 77.4% Jac source estimate; those are not fresh-clone availability, live vision accuracy, ASI:One discovery or Photon delivery evidence.

The original T1 verification comment and its checked documentation items are preserved; it did not establish live ping, sticker or private-send success. T3's assignee remains assigned. Existing issue states, milestones, comments, assignments and unrelated labels are retained. No paid plan, private chat processing, teammate message or unrelated Fetch-branch change is part of this update.

Actual issue links are recorded in published.json after sync. PR #10 carries the source changes; its observed status and source commit are recorded separately in methodology-update.json. Do not infer a merge or completed product from this document alone.
