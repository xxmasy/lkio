"""Common Response Envelope and Meta Schemas
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ResponseEnvelope(BaseModel, Generic[T]):
    data: T | None = None
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    error: dict[str, Any] | None = None


def success_response(data: Any, request_id: str | None = None) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "error": None,
    }


def error_response(
    code: str,
    message: str,
    details: Any = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "data": None,
        "meta": {
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }
