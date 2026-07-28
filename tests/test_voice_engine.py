"""Tests for Voice Engine prompt construction."""

import unittest

from app.models import BrandProfile
from app.voices.voice_engine import VoiceEngine


class FakeGeminiClient:
    """Test replacement that makes no external API calls."""

    settings = None

    def generate_text(self, prompt: str) -> str:
        return prompt


class VoiceEngineTests(unittest.TestCase):

    def setUp(self):
        self.brand = BrandProfile(
            brand_id="strand-auto-parts",
            name="Strand Auto Parts",
            industry="Automotive replacement parts",
            description="Supplier of automotive body and mechanical parts.",
            target_audience="Panel beaters, workshops, and vehicle owners",
            values=["reliability", "service", "product knowledge"],
        )

    def test_prompt_contains_brand_information(self):
        engine = VoiceEngine(
            gemini_client=FakeGeminiClient()
        )

        prompt = engine.build_analysis_prompt(
            self.brand,
            ["Quality parts supported by knowledgeable service."],
        )

        self.assertIn("Strand Auto Parts", prompt)
        self.assertIn("Quality parts", prompt)
        self.assertIn("Do not invent", prompt)

    def test_requires_writing_sample(self):
        engine = VoiceEngine(
            gemini_client=FakeGeminiClient()
        )

        with self.assertRaises(ValueError):
            engine.build_analysis_prompt(self.brand, [])


if __name__ == "__main__":
    unittest.main()
