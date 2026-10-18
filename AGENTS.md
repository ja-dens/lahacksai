# Project guidance

## Purpose and scope

Build the sticker interpreter described in README.md. Read docs/PRODUCT_SPEC.md, PLANS.md, docs/CONTRACTS.md, ERROR_LOG.md and the assigned planning issue before changing behavior. This branch contains an offline integrated backend and planning automation. Distinguish fixture verification from live model/Photon evidence.

User instructions define the authorized scope. Preserve supplied materials and unrelated changes. Record discoveries and actual verification in PLANS.md. Task completion requires evidence.

## Implementation agreements

- Keep one backend and one multimodal model call for the initial flow.
- Use the existing internal contracts. Coordinate changes to shared contracts and dependency files.
- Keep source conversation context and recipient routing separate. The model never chooses a recipient.
- Store credentials outside tracked files and use synthetic or explicitly permitted examples.
- Photon integration targets 2.0 beta. Verify the chosen channel's actual sticker and group behavior rather than mixing stable Spectrum examples into beta code.

## Verification and Git

Run available relevant checks before committing. Check imports, logic, and unused code. Log new errors in ERROR_LOG.md with cause, correction, and prevention.

Before every commit, summarize changed files, and checks. Use focused messages in the form type: description.

Before a PR, review functionality and regressions. Include Summary, Features, Testing, and Known Issues. Distinguish planning/tooling verification from application verification. For planning-only changes, report that no application source exists; do not invent a Jac percentage.

Respect the current request's scope when making external changes. Use a feature branch for review and retain actual issue/PR links in the planning report.
