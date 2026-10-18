"""Photon 2.0 transport boundary; no database, coordinator, or model imports.

Provider event decoding, authentication and native-sticker classification must be
supplied by trusted integration code. See docs/PHOTON_ADAPTER.md for evidence limits.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import struct
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_MEDIA_BYTES = 5_000_000
MAX_WEBHOOK_BYTES = 1_000_000
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
WEBP_RIFF = b"RIFF"
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
DELIVERY_FIELDS = {"recipient_id", "source_conversation_id", "source_message_id", "text"}
MEDIA_ABSTENTIONS = {"unsupported_media", "media_too_large", "invalid_png", "animated_media_unsupported",
                     "invalid_media_response", "response_too_large", "provider_http_404"}


class PhotonError(Exception):
    """Safe error codes only; never include provider bodies or credentials."""

    def __init__(self, code: str, *, retryable: bool = False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


def _identifier(value):
    if not isinstance(value, str) or not value.strip():
        raise PhotonError("invalid_identifier")
    return value


def _object(value):
    if not isinstance(value, Mapping):
        raise PhotonError("invalid_object")
    return value


def _timestamp(value):
    if not isinstance(value, str):
        raise PhotonError("invalid_timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError
        return stamp.astimezone(timezone.utc).isoformat(timespec="microseconds")
    except (ValueError, OverflowError):
        raise PhotonError("invalid_timestamp") from None


def _json_load(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def invalid_number(value):
        raise ValueError("non-finite JSON number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_number)


def _static_png(data):
    """Check PNG framing/CRCs and reject APNG; does not decode image pixels."""
    if not data.startswith(PNG_SIGNATURE):
        raise PhotonError("unsupported_media")
    offset, chunks = 8, []
    while offset < len(data):
        if offset + 12 > len(data):
            raise PhotonError("invalid_png")
        size = struct.unpack_from(">I", data, offset)[0]
        end = offset + 12 + size
        if end > len(data):
            raise PhotonError("invalid_png")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if binascii.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise PhotonError("invalid_png")
        if kind == b"acTL":
            raise PhotonError("animated_media_unsupported")
        if not chunks:
            if kind != b"IHDR" or size != 13 or not all(struct.unpack(">II", payload[:8])):
                raise PhotonError("invalid_png")
        elif kind == b"IHDR":
            raise PhotonError("invalid_png")
        chunks.append(kind)
        offset = end
        if kind == b"IEND":
            if size or offset != len(data) or b"IDAT" not in chunks:
                raise PhotonError("invalid_png")
            return
    raise PhotonError("invalid_png")


@dataclass(frozen=True)
class Attachment:
    data: bytes
    mime_type: str


class ProviderClient(Protocol):
    def fetch_attachment(self, attachment_id: str, *, max_bytes: int, timeout: float) -> Attachment: ...

    def send_message(self, body: dict, *, idempotency_key: str, timeout: float) -> Mapping: ...


@dataclass(frozen=True)
class PrivateDestination:
    """Only a trusted enrollment resolver may construct this binding."""

    recipient_id: str
    source_conversation_id: str
    platform: str
    space_id: str
    sender_id: str
    recipient_user_id: str
    participant_ids: tuple[str, ...]
    kind: str = "direct"
    verified: bool = False


@dataclass(frozen=True)
class NormalizedMessage:
    event: dict | None
    warning: str | None = None


@dataclass(frozen=True)
class IngressReceipt:
    status: str
    trigger: str = "none"
    event: dict | None = None
    warning: str | None = None
    error_code: str | None = None
    retryable: bool = False


@dataclass(frozen=True)
class SendReceipt:
    status: str
    idempotency_key: str | None = None
    provider_message_id: str | None = None
    provider_status: str | None = None
    delivered: bool = False  # False means phone receipt has not been verified.
    error_code: str | None = None
    retryable: bool = False


class PhotonAdapter:
    def __init__(self, *, project_id: str, platform: str, assistant_ids,
                 client: ProviderClient, verify_event: Callable,
                 decode_event: Callable, resolve_destination: Callable,
                 classify_attachment: Callable | None = None, timeout: float = 10.0):
        self.project_id, self.platform = _identifier(project_id), _identifier(platform)
        if isinstance(assistant_ids, str):
            raise ValueError("assistant_ids must be a collection of identities")
        self.assistant_ids = frozenset(_identifier(i) for i in assistant_ids)
        if not self.assistant_ids or not all(callable(f) for f in (verify_event, decode_event, resolve_destination)):
            raise ValueError("Trusted authentication, decoder, routing and assistant identities are required")
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive")
        self.client, self.verify_event, self.decode_event = client, verify_event, decode_event
        self.resolve_destination = resolve_destination
        self.classify_attachment = classify_attachment or (lambda message, part: "other")
        self.timeout = timeout

    def normalize_message(self, message: Mapping) -> NormalizedMessage:
        """Normalize one Photon Message resource; caller must authenticate first."""
        message = _object(message)
        if message.get("projectId") != self.project_id or message.get("platform") != self.platform:
            raise PhotonError("source_scope_mismatch")
        sender, space = _object(message.get("sentBy")), _object(message.get("space"))
        sender_id = _identifier(sender.get("id"))
        if message.get("status") != "received" or sender_id in self.assistant_ids:
            return NormalizedMessage(None)
        for record in (sender, space):
            if record.get("projectId") != self.project_id or record.get("platform") != self.platform:
                raise PhotonError("source_scope_mismatch")
        event = {
            "platform": self.platform, "conversation_id": _identifier(space.get("id")),
            "message_id": _identifier(message.get("id")), "sender_id": sender_id,
            "sent_at": _timestamp(_object(message.get("timestamps")).get("receivedAt")),
            "from_assistant": False, "text": None, "kind": "other", "sticker": None,
            "reply_to_message_id": message.get("parentMessageId"),
        }
        if event["reply_to_message_id"] is not None:
            _identifier(event["reply_to_message_id"])
        content = _object(message.get("content"))
        parts = content.get("parts") if content.get("type") == "group" else [content]
        if not isinstance(parts, list) or not parts:
            raise PhotonError("invalid_content")
        texts, media = [], []
        for part in parts:
            part = _object(part)
            if part.get("type") == "text":
                if not isinstance(part.get("text"), str):
                    raise PhotonError("invalid_text")
                texts.append(part["text"])
            elif part.get("type") == "attachment":
                kind = self.classify_attachment(message, part)
                if kind not in ("sticker", "image", "audio", "other"):
                    raise PhotonError("invalid_media_classification")
                media.append((part, kind))
            elif part.get("type") in ("message.read", "space.typing.update", "reaction"):
                if len(parts) == 1:
                    return NormalizedMessage(None)
        event["text"] = "\n".join(texts) if texts else None
        if not media:
            event["kind"] = "text" if texts else "other"
            return NormalizedMessage(event)
        if any(kind == "sticker" for _, kind in media):
            event["kind"] = "sticker"
            if len(media) != 1:
                return NormalizedMessage(event, "multiple_media_unsupported")
            attachment_id = _identifier(media[0][0].get("attachmentId"))
            try:
                attachment = self.client.fetch_attachment(attachment_id, max_bytes=MAX_MEDIA_BYTES, timeout=self.timeout)
                if not isinstance(attachment, Attachment) or not isinstance(attachment.data, bytes):
                    raise PhotonError("invalid_media_response")
                if len(attachment.data) > MAX_MEDIA_BYTES:
                    raise PhotonError("media_too_large")
                mime_type = attachment.mime_type.lower()
                if mime_type not in SUPPORTED_IMAGE_TYPES:
                    raise PhotonError("unsupported_media")
                if mime_type == "image/png":
                    _static_png(attachment.data)
                elif mime_type in ("image/jpeg", "image/jpg"):
                    if not attachment.data.startswith(JPEG_SIGNATURE):
                        raise PhotonError("invalid_media_response")
                    mime_type = "image/jpeg"
                elif (not attachment.data.startswith(WEBP_RIFF)
                      or len(attachment.data) < 12
                      or attachment.data[8:12] != b"WEBP"):
                    raise PhotonError("invalid_media_response")
                event["sticker"] = {"mime_type": mime_type, "data_base64": base64.b64encode(attachment.data).decode("ascii"),
                                    "sha256": hashlib.sha256(attachment.data).hexdigest()}
            except PhotonError as error:
                if error.retryable or error.code not in MEDIA_ABSTENTIONS:
                    raise
                return NormalizedMessage(event, error.code)
            except TimeoutError:
                raise PhotonError("media_timeout", retryable=True) from None
            except Exception:
                raise PhotonError("media_fetch_failed", retryable=True) from None
            return NormalizedMessage(event)
        event["kind"] = media[0][1] if len(media) == 1 else "other"
        return NormalizedMessage(event)

    def receive_webhook(self, raw_body: bytes, headers: Mapping, on_message: Callable) -> IngressReceipt:
        if not isinstance(raw_body, bytes) or len(raw_body) > MAX_WEBHOOK_BYTES:
            return IngressReceipt("rejected", error_code="invalid_webhook_size")
        try:
            # Authenticate exact raw bytes before JSON parsing, decoding or media access.
            if self.verify_event(raw_body, headers) is not True:
                return IngressReceipt("rejected", error_code="authentication_failed")
        except Exception:
            return IngressReceipt("rejected", error_code="authentication_failed")
        try:
            envelope = _object(_json_load(raw_body))
            message = self.decode_event(envelope)
            if message is None:
                return IngressReceipt("ignored")
            normalized = self.normalize_message(message)
            if normalized.event is None:
                return IngressReceipt("ignored")
        except PhotonError as error:
            return IngressReceipt("rejected" if not error.retryable else "error", error_code=error.code, retryable=error.retryable)
        except Exception:
            return IngressReceipt("rejected", error_code="invalid_event")
        try:
            # Persistent deduplication belongs to the coordinator, including replay.
            on_message(normalized.event)
        except Exception:
            return IngressReceipt("error", error_code="coordinator_failed", retryable=True)
        trigger = "interpret_sticker" if normalized.event["kind"] == "sticker" else "history_only"
        return IngressReceipt("forwarded", trigger, normalized.event, normalized.warning)

    def send_private_explanation(self, delivery: Mapping) -> SendReceipt:
        key = None
        try:
            if not isinstance(delivery, Mapping) or set(delivery) != DELIVERY_FIELDS:
                raise PhotonError("invalid_delivery")
            for value in delivery.values():
                _identifier(value)
            # Pass a fresh copy; no model output, arbitrary destination or extra fields.
            route = self.resolve_destination(dict(delivery))
            if not isinstance(route, PrivateDestination) or route.verified is not True or route.kind != "direct":
                raise PhotonError("unauthorized_destination")
            if (route.recipient_id != delivery["recipient_id"] or route.source_conversation_id != delivery["source_conversation_id"]
                    or route.platform != self.platform or route.sender_id not in self.assistant_ids):
                raise PhotonError("destination_binding_mismatch")
            for value in (route.space_id, route.sender_id, route.recipient_user_id):
                _identifier(value)
            if route.sender_id == route.recipient_user_id or len(route.participant_ids) != 2 or set(route.participant_ids) != {route.sender_id, route.recipient_user_id}:
                raise PhotonError("destination_not_private")
            identity = [self.project_id, self.platform, delivery["source_conversation_id"], delivery["source_message_id"], delivery["recipient_id"]]
            key = "sticker-explanation:v2:" + hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()
            body = {"spaceId": route.space_id, "senderId": route.sender_id,
                    "content": {"type": "text", "format": "plain", "text": delivery["text"]}}
            # No source-chat parentMessageId: it may belong to a different space.
            response = _object(self.client.send_message(body, idempotency_key=key, timeout=self.timeout))
            message_id = _identifier(response.get("id"))
            status = response.get("status")
            if status not in ("accepted", "dispatched", "delivered"):
                raise PhotonError("invalid_send_acknowledgment")
            return SendReceipt("accepted", key, message_id, status)
        except PhotonError as error:
            return SendReceipt("error", key, error_code=error.code, retryable=error.retryable)
        except PermissionError:
            return SendReceipt("error", key, error_code="unauthorized_destination")
        except TimeoutError:
            return SendReceipt("error", key, error_code="send_timeout", retryable=True)
        except Exception:
            return SendReceipt("error", key, error_code="send_failed", retryable=True)


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    body: bytes
    headers: Mapping


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def urllib_transport(method, url, *, headers, body, max_bytes, timeout):
    """Explicit live transport; bounded reads, TLS defaults, no redirect of keys."""
    request = Request(url, data=body, headers=headers, method=method)
    try:
        response = build_opener(_NoRedirect()).open(request, timeout=timeout)
    except HTTPError as error:
        error.close()
        return HTTPResponse(error.code, b"", {})
    except (TimeoutError, URLError):
        raise PhotonError("provider_unavailable", retryable=True) from None
    with response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise PhotonError("response_too_large")
        return HTTPResponse(response.status, data, dict(response.headers))


class PhotonHTTPClient:
    """Small documented REST client; inject a fake transport for standalone tests."""

    def __init__(self, *, project_id, api_key, transport=urllib_transport):
        self.project_id = _identifier(project_id)
        self._api_key = _identifier(api_key)
        self.transport = transport
        self.base_url = "https://api.photon.codes/v1/projects/" + quote(project_id, safe="")

    def _request(self, method, path, *, max_bytes, timeout, body=None, key=None, expected_status=200):
        headers = {
            "Authorization": "Bearer " + self._api_key,
            "Accept": "application/json",
            "User-Agent": "lahacksai-sticker-interpreter/0.1",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        if key is not None:
            headers["idempotency-key"] = key
        try:
            result = self.transport(method, self.base_url + path, headers=headers,
                                    body=json.dumps(body).encode() if body is not None else None,
                                    max_bytes=max_bytes, timeout=timeout)
        except PhotonError:
            raise
        except Exception:
            raise PhotonError("provider_unavailable", retryable=True) from None
        if result.status != expected_status:
            raise PhotonError("provider_http_" + str(result.status), retryable=result.status in (408, 429, 500, 502, 503, 504))
        if not isinstance(result.body, bytes) or len(result.body) > max_bytes:
            raise PhotonError("response_too_large")
        return result

    def _json_response(self, method, path, *, max_bytes=1_000_000, timeout=10.0,
                       body=None, key=None, expected_status=200):
        try:
            return _object(_json_load(self._request(
                method, path, max_bytes=max_bytes, timeout=timeout, body=body,
                key=key, expected_status=expected_status,
            ).body))
        except PhotonError:
            raise
        except (ValueError, UnicodeError, TypeError):
            raise PhotonError("invalid_provider_response") from None

    def list_messages(self, *, created_since=None, page_token=None, page_size=100,
                      platform="imessage", direction="received", order="asc",
                      timeout=10.0):
        if type(page_size) is not int or not 1 <= page_size <= 200:
            raise ValueError("page_size must be 1-200")
        query = {
            "pageSize": str(page_size), "platform": _identifier(platform),
            "direction": _identifier(direction), "order": _identifier(order),
        }
        if created_since is not None:
            query["createdSince"] = _timestamp(created_since)
        if page_token is not None:
            query["pageToken"] = _identifier(page_token)
        page = self._json_response("GET", "/messages?" + urlencode(query), timeout=timeout)
        items = page.get("items")
        if not isinstance(items, list) or any(not isinstance(item, Mapping) for item in items):
            raise PhotonError("invalid_provider_response")
        token = page.get("nextPageToken")
        if token is None:
            token = page.get("nextCursor")
        if token is not None:
            _identifier(token)
        return {"items": [dict(item) for item in items], "nextPageToken": token}

    def get_message(self, message_id, *, timeout=10.0):
        message = self._json_response(
            "GET", "/messages/" + quote(_identifier(message_id), safe=""),
            max_bytes=256_000, timeout=timeout,
        )
        if (message.get("id") != message_id
                or message.get("projectId", self.project_id) != self.project_id):
            raise PhotonError("message_scope_mismatch")
        return dict(message)

    def get_imessage_platform(self, *, timeout=10.0):
        result = self._json_response(
            "GET", "/platforms/imessage", max_bytes=64_000, timeout=timeout,
        )
        if result.get("mode") not in ("shared", "dedicated"):
            raise PhotonError("invalid_provider_response")
        return dict(result)

    def fetch_attachment(self, attachment_id, *, max_bytes, timeout):
        path = "/attachments/" + quote(_identifier(attachment_id), safe="")
        try:
            metadata = _object(_json_load(self._request("GET", path, max_bytes=64_000, timeout=timeout).body))
        except (ValueError, UnicodeError):
            raise PhotonError("invalid_media_response") from None
        size = metadata.get("sizeBytes")
        if (metadata.get("id") != attachment_id
                or metadata.get("projectId", self.project_id) != self.project_id):
            raise PhotonError("media_scope_mismatch")
        if type(size) is not int or size <= 0 or size > max_bytes:
            raise PhotonError("media_too_large")
        metadata_type = str(metadata.get("contentType", "")).split(";", 1)[0].strip().lower()
        if metadata_type not in SUPPORTED_IMAGE_TYPES:
            raise PhotonError("unsupported_media")
        result = self._request("GET", path + "/content", max_bytes=max_bytes, timeout=timeout)
        content_type = next((v for k, v in result.headers.items() if k.lower() == "content-type"), "")
        response_type = content_type.split(";", 1)[0].strip().lower()
        if response_type != metadata_type or len(result.body) != size:
            raise PhotonError("invalid_media_response")
        return Attachment(result.body, "image/jpeg" if metadata_type == "image/jpg" else metadata_type)

    def send_message(self, body, *, idempotency_key, timeout):
        response = self._request("POST", "/messages", max_bytes=128_000, timeout=timeout, body=body, key=idempotency_key, expected_status=202)
        try:
            message = _object(_json_load(response.body))
            if (message.get("projectId", self.project_id) != self.project_id or _object(message.get("space")).get("id") != body["spaceId"]
                    or _object(message.get("sentBy")).get("id") != body["senderId"]):
                raise PhotonError("send_scope_mismatch")
            return message
        except (ValueError, UnicodeError):
            raise PhotonError("invalid_send_acknowledgment") from None
