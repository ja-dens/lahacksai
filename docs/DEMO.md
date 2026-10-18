# Demo runbook

## Offline backup demo

This path uses real coordinator, persistence, policy, routing, and transport
boundaries with synthetic provider I/O and fixed candidates. It makes no
network or model request.

```sh
.venv/bin/python -m src demo --db local-data/demo.sqlite3 --replay
.venv/bin/python -m src inspect --db local-data/demo.sqlite3 --window-id 1
.venv/bin/python scripts/evaluate_stickers.py --mode fixture \
  --output local-data/evaluation-fixture.json
```

Expected evidence:

- one accepted synthetic delivery;
- replay does not create a second send;
- the saved request has at most 25 preceding messages and no feedback;
- the evaluation report says `fixture_output_is_model_accuracy: false`.

## Live direct-space demo

1. Complete [local setup](SETUP.md).
2. Run `.venv/bin/python -m src live`.
3. From the exact `PHOTON_ALLOWED_SENDER`, open the assigned shared-line thread.
4. Use the photo button to send a static test image. Do not use the sticker
   drawer for this beta fallback.
5. Observe one explanation in the same direct thread.
6. Read SQLite evidence without exposing message text:
   - `live_receipts` has one source message receipt;
   - `live_attachments` records MIME, size, and digest;
   - `live_model_calls` records status, latency, and token counts when returned;
   - `live_delivery_status` records the provider's latest state.

Record separately:

- Photon attachment observed;
- one model call observed;
- provider accepted/dispatched/delivered;
- explanation visually received on the phone;
- end-to-end latency;
- any mismatch or retry.

Provider `delivered` is not, by itself, visual phone receipt. Never include
credentials, personal message text, phone numbers, prompts, or image bytes in a
published report.
