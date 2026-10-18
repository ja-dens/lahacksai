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
- The qualifying live path is a Photon 2.0 beta shared iMessage thread, one enrolled sender, and a private explanation in that same thread. Group iMessage and iMessage calls need a dedicated line and are out of the hackathon demo. Voice, if pursued, is a separate SMS-number prize and is not attached to iMessage.
- Owner roles are planning labels until teammates' GitHub usernames are supplied.
- Existing general hackathon research stays outside this repository.

## Discoveries and unknowns

The target repository initially contained a single README and an initial commit. Git can read the repository and its push dry run permits a feature branch. The in-app browser is signed out; authenticated GitHub API access is not assumed.

The Photon sponsor guidelines state that iMessage group chat requires a dedicated line. Static-sticker media access, private-delivery behavior, the actual model budget, and deployment access still require real tests.

On October 17, 2026 the signed-in dashboard at https://app.photon.codes/dashboard was Spectrum, the stable product, for account Kalena D. A Free project named lahacksai was created with iMessage selected. Its project id is 9c35348c-9428-4dad-8a2c-b1eade874bce. The project secret is only in the gitignored local .env. Getting started reported account_phone_missing, so Spectrum cannot enroll a line until a phone is added from the account menu. This is not a Photon 2.0 beta project id (those start with pho_prj_). No application source was added.

The same account then signed in to Photon 2.0 beta. Organization Kalena's Org is `pho_org_01m55yft3jfvq9b64abja4yf5w`. Free project lahacksai is `pho_prj_01m55yjqt0esk81ms9g1w3kyxs`. A 90-day project key named lahacksai-t1 has platforms and project read/write; its secret is only in `.env`. Shared iMessage is one to one. On October 17, 2026 the owner's iMessage number was assigned a Free shared-pool line, `+16285024649`, assignment `pho_asg_01m562efr8e8g8pc3qtjvbcmre`. The sender stays in gitignored `.env`. A dedicated line, which is the documented group-chat option, requires Messaging Business at at least $250 a month and was not purchased. The enrolled sender then texted `Ping`. Photon stored it as a received direct-space message. A threaded reply was rejected with `SPACE_NOT_SENDABLE`. A normal text in that same space was delivered. Sticker media and a private explanation are still untested. Details are in docs/T1-verification.md. T1 stays open.

The October 17 hackathon brief awards the iMessage prize for a live Photon 2.0 beta channel and a separate voice prize for calls on an SMS number. Free includes shared iMessage, shared WhatsApp, and one email domain, and charges SMS and voice with no included allowance. The brief's Spectrum SDK link is not the beta client. The build follows docs/ARCHITECTURE.md: qualify on one shared iMessage thread, and add SMS voice only as a separate prize path.

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

## October 17 T5 mock integration — this chat and branch

The user designated this chat for T5, requested completion of the mock milestone on a new branch, and explicitly requested a commit/PR without merging or pushing changes to main. Created an isolated clone at lahacksai-t5 on codex/t5-mock-integration from main commit 89d0c0cbec5a0c34c6bd76e1d29a027a680633f8, preserving the older working directory and separate teammate modules. The user will notify this chat when working T2/T3/T4 versions are available.

Implemented src/main.jac as an injected coordinator with validated configuration, automatic normalized-event triggering, frozen-request checks, trusted private routing, final-result policy guards, explicit retry state and acknowledgment reconciliation. Added standard-library in-memory/fixed-output doubles, a mock-only CLI, 36 integration tests, a read-only PR workflow and docs/LIVE_INTEGRATION.md describing provisional ports and later real-component bridges. No shared v2 DTO fields, provider SDKs or teammate implementations were changed. requirements-t5.txt pins only the isolated Jac/llvmlite runtime; shared dependency consolidation remains coordinated through T0.

Observed checks: 36 integration tests passed while socket creation was denied; all coordinator Jac checks passed; all 10 existing fixture regressions and 15 planning-publisher tests passed; shared fixture verification and publisher dry run passed with no external writes. Ran compatible/opposing/unsupported and replay/retry demonstrations; a lost acknowledgment stayed reconciliation_required and did not cause another send. Workflow YAML parsed, whitespace checks passed, pip reported no broken dependencies, and generated Jac caches were verified ignored.

