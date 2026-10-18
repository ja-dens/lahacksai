"""One stateless model request, or an explicitly labeled offline substitute."""

import argparse
import base64
import copy
import hashlib
import io
import json
import math
import os
import time
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from src.interpreter import (
    interpret_sticker, model_output_schema, prepare_request, validate_model_output,
)

ROOT = Path(__file__).resolve().parents[2]
MAX_IMAGE_PIXELS = 16_777_216


class VisionError(RuntimeError):
    """A safe operational category; never carries prompts or provider response text."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _normalize_image(media):
    data = base64.b64decode(media["data_base64"], validate=True)
    try:
        detected_format = None
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=("PNG", "JPEG", "WEBP")) as image:
                detected_format = image.format
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise VisionError("image_dimensions_exceeded")
                if getattr(image, "is_animated", False):
                    raise VisionError("animated_media_unsupported")
                image.verify()
            with Image.open(io.BytesIO(data), formats=("PNG", "JPEG", "WEBP")) as image:
                image.load()
                image = ImageOps.exif_transpose(image)
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA")
                if detected_format == "PNG":
                    return data
                output = io.BytesIO()
                image.save(output, format="PNG", optimize=True)
                return output.getvalue()
    except VisionError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise VisionError("unreadable_media") from None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Nonfinite JSON value")


def _field(value, name, default=None):
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


def _read_output(response):
    for item in _field(response, "output", []) or []:
        if _field(item, "type") == "message":
            if any(_field(part, "type") == "refusal" for part in _field(item, "content", []) or []):
                raise VisionError("model_refused")
    if _field(response, "status") != "completed":
        raise VisionError("model_incomplete")
    text = _field(response, "output_text")
    if not isinstance(text, str) or not text.strip():
        raise VisionError("model_empty_output")
    if len(text) > 64_000:
        raise VisionError("invalid_model_output")
    try:
        raw = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
        return validate_model_output(raw)
    except (ValueError, TypeError, RecursionError):
        raise VisionError("invalid_model_output") from None


class FixtureVision:
    """Fixed output for interface checks; it does not interpret the image."""

    metadata = {"provider": "fixture", "model": "fixed-demo", "prompt_version": "fixture-v1"}

    def __init__(self, result):
        self.result = validate_model_output(copy.deepcopy(result))

    def __call__(self, request):
        evidence = prepare_request(request)
        _normalize_image(evidence["sticker"])
        return copy.deepcopy(self.result)


class OpenAIVision:
    """Raw-candidate adapter. Use interpret_sticker(request, adapter) for the result."""

    def __init__(self, api_key=None, model=None, client=None, timeout_seconds=30.0):
        from openai import OpenAI

        model = model or os.environ.get("VISION_MODEL")
        if not isinstance(model, str) or not model.strip():
            raise VisionError("model_not_configured")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool):
            raise VisionError("invalid_timeout")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise VisionError("invalid_timeout")
        self._owns_client = client is None
        if client is None:
            key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("VISION_API_KEY")
            if not isinstance(key, str) or not key.strip():
                raise VisionError("api_key_not_configured")
            client = OpenAI(api_key=key, max_retries=0, timeout=timeout_seconds)
        elif callable(getattr(client, "with_options", None)):
            client = client.with_options(max_retries=0, timeout=timeout_seconds)
        self.client = client
        self.model = model.strip()
        self.prompt = (ROOT / "prompts/sticker.txt").read_text()
        self.metadata = {
            "provider": "openai-api-key", "model": self.model,
            "prompt_sha256": hashlib.sha256(self.prompt.encode()).hexdigest(),
        }
        self.last_call_metadata = None
        self.call_count = 0

    def close(self):
        if self._owns_client:
            self.client.close()

    def __call__(self, request):
        from openai import (
            APIConnectionError, APIError, APIStatusError, APITimeoutError,
            AuthenticationError, RateLimitError,
        )

        evidence = prepare_request(request)
        media = evidence.pop("sticker")
        normalized = _normalize_image(media)
        evidence["sticker_metadata"] = {"mime_type": media["mime_type"], "sha256": media["sha256"]}
        started = time.monotonic()
        try:
            self.call_count += 1
            response = self.client.responses.create(
                model=self.model, instructions=self.prompt,
                input=[{"role": "user", "content": [
                    {"type": "input_text", "text": json.dumps(evidence, ensure_ascii=False)},
                    {"type": "input_image", "image_url": "data:image/png;base64,"
                     + base64.b64encode(normalized).decode("ascii")},
                ]}],
                text={"format": {"type": "json_schema", "name": "sticker_interpretation",
                                 "strict": True, "schema": model_output_schema()}},
                store=False, max_output_tokens=1500,
            )
        except (APITimeoutError, TimeoutError):
            self.last_call_metadata = {
                "status": "error", "error_code": "model_timeout",
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
            raise VisionError("model_timeout") from None
        except AuthenticationError:
            self.last_call_metadata = {
                "status": "error", "error_code": "model_authentication_failed",
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
            raise VisionError("model_authentication_failed") from None
        except RateLimitError:
            self.last_call_metadata = {
                "status": "error", "error_code": "model_rate_limited",
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
            raise VisionError("model_rate_limited") from None
        except APIConnectionError:
            self.last_call_metadata = {
                "status": "error", "error_code": "model_connection_failed",
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
            raise VisionError("model_connection_failed") from None
        except APIStatusError:
            self.last_call_metadata = {
                "status": "error", "error_code": "model_http_error",
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
            raise VisionError("model_http_error") from None
        except APIError:
            self.last_call_metadata = {
                "status": "error", "error_code": "model_api_error",
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
            raise VisionError("model_api_error") from None
        try:
            result = _read_output(response)
        except VisionError as error:
            self.last_call_metadata = {
                "status": "error", "error_code": error.code,
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
            raise
        usage = _field(response, "usage", {})
        self.last_call_metadata = {
            "status": "completed",
            "latency_ms": round((time.monotonic() - started) * 1000),
            "input_tokens": _field(usage, "input_tokens"),
            "output_tokens": _field(usage, "output_tokens"),
            "total_tokens": _field(usage, "total_tokens"),
        }
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Standalone T3 interpreter; fixture mode makes no model calls")
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--request", type=Path, default=ROOT / "fixtures/contracts/interpretation_request.json")
    parser.add_argument("--case", choices=("single", "compatible", "opposing", "unsupported", "unrankable"), default="single")
    parser.add_argument("--model", help="Image/structured-output model available to your API project")
    args = parser.parse_args(argv)
    vision = None
    try:
        request = json.loads(args.request.read_text())
        if args.mode == "fixture":
            name = "opposing" if args.case == "unrankable" else args.case
            raw = json.loads((ROOT / f"fixtures/contracts/candidate_{name}.json").read_text())
            if args.case == "unrankable":
                raw["rankable"] = False
            vision = FixtureVision(raw)
        else:
            vision = OpenAIVision(model=args.model)
        result = interpret_sticker(request, vision)
        print(json.dumps({"mode": args.mode, "interpretation_is_fixed_fixture": args.mode == "fixture",
                          "network_delivery_performed": False, "result": result}, ensure_ascii=False, indent=2))
        return 0
    except VisionError as error:
        configuration = error.code in ("api_key_not_configured", "model_not_configured")
        print(json.dumps({"status": "unverified" if configuration else "failed", "error_code": error.code,
                          "network_delivery_performed": False}))
        return 2 if configuration else 1
    except (OSError, ValueError, TypeError):
        print(json.dumps({"status": "failed", "error_code": "invalid_request", "network_delivery_performed": False}))
        return 1
    finally:
        if vision is not None and callable(getattr(vision, "close", None)):
            vision.close()


if __name__ == "__main__":
    raise SystemExit(main())
