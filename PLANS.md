# Sticker interpreter roadmap

## Outcome and scope

An enrolled recipient receives a short private explanation of a supported sticker, based on recent messages from an approved conversation. An existing multimodal model performs interpretation. One channel, static images, one language, and bounded conversation context form the first scope. The user selected longer database history, separate saved context windows, and no age cutoff. The local prototype uses SQLite and defaults to 25 preceding messages within the selected 20–25 range; production retention remains open.

Working phone delivery, useful interpretation, correct recipient routing, and honest uncertainty are the success criteria. Model training, a sticker dictionary, a new chat client, multiple channels, voice, and inline private annotations are later possibilities.

## Progress

- [x] Prepare product scope, interfaces, ownership, templates, and the original eight issue bodies locally; the later parallel-task refinement adds optional T8.
- [x] Add an automated planning publisher and local verification commands.
- [x] Publish codex/sticker-planning and verify planning/published.json: eight issues and two milestones exist.
- [x] Record the current user-confirmed behavior, settings preference, scoped validation, and open questions in docs/PRODUCT_SPEC.md; link the error log for future product work.
- [x] Implement the local history/profile/snapshot/policy/outbox foundation, a synthetic PNG demo, and a replaceable API-key vision adapter.
- [x] Verify the local demo, 21 backend tests, six Jac core modules, and the existing 11 planning-publisher tests. These do not establish live model accuracy or Photon delivery.
- [ ] Confirm the shared contract with the implementation team (T0).
- [ ] Verify Photon group/sticker/private-delivery access (T1).
- [ ] Implement independent modules (T2, T3, T4).
- [ ] Demonstrate one complete live exchange (T5).
- [ ] Evaluate context benefit and uncertainty (T6).
- [ ] Package a reproducible demo (T7).

Checked items distinguish planning and explicitly labeled local prototype checks. Update publication status only after observing the remote result.

## Milestones and dependencies

1. **Sticker MVP: independent modules** — T0/T1/T2/T3/T4 can start immediately against published contracts and fixtures; no prerequisite meeting or live account is needed for mocked module development.
2. **Sticker MVP: working phone demo** — T5 joins T2/T3/T4 for live completion. T6/T7 and optional Fetch T8 can complete their standalone harness/documentation/adapter deliverables with mocks; later integration requirements are tracked separately.

The canonical task details live in planning/issues/. Metadata, dependencies, owner roles, and optional username assignments live in planning/backlog.json.

Aim for the first complete path within roughly hours 4–6 of the 24-hour reference build. Reserve the last several hours for fixes, reproducibility, and rehearsal. Adjust estimates to the team's actual access and skills.

## Decisions

- Read [the current product specification](docs/PRODUCT_SPEC.md) for automatic per-sticker behavior, compatible interpretation pairs, the single-best-guess uncertainty fallback, exchange-specific feedback, and personalization settings. Suggestions and open questions are labeled there.
- Selected settings, in priority order: preferred language, explanation length, then sender relationship. Text context is a bounded number of messages preceding the target message and sticker; the user's preferred range is around 20–25, with an exact cap still open (PRODUCT_SPEC.md D08/Q09).
- Agreed user-context design: separate recipient preferences, sender–recipient relationships, and situation-specific validation records (D09). First-version live requests load preferences and relationships; stored validations are for evaluation only (D10).
- Store longer conversation history and immutable per-sticker/per-recipient snapshots (D11), without an age cutoff on selected context (D12). Local implementation uses SQLite, a default 25-message window, and v2 contracts. Teammates still need to review the boundary before live integration; no team sign-off is claimed.
- Interpretation starts with one multimodal call containing the actual sticker image and selected text.
- The backend chooses recipients from enrollment settings.
- Each owner develops against the shared format and substitutes unfinished dependencies.
- No live data, API key, model endpoint, or phone line is assumed provisioned.
- Owner roles are planning labels until teammates' GitHub usernames are supplied.
- Existing general hackathon research stays outside this repository.

## Discoveries and unknowns

The target repository initially contained a single README and an initial commit. Git can read the repository and its push dry run permits a feature branch. The in-app browser is signed out; authenticated GitHub API access is not assumed.

The Photon sponsor guidelines state that iMessage group chat requires a dedicated line. Static-sticker media access, private-delivery behavior, the actual model budget, and deployment access still require real tests.

GitHub Actions uses a short-lived repository token for issue publishing. Repository settings can prevent draft PR creation. If so, preserve the branch and issues and record the limitation; do not change settings automatically.

Observed publication result: the workflow created issues #1–#8 and milestones #1–#2. The draft PR request returned HTTP 403 because GitHub Actions is not permitted to create or approve pull requests in this repository. The review branch and issues are published; no PR was created and main remains unchanged. Review the changes at https://github.com/ja-dens/lahacksai/compare/main...codex%2Fsticker-planning. A signed-in user or another authorized GitHub integration can create the PR without changing this repository setting.

## Verification and outcomes

