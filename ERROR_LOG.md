# Error log and prevention notes

Purpose: retain actual problems, their causes, corrections, and prevention checks so later product work does not repeat them. Preserve earlier entries. Product decisions live in [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md).

Separate observed incidents from anticipated failure modes. A design revision is not automatically an error, a test scenario is not a bug already observed, and a proposed correction is not a verified runtime fix.

The existing setup/publication incidents below are retained as previously recorded. This product-spec update does not claim to have re-tested their remote outcomes.

## 2026-10-17: sandbox blocked live Fetch startup

What happened: startup inside the sandbox failed DNS lookup for Agentverse and
could not bind port 8001, producing SDK shutdown errors after the bind failure.

Cause: the restricted execution environment denied network and local-server access.

Correction: reran the same command with approved network/server permissions.
The server started, the ACP manifest was published, and Almanac API registration
succeeded. Mailbox creation remains a user step; no model request was verified.

Prevention: distinguish sandbox access failures from invalid credentials or
application errors before changing the sponsor example.

## 2026-10-17: Fetch quickstart environment and installer

What happened: the shell's default Python was 3.14, outside the uAgents package's
documented Python 3.10–3.13 range. uv could create an environment but its install
command stalled without progress. A pip retry's automatic approval review also
timed out before execution; the following retry began downloading packages.

Correction: use the installed Python 3.13 in the ignored .venv, bootstrap pip
with ensurepip, and install requirements-fetch.txt there. Follow the sponsor's
mailbox example rather than requiring the separate public-endpoint setup flow.

Prevention: verify the installed SDK and ACP schema before claiming runtime
success, and distinguish local checks from mailbox registration and ASI:One chat.
Node was also absent from this shell, so the existing planning publisher's Node
tests were not run; that publisher is unchanged by Fetch setup.

## 2026-10-17: GitHub access routes differed

What happened: the GitHub command-line tool was absent, and the in-app browser was signed out, even though Git could clone the private target repository and its push dry run succeeded.

Why: Git, the browser, and installed integrations use separate access paths.

Correction: use authenticated Git for the review branch and a repository-scoped GitHub Actions token for planning item publication. Verify actual results through a committed publication report. Do not treat clone access alone as proof of issue or PR access.

Prevention: check each required operation independently and record partial publication failures rather than claiming all items were created.

## 2026-10-17: integration discovery parameter mismatch

What happened: the first GitHub plugin discovery request used an unsupported plural parameter and failed validation.

Why: the callable tool's required argument was singular.

Correction: retry with the required argument; discovery then succeeded. No repository data was changed by the failed request.

Prevention: use the returned schema-validation information to correct a read-only request before continuing.

## 2026-10-17: optional YAML parser was not bundled

What happened: local YAML verification could not load the Node yaml module.

Why: the bundled Node runtime did not include that optional package.

Correction: use the system Ruby YAML parser for the owned workflow/form files and account for its YAML 1.1 handling of the on key. Keep the publisher itself dependency-free.

Prevention: check tool availability before relying on optional packages and make verification commands stop on a failed check.

## 2026-10-17: repository blocked Actions-created pull requests

What happened: issue and milestone publication succeeded, but the workflow's draft PR request returned HTTP 403: GitHub Actions is not permitted to create or approve pull requests.

Why: this repository's Actions policy does not allow that operation. Contents and issue access do not establish permission to create PRs as the Actions app.

Status and handling: eight issues, two milestones, and the review branch were published. The report includes the warning and compare link. No PR was created, main was left unchanged, and no repository setting was altered. PR creation remains available through a separately authenticated user or authorized integration.

Prevention: verify each external operation separately and keep optional PR creation failure from discarding successfully published planning items.

## DOC-001 — 2026-10-17: product decisions were not yet in the build guidance

What happened: the repository's earlier planning documents did not record the latest choices about automatic explanations for every sticker, compatible interpretation pairs, the best-guess uncertainty fallback, exchange-specific validation, and personalization in settings.

Why: those choices were made in a later product discussion after the initial planning package was prepared.

Correction: add docs/PRODUCT_SPEC.md with decision IDs, provenance, recommendations, open questions, and a change history. Link it from README.md, AGENTS.md, PLANS.md, architecture guidance, and the current contract document.

