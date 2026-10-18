# Evaluation

`evaluation/cases.json` contains permitted repository images and deterministic
policy cases. It tests candidate-policy wiring, not vision accuracy.
The held-out manifest includes paired image-only/context, relationship,
presentation, and 20/25-message windows plus long gaps, unrelated topics,
truncation, prior uninterpreted media, the same image in another chat,
compatible/opposing/unrankable candidates, and malformed media.

```sh
.venv/bin/python scripts/evaluate_stickers.py --mode fixture
```

The report must retain:

- `network_model_calls: 0`;
- `fixture_output_is_model_accuracy: false`;
- `measured_model_accuracy: null`;
- a passing comparison against each committed policy result.

To generate an opt-in OpenAI review packet:

```sh
.venv/bin/python scripts/evaluate_stickers.py --mode live \
  --model gpt-4.1-mini --output local-data/openai-review.json
```

Live mode makes one request per case. It marks every result
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