Planning automation must pass its automated checks and dry run before publication. planning/published.json records remote issue/milestone/PR results after a successful workflow run. It is evidence of planning publication, not product functionality.

Application verification must include ambiguous media, identical images in different contexts, duplicate events, paused conversations, and isolation between conversations.

October 17 product-spec update: documentation was checked for local links, whitespace, and consistency with the recorded decisions. This did not install dependencies, change application behavior, revise the shared data schema, or republish GitHub issues. Profile/settings/feedback fields still require T0 coordination; no application tests or accuracy results are claimed.

October 17 user-context agreement: recorded D09/D10, resolved the initial feedback-reuse choice, and reconciled architecture/interface guidance. Checked the updated Markdown links and whitespace. The three-record structure is a conceptual agreement; no database, application implementation, or live model evaluation is claimed. Message retention remains an open proposal.

October 17 context-storage discussion: recorded the preferred 20–25-message range and separated model-input selection from retention. Reviewed official PostgreSQL ordering/limit documentation and Python bounded-deque documentation; these establish implementation possibilities, not product benchmarks or a selected database. Updated the storage recommendation to limited persistent recent history, leaving retention, content budgets, media handling, and context age open. Checked local documentation links and whitespace; no application tests, dependency changes, or live integrations were performed.

## October 17 initial backend build

The user selected longer database history with separate context instances, maintained context across time, and asked to move into creation. Built the Jac core with SQLite history, immutable input snapshots and hashes, user-context records, evaluation-only feedback, source-event deduplication, interpretation-pair policy, and enrollment-controlled local outbox routing. Added a Python CLI and a replaceable OpenAI Responses API-key adapter; the default demo uses a clearly labeled fixed result.

Environment: Python 3.13.15, project-local jaclang 0.16.7, llvmlite 0.50.0, and openai 3.34.0. requirements.lock records all resolved dependencies. The pinned PyPI Jac runtime differs from the newer native-binary documentation; use the recorded setup and tested import registration rather than silently changing runtimes.

Observed checks: 21 backend tests passed, including actual SDK serialization through a mock HTTP transport; all six Jac modules passed `jac check src --nowarn`; the fixture demo queued a private explanation with delivered=false, its saved input was inspected, and repeating the same events returned duplicate. All 11 existing planning-publisher tests and its dry run passed using the bundled Node runtime; the dry run reported zero external writes. The synthetic PNG was opened and visually inspected. Repository text whitespace/local Markdown links passed, git diff --check was clean, and pip check reported no broken requirements.

Jac usage at this checkpoint: 452 Jac / 584 total nonblank, noncomment application source lines under src/ = 77.4%. Excluded tests, scripts, fixtures, prompts, docs, dependency files and installed packages. Reproduce with scripts/jac_share.py; this is a source-share estimate, not a claim about sponsor judging acceptance.