Measured source share: 254 Jac / 465 total nonblank/noncomment lines under src/ = 54.6%, including every Python mock/CLI file. Excludes tests, checks, scripts, docs, fixtures, dependencies and generated output. Reproduce with scripts/check_t5_source_share.py. This is harness source share, not sponsor acceptance or a claim that live backend components exist.

T5_ERROR_LOG.md is this chat's ongoing T5 incident record; the shared ERROR_LOG.md carries the same observed incidents. Only the mock-assembly checkbox is proposed complete. Full T5 remains open: real Photon verification, actual model inference/accuracy/cost, durable T4 storage, authentication, delivery reconciliation and observed phone receipt remain pending. No live calls or real personal chat processing were performed. The source PR will remain unmerged; actual branch/PR/CI results are verified after creation.

T5 source publication: committed mock implementation as 0dcc77719cb764fdf6deb34843f9bf193ebfbecf and pushed only codex/t5-mock-integration. Created [PR #14](https://github.com/ja-dens/lahacksai/pull/14), targeting main but unmerged. The branch worktree was clean after the implementation commit. GitHub's planning verifier passed; the dedicated mock job is checked separately. Main's issue-sync job is skipped on the PR, so the proposed mock checkbox has not been published to the live issue. Full T5 stays open.

Remote verification: [T5 mock integration run 39079802720](https://github.com/ja-dens/lahacksai/actions/runs/39079802720) completed successfully on Ubuntu/Python 3.13. Installation, full Jac checking, 36 integration tests, opposing/replay demo, 54.6% source share, shared fixture verifier and 10 contract regressions passed. The separate planning workflow also passed with its issue-sync job skipped. The follow-up documentation commit records this evidence and the corrected chat attachment; it changes no application source. PR #14 remains open and unmerged, with no main push or auto-merge request.

## October 17 T3 integration refresh

User authorized fixing the open PRs and commits for main integration while preserving component functions. Merged main into T3 without rewriting its history, retained current v2/defaults and both owners' log entries, and added read-only T3 application CI. No model or phone call is part of this change. Verification is pending below.

Verified refresh: 34 T3 tests, one Jac module check, 10 contract regressions, shared-fixture checker, 15 publisher tests and whitespace checks passed. Measured application source under src/ using the combined counter: 203 Jac / 374 total = 54.3%. T3 APIs, fixtures and one-call policy are unchanged.

## October 17 T5/T3 assembly checkpoint

Combined the preserved T5 mock coordinator with the refreshed T3 component and main/T0 baseline. Both existing suites (70 tests total), both Jac modules, 10 contract regressions, fixtures and whitespace checks passed. Source-share gate passed; the emitted counter is the canonical measurement. Component APIs and the existing mock-demo command are retained. Runtime bridges and durable T4 scheduling are the next focused change.

## October 17 persistent T4/T5 integration

Retained the four local Jac core modules in the isolated integration checkout and added Jac durable scheduling/outbox ports with a thin SQLiteStore adapter. Added explicit trusted direct-source enrollment, immutable snapshots, migration of local queued results, scoped lookup/feedback and conditional claims. Source/recipient routing remains outside model data; feedback stays evaluation-only. Original checkouts were not changed.

Verification: 89 application tests (including 19 real-SQLite integration cases), all eight Jac modules and whitespace checks passed. Source share is 1,012 Jac / 1,436 total nonblank/noncomment src/ lines = 70.5%, including Python mocks and adapter glue. Existing 10 contract checks and 15 publisher checks passed in the preceding component checkpoint; their source is unchanged. No live model or phone call occurred.

## October 17 T2 Photon adapter implementation

Created codex/t2-photon-adapter from current remote main in a separate checkout, preserving the original working tree and teammates' T1/T4 files. Implemented src/adapters/photon.py only at the vendor boundary: raw-event authentication and injected decoding/classification, scoped Message normalization, static PNG/size checks, history-only text/media behavior, automatic classified-sticker forwarding, safe operational errors, trusted direct-recipient resolution, stable provider idempotency, and bounded beta REST attachment/send operations. No model, database or coordinator implementation is imported.

Verified 60 T2 tests and 10 existing shared-contract tests with Python site packages disabled; socket access is forbidden by the adapter tests. Shared fixture checking passed. Synthetic input/output examples and handoff guidance are in docs/PHOTON_ADAPTER.md and docs/examples/T2_PHOTON_ADAPTER.json. Actual discoveries/corrections are maintained in docs/errors/T2_PHOTON_ADAPTER.md and ERROR_LOG.md. A dedicated read-only CI workflow checks the module independently.

T2 is a Python transport module; this branch's application source share is currently 0% Jac. The project-wide at-least-40% Jac requirement remains a core-integration measurement, not a claim made from this isolated module. Do not copy unpublished teammate/source files or add filler to meet a module ratio. T4/T3 retain Jac core ownership.

The implementation is for PR review only, with no merge/push to main. No paid plan, live credentials, model call or real phone send was used. The beta event decoder and native-sticker classifier still require T1's observed channel evidence and T5 wiring. No live integration is claimed from passing mocks.

### T2 publication checkpoint

Implementation commit 31d52069dae9ef80c769f2959ba05bcedd1c0a89 was pushed only to codex/t2-photon-adapter. [PR #13](https://github.com/ja-dens/lahacksai/pull/13) is open against main and remains unmerged. Remote photon-adapter and planning verify checks passed; the issue-publishing sync job was correctly skipped for the PR. The diff contains only the nine T2 implementation/test/CI/documentation/checklist files and no T1/T4 implementation changes. The existing issue stays open until review/merge; this branch's checked canonical T2 criteria describe the standalone deliverable, not live provider success. No main-branch push or merge was performed.

T2 isolation follow-up: the standalone test harness now loads only the transport file, bypassing any future Jac src package initializer. A subprocess regression forbids other application imports and network. All 60 T2 tests passed on Python 3.13/3.14; the transport implementation and its 356-line/0% Jac accounting are unchanged. This test/documentation correction remains on PR #13's feature branch, without a main merge.

### Reminder for the Photon API key handoff

The user requested a persistent reminder of what follows obtaining a Photon key. [PHOTON_ADAPTER.md](docs/PHOTON_ADAPTER.md#reminder-when-the-photon-api-key-is-available) now has an unchecked T1/T2/T4/T5 checklist covering beta access/configuration, actual event and sticker evidence, real verifier/decoder/classifier hooks, authorized private routing, phone receive/send and replay tests, regression updates and dated evidence/error recording. Adding the key alone does not establish a working integration. This reminder changes documentation only and stays in PR #13; it neither uses credentials nor merges the branch.

## October 17 real-component bridge checkpoint

Merged T2 history into the T5 integration branch, retaining both logs. Added Jac policy plus thin object bridges for final T3 results and T2 receipts/private destinations; saved safe interpreter metadata before inference and provider idempotency keys on actual adapter acknowledgment. Added an explicitly synthetic ingress/provider fixture over the real T2/T3/T4/T5 components. Main is not to be merged: the user explicitly confirmed keeping all changes on PR branches.

Verification: 157 application tests (including eight real-component assembly cases), all nine Jac modules and 10 contract regressions passed. Tests cover raw-byte verification, recipient binding, direct mode, compatible/opposing policy, accepted restart/replay, definitive rejection retry and uncertain-send reconciliation. Source share is recorded by the combined counter. There were no live provider calls.

## Fetch quickstart checkpoint and task reorientation

The following records the earlier standalone setup checkpoint in this clone; the updated product specification and T8 supersede its earlier integration proposal.

Fetch setup work uses the local codex/fetch-ai-setup branch. See
docs/FETCH_SETUP.md for the sponsor's mailbox route and local commands. A Python
3.13 virtual environment and ignored .env with a unique name and seed were
created. The user supplied the ASI:One key locally. Live startup published the
AgentChatProtocol manifest and registered successfully on the Almanac API.
After the user connected through the Inspector, the running SDK reported
"Successfully registered as mailbox agent in Agentverse". The user then showed
an ASI:One response from the named agent to the sun-facts question. The running
process logged HTTP 200 OK from POST https://api.asi1.ai/v1/chat/completions,
confirming a successful model API call. The quickstart's live round trip works;
Photon integration remains unverified. The standalone Python
sponsor example is outside product application-source counting; there is still
no implemented Jac sticker workflow or application Jac percentage to report.

Local Fetch verification passed on October 17, 2026: Python 3.13.14,
uagents 0.26.1, openai 3.34.0; agent.py --check; pip check; Python compilation;
mocked handler checks for acknowledgement/reply, provider failure, and empty
input; and git diff --check. Environment/runtime paths are ignored by Git. These
checks made no model requests and do not establish live registration or delivery.

Live startup evidence: agent address
agent1q2njg7mwfkt7pm83e883dpsghgee668adzc72flk5nt27ss2enfd2n8785k,
local server port 8001. The SDK also warned of insufficient funds for the separate
Almanac contract registration; no funds were sent. The mailbox connection is
verified from the runtime log; the subsequent ASI:One exchange is verified by
the user's screenshot and the successful model request in the runtime log.

The user selected ownership of both T8/#11 and T3/#4 after reviewing the revised plan. Live GitHub read-back verified BeavyHombs on both issues:

- https://github.com/ja-dens/lahacksai/issues/11
- https://github.com/ja-dens/lahacksai/issues/4

Continue on codex/fetch-tools with the reviewed origin/main planning and fixtures, while preserving codex/fetch-ai-setup. The two original uncommitted planning notes remain preserved in the Git stash named "Fetch task reorientation: preserve original issue notes". Their ownership information is reconciled here; the earlier missing-image and T3-only scope notes are superseded by the published fixtures and the two-task ownership decision.

The first learning/build step is an authorized saved-explanation lookup against the synthetic T8 backend boundary. It makes no interpretation request and does not enter the automatic Photon path. Then add feedback validation/replay handling and ACP wiring. T3 remains a separate one-call multimodal interpreter and candidate-policy task.

Reorientation checks passed: the current shared fixture checker, agent.py --check,
pip check, and staged whitespace checks. The new T8 tools and T3 interpreter have
not been implemented in this clone. The earlier 21-test/Jac results above describe
the other workspace checkpoint, not application tests rerun in this branch.

## October 17 T8 and T3 independent module implementation

The user clarified that Codex should implement clear requirements and explicitly
justify decisions, rather than requiring the user to invent the design first.
Implemented the assigned independent modules on codex/fetch-tools. These are
local working-tree changes; no commit, push, issue update, registration or paid
model request was made for this implementation.

T8: src/adapters/fetch_agent.py supplies the two narrow saved-result operations,
an in-memory synthetic backend, bounded parsing of the approved prompts, and a
thin ACP handler. The additional src/fetch_tools.jac contains scoped lookup,
feedback validation and replay policy so important product rules remain in Jac.
Missing, unknown and unauthorized windows return the same safe response. The
trusted caller supplies identity; tool arguments cannot set it. Same-command
replays return the original receipt without another write, while changed
arguments under an existing command are rejected. Public synthetic serving is
explicitly opt-in; it exposes fictional sample data rather than claiming real
app authentication. No model or Photon operation is called by these tools.

T3: src/interpreter.jac validates the frozen v2 context, orchestrates one model
request and applies the published candidate policy. src/adapters/vision.py sends
the actual decoded PNG and projected context to the replaceable OpenAI Responses
adapter with retries disabled. It excludes recipient routing, feedback and
older-history fields. Invalid inputs, corrupt media, invalid outputs, timeouts
and provider failures preserve a failed-run snapshot in memory and raise rather
than fabricate a meaning. prompts/sticker.txt keeps conversation/image content
as evidence and presentation settings separate from inferred meaning.

Rationale and tradeoffs are in docs/FETCH_AGENT_DEMO.md and docs/INTERPRETER.md.
Explicit prompt matching avoids an unnecessary local model call for deterministic
saved-result tools; arbitrary paraphrases are currently unsupported. Jac owns
policy, Python owns external SDK/format decoding. A separate optional
requirements-agent-modules.txt pins the runtime without rewriting another owner's
unpublished dependency setup; T0 must consolidate the reviewed dependency files.
Pillow enables actual PNG integrity/pixel checks before inference.

Verification in this clone: all 26 unittest cases passed (15 Fetch, 11 interpreter),
including real ACP message schemas with fake transport and real OpenAI SDK
serialization through httpx.MockTransport. Tests cover both approved tool prompts,
permission/identity failures, second-choice validation, repeated writes, published
candidate/result fixtures, one serialized request containing the exact synthetic
PNG, context exclusion, operational failures and disabled retries. Both Jac
modules passed jac check src --nowarn. Shared fixture checks, the original
agent.py --check, pip check, Python compilation and whitespace checks passed.
The offline Fetch demo returned the stored explanation and a recipient_judgment
receipt. These results do not establish semantic accuracy or live service access.

Application source estimate: 289 Jac / 500 total nonblank, noncomment source lines
under src/ = 57.8%. Count .jac and .py files, ignoring blank lines, lines beginning
with #, and one-line triple-quoted docstrings. Exclude tests, prompts, scripts,
docs, fixtures, dependencies and the standalone agent.py tutorial. This is an
estimate for the currently published module scope, not a sponsor acceptance claim
or the separate workspace's earlier whole-backend estimate.

Remaining handoffs: T4's real database/authorized operations and durable atomic
feedback-command deduplication; T5's verified account binding, model access,
persistent run storage and Photon integration; T6's held-out semantic evaluation.
The existing earlier sun tutorial's live round trip remains the only observed
live Fetch interaction. The new tools' live registration/query and the vision
smoke command are documented opt-in steps and have not been run. No issues were
closed, no teammate messages were sent, and codex/fetch-ai-setup was preserved.

## October 17 user-selected demo sticker

Replaced the generated laughing image with the user-supplied
fixtures/stickers/hamster_tongue_out.png (498 × 408 PNG), copied unchanged from
the supplied attachment. Updated chat/contract references, the incoming and
request base64 bytes and image hashes, and the saved request/snapshot hash.
Fixture documentation now distinguishes the provided image from the fictional
chat; no original authorship or regeneration claim is made for this image.
Fixed model/candidate outputs remain policy-test examples, not measured
interpretations of the replacement sticker. The prior synthetic-image checks
above describe the earlier fixture revision.

Verification: all 26 module tests, the shared contract fixture checker (including
the image-byte comparison and snapshot hash), and git diff --check passed.
No references to laughing.png remain in the active fixture/check/test guides.
Existing staged work is preserved; replacement changes are left unstaged for
the user's planned stage, commit and push.

## October 17 language-policy change

User explicitly removed the Jac requirement. Updated global Codex Git commit/PR instruction fields and local checkout AGENTS.md copies; unrelated configuration was verified unchanged. This branch removes active quota/preference wording from guidance/planning/templates and makes the existing source-share command informational. Actual Jac compilation remains necessary while .jac source is present. Main remains unmerged.

## October 17 optional Fetch and common build

Merged the Fetch branch history while retaining canonical T3 interfaces/tests, the strengthened shared checker and original exchange; the alternate image is a separate asset. Optional lookup/feedback and the sponsor quickstart remain runnable. Consolidated Python 3.13 dependencies at Pillow 13.0.0 with a full requirements.lock. Added a common offline demo/inspect/doctor entry point, preserved mock-demo, a combined application workflow and CODE_WALKTHROUGH.md. No language quota is enforced; a Python-only zero-Jac tree passes the informational source report.

Observed verification: 172 application tests, all ten Jac modules, 10 contract regressions, 15 publisher tests, dry run (zero writes), dependency checks, group/direct replay demos, optional Fetch demo and sponsor offline check passed. Local Markdown links and whitespace passed. The new lock is being installed in a fresh environment before publication. Main must remain unmerged at the user's explicit request. No live model, phone send or saved-result agent registration was performed.

Fresh-environment verification completed: the exact combined requirements.lock installed successfully into a new Python 3.13 virtual environment; all 172 tests, ten Jac modules and pip check passed there. Canonical T3 implementation/tests/prompt and shared checker/exchange bytes were explicitly compared with the pre-Fetch commit and are unchanged. The inspector removes binary data from its printed copy. Source quota removal was verified with a zero-Jac Python-only source tree.

## October 17 T1 history reconciliation

Retained the T1 branch commits/report while reconciling older README/architecture/task wording with current persisted context and direct/group routing. Later issue evidence is linked explicitly: native sticker API ingress remains blocked. This documentation change does not establish a live test.


## October 17 component language-policy refresh

Removed the Jac percentage/preference policy at the user's request; preserved component implementation and runtime dependencies. Main must remain unmerged. Component, contract and planning checks are run before this focused policy commit.

Verified policy refresh: 60 adapter tests, 10 contract regressions and 15 publisher tests passed; whitespace clean. Application source unchanged.

Verified policy refresh: 34 interpreter tests, one Jac module check, 10 contract regressions and 15 publisher tests passed; whitespace clean. Application source unchanged.

Final component heads included: T2 831aee6 and T3 69a7d21. Both quota-removal commits retain application source and their independently passing suites. The combined branch includes T1/T2/T3/T5/Fetch history and the new durable T4 implementation. Main remains unchanged and must not be merged.

Refreshed against externally updated main 5a97907, preserving its exact AGENTS.md policy removal and wording. No application source changed.