Status: corrected in local documentation. No application implementation or runtime fix is claimed; GitHub issue publication was not refreshed by this update.

Verification: check local Markdown links, whitespace, decision coverage, and preservation of the earlier error-log entries. Product acceptance tests remain to be implemented.

Prevention: record each confirmed product change in the specification before coding against it. Reconcile affected guidance and distinguish confirmed decisions from proposed fields or defaults.

## SETUP-001 — 2026-10-17: system Python metadata lookup could not validate TLS

What happened: Python 3.13 urllib could not verify the issuer certificate while reading public package metadata. Why: that interpreter's certificate configuration did not establish the needed trust chain; no broader network outage was established.

Correction: used the system curl client for the read-only metadata lookup and installed pinned dependencies through the project environment's pip with certificate verification intact. No global certificate configuration was changed and TLS verification was not disabled.

Verification: metadata retrieval and dependency installation succeeded. This is a tooling workaround, not a verified repair of the system Python certificate store or evidence of live API access.

Prevention: distinguish certificate configuration from connectivity; use a verified client or configure a trusted certificate store rather than disabling verification.

## JAC-001 — 2026-10-17: packaged Jac modules needed explicit importer registration

What happened: the first Python CLI launch could not import src.main even though src/main.jac existed. Current general documentation describes automatic import handling, but the pinned runtime needed explicit registration for this packaged entry path.

Correction: import jaclang in src/__init__.py before importing packaged Jac modules. Use the project-local jaclang 0.16.7 environment consistently.

Verification: the CLI demo and 21 backend tests then loaded and exercised the Jac core successfully. No global Jac installation was modified.

Prevention: pin and test the runtime and Python entry path together; do not assume behavior from a newer runtime's documentation.

## JAC-002 — 2026-10-17: parse success and runtime success did not imply type-check success

What happened: a preliminary smoke example used an unparenthesized tuple loop that the Jac parser rejected. After correcting it, application parsing/runtime checks passed, but full type checking found dynamic SQLite/JSON values crossing typed function boundaries and an untyped database context manager.

Correction: use the Jac tuple-loop syntax, annotate SQLite connections explicitly, validate external values, and make boundary conversions explicit where the checker cannot establish the type. Retain runtime validation for dynamic dictionary inputs.

Verification: all six Jac core modules passed jac check src --nowarn; the flag hides warnings, not errors. Backend tests also passed. This does not claim fully static schemas or semantic model accuracy.

Prevention: run both runtime tests and full Jac checking rather than treating parse-only success as completion.

## SETUP-002 — 2026-10-17: Node was absent from the shell PATH

What happened: the shell could not find node when checking the existing planning publisher. Correction: located the bundled workspace Node runtime and used its absolute path, without changing the user's global PATH or installing another Node runtime.

Verification: all 11 existing planning-publisher tests passed. Prevention: check the configured workspace runtime before adding a dependency solely to repair a missing shell command.

## GITHUB-001 — 2026-10-17: repository-root API path returned a misleading 404

What happened: an authenticated issue read succeeded, while a later repository metadata read used a trailing slash on the repository-root endpoint and returned 404.

Correction: use the canonical /repos/owner/repository endpoint without a trailing slash. The corrected request succeeded and confirmed repository access; subsequent issue updates were verified independently.

Prevention: distinguish endpoint construction from authentication or repository availability before changing access routes. Never print credentials while diagnosing access. This incident did not modify repository permissions or issue data.

## Anticipated product failure modes — not observed runtime bugs

