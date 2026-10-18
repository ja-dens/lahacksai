# Project guidance

## Purpose and scope

Build the sticker interpreter described in README.md. Read PLANS.md, docs/CONTRACTS.md, and the assigned planning issue before changing application behavior. This repository currently contains planning artifacts and planning automation; do not claim that the product is implemented.

User instructions define the authorized scope. Preserve supplied materials and unrelated changes. Record discoveries and actual verification in PLANS.md. Task completion requires evidence.

## Implementation agreements

- No language quota or preference is required. Preserve working component behavior; choose languages for clarity and compatibility. Existing Jac modules remain supported until deliberately migrated.

- Keep one backend and one multimodal model call for the initial flow.
- Use the existing internal contracts. Coordinate changes to shared contracts and dependency files.
- Keep source conversation context and recipient routing separate. The model never chooses a recipient.
- Store credentials outside tracked files and use synthetic or explicitly permitted examples.
- Photon integration targets 2.0 beta. Verify the chosen channel's actual sticker and group behavior rather than mixing stable Spectrum examples into beta code.

## Verification and Git

Run available relevant checks before committing. Check imports, logic, and unused code. Log new errors in ERROR_LOG.md with cause, correction, and prevention.

Before every commit, summarize changed files and checks. Use focused messages in the form type: description.

Before a PR, review functionality and regressions. Include Summary, Features, Implementation, Testing, and Known Issues. Distinguish planning/tooling verification from application verification. For planning-only changes, distinguish planning verification from application behavior.

Respect the current request's scope when making external changes. Use a feature branch for review and retain actual issue/PR links in the planning report.
