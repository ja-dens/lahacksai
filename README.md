# Automatic sticker interpreter

Help older adults understand stickers in context. In an enabled conversation, the intended backend automatically interprets each incoming sticker and sends a short private explanation to the enrolled recipient. No separate per-sticker AI request or required feedback is part of the core flow.

## Current repository scope

This local T3 branch adds a standalone multimodal interpreter, Jac policy, mock-tested SDK adapter and fixture/live commands to the planning repository. Start with [the T3 guide](docs/T3_INTERPRETER.md). The rest of the application backend and Photon integration remain separate work. The branch has not been pushed or merged; fixture checks do not establish live model accuracy, Photon delivery or ASI:One availability.

Read [the product decisions](docs/PRODUCT_SPEC.md), [internal contracts](docs/CONTRACTS.md), [parallel assignments](docs/DELEGATION.md), [roadmap and observed progress](PLANS.md), and [error log](ERROR_LOG.md). Original parent-folder planning informed the module split; the current specification records subsequent user choices.

## Method

- Keep longer conversation history and immutable per-sticker/recipient snapshots. Include target image/text plus 20–25 preceding messages, default 25, without an age cutoff or later replies.
- Separate declared language/length preferences and sender relationship. Store voluntary scoped feedback for evaluation only.
- Show two strongest meanings only when compatible; otherwise show a rankable best interpretation with uncertainty or abstain when evidence is insufficient.
- Use one backend and one multimodal call in the automatic path. Application enrollment controls private recipients.
- Optional Fetch/ASI:One tools retrieve a saved explanation or record voluntary feedback, separate from automatic Photon interpretation.

## Start independently

```sh
python3 scripts/check_contract_fixtures.py
```

This Python standard-library check needs no API key, installed application modules or network. See [the serialized examples](fixtures/contracts/README.md) and [delegation guide](docs/DELEGATION.md) for mock strategies and owned files. Every module task can finish its standalone deliverable independently; final live assembly is T5.

The backend is planned to use meaningful Jac core functionality with at least 40% Jac application source. No application code is published by this planning revision, so its Jac share is not applicable.

## GitHub planning

[Open task issues](https://github.com/ja-dens/lahacksai/issues) are generated from [backlog.json](planning/backlog.json) and [task Markdown](planning/issues/). Edit those sources first. PR checks are read-only; the reviewed main branch syncs issues while preserving human content, assignments, state and checked work. [published.json](planning/published.json) records actual task links.

```sh
node --test .github/scripts/sync-planning.test.cjs
node .github/scripts/sync-planning.cjs --dry-run
```

Photon 2.0 beta line/sticker/private-send access, live model evaluation, authenticated enrollment and deployment still require verification. See T1's existing evidence and the task-specific done criteria. Keep credentials and real chat histories outside tracked files.

## Local T3 component branch

This branch adds the independently runnable multimodal interpreter. Start with [T3 setup, tests and handoff](docs/T3_INTERPRETER.md). Fixture command: `.venv/bin/python -m src.adapters.vision --case compatible`. The dedicated [T3 error log](docs/T3_ERROR_LOG.md) supplements the existing ERROR_LOG.md. These local changes are not pushed or merged and do not implement Photon delivery.
