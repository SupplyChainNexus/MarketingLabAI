"""MarketingLabAI command-line entry point."""

import argparse

from app.health import run_health_check


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="MarketingLabAI",
        description="AI Marketing Operating System",
    )

    parser.add_argument(
        "--health",
        action="store_true",
        help="Run the local application health check.",
    )

    parser.add_argument(
        "--api-test",
        action="store_true",
        help="Include a live Gemini API request in the health check.",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.health or args.api_test:
        run_health_check(include_api_test=args.api_test)
        return

    print("MarketingLabAI")
    print("Run: python -m app.main --health")


if __name__ == "__main__":
    main()
