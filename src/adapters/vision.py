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
HAMSTER_PACK_MANIFEST = ROOT / "evaluation/hamster_pack.json"


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


def _hamster_pack_reference():
    """Load the local-only recognition sheet, or ("", None) when it is absent."""
    if not HAMSTER_PACK_MANIFEST.exists():
        return "", None
    manifest = json.loads(HAMSTER_PACK_MANIFEST.read_text())
    image_path = ROOT / manifest["source_image"]
    data = image_path.read_bytes()
    try:
        with Image.open(io.BytesIO(data), formats=("JPEG",)) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise VisionError("image_dimensions_exceeded")
            image.verify()
    except (KeyError, TypeError, UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise VisionError("invalid_hamster_reference") from None
    stickers = manifest.get("stickers")
    if not isinstance(stickers, list) or len(stickers) != 19:
        raise VisionError("invalid_hamster_reference")
    cues = []
    for sticker in stickers:
        if not isinstance(sticker, dict):
            raise VisionError("invalid_hamster_reference")
        identifier = sticker.get("id")
        cue = sticker.get("visual_cue")
        if not isinstance(identifier, str) or not isinstance(cue, str):
            raise VisionError("invalid_hamster_reference")
        cues.append(f"- {identifier}: {cue}")
    guidance = (
        "\n\nThe final input image is an app-supplied reference sheet for a known "
        "19-image hamster sticker family. Use it only to recognize the target's "
        "visual family, expression, pose, or accessory. The target image immediately "
        "before it is the sticker to interpret. Do not interpret the whole sheet, "
        "assume a catalog cue fixes the conversational meaning, or mention catalog IDs "
        "to the recipient.\n" + "\n".join(cues)
    )
    return guidance, data


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


DEFAULT_VISION_MODEL = "gemini-3.5-flash-lite"
_GEMINI_KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "VISION_API_KEY")
_REFUSAL_FINISH = {
    "SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY",
}
_INCOMPLETE_FINISH = {
    "MAX_TOKENS", "OTHER", "MALFORMED_FUNCTION_CALL", "UNEXPECTED_TOOL_CALL",
    "LANGUAGE", "CONTINUATION",
}
_SCHEMA_KEYS_GEMINI_REJECTS = {"additionalProperties", "minLength", "maxLength"}


