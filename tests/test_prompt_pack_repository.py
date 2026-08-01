"""Tests for versioned Prompt Pack persistence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.repositories import BrandRepository
from app.prompts.models import PromptPack
from app.prompts.repository import PromptPackRepository
from app.tenants.models import Tenant
from app.tenants.repository import TenantRepository


class PromptPackRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = SQLiteDatabase(
            Path(self.temporary_directory.name) / "marketinglabai.db"
        )
        self.database.initialise()

        self.tenants = TenantRepository(self.database)
        self.brands = BrandRepository(self.database)
        self.repository = PromptPackRepository(self.database)

        self.tenants.save(
            Tenant(
                tenant_id="tenant-two",
                name="Tenant Two",
            )
        )

        self.brands.save(
            {
                "brand_id": "brand-one",
                "tenant_id": "default",
                "name": "Brand One",
            }
        )
        self.brands.save(
            {
                "brand_id": "brand-two",
                "tenant_id": "tenant-two",
                "name": "Brand Two",
            }
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def create_pack(
        *,
        prompt_pack_id: str = "facebook-organic",
        tenant_id: str = "default",
        brand_id: str | None = "brand-one",
        task_type: str = "social_post",
        channel: str = "facebook",
        enabled: bool = True,
        version: int = 1,
        template: str = "Create a post about {topic}.",
    ) -> PromptPack:
        return PromptPack(
            prompt_pack_id=prompt_pack_id,
            tenant_id=tenant_id,
            brand_id=brand_id,
            name="Facebook Organic",
            task_type=task_type,
            channel=channel,
            template=template,
            variables=["topic"],
            enabled=enabled,
            version=version,
        )

    def test_repository_round_trip(self) -> None:
        original = self.create_pack()

        self.repository.save(original)

        restored = self.repository.get(
            "facebook-organic",
            tenant_id="default",
        )

        self.assertEqual(
            restored.to_dict(),
            original.to_dict(),
        )

    def test_latest_version_is_returned_by_default(
        self,
    ) -> None:
        self.repository.save(self.create_pack(version=1))
        self.repository.save(
            self.create_pack(
                version=2,
                template="Create an improved post.",
            )
        )

        restored = self.repository.get(
            "facebook-organic",
            tenant_id="default",
        )

        self.assertEqual(restored.version, 2)
        self.assertEqual(
            restored.template,
            "Create an improved post.",
        )

    def test_specific_version_can_be_retrieved(
        self,
    ) -> None:
        self.repository.save(self.create_pack(version=1))
        self.repository.save(self.create_pack(version=2))

        restored = self.repository.get(
            "facebook-organic",
            tenant_id="default",
            version=1,
        )

        self.assertEqual(restored.version, 1)

    def test_duplicate_version_is_rejected(
        self,
    ) -> None:
        self.repository.save(self.create_pack())

        with self.assertRaisesRegex(
            ValueError,
            "already exists",
        ):
            self.repository.save(self.create_pack())

    def test_list_versions_preserves_history(
        self,
    ) -> None:
        for version in range(1, 4):
            self.repository.save(self.create_pack(version=version))

        versions = self.repository.list_versions(
            "facebook-organic",
            tenant_id="default",
        )

        self.assertEqual(
            [pack.version for pack in versions],
            [1, 2, 3],
        )

    def test_list_for_tenant_returns_latest_versions(
        self,
    ) -> None:
        self.repository.save(self.create_pack(version=1))
        self.repository.save(self.create_pack(version=2))
        self.repository.save(
            self.create_pack(
                prompt_pack_id="email-newsletter",
                task_type="email",
                channel="email",
                version=1,
            )
        )

        packs = self.repository.list_for_tenant("default")

        self.assertEqual(
            [
                (
                    pack.prompt_pack_id,
                    pack.version,
                )
                for pack in packs
            ],
            [
                ("email-newsletter", 1),
                ("facebook-organic", 2),
            ],
        )

    def test_list_for_tenant_excludes_latest_disabled_pack(
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

        self.assertEqual(
            self.repository.list_for_tenant("default"),
            [],
        )

        packs = self.repository.list_for_tenant(
            "default",
            enabled_only=False,
        )

        self.assertEqual(len(packs), 1)
        self.assertFalse(packs[0].enabled)

    def test_list_for_tenant_supports_filters(
        self,
    ) -> None:
        self.repository.save(self.create_pack())
        self.repository.save(
            self.create_pack(
                prompt_pack_id="email-newsletter",
                task_type="email",
                channel="email",
            )
        )

        packs = self.repository.list_for_tenant(
            "default",
            brand_id="brand-one",
            task_type="email",
            channel="email",
        )

        self.assertEqual(len(packs), 1)
        self.assertEqual(
            packs[0].prompt_pack_id,
            "email-newsletter",
        )

    def test_repository_enforces_tenant_isolation(
        self,
    ) -> None:
        self.repository.save(self.create_pack())

        with self.assertRaises(FileNotFoundError):
            self.repository.get(
                "facebook-organic",
                tenant_id="tenant-two",
            )

        self.assertFalse(
            self.repository.exists(
                "facebook-organic",
                tenant_id="tenant-two",
            )
        )

    def test_unknown_tenant_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "does not exist",
        ):
            self.repository.save(
                self.create_pack(
                    tenant_id="unknown",
                    brand_id=None,
                )
            )

    def test_unknown_brand_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "does not exist",
        ):
            self.repository.save(
                self.create_pack(
                    brand_id="unknown-brand",
                )
            )

    def test_cross_tenant_brand_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "does not belong",
        ):
            self.repository.save(
                self.create_pack(
                    tenant_id="default",
                    brand_id="brand-two",
                )
            )

    def test_exists_can_check_specific_version(
        self,
    ) -> None:
        self.repository.save(self.create_pack(version=1))

        self.assertTrue(
            self.repository.exists(
                "facebook-organic",
                tenant_id="default",
                version=1,
            )
        )
        self.assertFalse(
            self.repository.exists(
                "facebook-organic",
                tenant_id="default",
                version=2,
            )
        )

    def test_count_can_filter_by_tenant(
        self,
    ) -> None:
        self.repository.save(self.create_pack(version=1))
        self.repository.save(self.create_pack(version=2))
        self.repository.save(
            self.create_pack(
                prompt_pack_id="tenant-two-pack",
                tenant_id="tenant-two",
                brand_id="brand-two",
            )
        )

        self.assertEqual(
            self.repository.count(),
            3,
        )
        self.assertEqual(
            self.repository.count(
                tenant_id="default",
            ),
            2,
        )
        self.assertEqual(
            self.repository.count(
                tenant_id="tenant-two",
            ),
            1,
        )

    def test_repository_rejects_invalid_object(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "PromptPack",
        ):
            self.repository.save(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
