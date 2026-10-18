# Automatic sticker interpreter

Automatically explain a supported sticker in conversational context and route the explanation privately to an enrolled recipient. The integration branch contains the Photon adapter, one-call interpreter, persistent context store, coordinator and optional saved-result Fetch tools.

**This branch is prepared for review and must remain unmerged until the user requests a merge.** Offline compilation/integration is verified separately from native Photon sticker access, live model accuracy and phone receipt, which remain unverified.

## Install and run

Use Python 3.13 and an isolated environment:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m src demo --db local-data/demo.sqlite3 --replay
```

The demo connects the real T2/T3/T4/T5 modules to synthetic provider I/O and fixed model candidates. It performs no network calls. Repeating the same database/event reuses the accepted job. For another policy case or source mode, use a separate database:

```sh
.venv/bin/python -m src demo --db local-data/direct.sqlite3 --direct --replay
.venv/bin/python -m src demo --db local-data/opposing.sqlite3 --case opposing
.venv/bin/python -m src inspect --db local-data/demo.sqlite3 --window-id 1
.venv/bin/python -m src doctor
.venv/bin/python -m src mock-demo --case compatible --replay
.venv/bin/python -m src.adapters.vision --case opposing
.venv/bin/python -m src.adapters.fetch_agent --demo
.venv/bin/python agent.py --check
```

`mock-demo` retains the original fully mocked coordinator commands. The vision command retains T3's standalone policy fixture; its opt-in live model command is documented separately. The Fetch demo performs saved-output lookup and voluntary feedback on fictional records. `agent.py --check` checks the separate sponsor quickstart without registration or a model call.

## Understand the code

Read [the walkthrough](docs/CODE_WALKTHROUGH.md) for the data flow and file roles. Core behavior remains automatic, with one image-model call, up to 25 preceding same-chat messages (20–25 configurable), no age cutoff, frozen per-recipient requests, declared preferences/relationships and evaluation-only feedback. Compatible meanings may both appear; opposing meanings yield one supported guess with uncertainty.

The user removed the Jac percentage/preference policy. There is no language quota. Existing Jac modules remain supported alongside Python, and require the pinned runtime while present.

## Verify the combined application

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/jac check src --nowarn
.venv/bin/python -m pip check
python3 -I -S scripts/check_contract_fixtures.py
python3 -S -m unittest discover -s checks -p 'test_contract_fixtures.py'
node --test .github/scripts/sync-planning.test.cjs
node .github/scripts/sync-planning.cjs --dry-run
```

CI installs the combined lock and checks every component together. Legacy component requirements files remain usable; requirements-agent-modules.txt points to the common setup. The source-share script is informational only.

## Live integration limits

The transport accepts real clients and verified callbacks, but the synthetic verifier/decoder/classifier in the demo are not production hooks. Real operation still needs native sticker bytes/events, an authenticated ingress/subscription, verified source membership and private destination resolution, configured model access, and observed phone evidence. Keys alone do not implement these hooks. Enrollment and pause/settings methods accept trusted setup; they do not independently prove platform identity.

See [Photon transport](docs/PHOTON_ADAPTER.md), [T3 interpretation](docs/T3_INTERPRETER.md), [persistent store](docs/CONTEXT_STORE.md), [integration runbook](docs/LIVE_INTEGRATION.md), [optional Fetch demo](docs/FETCH_AGENT_DEMO.md), and [product decisions](docs/PRODUCT_SPEC.md). [ERROR_LOG.md](ERROR_LOG.md) records actual failures, causes and corrections; [PLANS.md](PLANS.md) records verification. Keep secrets and databases in ignored local paths.

The [planning backlog](planning/backlog.json) and [task definitions](planning/issues/) remain canonical. PR verification performs no issue writes; main-only publication preserves human issue content. No live integration/evaluation issue is closed merely by passing offline checks.
