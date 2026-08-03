"Tests for Marketing Brief versioning service."

from __future__ import annotations

import unittest

from app.marketing_brief import (
    BriefStatus,
    MarketingBrief,
    MarketingBriefService,
)


class MarketingBriefServiceTests(unittest.TestCase):
    "Validate immutable Marketing Brief version creation."

    def setUp(self) -> None:
        self.service = MarketingBriefService.__new__(MarketingBriefService)
        self.brief = MarketingBrief(
            brief_id="brief-one",
            tenant_id="default",
            brand_id="brand-one",
            name="Workshop Acquisition",
            objective="Increase qualified enquiries",
            audience="Repair workshops",
            key_message="Dependable access to parts",
            call_to_action="Request a quote",
            channels=["facebook"],
            deliverables=["Lead advert"],
            status=BriefStatus.APPROVED,
        )

    def test_create_next_version_increments_version(
        self,
    ) -> None:
        updated = self.service.create_next_version(
            self.brief,
            name="Updated Brief",
        )

        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.name, "Updated Brief")
        self.assertEqual(self.brief.version, 1)

    def test_create_next_version_preserves_identity(
        self,
    ) -> None:
        updated = self.service.create_next_version(
            self.brief,
            notes="New note",
        )

        self.assertEqual(updated.brief_id, self.brief.brief_id)
        self.assertEqual(updated.tenant_id, self.brief.tenant_id)
        self.assertEqual(updated.brand_id, self.brief.brand_id)
        self.assertEqual(updated.created_at, self.brief.created_at)

    def test_protected_fields_cannot_be_changed(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "protected"):
            self.service.create_next_version(
                self.brief,
                brand_id="other-brand",
            )

    def test_unknown_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown"):
            self.service.create_next_version(
                self.brief,
                unknown_field=True,
            )

    def test_next_version_is_revalidated(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Execution-ready",
        ):
            self.service.create_next_version(
                self.brief,
                channels=[],
            )


if __name__ == "__main__":
    unittest.main()
