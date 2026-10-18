# Automatic sticker interpreter

Automatically explain a supported sticker in conversational context and route the explanation privately to an enrolled recipient. The integration branch contains the Photon adapter, one-call interpreter, persistent context store, coordinator and optional saved-result Fetch tools.

**This branch is prepared for review and must remain unmerged until the user requests a merge.** Offline compilation/integration is verified separately from native Photon sticker access, live model accuracy and phone receipt, which remain unverified.

## Install and run

Use Python 3.13 and an isolated environment:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m src demo --db local-data/demo.sqlite3 --replay
.venv/bin/python -m src demo --local
```

The demo connects the real T2/T3/T4/T5 modules to synthetic provider I/O and fixed model candidates. It performs no network calls. Repeating the same database/event reuses the accepted job. For another policy case or source mode, use a separate database:

```sh
.venv/bin/python -m src demo --db local-data/direct.sqlite3 --direct --replay
.venv/bin/python -m src demo --db local-data/opposing.sqlite3 --case opposing
.venv/bin/python -m src inspect --db local-data/demo.sqlite3 --window-id 1
.venv/bin/python -m src doctor
.venv/bin/python -m src live --once
.venv/bin/python -m src mock-demo --case compatible --replay
.venv/bin/python -m src.adapters.vision --case opposing
.venv/bin/python -m src.adapters.fetch_agent --demo
.venv/bin/python agent.py --check
```

`mock-demo` retains the original fully mocked coordinator commands. The vision command retains T3's standalone policy fixture; its opt-in live model command is documented separately. The Fetch demo performs saved-output lookup and voluntary feedback on fictional records. `agent.py --check` checks the separate sponsor quickstart without registration or a model call.

## Understand the code

Read [the walkthrough](docs/CODE_WALKTHROUGH.md) for the data flow and file roles. Core behavior remains automatic, with one image-model call, up to 25 preceding same-chat messages (20–25 configurable), no age cutoff, frozen per-recipient requests, declared preferences/relationships and evaluation-only feedback. Compatible meanings may both appear; opposing meanings yield one supported guess with uncertainty.

The backend now uses Python throughout. Its validation, routing, SQLite and coordination code did not use Jac-specific features, so Python removes an extra compiler/runtime without changing those behaviors. No Jac installation is needed. See [the migration review](docs/PYTHON_MIGRATION.md) for the rationale and compatibility checks.

## Verify the combined application

```sh
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m compileall -q src
.venv/bin/python -m pip check
python3 -I -S scripts/check_contract_fixtures.py
python3 -S -m unittest discover -s checks -p 'test_contract_fixtures.py'
node --test .github/scripts/sync-planning.test.cjs
node .github/scripts/sync-planning.cjs --dry-run
```

CI installs the combined lock and checks every component together. Legacy component requirements files remain usable; requirements-agent-modules.txt points to the common setup. The mock coordinator and SQLite store need only the Python standard library; optional vision and Fetch adapters retain their existing SDK dependencies.

## Live integration

The local runtime polls authenticated Photon 2.0 beta message resources, verifies
one configured direct sender/agent/space, persists source and delivery state, and
routes through the frozen enrollment. Photon did not expose a native sticker
bubble in the tested shared thread, so the supported live trigger is a static
PNG/JPEG/WebP sent with the iMessage photo button. Gemini access and an observed
photo → model → phone round trip are still required before claiming a complete
live demonstration.

See [setup](docs/SETUP.md), [demo](docs/DEMO.md),
[reproduction](docs/REPRODUCTION.md), [evaluation](docs/EVALUATION.md),
[Photon transport](docs/PHOTON_ADAPTER.md), [T3 interpretation](docs/T3_INTERPRETER.md),
[persistent store](docs/CONTEXT_STORE.md), [integration runbook](docs/LIVE_INTEGRATION.md),
[optional Fetch demo](docs/FETCH_AGENT_DEMO.md), and
[product decisions](docs/PRODUCT_SPEC.md). [ERROR_LOG.md](ERROR_LOG.md) records
actual failures, causes and corrections; [PLANS.md](PLANS.md) records
verification. Keep secrets and databases in ignored local paths.

The [planning backlog](planning/backlog.json) and [task definitions](planning/issues/) remain canonical. PR verification performs no issue writes; main-only publication preserves human issue content. No live integration/evaluation issue is closed merely by passing offline checks.
