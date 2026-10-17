# Error log and prevention notes

Purpose: retain actual problems, their causes, corrections, and prevention checks so later product work does not repeat them. Preserve earlier entries. Product decisions live in [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md).

Separate observed incidents from anticipated failure modes. A design revision is not automatically an error, a test scenario is not a bug already observed, and a proposed correction is not a verified runtime fix.

The existing setup/publication incidents below are retained as previously recorded. This product-spec update does not claim to have re-tested their remote outcomes.

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
