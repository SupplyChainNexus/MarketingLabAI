"""Tests for campaign persistence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.campaigns.campaign_service import CampaignService
from app.config import Settings
from app.models import GeneratedContent


class CampaignServiceTests(unittest.TestCase):
    @staticmethod
    def create_settings(
        root: Path,
    ) -> Settings:
        return Settings(
            project_root=root,
            gemini_api_key="test-key",
            gemini_model="test-model",
            database_folder=root / "database",
            output_folder=root / "outputs",
            assets_folder=root / "assets",
            prompts_folder=root / "prompts",
        )

    def test_saves_generated_content(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = CampaignService(self.create_settings(root))

            generated = GeneratedContent(
                campaign_id="campaign-1",
                platform="Facebook",
                content_type="Post",
                content="Generated test content.",
                provider="mock",
                model="test-model",
                input_tokens=12,
                output_tokens=24,
                finish_reason="stop",
                metadata={
                    "request_id": "request-1",
                },
            )

            path = service.save_generated_content(generated)

            saved_content = path.read_text(encoding="utf-8")

            self.assertTrue(path.exists())
            self.assertIn(
                "Generated test content.",
                saved_content,
            )
            self.assertIn(
                "Provider: mock",
                saved_content,
            )
            self.assertIn(
                "Model: test-model",
                saved_content,
            )
            self.assertIn(
                "Input tokens: 12",
                saved_content,
            )
            self.assertIn(
                "Output tokens: 24",
                saved_content,
            )
            self.assertIn(
                "Finish reason: stop",
                saved_content,
            )

    def test_saves_unknown_token_usage_cleanly(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = CampaignService(self.create_settings(root))

            generated = GeneratedContent(
                campaign_id="campaign-1",
                platform="Facebook",
                content_type="Post",
                content="Generated test content.",
                model="test-model",
            )

            path = service.save_generated_content(generated)

            saved_content = path.read_text(encoding="utf-8")

            self.assertIn(
                "Provider: Not recorded",
                saved_content,
            )
            self.assertIn(
                "Input tokens: Unknown",
                saved_content,
            )
            self.assertIn(
                "Output tokens: Unknown",
                saved_content,
            )


if __name__ == "__main__":
    unittest.main()
