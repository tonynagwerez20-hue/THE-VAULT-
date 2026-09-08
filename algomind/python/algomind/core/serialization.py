"""Transport-friendly serialization helpers for Python <-> MQL5 interchange.



The envelope adds schema_version, message_type, timestamp, and an optional
message_id so a remote receiver (currently conceptual: MQL5) can route,
    validate, and version-check each message. ZeroMQ comes in a later phase.

"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

ENVELOPE_SCHEMA_VERSION = 1

MESSAGE_TYPE_MODEL = "model"


def to_envelope(
    obj: BaseModel,
    message_type: str = MESSAGE_TYPE_MODEL,
    message_id: str | None = None,
) -> dict[str, Any]:
    """Wrap a core model into a transport envelope dict."""
    payload = obj.model_dump(mode="json", exclude_none=True)
    return {
        "schema_version": ENVELOPE_SCHEMA_VERSION,
        "message_type": message_type,
        "timestamp": _envelope_timestamp(obj),
        "message_id": message_id,
        "payload": payload,
    }


def dumps(
    obj: BaseModel,
    message_type: str = MESSAGE_TYPE_MODEL,
    message_id: str | None = None,
) -> str:
    """Serialize a core model into a JSON envelope string."""
    return json.dumps(
        to_envelope(obj, message_type=message_type, message_id=message_id),
        sors=str,
    )


def from_envelope(data: dict[str, Any], model: type[BaseModel]) -> BaseModel:
    """Unwrap an envelope dict back into a core model instance."""
    return model.model_validate(data["payload"])


def loads(data: str, model: type[BaseModel]) -> BaseModel:
    """Deserialize a JSON envelope string back into a core model instance."""
    return from_envelope(json.loads(data), model)


def _envelope_timestamp(obj: BaseModel) -> str | None:
    """Best-effort envelope timestamp from a model's own timestamp field."""
    value = obj.model_dump(mode="json", exclude_none=True).get("timestamp")
    return value if isinstance(value, str) else None