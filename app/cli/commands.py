"""Command handlers for MarketingLabAI workflows."""

import json

from app.brands.brand_service import BrandService
from app.campaigns.campaign_engine import CampaignEngine
from app.campaigns.campaign_service import CampaignService
from app.models import BrandProfile, CampaignBrief
from app.services.input_files import (
    read_json_file,
    read_writing_samples,
)
from app.voices.voice_engine import VoiceEngine


def create_brand_from_file(file_path: str) -> None:
    """Create and save a brand profile from JSON."""

    data = read_json_file(file_path)
    brand = BrandProfile(**data)

    service = BrandService()
    service.save_brand(brand)

    print("Brand saved successfully")
    print(f"Brand ID: {brand.brand_id}")
    print(f"Brand name: {brand.name}")


def list_brands() -> None:
    """List all saved brand IDs."""

    brand_ids = BrandService().list_brand_ids()

    if not brand_ids:
        print("No brands have been saved.")
        return

    print("Saved brands:")

    for brand_id in brand_ids:
        print(f"- {brand_id}")


def analyse_voice(
    brand_id: str,
    samples_file: str,
) -> None:
    """Analyse writing samples and save a voice profile."""

    brand = BrandService().get_brand(brand_id)
    samples = read_writing_samples(samples_file)

    print(f"Analysing {len(samples)} writing sample(s) " f"for {brand.name}...")

    voice = VoiceEngine().analyse_voice(
        brand,
        samples,
    )

    print("Voice profile created successfully")
    print(f"Voice ID: {voice.voice_id}")
    print(f"Brand ID: {voice.brand_id}")
    print(f"Summary: {voice.summary}")
    print("Tone traits: " + ", ".join(voice.tone_traits))


def list_voices() -> None:
    """List all saved voice-profile IDs."""

    voice_ids = VoiceEngine().list_voice_ids()

    if not voice_ids:
        print("No voice profiles have been saved.")
        return

    print("Saved voice profiles:")

    for voice_id in voice_ids:
        print(f"- {voice_id}")


def show_voice(voice_id: str) -> None:
    """Display a saved voice profile."""

    voice = VoiceEngine().get_voice(voice_id)

    print(
        json.dumps(
            voice.to_dict(),
            indent=2,
            ensure_ascii=False,
        )
    )


def generate_campaign(
    brand_id: str,
    voice_id: str,
    brief_file: str,
) -> None:
    """Generate and save campaign content."""

    brand_service = BrandService()
    voice_engine = VoiceEngine()
    campaign_service = CampaignService()

    brand = brand_service.get_brand(brand_id)
    voice = voice_engine.get_voice(voice_id)

    brief_data = read_json_file(brief_file)
    brief = CampaignBrief(**brief_data)

    if brief.brand_id != brand_id:
        raise ValueError(
            "The campaign brief brand_id does not match " "the supplied brand ID."
        )

    campaign_service.save_brief(brief)

    print(f"Generating {brief.content_type} for " f"{brief.platform}...")

    generated = CampaignEngine().generate_campaign_content(
        brand=brand,
        voice=voice,
        brief=brief,
    )

    output_path = campaign_service.save_generated_content(generated)

    print("")
    print("Generated content")
    print("-----------------")
    print(generated.content)
    print("-----------------")
    print(f"Saved to: {output_path}")


def list_campaigns() -> None:
    """List saved campaign records."""

    records = CampaignService().list_campaign_records()

    if not records:
        print("No campaign records have been saved.")
        return

    print("Saved campaign records:")

    for record in records:
        print(f"- {record}")
