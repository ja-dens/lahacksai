# Evaluation

`evaluation/cases.json` contains permitted repository images and deterministic
policy cases. It tests candidate-policy wiring, not vision accuracy.
The held-out manifest includes paired image-only/context, relationship,
presentation, and 20/25-message windows plus long gaps, unrelated topics,
truncation, prior uninterpreted media, the same image in another chat,
compatible/opposing/unrankable candidates, and malformed media.

`evaluation/hamster_pack.json` separately indexes all 19 tiles in the
user-permitted hamster reference sheet. The pack is local-only and is not
pushed; without it the hamster commands and test are skipped. Fixture mode verifies that every crop is
valid and reaches the interpreter; it does not measure whether the model assigns
the right meaning.

```sh
.venv/bin/python scripts/evaluate_stickers.py --mode fixture
.venv/bin/python scripts/evaluate_stickers.py --mode fixture --dataset hamster-pack
```

The report must retain:

- `network_model_calls: 0`;
- `fixture_output_is_model_accuracy: false`;
- `measured_model_accuracy: null`;
- a passing comparison against each committed policy result.

To generate an opt-in Gemini review packet:

```sh
.venv/bin/python scripts/evaluate_stickers.py --mode live \
  --model gemini-3.5-flash-lite --output local-data/gemini-review.json

.venv/bin/python scripts/evaluate_stickers.py --mode live \
  --dataset hamster-pack --model gemini-3.5-flash-lite \
  --output local-data/hamster-pack-review.json
```

Live mode makes one request per case. Each request remains one multimodal model
call; for recognition it includes the target plus the permitted full reference
sheet. It marks every result
`human_review_required` and does not compute accuracy. A reviewer should score
these dimensions separately:

- semantic meaning: correct, partially supported, confidently wrong, or
  insufficient label;
- context use: useful, ignored when needed, or overfit to unrelated text;
- policy/schema: valid abstention, compatible alternatives, opposing-choice
  ranking, and uncertainty;
- personalization: presentation changed appropriately without changing meaning
  or introducing a relationship stereotype;
- comprehension: intended user understood the explanation.

Use a larger held-out, permitted dataset before making a quality claim. Keep
tuning examples separate, and do not add private chat content or unlicensed
sticker art. Synthetic expected meanings and recipient judgments are weaker
provenance than sender-confirmed labels.

Latency/token metadata from the automatic service is operational evidence, not
an accuracy metric. Cost is reported only when an authoritative provider value
or versioned pricing calculation is available; this implementation does not
fabricate one.
