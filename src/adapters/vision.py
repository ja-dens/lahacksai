"""Replaceable one-request Responses adapter. --smoke is an opt-in paid live check."""

import argparse
import base64
from copy import deepcopy
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import warnings

from PIL import Image

from src import interpreter

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "candidates": {"type": "array", "items": {"type": "string"}, "maxItems": 2},
        "candidate_relation": {"type": "string", "enum": ["none", "single", "compatible", "opposing"]},
        "rankable": {"type": "boolean"}, "context_cue": {"type": "string"},
        "uncertainty_caveat": {"type": "string"},
    },
    "required": ["candidates", "candidate_relation", "rankable", "context_cue", "uncertainty_caveat"],
}


def png_data_url(media):
    if not isinstance(media, dict) or media.get("mime_type") != "image/png":
        raise ValueError("Only static PNG stickers are supported.")
    encoded = media.get("data_base64")
    if not isinstance(encoded, str) or len(encoded) > 4 * ((5_000_000 + 2) // 3):
        raise ValueError("Missing or oversized sticker bytes.")
    data = base64.b64decode(encoded, validate=True)
    if not data or len(data) > 5_000_000 or hashlib.sha256(data).hexdigest() != media.get("sha256"):
        raise ValueError("Sticker size or hash does not match the snapshot.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG" or getattr(image, "is_animated", False):
                raise ValueError("Only static PNG stickers are supported.")
            if image.width * image.height > 16_000_000:
                raise ValueError("Sticker dimensions are too large.")
            image.verify()
        # verify checks integrity; load also checks actual pixel decoding.
        with Image.open(BytesIO(data)) as image:
            image.load()
    return "data:image/png;base64," + encoded


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON output key.")
        result[key] = value
    return result


class VisionAdapter:
    def __init__(self, client, model, prompt=None):
        if not isinstance(model, str) or not model.strip():
            raise ValueError("An explicitly configured vision model is required.")
        self.client = client.with_options(max_retries=0, timeout=30.0)
        self.model = model
        self.prompt = prompt if prompt is not None else (ROOT / "prompts/sticker.txt").read_text()
        self.last_run = None

    def start_run(self, snapshot):
        self.last_run = {"snapshot": deepcopy(snapshot), "status": "running", "result": None,
                         "provider": "openai-responses", "model": self.model,
                         "prompt_sha256": hashlib.sha256(self.prompt.encode()).hexdigest()}

    def generate(self, snapshot, context):
        image_url = png_data_url(snapshot.get("sticker"))
        response = self.client.responses.create(
            model=self.model, instructions=self.prompt, store=False,
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": json.dumps(context, ensure_ascii=False)},
                {"type": "input_image", "image_url": image_url, "detail": "auto"},
            ]}],
            text={"format": {"type": "json_schema", "name": "sticker_candidates", "strict": True,
                             "schema": CANDIDATE_SCHEMA}},
        )
        if response.status != "completed" or not response.output_text:
            raise ValueError("Model did not complete a candidate response.")
        return json.loads(response.output_text, object_pairs_hook=unique_json_object)

    def finish_run(self, result):
        self.last_run.update(status="completed", result=deepcopy(result))

    def fail_run(self, error_type):
        self.last_run.update(status="failed", result=None, error_type=error_type)

    def interpret(self, request):
        return interpreter.interpret_sticker(request, self)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", required=True,
                        help="Send the synthetic PNG/context once using VISION_API_KEY and VISION_MODEL.")
    parser.parse_args()
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(ROOT / ".env")
    for name in ("VISION_API_KEY", "VISION_MODEL"):
        if not os.getenv(name, "").strip():
            parser.error(f"Set {name} in .env before this opt-in live check.")
    adapter = VisionAdapter(OpenAI(api_key=os.environ["VISION_API_KEY"]), os.environ["VISION_MODEL"])
    request = json.loads((ROOT / "fixtures/contracts/interpretation_request.json").read_text())
    try:
        print(json.dumps(adapter.interpret(request), indent=2))
    except Exception as exc:
        parser.exit(1, f"Live interpretation failed ({type(exc).__name__}); no result was fabricated.\n")


if __name__ == "__main__":
    main()