| ID | Failure to avoid | Why it matters | Prevention / future verification |
| --- | --- | --- | --- |
| R01 | Requiring the recipient to ask an AI before each explanation. | Breaks the automatic per-sticker experience in D01. | Verify an enabled-chat sticker triggers an explanation without a new request. Reassess any integration that makes a separate AI interface mandatory. |
| R02 | Showing opposing interpretations together. | Conflicts with D02 and D03. | Test approval versus disapproval examples; show the best-supported candidate with an explicit uncertainty caveat when it can be ranked. |
| R03 | Replacing an opposing top candidate with a weaker third choice merely to show two answers. | Hides genuine ambiguity. | Evaluate the strongest candidates before compatibility; keep the uncertainty response rather than manufacture agreement. |
| R04 | Turning one feedback selection into a universal sticker meaning or a broad personality claim. | Defeats the user's choice to limit overgeneralization. | Preserve the particular exchange and its context; test the same sticker in a different situation. |
| R05 | Treating a recipient's selection as proof of sender intent. | Personalization could reinforce an incorrect interpretation. | Preserve feedback source and label recipient judgment separately from explicit sender confirmation. |
| R06 | Letting presentation preferences rewrite the inferred meaning or remove uncertainty. | Friendly wording could misrepresent an unfriendly message. | Change language/verbosity settings while checking that meaning and uncertainty remain consistent. |
| R07 | Suppressing a new sticker message because its image was seen before. | A reused image in a new message still requires an explanation under D01. | Deduplicate source events, not every occurrence of an image; separately test event retries and repeated image sends. |
| R08 | Using another conversation's history, feedback, or recipient destination without authorization. | Private context or explanations could reach the wrong person. | Test conversation and recipient isolation; resolve delivery destinations outside the model. |
| R09 | Fabricating meaning when media is unreadable or the provider fails. | Confuses unsupported inputs and operational errors with valid interpretations. | Use explicit failure handling; decide the user-facing no-defensible-interpretation fallback before claiming that behavior is complete. |
| R10 | Expanding settings beyond the selected language, explanation length, and sender relationship controls, or assuming their defaults. | Expands the product beyond D06. | Keep the selected priority order; resolve remaining defaults and setup questions in PRODUCT_SPEC.md Q01 and Q02; coordinate new shared fields through T0. |
| R11 | Bypassing the preceding-message limit by silently adding older chat or unrestricted historical summaries to a user profile. | Breaks the bounded text-context decision in D08 and obscures what evidence influenced the result. | Enforce the N-message window and keep explicit profile fields separate. D10 defers live reuse of scoped feedback. Inspect the actual model payload during evaluation. |
| R12 | Automatically inserting stored validations into first-version live requests, or using a target exchange's own feedback as evaluation input. | Conflicts with D10 and can make evaluation results misleading. | Keep live context building separate from feedback storage. Check that adding a stored validation leaves the live request unchanged; in reuse experiments, exclude target-exchange feedback from retrieved evidence. |
| R13 | Treating a 20–25-message count as a complete memory, token, media, or age limit, or assuming a database archive must all enter the prompt. | Message sizes and ages vary; storage and model context are independent policies. | Define count/content-size/media/age/retention rules separately under Q09/Q11/Q12. Check the actual target-anchored payload and do not claim storage choice alone improves accuracy or changes model-input cost. |

## Template for future observed incidents

Append one entry per actual incident and assign a stable ID. Use the user's local date.

```text
ID / date / short title:
Type: product behavior | integration | model output | data/context | tooling | documentation
What happened:
Expected behavior / relevant product decision:
Evidence or reproduction steps:
Why it happened: confirmed cause, or unknown with the current hypothesis
How it was fixed: implemented change, proposed change, or workaround
How to prevent it:
Verification performed and actual result:
Status: open | investigating | mitigated | resolved
Remaining limitation / related issue:
```

Use synthetic or redacted examples. Do not log API keys, private account identifiers, or full personal chat histories. Mark an incident resolved only after the stated correction has been verified.

## PLAN-001 — 2026-10-17: generated issues and parallel work could drift

Type: documentation / planning automation.

What happened: teammate feedback identified that editing generated issue sections without landing the canonical planning files could be overwritten by a later sync. Earlier task definitions also combined mockable module work with live integration prerequisites, making parallel assignments appear blocked. The parent planning Markdown still recommended a rolling-only buffer despite later selected longer history and immutable snapshots.

Correction: reconcile D01–D13 in the repository specification, update backlog.json and all task Markdown, distinguish hard start dependencies from later live handoffs, publish shared synthetic interfaces, and restrict issue publication to main. Preserve matching checked items and retain removed checked work as historical evidence. The optional Fetch task now has two concrete lookup/feedback operations and no role in automatic Photon processing.

Prevention: edit versioned planning sources before syncing issues; every module task needs its own mock inputs, file ownership, test command and done criteria. Do not infer live success from fixture tests or a completed blocked feasibility investigation.

