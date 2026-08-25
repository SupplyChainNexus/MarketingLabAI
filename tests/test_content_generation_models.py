"""Model-level tests for C5 grounding references and privacy boundaries."""

from __future__ import annotations

import unittest

from app.content_generation.models import (
    GroundingSnapshot,
    PrivacyClassification,
    SourceLifecycle,
    SourceReference,
)


class GroundingModelTests(unittest.TestCase):
    def test_source_reference_normalizes_enum_values(self) -> None:
        reference = SourceReference(
            source_type="campaign_plan",
            source_id="plan-1",
            tenant_id="tenant-1",
            brand_id="brand-1",
            version=1,
            digest="a" * 64,
            lifecycle="approved",
            privacy_classification="confidential",
        )
        self.assertIs(reference.lifecycle, SourceLifecycle.APPROVED)
        self.assertIs(
            reference.privacy_classification, PrivacyClassification.CONFIDENTIAL
        )

    def test_source_reference_rejects_raw_content_and_bad_digest(self) -> None:
        with self.assertRaises(TypeError):
            SourceReference(
                source_type="campaign_plan",
                source_id="plan-1",
                tenant_id="tenant-1",
                brand_id="brand-1",
                version=1,
                digest="a" * 64,
                lifecycle="approved",
                privacy_classification="internal",
                raw_content="secret",
            )
        with self.assertRaises(ValueError):
            SourceReference(
                source_type="campaign_plan",
                source_id="plan-1",
                tenant_id="tenant-1",
                brand_id="brand-1",
                version=1,
                digest="not-a-digest",
                lifecycle="approved",
                privacy_classification="internal",
            )

    def test_snapshot_is_frozen_and_requires_plan_source(self) -> None:
        with self.assertRaises(TypeError):
            GroundingSnapshot.create(
                generation_identity="generation-1",
                tenant_id="tenant-1",
                brand_id="brand-1",
                captured_at="2026-08-25T12:34:56.000000Z",
                selected_fields={
                    "objective": "objective",
                    "audience": "audience",
                    "channels": ["email"],
                    "content_type": "email",
                },
                source_refs=(),
            )


if __name__ == "__main__":
    unittest.main()
