# Backend language review and Python migration

Date: October 17, 2026. Scope: integration PR #14; main remains unmerged.

The user requested replacing Jac wherever another language was a better fit. All ten Jac modules implement ordinary functions over dictionaries, JSON, dates, hashing and SQLite. None uses Jac nodes, edges, walkers or other language-specific facilities. Python already hosts the model/image SDK, Photon transport, optional Fetch SDK and CLI. Keeping these functions in Python removes an extra importer, compiler and LLVM dependency while preserving the component boundaries.

## Module decisions

| Modules now in `src/` | Responsibility | Reason for Python |
| --- | --- | --- |
| `contracts.py`, `interpreter.py` | Normalize events, validate frozen evidence/model output, apply candidate policy | Standard-library validation and direct integration with the existing Python vision adapter. |
| `repository.py`, `context.py`, `store.py` | SQLite schema, history, frozen requests, jobs, claims, outbox, feedback | Direct use of Python's `sqlite3`, JSON and date libraries; no graph traversal or graph storage. |
| `main.py`, `routing.py`, `assembly.py` | Coordinate ports, verify enrollment, classify receipts | Ordinary state transitions and injected Python objects; normal imports and debugger behavior. |
| `delivery.py`, `fetch_tools.py` | Legacy local queue API and authorized saved-result tools | Preserve existing public calls and behavior in the same language as their callers. |

Existing Python SDK adapters remain in Python. JavaScript continues to handle GitHub planning automation. Moving SDK calls or SQLite orchestration to another language would add interoperability work without an identified benefit here. This migration does not change the model, provider, prompt or interpretation strategy.

## Compatibility

- Public module/function names and v2 JSON fields are unchanged. Imports such as `from src.interpreter import interpret_sticker` work normally.
- SQLite table definitions, SQL statements, serialization/hashes, triggers, outbox records and job states are preserved. No database conversion is required.
- A structural comparison of all ten modules against the old compiler's Python representation matched after excluding module descriptions and three unused compiler-generated imports. Important explanatory comments were retained in editable, formatted Python source.
- A database created by the pre-migration commit `5690193` was opened by the Python implementation. All saved jobs, request hashes, receipts, feedback and schema matched before further work. An accepted job did not resend; an explicitly retried rejected send reused its saved result with zero model calls; an uncertain send remained blocked for reconciliation.
- The package initializer no longer loads a Jac importer. Both dependency locks were regenerated in fresh Python 3.13 environments. Only `jaclang` and `llvmlite` were removed; every other resolved version is unchanged.
- CI uses Python compilation and the existing component tests. The obsolete source-percentage script was removed. Historical verification/error records retain their original language checkpoints.

## Verification

The original 172 application tests passed before migration. After migration, all 174 application tests passed in a fresh environment with neither Jac nor llvmlite installed. The two additional tests run isolated subprocesses without site packages: they exercise real SQLite/policy/feedback/replay with fake external I/O and run the mock CLI. Optional SDK and compiler imports are forbidden in the core-workflow subprocess.

The 19 real-store tests and 36 mock-integration tests also run with site packages disabled. The standalone T3 environment retains 34 passing interpreter tests. Shared fixture validation, 10 contract regressions, 15 planning tests, compilation and dependency checks are run separately. Fixed candidates and synthetic transport provide regression evidence, not model-accuracy or phone-receipt evidence.

```sh
python -m pip install -r requirements.lock
python -m compileall -q src
python -m pip check
python -m unittest discover -s tests
python -S -m unittest discover -s tests -p 'test_context_store.py'
python -S -m unittest discover -s tests -p 'test_integration.py'
python -S -m unittest discover -s tests -p 'test_python_runtime.py'
python -I -S scripts/check_contract_fixtures.py
python -S -m unittest discover -s checks -p 'test_contract_fixtures.py'
```

## Local import comparison

With the same Python 3.13 executable and machine, seven fresh subprocess imports of `src.main`, after one warm-up, had a median of 457.8 ms before migration and 5.6 ms afterward. The previous Jac bytecode cache was already present. The timing covered the import inside each process, excluding process launch. It is a local startup measurement, not an end-to-end request benchmark or a guarantee for other machines. Model and network latency were not measured.

## Still missing

The language migration does not supply native Photon sticker ingress, verified live account/destination binding, real model-quality evaluation, deployment/retention operations, phone receipt evidence, or persistent atomic Fetch command deduplication. These remain tracked integration/evaluation work. The integration PR stays open; no change was merged into main.