Verification: 15 publisher tests passed, including preservation and handoff checks; the synthetic interface check, dry run and workflow parse passed. Remote source landing and issue read-back are verified separately in the publication report.

Status: local correction verified; remote publication is recorded after execution.

## TOOL-006 — 2026-10-17: patch context differed from the current publisher

A small dry-run-output patch expected a destructuring expression, while the file used an explicit task mapping. The patch failed without changing files. Read the exact current lines, applied the matching patch, and included the added integration-dependency output in the publisher tests. Prevention: inspect current source before constructing exact-context patches.

## T3 implementation chat — October 17, 2026

Detailed observed errors, reproductions, fixes and verification for this branch are maintained in [docs/T3_ERROR_LOG.md](docs/T3_ERROR_LOG.md). Initial verified defects in the earlier local prototype: T3-001 malformed candidate sets bypassed policy validation; T3-002 extra request fields reached the model text; T3-003 invalid media reached a mock SDK. These were reproduced with synthetic data and no network calls. Track resolution in the dedicated log; negative-test scenarios are not claims of additional observed incidents.

T3 completion verification: all 34 standalone tests, Jac checking and synthetic contract checks passed. T3-001 through T3-005 are resolved in the dedicated log. Tests verify behavior with fake SDK clients and HTTP transports; no live inference/accuracy or phone delivery is claimed.

T3-006 also corrects the legacy environment example's 8-message default to the agreed 25. Actual credentials/environment files were not edited. Shared example integration is documented for T0/T4.

T3-007 excludes generated Jac caches. T3-008 aligns null relationship provenance with the reviewed v2 boundary and requires normalized nullable fields. All 34 T3 tests and Jac checking pass. Concurrent documentation work in the original checkout was observed and left intact; the original application source, prompts and tests remain unchanged by this task.

## CONFIG-001 — 2026-10-17: published context default still used eight messages

Type: documentation/configuration drift.

What happened: live main's .env.example retained CONTEXT_MESSAGE_LIMIT=8 while PRODUCT_SPEC.md, CONTRACTS.md and shared request fixtures selected default 25 within the user's 20–25 range. A teammate copying the published template could implement the wrong window despite consistent local prototype defaults.

Cause: the earlier planning/fixture publication did not include the local configuration-template correction. Existing fixture checks did not compare the template with the agreed defaults.

Correction: set the published template to 25, record existing defaults in config/defaults.v2.json, document task-based shared-file ownership/change review, and validate template/default/request consistency. This changes no v2 DTO fields and does not claim a runtime loader exists.

Prevention and verification: the regression suite explicitly substitutes the old value 8 and verifies rejection; it also keeps credentials/model placeholders empty and runs without application packages or network. CI now checks the configuration surfaces. Local check results and actual remote publication status are recorded in PLANS.md/T0's review.

Status: correction implemented and locally verified; remote CI/source landing verified through the T0 PR.

## T5-JAC-001 — 2026-10-17: coordinator import hid compile diagnostics

Type: tooling / implementation. An initial import reported "No bytecode found". Full `jac check` identified a missing final function brace and dynamic JSON/port values that required explicit dictionary/string conversions for the pinned Jac type checker. Added the missing brace, made boundary conversions explicit and checked the complete source, rather than treating an import failure as a dependency problem.

Verification: Jac checking passed after correction, and the integration suite imported/executed the coordinator successfully. Prevention: run full Jac checks alongside runtime tests whenever changing the coordinator. This was a local implementation error, not a live-provider incident. Status: resolved.

## T5-BUILD-002 — 2026-10-17: compiler cache appeared under source

Type: tooling. Running the new Jac coordinator generated src/.jac/cache bytecode, while the base ignore file excluded Python caches but not Jac output. The cache was untracked and was not committed. Added .jac/ and .jac_cache/ ignore patterns and excluded generated output from source counting. `git check-ignore` verified the generated cache is ignored. Prevention: stage explicit source paths and inspect staged files; do not count compiler output toward Jac usage. Status: resolved; no compiler cache was committed.

## T5-GITHUB-003 — 2026-10-17: chat artifact used an assumed PR number

Type: tooling / publication. The PR creation API returned #14, but the immediately following chat-artifact call mistakenly used an assumed #15. Removed the incorrect attachment and attached the actual returned PR #14; both correction calls succeeded. No issue, branch or remote PR content was changed by the mistaken attachment.

