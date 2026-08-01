"""Tests for deterministic Prompt Pack selection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.prompts.models import PromptPack
from app.prompts.repository import PromptPackRepository
from app.prompts.selector import PromptPackSelector


class PromptPackSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.brands = BrandRepository(self.database)
        self.repository = PromptPackRepository(self.database)
        self.selector = PromptPackSelector(self.repository)

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
        prompt_pack_id: str,
        brand_id: str | None = None,
        task_type: str = "social_post",
        channel: str = "facebook",
        enabled: bool = True,
        version: int = 1,
    ) -> PromptPack:
        return PromptPack(
            prompt_pack_id=prompt_pack_id,
            tenant_id="default",
            brand_id=brand_id,
            name=prompt_pack_id,
            task_type=task_type,
            channel=channel,
            template="Create content about {topic}.",
            variables=["topic"],
            enabled=enabled,
            version=version,
        )

    def test_selects_tenant_wide_pack(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id="global-facebook",
            )
        )

        selected = self.selector.select(
            tenant_id="default",
            task_type="social_post",
            channel="facebook",
        )

        self.assertEqual(
            selected.prompt_pack_id,
            "global-facebook",
        )

    def test_prefers_brand_specific_pack(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id="global-facebook",
            )
        )
        self.repository.save(
            self.create_pack(
                prompt_pack_id="brand-facebook",
                brand_id="brand-one",
            )
        )

        selected = self.selector.select(
            tenant_id="default",
            brand_id="brand-one",
            task_type="social_post",
            channel="facebook",
        )

        self.assertEqual(
            selected.prompt_pack_id,
            "brand-facebook",
        )

    def test_falls_back_to_tenant_pack(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id="global-facebook",
            )
        )

        selected = self.selector.select(
            tenant_id="default",
            brand_id="brand-one",
            task_type="social_post",
            channel="facebook",
        )

        self.assertIsNone(selected.brand_id)

    def test_selects_latest_enabled_version(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id="global-facebook",
                version=1,
            )
        )
        self.repository.save(
            self.create_pack(
                prompt_pack_id="global-facebook",
                version=2,
            )
        )

        selected = self.selector.select(
            tenant_id="default",
            task_type="social_post",
            channel="facebook",
        )

        self.assertEqual(selected.version, 2)

    def test_disabled_latest_version_is_not_selected(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id="global-facebook",
                enabled=True,
                version=1,
            )
        )
        self.repository.save(
            self.create_pack(
                prompt_pack_id="global-facebook",
                enabled=False,
                version=2,
            )
        )

        with self.assertRaises(FileNotFoundError):
            self.selector.select(
                tenant_id="default",
                task_type="social_post",
                channel="facebook",
            )

    def test_filters_by_task_type(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id="email-pack",
                task_type="email",
                channel="email",
            )
        )

        selected = self.selector.select(
            tenant_id="default",
            task_type="email",
            channel="email",
        )

        self.assertEqual(
            selected.prompt_pack_id,
            "email-pack",
        )

    def test_exact_pack_identifier_resolves_ambiguity(
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

        selected = self.selector.select(
            tenant_id="default",
            task_type="social_post",
            channel="facebook",
            prompt_pack_id="facebook-two",
        )

        self.assertEqual(
            selected.prompt_pack_id,
            "facebook-two",
        )

    def test_ambiguous_selection_is_rejected(
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

        with self.assertRaisesRegex(
            ValueError,
            "ambiguous",
        ):
            self.selector.select(
                tenant_id="default",
                task_type="social_post",
                channel="facebook",
            )

    def test_missing_pack_raises_clear_error(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError,
            "No enabled Prompt Pack",
        ):
            self.selector.select(
                tenant_id="default",
                task_type="email",
                channel="email",
            )

    def test_global_selection_ignores_brand_packs(
        self,
    ) -> None:
        self.repository.save(
            self.create_pack(
                prompt_pack_id="brand-facebook",
                brand_id="brand-one",
            )
        )

        with self.assertRaises(FileNotFoundError):
            self.selector.select(
                tenant_id="default",
                task_type="social_post",
                channel="facebook",
            )

    def test_rejects_blank_tenant(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "tenant_id",
        ):
            self.selector.select(
                tenant_id=" ",
                task_type="social_post",
            )

    def test_rejects_blank_task_type(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "task_type",
        ):
            self.selector.select(
                tenant_id="default",
                task_type=" ",
            )

    def test_rejects_invalid_repository(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "PromptPackRepository",
        ):
            PromptPackSelector(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
