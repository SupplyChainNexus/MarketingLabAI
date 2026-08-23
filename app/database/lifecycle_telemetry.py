"""Privacy-safe, best-effort database lifecycle telemetry contracts."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

MonotonicClock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class DatabaseLifecycleEvent:
    """One allowlisted database lifecycle observation."""

    name: str
    backend: str
    operation_type: str
    target_migration_version: int
    target_fingerprint: str
    observed_version: int | None = None
    duration_ms: int | None = None
    wait_duration_ms: int | None = None
    failure_category: str | None = None
    retry_ordinal: int = 0


class DatabaseLifecycleEventSink(Protocol):
    """Injected consumer for privacy-safe database lifecycle events."""

    def emit(self, event: DatabaseLifecycleEvent) -> None: ...


class NullDatabaseLifecycleEventSink:
    """Default sink that deliberately performs no work."""

    def emit(self, event: DatabaseLifecycleEvent) -> None:
        del event


def monotonic_clock() -> float:
    return time.monotonic()


def target_fingerprint(value: str, *, length: int = 16) -> str:
    """Return a bounded opaque target correlation value."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
