"""Brand Voice Engine for MarketingLabAI."""

import json
from typing import Any
from uuid import uuid4

from app.ai.gemini_client import GeminiClient, get_gemini_client
from app.config import Settings, load_settings
from app.models import BrandProfile, VoiceProfile
from app.services.json_storage import JsonStorage

VOICE_ANALYSIS_SYSTEM_RULES = """
You are the MarketingLabAI Voice Engine.

Analyse supplied writing samples and identify the authentic communication
style demonstrated by the evidence.

Rules:

1. Preserve the organisation's natural communication style.
2. Do not invent personal experiences, customer stories, credentials,
   statistics, awards, testimonials, partnerships, or business results.
3. Do not claim that the brand experienced something unless the supplied
   material explicitly proves it.
4. Separate observed writing patterns from unsupported assumptions.
5. Return valid JSON only.
6. Do not include Markdown code fences.
""".strip()


class VoiceEngine:
    """Analyse writing samples and store reusable voice profiles."""

    def __init__(
        self,
        settings: Settings | None = None,
        gemini_client: GeminiClient | None = None,
    ):
        self.settings = settings or load_settings()
        self.gemini_client = gemini_client or get_gemini_client()

        self.storage = JsonStorage(self.settings.database_folder / "voices")

    def build_analysis_prompt(
        self,
        brand: BrandProfile,
        writing_samples: list[str],
    ) -> str:
        cleaned_samples = [
            sample.strip() for sample in writing_samples if sample and sample.strip()
        ]

        if not cleaned_samples:
            raise ValueError("At least one writing sample is required.")

        samples_text = "\n\n".join(
            f"SAMPLE {index + 1}:\n{sample}"
            for index, sample in enumerate(cleaned_samples)
        )

        return f"""
{VOICE_ANALYSIS_SYSTEM_RULES}

BRAND INFORMATION

Name: {brand.name}
Industry: {brand.industry}
Description: {brand.description}
Target audience: {brand.target_audience}
Values: {", ".join(brand.values) or "Not supplied"}

WRITING SAMPLES

{samples_text}

Analyse only the evidence contained in the writing samples.

Return exactly this JSON structure:

{{
  "summary": "A concise description of the voice",
  "tone_traits": ["trait 1", "trait 2"],
  "preferred_words": ["word or phrase"],
  "avoided_words": ["word or phrase"],
  "sentence_style": "Description of sentence structure and rhythm",
  "call_to_action_style": "Description of CTA style",
  "authenticity_rules": [
    "Rule preventing unsupported or fabricated claims"
  ]
}}
""".strip()

    @staticmethod
    def parse_analysis_response(
        response_text: str,
    ) -> dict[str, Any]:
        """Parse JSON even if the model adds a Markdown fence."""

        cleaned = response_text.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines:
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Gemini returned invalid JSON during voice analysis."
            ) from error

        if not isinstance(data, dict):
            raise RuntimeError("Voice analysis must return a JSON object.")

        return data

    @staticmethod
    def validate_analysis_data(
        data: dict[str, Any],
    ) -> None:
        required_fields = {
            "summary",
            "tone_traits",
            "preferred_words",
            "avoided_words",
            "sentence_style",
            "call_to_action_style",
            "authenticity_rules",
        }

        missing_fields = required_fields.difference(data)

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))

            raise RuntimeError(
                "Voice analysis is missing required fields: " f"{missing}"
            )

        list_fields = (
            "tone_traits",
            "preferred_words",
            "avoided_words",
            "authenticity_rules",
        )

        for field_name in list_fields:
            if not isinstance(data[field_name], list):
                raise RuntimeError(f"Voice field must be a list: {field_name}")

    def analyse_voice(
        self,
        brand: BrandProfile,
        writing_samples: list[str],
    ) -> VoiceProfile:
        prompt = self.build_analysis_prompt(
            brand,
            writing_samples,
        )

        response_text = self.gemini_client.generate_text(prompt)

        data = self.parse_analysis_response(response_text)

        self.validate_analysis_data(data)

        voice = VoiceProfile(
            voice_id=f"voice-{uuid4().hex[:12]}",
            brand_id=brand.brand_id,
            summary=str(data["summary"]).strip(),
            tone_traits=[
                str(item).strip() for item in data["tone_traits"] if str(item).strip()
            ],
            preferred_words=[
                str(item).strip()
                for item in data["preferred_words"]
                if str(item).strip()
            ],
            avoided_words=[
                str(item).strip() for item in data["avoided_words"] if str(item).strip()
            ],
            sentence_style=str(data["sentence_style"]).strip(),
            call_to_action_style=str(data["call_to_action_style"]).strip(),
            authenticity_rules=[
                str(item).strip()
                for item in data["authenticity_rules"]
                if str(item).strip()
            ],
        )

        self.storage.save(
            voice.voice_id,
            voice.to_dict(),
        )

        return voice

    def save_voice(
        self,
        voice: VoiceProfile,
    ) -> VoiceProfile:
        self.storage.save(
            voice.voice_id,
            voice.to_dict(),
        )
        return voice

    def get_voice(
        self,
        voice_id: str,
    ) -> VoiceProfile:
        return VoiceProfile(**self.storage.load(voice_id))

    def list_voice_ids(self) -> list[str]:
        return self.storage.list_records()