Prevention: derive attachment URLs from the successful PR result instead of predicting the next number. Verification: the API confirms PR #14 has head codex/t5-mock-integration and commit 0dcc77719cb764fdf6deb34843f9bf193ebfbecf; the chat artifact points to that URL. Status: resolved.

## INT-001 — October 17: T3 could not merge after the T0 baseline

What happened: PR #15 conflicted with main in .env.example, ERROR_LOG.md and PLANS.md. Cause: its base predates the merged T0 default/configuration changes. Fixed by merging current main, retaining both T0/T3 records, the preferred model key and the 25-message default. Added dedicated interpreter CI so planning-only checks cannot mask an application failure. Prevention: refresh component branches and run their actual suites before integration. Verification is recorded in PLANS.md after the checks finish.

## INT-002 — October 17: component documents collided during assembly

T3/T5 both owned README, Jac importer initialization and appended evidence logs. Preserved both logs, retained one Jac-registration initializer and both component runbook links. Application modules and fixtures were retained unchanged. Prevention: assign shared assembly files to T5 and run both component suites together.

## INT-003 — October 17: Jac rejected untyped context settings at the store boundary

What happened: the new store ran its tests but `jac check` reported four E1053 errors when dictionary values were passed to typed integer context parameters. Cause: runtime dictionary lookup has an unknown static type. Fixed by validating exact integer types/positive values and then explicitly converting the validated values at the boundary. Prevention: run Jac checks as well as execution tests. Status: correction implemented; combined reverification follows.

## INT-004 — October 17: feedback exclusion assertion matched a message ID

What happened: a new regression test searched the entire serialized request for the word feedback, which was also in its own source message ID. No stored feedback had entered the request. Fixed the test to use a unique feedback-content canary and inspect the user-context keys. Prevention: make privacy assertions about actual data/fields rather than incidental identifier substrings. Status: test corrected; product behavior unchanged.

## INT-005 — October 17: local database did not implement the coordinator ports

What happened: T4's connection-oriented local functions could not replace T5's mock store. Accepted-send/claim state was absent from the prototype. Fixed by retaining the Jac history/context/repository modules, adding Jac transaction/job/outbox logic and a thin SQLiteStore object port. Existing queued results migrate without repeating inference. Conditional claims, stable identities and persisted uncertain outcomes are covered by real temporary-database tests. Prevention: exercise real component ports together, including restarts, before describing assembly as complete. Status: implemented; live provider reconciliation remains external work.

## INT-006 — October 17: direct assistant threads were rejected by group-only guards

What happened: the selected shared-direct demo was blocked when source and destination matched, and recipient submissions created no job. Fixed with an explicit trusted direct-source enrollment mode requiring exactly the configured assistant and recipient. Group restrictions, unverified same-thread rejection and echo filtering remain. Prevention: cover both direct and group routes with a real store; do not derive verification from event/model fields. Status: offline regression cases pass; actual Photon bindings remain unverified.

## T2 — 2026-10-17: Photon adapter discoveries and corrections

The dedicated [T2 chat log](docs/errors/T2_PHOTON_ADAPTER.md) records ongoing adapter work on codex/t2-photon-adapter. T2-001: the generic documentation URL resolved to Spectrum and searches mixed unrelated Photon products; use explicit beta pages and a pinned official specification. T2-002: an AsyncAPI inspection assumed components.messages and failed; inspect actual structure and keep version-specific event decoding injected. T2-003: code review found credential/scope failures could become unsupported-media results and denied routing could become retryable send failures; narrowed the abstention error set, preserved operational errors, denied unauthorized destinations, and checked REST acknowledgment scope/status.

Verification: 60 adapter tests, 10 shared-contract regression tests and the contract checker passed without credentials, installed application packages or network access. The test suite forbids socket creation and tests the auth/routing regressions. No live Photon failure, phone delivery or deployed fix is claimed. Preserve future errors and corrections in both logs; T1/T5 still verify actual beta event/sticker metadata and channel access.

T2-004 follow-up: review identified that importing through src in the standalone test harness could initialize the separate Jac app after core integration. Tests now load only the adapter file; a subprocess regression forbids other app imports and network. All 60 T2 tests pass on Python 3.13/3.14 with site packages disabled. See the dedicated T2 log for the cause, correction and prevention evidence.

