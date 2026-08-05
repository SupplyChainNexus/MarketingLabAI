"""Structured event logging that excludes secrets and customer content."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any


class PrivacySafeJsonLogger:
    _FORBIDDEN = {
        "authorization",
        "content",
        "credential",
        "instructions",
        "prompt",
        "secret",
        "session",
        "token",
    }

    def __init__(self, writer: Callable[[str], None] = print) -> None:
        self.writer = writer

    def emit(self, event: str, **metadata: Any) -> str:
        if not isinstance(event, str) or not event.strip():
            raise ValueError("event is required.")
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event.strip(),
            **self._sanitize(metadata),
        }
        line = json.dumps(
            payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        self.writer(line)
        return line

    @classmethod
    def _sanitize(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            safe: dict[str, Any] = {}
            for key, item in value.items():
                name = str(key)
                if any(term in name.lower() for term in cls._FORBIDDEN):
                    safe[name] = "[REDACTED]"
                else:
                    safe[name] = cls._sanitize(item)
            return safe
        if isinstance(value, (list, tuple)):
            return [cls._sanitize(item) for item in value]
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        return str(value)
