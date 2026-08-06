"""Structured event logging that excludes secrets and customer content."""

from __future__ import annotations

import json
from collections import Counter
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


class OperationalSignalMonitor:
    """Count privacy-safe operational signals and expose deterministic alerts."""

    SIGNALS = (
        "readiness_failure",
        "authentication_failure",
        "rate_limit_rejection",
        "database_integrity_failure",
        "backup_failure",
        "server_error",
    )

    def __init__(self, thresholds: Mapping[str, int] | None = None) -> None:
        selected = dict(thresholds or {name: 1 for name in self.SIGNALS})
        if set(selected) != set(self.SIGNALS):
            raise ValueError("Thresholds must cover every operational signal.")
        if any(not isinstance(value, int) or value < 1 for value in selected.values()):
            raise ValueError("Operational signal thresholds must be positive integers.")
        self.thresholds = selected
        self.counts: Counter[str] = Counter()

    def observe(self, signal: str) -> None:
        if signal not in self.SIGNALS:
            raise ValueError(f"Unsupported operational signal: {signal}")
        self.counts[signal] += 1

    def snapshot(self) -> dict[str, dict[str, int | bool]]:
        return {
            name: {
                "count": self.counts[name],
                "threshold": self.thresholds[name],
                "alerting": self.counts[name] >= self.thresholds[name],
            }
            for name in self.SIGNALS
        }
