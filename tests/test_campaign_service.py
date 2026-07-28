"""Tests for campaign persistence."""

import tempfile
import unittest
from pathlib import Path

from app.campaigns.campaign_service import CampaignService
from app.config import Settings
from app.models import GeneratedContent


class CampaignServiceTests(unittest.TestCase):

    def test_saves_generated_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            settings = Settings(
                project_root=root,
                gemini_api_key="test-key",
                gemini_model="test-model",
                database_folder=root / "database",
                output_folder=root / "outputs",
                assets_folder=root / "assets",
                prompts_folder=root / "prompts",
            )

            service = CampaignService(settings)

            generated = GeneratedContent(
                campaign_id="campaign-1",
                platform="Facebook",
                content_type="Post",
                content="Generated test content.",
                model="test-model",
            )

            path = service.save_generated_content(generated)

            self.assertTrue(path.exists())
            self.assertIn(
                "Generated test content.",
                path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
