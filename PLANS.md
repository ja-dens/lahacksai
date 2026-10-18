# Sticker interpreter roadmap

## Current implementation language

The user corrected the inherited project context: all application code must use
Python. The former Jac requirement and source-share targets are superseded.
Earlier checkpoints below record historical work and are not current setup
instructions. Use src/interpreter.py and src/fetch_tools.py with ordinary Python
imports; no Jac compiler, importer or runtime is required.

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

## October 17 Python-only correction

The user reported that the inherited Jac requirement came from an unrelated
past project and explicitly requested no Jac application code. This supersedes
the former language split and all source-share targets recorded above.

Converted src/interpreter.jac to src/interpreter.py and src/fetch_tools.jac to
src/fetch_tools.py, preserving the published interfaces, input validation,
candidate display policy, authorization checks and feedback replay behavior.
src/__init__.py now has no importer side effects. Removed Jac/LLVM dependency
pins from requirements-agent-modules.txt, uninstalled jaclang/llvmlite from the
local venv and removed src/.jac's generated compiler artifacts. The existing
hamster image, context fixtures, transport and model adapters remain in place.

Updated active AGENTS.md guidance, README/setup/module docs, contracts/delegation,
PR templates and canonical T0/T3/T4/T5/T7 ownership/checks to use Python. Removed
source-share tooling requirements. Historical Jac references remain only in
explicitly superseded progress/error/methodology notes. No other teammate's
unpublished workspace was inspected or converted.

Observed checks passed after removing the runtime: all 26 existing module tests,
all 15 planning-publisher tests, publisher dry run with zero external writes,
the shared fixture checker, offline saved-result demo, original agent.py --check,
Python compilation and pip check. Source/import inspection confirms no existing
.jac source files or Jac/LLVM imports, and neither runtime package is installed.

The branch was clean and already pushed at the start of this correction. These
new edits are local and unstaged on codex/fetch-tools; no commit, push, PR update,
issue publication, teammate message or live service call was performed. GitHub's
existing source and issue wording still require the normal commit/push/review/
merge path before this correction becomes the shared version.
