"""Atomic, integrity-checked external state for release orchestration."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import AbstractContextManager
from pathlib import Path
from typing import IO, Mapping


def canonical_json(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json_atomic(path: Path, value: Mapping[str, object]) -> str:
    """Write canonical JSON and its digest through same-directory replacements."""

    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    digest = sha256_bytes(encoded)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary_hash = temporary.with_suffix(temporary.suffix + ".sha256")
    final_hash = path.with_suffix(path.suffix + ".sha256")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        with temporary_hash.open("x", encoding="ascii", newline="\n") as stream:
            stream.write(digest + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.replace(temporary_hash, final_hash)
    finally:
        for candidate in (temporary, temporary_hash):
            if candidate.exists():
                candidate.unlink()
    return digest


def read_json_verified(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"Required release-control record is missing: {path}")
    digest_path = path.with_suffix(path.suffix + ".sha256")
    if not digest_path.is_file():
        raise ValueError(f"Release-control digest is missing: {digest_path}")
    encoded = path.read_bytes()
    expected = digest_path.read_text(encoding="ascii").strip()
    actual = sha256_bytes(encoded)
    if expected != actual:
        raise ValueError(f"Release-control record has been modified: {path}")
    value = json.loads(encoded)
    if not isinstance(value, dict):
        raise ValueError(f"Release-control record must be an object: {path}")
    return value


class RunLock(AbstractContextManager["RunLock"]):
    """Cross-platform process lock released automatically on interruption."""

    def __init__(self, path: Path):
        self.path = path
        self.stream: IO[bytes] | None = None

    def __enter__(self) -> "RunLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                self.stream.seek(0)
                if self.stream.read(1) == b"":
                    self.stream.write(b"0")
                    self.stream.flush()
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as error:
            self.stream.close()
            self.stream = None
            raise ValueError(
                "Another release-control operation is active; inspect status and resume."
            ) from error
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.stream is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        finally:
            self.stream.close()
            self.stream = None
