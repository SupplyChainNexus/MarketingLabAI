"""Bounded Waitress entry point for the controlled Cloud Run container."""

from __future__ import annotations

import os

from waitress import serve

from app.operations.runtime import create_application


def configured_port(values: dict[str, str] | None = None) -> int:
    """Return Cloud Run's bounded port without accepting arbitrary listeners."""

    selected = os.environ if values is None else values
    try:
        port = int(str(selected.get("PORT", "8080")))
    except ValueError as error:
        raise ValueError("PORT must be an integer.") from error
    if not 1024 <= port <= 65535:
        raise ValueError("PORT must be between 1024 and 65535.")
    return port


def main() -> None:
    """Serve exactly one canonical application on the Cloud Run listener."""

    serve(
        create_application(),
        host="0.0.0.0",
        port=configured_port(),
        threads=4,
        clear_untrusted_proxy_headers=True,
    )


if __name__ == "__main__":
    main()
