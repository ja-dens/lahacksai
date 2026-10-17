# T5 integration error log

This chat owns T5. Continue appending here and to ERROR_LOG.md as actual incidents occur. Product decisions are recorded in docs/PRODUCT_SPEC.md. Synthetic fault-injection scenarios are tests, not observed live failures.

## Scope — October 17, 2026

Work happens on codex/t5-mock-integration in an isolated checkout. The original working directory and teammate T1/T2/T3/T4 implementations remain separate. This milestone builds mock integration only; live integration waits for the user to provide working T2/T3/T4 versions. The branch will be committed and proposed through a PR, with no merge into main.

## Incident format

Record ID/date, symptom, confirmed cause, correction, prevention, verification and remaining limits. Never log credentials, raw vendor responses or personal chats. Add equivalent concise entries to the shared ERROR_LOG.md.

## Observed incidents

See the resolved/local incidents below. Fault-injection failures are documented separately in the runbook and do not imply a real provider failure.

## T5-JAC-001 — 2026-10-17: coordinator import hid compile diagnostics

Type: tooling / implementation. An initial import reported "No bytecode found". Full `jac check` identified a missing final function brace and dynamic JSON/port values that required explicit dictionary/string conversions for the pinned Jac type checker. Added the missing brace, made boundary conversions explicit and checked the complete source, rather than treating an import failure as a dependency problem.

Verification: Jac checking passed after correction, and the integration suite imported/executed the coordinator successfully. Prevention: run full Jac checks alongside runtime tests whenever changing the coordinator. This was a local implementation error, not a live-provider incident. Status: resolved.

## T5-BUILD-002 — 2026-10-17: compiler cache appeared under source

Type: tooling. Running the new Jac coordinator generated src/.jac/cache bytecode, while the base ignore file excluded Python caches but not Jac output. The cache was untracked and was not committed. Added .jac/ and .jac_cache/ ignore patterns and excluded generated output from source counting. `git check-ignore` verified the generated cache is ignored. Prevention: stage explicit source paths and inspect staged files; do not count compiler output toward Jac usage. Status: resolved; no compiler cache was committed.