Runtime doctor observed no API key, no model setting, and no Photon key in this process. No paid model request, phone message, live Photon test, commit, push, or issue republishing was performed. ChatGPT account access can support manual checks; eligible plan usage through Sign in with ChatGPT requires its own authorized integration and is not implemented by the current API-key adapter. Sources: [OpenAI SDK](https://developers.openai.com/api/reference/python), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Sign in with ChatGPT](https://learn.chatgpt.com/docs/sign-in-with-chatgpt), and [plan-usage limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations).

Remaining live blockers: verify Photon 2.0 beta media/private-delivery access, provision an authorized model route and evaluate accuracy/latency/cost, then add authenticated ingress, verified membership, transport, explicit retries and deployment. The local prototype uses dynamic dictionary boundaries with runtime validation; passing Jac checks is not a proof of semantic correctness. Unsupported/insufficient-evidence fallback wording is an initial English default. Production data retention/access controls remain to be implemented before real personal chats are used.

## October 17 issue-methodology publication

Updated the existing GitHub tasks T0–T7 (#1–#8) in place with the confirmed methodology, local prototype progress, honest live blockers, revised actionables and acceptance evidence. T6 now depends on both T3 and T4. Read-back verification preserved issue state, assignees (including BeavyHombs on T3), labels, milestones, comments, and previously checked work. The T1 verification comment and its two completed documentation items remain intact; no phone/sticker/private-send success was inferred from that comment.

Published canonical planning definitions and methodology/interface documentation on codex/sticker-methodology-update, based on the current remote main, in [draft PR #10](https://github.com/ja-dens/lahacksai/pull/10). This review publishes no application, test, dependency, or private-data source and is unmerged. The backend remains in the working tree; T0/T7 explicitly track its publication and teammate reproduction. The original local checkout and unrelated working changes were preserved. Immutable issue-document references point to source commit 285a956c327b27079472343ab548e26e9e962a90. The separate planning/methodology-update.json report records verified issue URLs and preserves the original planning/published.json publication history.

Reverification: 11 publisher tests, publisher dry run, and 21 local backend tests passed. Review-tree links/whitespace and preservation of existing checked items passed before publication. Authenticated Git credential-helper access was verified separately for issue reads and updates; no GitHub plugin installation, repository permission change, merge, teammate message or live model/Photon call was performed.

## October 17 independent-task refinement

Pulled the original module boundaries from the parent STICKER_PROJECT_PLAN.md and reconciled them with current PRODUCT_SPEC.md decisions. D13 now records explicit approval of an optional ASI:One saved-explanation lookup and voluntary-feedback demo. The automatic Photon path stays one multimodal request and requires no per-sticker user action.

Rewrote T0–T7 around independent inputs/outputs, owned files, mock strategies, proposed standalone commands and assessable done criteria; added optional T8. Only T5 has hard component prerequisites. Later live handoffs use integration_depends_on and do not block standalone completion. Published synthetic serialized boundaries and an original PNG can be checked using Python standard library without unpublished backend imports. No live accuracy, registration or delivery is implied.

The planning publisher now preserves removed checked items as historical work and distinguishes start dependencies from later integration. PR checks remain read-only; source publication to main is required before canonical issue sync. External publication status will be recorded after verification.

## October 17 T3 implementation in an isolated local branch

This chat now owns T3 implementation on codex/t3-multimodal-interpreter in the lahacksai-t3 checkout, based on main bb236d875dc080270a7e94dcaa3033511a5f07e5. The original checkout's application and teammate work is preserved. New files implement the standalone Jac evidence/policy component, thin Python OpenAI/fixture adapter and CLI, prompt, scoped dependency lock and 34 independent tests. Detailed handoff: docs/T3_INTERPRETER.md. Dedicated errors: docs/T3_ERROR_LOG.md, with summaries retained in ERROR_LOG.md.

Verified locally: 32 T3 tests passed without live requests; the actual SDK serialized one model request through MockTransport and simulated HTTP/timeouts were not retried. Jac checking passed, the existing synthetic contract check passed and pip check found no broken requirements. Application source share: 204 Jac / 381 total nonblank/noncomment lines under src/ = 53.5%, excluding tests/tooling/prompts/fixtures/docs/dependencies. Configuration is isolated in requirements-t3.txt/requirements-t3.lock; no other teammate's implementation was copied into this branch.

All T3 task checkboxes are checked locally with requirement evidence. The GitHub issue stays open and no remote issue changes, push, PR or merge is performed. Live API access and interpretation accuracy remain unverified; the opt-in smoke command reports unavailable configuration honestly. T1/T4 integration, snapshot persistence, phone delivery and deployment remain their own tasks.

Final T3 handoff review added valid-null relationship provenance and required normalized nullable-field tests; the suite now passes 34 tests. Final source share is 204 Jac / 381 application source lines = 53.5%. All 15 planning-publisher regressions and its no-write dry run also passed. Generated Jac caches are ignored. Concurrent T0 documentation refinements in the original checkout were inspected for compatibility and preserved; no original application source was modified.

## October 17 T0 technical baseline

The user requested completion of T0 and reported no teammate field changes, directing use of the existing v2 contract. Reviewed live main and issue #1, preserving the separate T1/T4 work, all assignments/comments and the unpublished local application prototype. Work is isolated on codex/t0-contract-baseline rather than overwriting the earlier working directory.

Found and corrected .env.example's stale CONTEXT_MESSAGE_LIMIT=8 to the agreed engineering default 25. Added config/defaults.v2.json and CONFIGURATION.md for existing limits, task-based shared-file ownership, loader caveats and versioned corrections. CONTRACTS.md now makes the existing field types and trusted delivery-destination resolver explicit without adding/removing/renaming v2 fields. T0_REVIEW.md walks through all five record boundaries, traces D01–D13, records A/B/C technical review perspectives and keeps human acknowledgments pending.

The standard-library verifier now checks normalized field shapes, timestamp timezones, source window/content, text bounds, exact user context without feedback, image/request hashes, output cases, private routing, scoped feedback and default/template consistency. Ten regression tests include empty process configuration with socket creation denied, malformed fields, the old eight-message default, old-context acceptance, future messages, altered snapshots/images, opposing alternatives and wrong recipients. The existing 15 planning-publisher tests remain relevant. CI triggers include configuration/contract changes and run both verification suites.

T0's technical standalone criteria are complete; the original all-three-owner review and owner-correction feedback remain unchecked and issue #1 must stay open until those acknowledgments exist. No messages were sent to teammates, no field changes were invented, and no application/backend, model/Photon call or real private chat was used. Actual remote source publication and CI/issue synchronization are verified after the focused PR is created and merged.

## October 17 T3 integration refresh

User authorized fixing the open PRs and commits for main integration while preserving component functions. Merged main into T3 without rewriting its history, retained current v2/defaults and both owners' log entries, and added read-only T3 application CI. No model or phone call is part of this change. Verification is pending below.

Verified refresh: 34 T3 tests, one Jac module check, 10 contract regressions, shared-fixture checker, 15 publisher tests and whitespace checks passed. Measured application source under src/ using the combined counter: 203 Jac / 374 total = 54.3%. T3 APIs, fixtures and one-call policy are unchanged.
