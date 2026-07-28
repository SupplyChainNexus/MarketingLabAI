"""Utilities for reading structured workflow input files."""

import json
from pathlib import Path
from typing import Any


def read_json_file(file_path: str | Path) -> dict[str, Any]:
    """Read and validate a JSON object from a file."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {path}: {error.msg}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a JSON object in {path}."
        )

    return data


def read_writing_samples(file_path: str | Path) -> list[str]:
    """
    Read writing samples separated by a line containing three hyphens.

    Example:

    First writing sample.

    ---

    Second writing sample.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Writing-samples file not found: {path}"
        )

    text = path.read_text(encoding="utf-8-sig")

    samples = [
        section.strip()
        for section in text.split("\n---\n")
        if section.strip()
    ]

    if not samples:
        raise ValueError(
            "The writing-samples file contains no usable samples."
        )

    return samples
