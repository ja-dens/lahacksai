#!/usr/bin/env python3
"""Deterministic policy regression and opt-in Gemini review packet generator."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import mimetypes
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.vision import FixtureVision, GeminiVision  # noqa: E402
from src.interpreter import interpret_sticker  # noqa: E402


def load_request(image_path: Path, crop: list[int] | None = None) -> dict:
    request = json.loads(
        (ROOT / "fixtures/contracts/interpretation_request.json").read_text()
    )
    if crop is None:
        data = image_path.read_bytes()
        mime_type = mimetypes.guess_type(image_path.name)[0]
    else:
        if (
            not isinstance(crop, list) or len(crop) != 4
            or any(not isinstance(value, int) for value in crop)
        ):
            raise ValueError("Invalid evaluation crop")
        with Image.open(image_path) as image:
            left, top, right, bottom = crop
            if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                raise ValueError("Evaluation crop is outside the source image")
            output = io.BytesIO()
            image.crop((left, top, right, bottom)).save(output, format="PNG")
            data = output.getvalue()
        mime_type = "image/png"
    if mime_type not in ("image/png", "image/jpeg", "image/webp"):
        raise ValueError("Unsupported evaluation image type")
    request["sticker"] = {
        "mime_type": mime_type,
        "data_base64": base64.b64encode(data).decode("ascii"),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    return request


def apply_variant(request: dict, variant: str) -> dict:
    if variant == "baseline":
        return request
    if variant == "image_only":
        request["recent_messages"] = []
        request["target_text"] = None
    elif variant == "relationship_unknown":
        request["user_context"]["relationship"] = None
        request["user_context"]["relationship_source"] = None
    elif variant == "detailed_spanish":
        request["user_context"]["preferences"] = {
            "language": "es", "explanation_length": "detailed",
        }
    elif variant in ("window_20", "window_25"):
        count = int(variant.split("_")[1])
        start = datetime(2026, 10, 17, 18, 59, tzinfo=timezone.utc)
        request["recent_messages"] = [
            {
                "message_id": f"evaluation-{index:02d}",
                "sender_id": (
                    request["recipient_id"] if index % 2 == 0
                    else request["sender_id"]
                ),
                "sent_at": (start + timedelta(seconds=index * 2)).isoformat(),
                "text": f"Permitted synthetic context message {index + 1}.",
                "kind": "text", "reply_to_message_id": None,
                "media_not_interpreted": False, "text_truncated": False,
            }
            for index in range(count)
        ]
    elif variant == "long_gap":
        request["recent_messages"][0]["sent_at"] = "2020-01-01T00:00:00+00:00"
    elif variant == "unrelated":
        request["recent_messages"][-1]["text"] = "The bus arrives at seven."
    elif variant == "truncated":
        request["recent_messages"][-1]["text"] = "That joke got"
        request["recent_messages"][-1]["text_truncated"] = True
    elif variant == "prior_media":
        request["recent_messages"][-1].update(
            text=None, kind="audio", media_not_interpreted=True,
        )
    elif variant == "other_chat":
        request["conversation_id"] = "evaluation-other-chat"
    elif variant == "invalid_media":
        data = b"\x89PNG\r\n\x1a\nnot a decodable image"
        request["sticker"].update(
            data_base64=base64.b64encode(data).decode("ascii"),
            sha256=hashlib.sha256(data).hexdigest(),
        )
    elif variant != "unrankable":
        raise ValueError("Unknown evaluation variant")
    return request


def _manifest(dataset: str) -> dict:
    if dataset == "policy":
        return json.loads((ROOT / "evaluation/cases.json").read_text())
    if dataset != "hamster-pack":
        raise ValueError("Unknown evaluation dataset")
    pack = json.loads((ROOT / "evaluation/hamster_pack.json").read_text())
    return {
        "dataset": pack["dataset"],
        "accuracy_claim": False,
        "cases": [
            {
                "id": item["id"],
                "variant": "image_only",
                "image": pack["source_image"],
                "crop": item["crop"],
                "candidate_fixture": "fixtures/contracts/candidate_single.json",
                "expected_result": "fixtures/contracts/interpretation_result.json",
                "label_provenance": "user_permitted_visual_reference_only",
                "split": "coverage",
                "review_note": item["visual_cue"],
            }
            for item in pack["stickers"]
        ],
    }


def evaluate(*, mode: str, model: str | None = None, dataset: str = "policy") -> dict:
    manifest = _manifest(dataset)
    reports = []
    vision = None
    try:
        if mode == "live":
            vision = GeminiVision(model=model)
        for case in manifest["cases"]:
            request = apply_variant(
                load_request(ROOT / case["image"], case.get("crop")),
                case.get("variant", "baseline"),
            )
            if mode == "fixture":
                candidate = json.loads((ROOT / case["candidate_fixture"]).read_text())
                if case.get("variant") == "unrankable":
                    candidate["rankable"] = False
                adapter = FixtureVision(candidate)
            else:
                adapter = vision
            report = {
                "id": case["id"],
                "mode": mode,
                "pair_id": case.get("pair_id"),
                "split": case["split"],
                "label_provenance": case["label_provenance"],
                "review_note": case["review_note"],
            }
            try:
                result = interpret_sticker(request, adapter)
                report["result"] = result
                if "expected_error" in case:
                    report["policy_regression_passed"] = False
                    report["unexpected_success"] = True
                elif mode == "fixture":
                    if case.get("variant") == "unrankable":
                        report["policy_regression_passed"] = (
                            result["status"] == "unsupported"
                            and result["meaning"] == ""
                            and result["alternative"] is None
                            and result["candidate_relation"] == "opposing"
                        )
                    else:
                        expected = json.loads((ROOT / case["expected_result"]).read_text())
                        report["policy_regression_passed"] = result == expected
                else:
                    report["human_review_required"] = True
            except Exception as error:
                code = getattr(error, "code", type(error).__name__)
                report["error_code"] = code
                if mode == "fixture":
                    report["policy_regression_passed"] = (
                        code == case.get("expected_error")
                    )
                else:
                    report["human_review_required"] = True
            reports.append(report)
    finally:
        if vision is not None:
            vision.close()
    return {
        "dataset": manifest["dataset"],
        "mode": mode,
        "network_model_calls": (
            int(getattr(vision, "call_count", 0)) if mode == "live" else 0
        ),
        "fixture_output_is_model_accuracy": False,
        "measured_model_accuracy": None,
        "all_policy_regressions_passed": (
            all(item["policy_regression_passed"] for item in reports)
            if mode == "fixture" else None
        ),
        "pairs": {
            pair_id: [item["id"] for item in reports if item["pair_id"] == pair_id]
            for pair_id in sorted({
                item["pair_id"] for item in reports if item["pair_id"] is not None
            })
        },
        "cases": reports,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    parser.add_argument("--dataset", choices=("policy", "hamster-pack"), default="policy")
    parser.add_argument("--model", help="Override VISION_MODEL in live mode")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate(mode=args.mode, model=args.model, dataset=args.dataset)
    except Exception as error:
        code = getattr(error, "code", type(error).__name__)
        print(json.dumps({"status": "failed", "error_code": code}))
        return 1
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    if args.mode == "fixture" and not report["all_policy_regressions_passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
