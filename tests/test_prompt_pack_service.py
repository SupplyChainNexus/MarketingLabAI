"""Tests for the Prompt Pack business workflow service."""

from __future__ import annotations

import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.prompts.models import PromptPack
from app.prompts.renderer import PromptPackRenderer
from app.prompts.repository import PromptPackRepository
from app.prompts.selector import PromptPackSelector
from app.prompts.service import (
    PromptPackService,
    RenderedPrompt,
)


class PromptPackServiceTests(unittest.TestCase):
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
        system_instruction: str = ("Write clear and trustworthy " "marketing content."),
    ) -> PromptPack:
        return PromptPack(
            prompt_pack_id=prompt_pack_id,
            tenant_id="default",
            brand_id=brand_id,
            name="Social Post",
            task_type="social_post",
            channel="facebook",
            template=("Create a Facebook post about " "{topic} for {audience}."),
            system_instruction=system_instruction,
            variables=[
                "topic",
                "audience",
            ],
            enabled=enabled,
            version=version,
        )

    def test_service_selects_and_renders_pack(
        self,
    ) -> None:
        self.repository.save(self.create_pack())

        result = self.service.render(
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
        self.assertEqual(
            result.prompt_pack_id,
            "social-post",
        )
        self.assertEqual(
            result.version,
            1,
        )

    def test_result_contains_audit_metadata(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id=("facebook-organic"),
                version=2,
            )
        )

        result = self.service.render(
            tenant_id="default",
            task_type="social_post",
            channel="facebook",
            prompt_pack_id=("facebook-organic"),
            values={
                "topic": "inventory management",
                "audience": "small businesses",
            },
        )

        self.assertEqual(
            result.system_instruction,
            ("Write clear and trustworthy " "marketing content."),
        )
        self.assertEqual(
            result.prompt_pack_id,
            "facebook-organic",
        )
        self.assertEqual(
            result.version,
            2,
        )
        self.assertEqual(
            result.tenant_id,
            "default",
        )
        self.assertIsNone(result.brand_id)
        self.assertEqual(
            result.task_type,
            "social_post",
        )
        self.assertEqual(
            result.channel,
            "facebook",
        )

    def test_service_prefers_brand_specific_pack(
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

        result = self.service.render(
            tenant_id="default",
            brand_id="brand-one",
            task_type="social_post",
            channel="facebook",
            values={
                "topic": "customer service",
                "audience": "workshops",
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

    def test_service_uses_latest_enabled_version(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                version=1,
                enabled=True,
            )
        )
        self.repository.save(
            self.create_pack(
                version=2,
                enabled=True,
            )
        )

        result = self.service.render(
            tenant_id="default",
            task_type="social_post",
            channel="facebook",
            values={
                "topic": "stock availability",
                "audience": "panel beaters",
            },
        )

        self.assertEqual(
            result.version,
            2,
        )

    def test_service_does_not_select_disabled_latest_version(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                version=1,
                enabled=True,
            )
        )
        self.repository.save(
            self.create_pack(
                version=2,
                enabled=False,
            )
        )

        with self.assertRaises(FileNotFoundError):
            self.service.render(
                tenant_id="default",
                task_type="social_post",
                channel="facebook",
                values={
                    "topic": "stock availability",
                    "audience": "panel beaters",
                },
            )

    def test_service_propagates_missing_pack_error(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError,
            "No enabled Prompt Pack",
        ):
            self.service.render(
                tenant_id="default",
                task_type="email",
                channel="email",
                values={},
            )

    def test_service_propagates_rendering_error(
        self,
    ) -> None:
        self.repository.save(self.create_pack())

        with self.assertRaisesRegex(
            ValueError,
            "Missing prompt values: audience",
        ):
            self.service.render(
                tenant_id="default",
                task_type="social_post",
                channel="facebook",
                values={
                    "topic": "new products",
                },
            )

    def test_service_rejects_non_mapping_values(
        self,
    ) -> None:
        invalid_values = cast(
            Mapping[str, Any],
            [],
        )

        with self.assertRaisesRegex(
            TypeError,
            "mapping",
        ):
            self.service.render(
                tenant_id="default",
                task_type="social_post",
                values=invalid_values,
            )

    def test_service_rejects_invalid_selector(
        self,
    ) -> None:
        invalid_selector = cast(
            PromptPackSelector,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "PromptPackSelector",
        ):
            PromptPackService(invalid_selector)

    def test_service_rejects_invalid_renderer(
        self,
    ) -> None:
        invalid_renderer = cast(
            PromptPackRenderer,
            object(),
        )

        with self.assertRaisesRegex(
            TypeError,
            "PromptPackRenderer",
        ):
            PromptPackService(
                self.selector,
                renderer=invalid_renderer,
            )


class RenderedPromptTests(unittest.TestCase):
    def test_result_is_immutable(
        self,
    ) -> None:
        result = RenderedPrompt(
            content="Rendered content",
            system_instruction="Be accurate.",
            prompt_pack_id="pack-one",
            version=1,
            tenant_id="default",
            brand_id=None,
            task_type="social_post",
            channel="facebook",
        )

        with self.assertRaises(
            (
                AttributeError,
                TypeError,
            )
        ):
            result.content = "Changed"  # type: ignore[misc]

    def test_result_rejects_blank_content(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "content",
        ):
            RenderedPrompt(
                content=" ",
                system_instruction="",
                prompt_pack_id="pack-one",
                version=1,
                tenant_id="default",
                brand_id=None,
                task_type="social_post",
                channel="facebook",
            )

    def test_result_rejects_blank_prompt_pack_id(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "prompt_pack_id",
        ):
            RenderedPrompt(
                content="Rendered content",
                system_instruction="",
                prompt_pack_id=" ",
                version=1,
                tenant_id="default",
                brand_id=None,
                task_type="social_post",
                channel="facebook",
            )

    def test_result_rejects_invalid_version(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "version",
        ):
            RenderedPrompt(
                content="Rendered content",
                system_instruction="",
                prompt_pack_id="pack-one",
                version=0,
                tenant_id="default",
                brand_id=None,
                task_type="social_post",
                channel="facebook",
            )

    def test_result_rejects_blank_tenant_id(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "tenant_id",
        ):
            RenderedPrompt(
                content="Rendered content",
                system_instruction="",
                prompt_pack_id="pack-one",
                version=1,
                tenant_id=" ",
                brand_id=None,
                task_type="social_post",
                channel="facebook",
            )

    def test_result_rejects_blank_task_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "task_type",
        ):
            RenderedPrompt(
                content="Rendered content",
                system_instruction="",
                prompt_pack_id="pack-one",
                version=1,
                tenant_id="default",
                brand_id=None,
                task_type=" ",
                channel="facebook",
            )


if __name__ == "__main__":
    unittest.main()
