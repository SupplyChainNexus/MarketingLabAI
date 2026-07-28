"""MarketingLabAI command-line application."""

import argparse
import sys

from app.cli.commands import (
    analyse_voice,
    create_brand_from_file,
    generate_campaign,
    list_brands,
    list_campaigns,
    list_voices,
    show_voice,
)
from app.health import run_health_check


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="MarketingLabAI",
        description="AI Marketing Operating System",
    )

    subparsers = parser.add_subparsers(
        dest="command",
    )

    health_parser = subparsers.add_parser(
        "health",
        help="Run system health checks.",
    )

    health_parser.add_argument(
        "--api",
        action="store_true",
        help="Include a live Gemini API test.",
    )

    brand_parser = subparsers.add_parser(
        "brand",
        help="Manage brand profiles.",
    )

    brand_subparsers = brand_parser.add_subparsers(
        dest="brand_command",
    )

    brand_create = brand_subparsers.add_parser(
        "create",
        help="Create a brand from a JSON file.",
    )

    brand_create.add_argument(
        "--file",
        required=True,
        help="Path to the brand JSON file.",
    )

    brand_subparsers.add_parser(
        "list",
        help="List saved brands.",
    )

    voice_parser = subparsers.add_parser(
        "voice",
        help="Manage brand voice profiles.",
    )

    voice_subparsers = voice_parser.add_subparsers(
        dest="voice_command",
    )

    voice_analyse = voice_subparsers.add_parser(
        "analyse",
        help="Analyse writing samples.",
    )

    voice_analyse.add_argument(
        "--brand-id",
        required=True,
    )

    voice_analyse.add_argument(
        "--samples-file",
        required=True,
    )

    voice_subparsers.add_parser(
        "list",
        help="List saved voice profiles.",
    )

    voice_show = voice_subparsers.add_parser(
        "show",
        help="Display a saved voice profile.",
    )

    voice_show.add_argument(
        "--voice-id",
        required=True,
    )

    campaign_parser = subparsers.add_parser(
        "campaign",
        help="Generate and manage campaigns.",
    )

    campaign_subparsers = campaign_parser.add_subparsers(
        dest="campaign_command",
    )

    campaign_generate = campaign_subparsers.add_parser(
        "generate",
        help="Generate marketing content.",
    )

    campaign_generate.add_argument(
        "--brand-id",
        required=True,
    )

    campaign_generate.add_argument(
        "--voice-id",
        required=True,
    )

    campaign_generate.add_argument(
        "--brief-file",
        required=True,
    )

    campaign_subparsers.add_parser(
        "list",
        help="List saved campaign records.",
    )

    return parser


def run_command(args: argparse.Namespace) -> None:
    if args.command == "health":
        run_health_check(include_api_test=args.api)
        return

    if args.command == "brand":
        if args.brand_command == "create":
            create_brand_from_file(args.file)
            return

        if args.brand_command == "list":
            list_brands()
            return

    if args.command == "voice":
        if args.voice_command == "analyse":
            analyse_voice(
                brand_id=args.brand_id,
                samples_file=args.samples_file,
            )
            return

        if args.voice_command == "list":
            list_voices()
            return

        if args.voice_command == "show":
            show_voice(args.voice_id)
            return

    if args.command == "campaign":
        if args.campaign_command == "generate":
            generate_campaign(
                brand_id=args.brand_id,
                voice_id=args.voice_id,
                brief_file=args.brief_file,
            )
            return

        if args.campaign_command == "list":
            list_campaigns()
            return

    raise ValueError("No valid command was selected. " "Run: python -m app.main --help")


def main() -> None:
    parser = build_parser()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()

    try:
        run_command(args)
    except Exception as error:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
