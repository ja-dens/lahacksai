# Reproduction checklist

Use Python 3.13 and the committed lock file.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src scripts
.venv/bin/python -m pip check
python3 -I -S scripts/check_contract_fixtures.py
python3 -S -m unittest discover -s checks -p 'test_contract_fixtures.py'
.venv/bin/python scripts/check_photon_feasibility.py
.venv/bin/python scripts/evaluate_stickers.py --mode fixture
node --test .github/scripts/sync-planning.test.cjs
node .github/scripts/sync-planning.cjs --dry-run
git diff --check
```

For a credentialed run, create an ignored `.env` from `.env.example`, run
`python -m src doctor`, then follow [the demo runbook](DEMO.md). A new operator
must use their own consenting test sender and must not reuse published personal
identifiers.

Report environment, commit, command, exit status, test counts, dataset version,
provider state, model-call count, and phone observation. Keep fixture-policy
results, live model review, provider acknowledgment, and visual phone evidence
as four separate claims.

Current limitations:

- Photon 2.0 beta shared iMessage is direct only.
- Native sticker bubbles were not returned as messages or attachments.
- The photo-button image attachment is the supported fallback.
- Live model quality needs a human-reviewed permitted dataset.
- Provider delivery status does not prove phone receipt.
