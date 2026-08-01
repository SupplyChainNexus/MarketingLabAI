"""Tests for the public Prompt Engine façade."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import cast

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.prompts.engine import PromptEngine
from app.prompts.models import PromptPack
from app.prompts.repository import PromptPackRepository
from app.prompts.selector import PromptPackSelector
from app.prompts.service import (
    PromptPackService,
    RenderedPrompt,
)


class PromptEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()

        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.brands = BrandRepository(self.database)
        self.repository = PromptPackRepository(self.database)
        self.selector = PromptPackSelector(self.repository)
        self.service = PromptPackService(self.selector)
        self.engine = PromptEngine(self.service)

        self.brands.save(
            {
                "brand_id": "brand-one",
                "tenant_id": "default",
                "name": "Brand One",
            }
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def create_pack(
        *,
        prompt_pack_id: str = "social-post",
        brand_id: str | None = None,
        version: int = 1,
        enabled: bool = True,
    ) -> PromptPack:
        return PromptPack(
            prompt_pack_id=prompt_pack_id,
            tenant_id="default",
            brand_id=brand_id,
            name="Social Post",
            task_type="social_post",
            channel="facebook",
            template=("Create a Facebook post about " "{topic} for {audience}."),
            system_instruction=("Write accurate and trustworthy " "marketing content."),
            variables=[
                "topic",
                "audience",
            ],
            enabled=enabled,
            version=version,
        )

    def test_engine_renders_prompt(self) -> None:
        self.repository.save(self.create_pack())

        result = self.engine.render(
            tenant_id="default",
            task_type="social_post",
            channel="facebook",
            values={
                "topic": "delivery reliability",
                "audience": "retailers",
            },
        )

        self.assertEqual(
            result.content,
            ("Create a Facebook post about " "delivery reliability for retailers."),
        )

    def test_engine_returns_rendered_prompt(
        self,
    ) -> None:
        self.repository.save(self.create_pack())

        result = self.engine.render(
            tenant_id="default",
            task_type="social_post",
            channel="facebook",
            values={
                "topic": "new products",
                "audience": "workshops",
            },
        )

        self.assertIsInstance(
            result,
            RenderedPrompt,
        )
        self.assertEqual(
            result.prompt_pack_id,
            "social-post",
        )
        self.assertEqual(
            result.version,
            1,
        )
        self.assertEqual(
            result.tenant_id,
            "default",
        )
        self.assertEqual(
            result.system_instruction,
            ("Write accurate and trustworthy " "marketing content."),
        )

    def test_engine_supports_brand_override(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id="tenant-pack",
            )
        )
        self.repository.save(
            self.create_pack(
                prompt_pack_id="brand-pack",
                brand_id="brand-one",
            )
        )

        result = self.engine.render(
            tenant_id="default",
            brand_id="brand-one",
            task_type="social_post",
            channel="facebook",
            values={
                "topic": "stock availability",
                "audience": "panel beaters",
            },
        )

        self.assertEqual(
            result.prompt_pack_id,
            "brand-pack",
        )
        self.assertEqual(
            result.brand_id,
            "brand-one",
        )

    def test_engine_uses_latest_enabled_version(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                version=1,
            )
        )
        self.repository.save(
            self.create_pack(
                version=2,
            )
        )

        result = self.engine.render(
            tenant_id="default",
            task_type="social_post",
            channel="facebook",
            values={
                "topic": "customer retention",
                "audience": "retailers",
            },
        )

        self.assertEqual(
            result.version,
            2,
        )

    def test_engine_can_select_exact_pack(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id="facebook-one",
            )
        )
        self.repository.save(
            self.create_pack(
                prompt_pack_id="facebook-two",
            )
        )

        result = self.engine.render(
            tenant_id="default",
            task_type="social_post",
            channel="facebook",
            prompt_pack_id="facebook-two",
            values={
                "topic": "inventory planning",
                "audience": "small businesses",
            },
        )

        self.assertEqual(
            result.prompt_pack_id,
            "facebook-two",
        )

    def test_engine_propagates_missing_prompt(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError,
            "No enabled Prompt Pack",
        ):
            self.engine.render(
                tenant_id="default",
                task_type="email",
                channel="email",
                values={},
            )

    def test_engine_propagates_rendering_error(
        self,
    ) -> None:
        self.repository.save(self.create_pack())

        with self.assertRaisesRegex(
            ValueError,
            "Missing prompt values: audience",
        ):
            self.engine.render(
                tenant_id="default",
                task_type="social_post",
                channel="facebook",
                values={
                    "topic": "new products",
                },
            )

    def test_engine_rejects_invalid_service(
        self,
    ) -> None:
        invalid_service = cast(
            PromptPackService,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "PromptPackService",
        ):
            PromptEngine(invalid_service)


if __name__ == "__main__":
    unittest.main()
