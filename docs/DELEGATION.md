# Parallel assignments and ownership

Use docs/PRODUCT_SPEC.md for current product choices and docs/CONTRACTS.md for interfaces. The older parent-folder STICKER_PROJECT_PLAN.md supplies the original module split; its rolling-only buffer and older dependency sequence are superseded by D08–D13 and this breakdown.

Every module task can start with the published synthetic JSON boundaries in fixtures/contracts/ and the original PNG in fixtures/stickers/laughing.png. Run `python3 scripts/check_contract_fixtures.py` first; it uses Python's standard library and no credentials. Backend application source remains separate implementation/publication work. File names below are ownership targets, not a claim those implementations already exist on GitHub.

## Independently completable tasks

| Task | Deliverable | Owned files | Substitute for unfinished components |
| --- | --- | --- | --- |
| [T0 / #1](https://github.com/ja-dens/lahacksai/issues/1) | Contract/fixture stewardship and coordinated shared changes | docs/PRODUCT_SPEC.md, docs/CONTRACTS.md, docs/CONFIGURATION.md, docs/T0_REVIEW.md, docs/DELEGATION.md, config/defaults.v2.json, .env.example, planning/, fixtures/contracts/, synthetic chat/PNG, scripts/check_contract_fixtures.py, checks/test_contract_fixtures.py | Published JSON; no provider or app runtime needed |
| [T1 / #2](https://github.com/ja-dens/lahacksai/issues/2) | Photon feasibility report, including explicit blockers | docs/PHOTON_FEASIBILITY.md, fixtures/photon_vendor/ | Vendor test client and fixed explanation; no LLM/backend |
| [T2 / #3](https://github.com/ja-dens/lahacksai/issues/3) | Photon normalization/private-send adapter with tests | src/adapters/photon.py, tests/test_photon.py, docs/PHOTON_ADAPTER.md | Fake provider, auth verifier, destination resolver and coordinator callback |
| [T3 / #4](https://github.com/ja-dens/lahacksai/issues/4) | One-call vision adapter and candidate policy | src/interpreter.jac, src/adapters/vision.py, prompts/sticker.txt, tests/test_interpreter.py | Frozen request and image plus mock SDK/HTTP transport |
| [T4 / #5](https://github.com/ja-dens/lahacksai/issues/5) | History/snapshots/profiles/private outbox and authorized lookup/feedback | src/repository.jac, src/context.jac, src/delivery.jac, tests/test_context_store.py | Temporary SQLite, fixed model result and fake transport |
| [T6 / #7](https://github.com/ja-dens/lahacksai/issues/7) | Evaluation harness, held-out cases and provenance-aware report | evaluation/, scripts/evaluate_stickers.py, tests/test_evaluation.py, docs/EVALUATION.md | Saved outputs or injected fake interpreter; fake metrics marked unmeasured |
| [T7 / #8](https://github.com/ja-dens/lahacksai/issues/8) | Reproducible fixture/setup guide and demo package | README.md, docs/SETUP.md, docs/DEMO.md, docs/REPRODUCTION.md, scripts/jac_share.py | Shared fixtures, documented module boundaries and explicit pending evidence |
| [T8 / #11](https://github.com/ja-dens/lahacksai/issues/11) | Fetch/ASI:One stored-explanation lookup and voluntary-feedback adapter | src/adapters/fetch_agent.py, tests/test_fetch_agent.py, docs/FETCH_AGENT_DEMO.md | Fake scoped backend and protocol transport; no Photon or model key |

Roles A/B/C/D are suggested skill groupings, not assignments to particular people or a required team size. Different teammates can own T1 and T2, or T3 and T6. Preserve the existing T3 assignee. Map usernames only when supplied; the publisher adds desired assignments and never removes human ones.

T0's baseline and task-based shared configuration ownership are recorded in [T0_REVIEW.md](T0_REVIEW.md) and [CONFIGURATION.md](CONFIGURATION.md). The user directed use of the existing v2 fields; no three-owner human sign-off is claimed. T1/T4 retain their independent work and may propose a versioned correction later.

Each owner supplies the test command and input/output example required by their issue. Commands referencing not-yet-created test modules are deliverable requirements, not commands already verified against the planning-only repository. Test fixed outputs honestly; they do not establish model accuracy, account access, ASI:One discovery or phone delivery.

## Final integration

[T5 / #6](https://github.com/ja-dens/lahacksai/issues/6) owns src/main.jac, src/__main__.py, tests/test_integration.py, deployment wiring and docs/LIVE_INTEGRATION.md. It joins T2/T3/T4 and is the only task whose final completion requires finished component implementations. Mock-based assembly can begin earlier. Actual Photon operations must pass T1 before a live claim; a blocked feasibility report is a completed investigation, not verified platform support.

`depends_on` in backlog.json means a prerequisite for the task's deliverable. `integration_depends_on` means a later live handoff and does **not** prevent standalone completion. Thus T2 can finish with a fake provider before T1 access is resolved; T6 can finish its harness before live model/context integration; T7 can finish its fixture guide before phone evidence; T8 can finish with a fake backend before T4 is wired.

## Coordination rules

- One owner edits each shared file at a time. T0 coordinates src/contracts.jac, dependency/configuration changes and product decisions. T5 owns assembly; other module owners do not edit the coordinator to work around defects.
- Publish small module PRs with their own tests and JSON input/output evidence. Teammates use separate clones; branches do not isolate concurrent edits in a shared directory.
- Keep at least 40% meaningful Jac application source. Core context, policy, workflow and delivery decisions belong in Jac; Python is appropriate for thin vendor adapters. Recompute share when application source is published.
- D13's example prompts are "Explain the sticker in saved demo exchange demo-3" and "Mark interpretation one as helpful for demo-3." They perform a saved-result read or scoped feedback write, with identity supplied by a trusted session. No Fetch call enters the automatic Photon flow.
- Keep planning changes in backlog.json and planning/issues/ and sync from reviewed main. Human comments, assignments, state, milestones, labels and checked work remain intact. Do not alter a teammate's Fetch branch or send messages on their behalf.