def gemini_api_key(environ=None):
    values = os.environ if environ is None else environ
    for name in _GEMINI_KEY_NAMES:
        value = values.get(name, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _enum_name(value):
    if value is None:
        return ""
    name = getattr(value, "name", None)
    if isinstance(name, str) and name:
        return name
    return str(value).split(".")[-1]


def _gemini_response_schema(node=None):
    """JSON Schema subset accepted by Gemini structured output."""
    if node is None:
        node = model_output_schema()
    if isinstance(node, dict):
        return {
            key: _gemini_response_schema(value)
            for key, value in node.items()
            if key not in _SCHEMA_KEYS_GEMINI_REJECTS
        }
    if isinstance(node, list):
        return [_gemini_response_schema(value) for value in node]
    return node


def _read_output(response):
    feedback = _field(response, "prompt_feedback")
    block = _enum_name(_field(feedback, "block_reason"))
    if block and "UNSPECIFIED" not in block:
        raise VisionError("model_refused")
    candidates = _field(response, "candidates") or []
    finish = _enum_name(_field(candidates[0], "finish_reason")) if candidates else ""
    if finish in _REFUSAL_FINISH:
        raise VisionError("model_refused")
    if finish in _INCOMPLETE_FINISH:
        raise VisionError("model_incomplete")
    try:
        text = _field(response, "text")
    except (TypeError, ValueError):
        text = None
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


class GeminiVision:
    """Raw-candidate adapter. Use interpret_sticker(request, adapter) for the result."""

    def __init__(self, api_key=None, model=None, client=None, timeout_seconds=30.0,
                 http_client=None):
        model = model or os.environ.get("VISION_MODEL")
        if not isinstance(model, str) or not model.strip():
            raise VisionError("model_not_configured")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool):
            raise VisionError("invalid_timeout")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise VisionError("invalid_timeout")
        self._owns_client = client is None
        if client is None:
            from google import genai
            from google.genai import types

            key = (api_key.strip() if isinstance(api_key, str) else "") or gemini_api_key()
            if not key:
                raise VisionError("api_key_not_configured")
            client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(
                    timeout=int(timeout_seconds * 1000),
                    retry_options=types.HttpRetryOptions(attempts=1),
                    httpx_client=http_client,
                ),
            )
        self.client = client
        self.model = model.strip()
        reference_guidance, self.reference_image = _hamster_pack_reference()
        self.prompt = (ROOT / "prompts/sticker.txt").read_text() + reference_guidance
        self.metadata = {
            "provider": "gemini-api-key", "model": self.model,
            "prompt_sha256": hashlib.sha256(self.prompt.encode()).hexdigest(),
        }
        if self.reference_image is not None:
            self.metadata["hamster_reference_sha256"] = hashlib.sha256(
                self.reference_image).hexdigest()
        self.last_call_metadata = None
        self.call_count = 0

    def close(self):
        if self._owns_client:
            self.client.close()

    def _fail(self, started, code):
        self.last_call_metadata = {
            "status": "error", "error_code": code,
            "latency_ms": round((time.monotonic() - started) * 1000),
        }
        raise VisionError(code)

    def __call__(self, request):
        import httpx
        from google.genai import errors

        evidence = prepare_request(request)
        media = evidence.pop("sticker")
        normalized = _normalize_image(media)
        evidence["sticker_metadata"] = {"mime_type": media["mime_type"], "sha256": media["sha256"]}
        parts = [
            {"text": json.dumps(evidence, ensure_ascii=False)},
            {"inline_data": {"mime_type": "image/png", "data": normalized}},
        ]
        if self.reference_image is not None:
            parts += [
                {"text": "Recognition reference only; the preceding image is the target."},
                {"inline_data": {"mime_type": "image/jpeg", "data": self.reference_image}},
            ]
        started = time.monotonic()
        try:
            self.call_count += 1
            response = self.client.models.generate_content(
                model=self.model,
                contents=[{"role": "user", "parts": parts}],
                config={
                    "system_instruction": self.prompt,
                    "response_mime_type": "application/json",
                    "response_json_schema": _gemini_response_schema(),
                    "max_output_tokens": 1500,
                    "candidate_count": 1,
                    "automatic_continuation": False,
                    "automatic_function_calling": {"disable": True},
                    "thinking_config": {
                        "thinking_level": "MINIMAL",
                        "include_thoughts": False,
                    },
                },
            )
        except (httpx.TimeoutException, TimeoutError):
            self._fail(started, "model_timeout")
        except httpx.TransportError:
            self._fail(started, "model_connection_failed")
        except errors.ClientError as error:
            if getattr(error, "code", None) in (401, 403):
                self._fail(started, "model_authentication_failed")
            if getattr(error, "code", None) == 429:
                self._fail(started, "model_rate_limited")
            self._fail(started, "model_http_error")
        except errors.ServerError:
            self._fail(started, "model_http_error")
        except errors.APIError:
            self._fail(started, "model_api_error")
        try:
            result = _read_output(response)
        except VisionError as error:
            self.last_call_metadata = {
                "status": "error", "error_code": error.code,
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
            raise
        usage = _field(response, "usage_metadata", {})
        self.last_call_metadata = {
            "status": "completed",
            "latency_ms": round((time.monotonic() - started) * 1000),
            "input_tokens": _field(usage, "prompt_token_count"),
            "output_tokens": _field(usage, "candidates_token_count"),
            "total_tokens": _field(usage, "total_token_count"),
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
            vision = GeminiVision(model=args.model)
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