## INT-007 — October 17: send-receipt expansion broke an existing minimization invariant

What happened: the combined suite caught a changed generic receipt shape while adding real Photon idempotency metadata. Fixed by preserving the original minimal status/message-ID receipt for transports that provide no explicit key; the Photon bridge's validated locally generated provider key is persisted only when present. Raw provider details remain excluded. Prevention: retain existing T5 receipt-projection tests during integration. Status: correction implemented; rerunning the full component suites.

## FETCH-GIT-001 — 2026-10-17: revised planning conflicted with quickstart documentation

Bringing origin/main into codex/fetch-tools conflicted in README.md and PLANS.md:
both branches had extended the original planning text. The original uncommitted
notes were preserved in a named Git stash before integration. Resolved the
conflicts using the current main product plan, retaining the verified Fetch
quickstart checkpoint, and updating FETCH_SETUP.md to T8's saved-result scope.

Verification: no unresolved files remained; staged whitespace checks, the shared
contract fixture checker, agent.py --check, and pip check passed. No application
backend, Photon transport, or new live agent interaction was verified by this
merge. Prevention: fetch and reconcile shared task definitions before starting
new module work; keep earlier evidence clearly labeled as historical.

## MODULE-001 — 2026-10-17: local runtime and SDK compatibility checks

The first Jac installation attempt could not resolve PyPI inside the network
sandbox. The same pinned install succeeded with approved network access; no
package-version fallback was needed. Jac 0.16.7 and llvmlite 0.50.0 match the
recorded prototype runtime; Pillow 12.0.0 supplies actual PNG verification.

Initial ACP test code called build_schema_digest without the explicit model
argument required by installed uagents 0.26.1. Corrected the test to use the real
installed method signature. Initial Jac checks also caught a missing closing
brace and dynamic-boundary type mismatches. Corrected the brace, kept runtime
validation and added explicit conversions after validation. Subsequent module
tests and both Jac module checks passed. Prevention: test actual installed SDK
schemas and run the pinned compiler before claiming module completion.

The final text/credential scan found generated binary .jir files in src/.jac/cache
and stopped on decoding them as text. Added .jac/ to .gitignore so compiler caches
stay local, then reran the changed-file scan. Prevention: exclude generated
runtime files before reviewing/staging source; do not treat a mixed shell batch's
last exit code as proof that every preceding check passed.

## INT-008 — October 17: duplicated language policy kept enforcing an unwanted quota

What happened: the 40% Jac rule existed in global Codex commit/PR instructions, each checkout's AGENTS.md, active planning text and a failing source-share script. The user explicitly requested its removal. Removed the percentage/preference instructions from both global fields while verifying all unrelated TOML values were unchanged, removed the repo policy/template wording, and made the source report informational. Existing functional Jac code remains runnable; no language rewrite was requested. Prevention: keep implementation requirements distinct from optional source metrics and avoid global language quotas. Status: global instructions updated; branch policy/checks are included in the integration change.

## INT-009 — October 17: patch tool rejected replacing a file twice in one patch

A patch attempted delete/add operations on the same CLI path. The patch tool rejected it before changes were applied. Replaced the file with one write and applied new files separately. Prevention: use one update operation per path. No application state or external data was affected.

## INT-010 — October 17: Fetch overlapped T3 and the current fixture checker

What happened: full Fetch integration conflicted with the canonical interpreter, shared image/checker and Pillow pin. Fixed by retaining T3's implementation/tests and main's strengthened checker/original exchange, keeping the hamster asset separately and unifying Pillow at 13.0.0 in the combined lock. Optional saved-result tools and sponsor quickstart are retained. Prevention: run all component suites and shared regressions in one locked environment; keep separate optional fixtures from changing canonical request hashes. Status: implementation reconciled; combined verification follows.

## INT-011 — October 17: older channel documents conflicted with current application scope

The T1 branch modified README, architecture and task wording against an older planning base. Preserved the integrated README and current context methodology, retained the original verification record with a dated link to later issue evidence, and documented native media as blocked. Prevention: distinguish historical provider evidence from the current application and do not turn text delivery into sticker support. No live check was inferred or performed.
