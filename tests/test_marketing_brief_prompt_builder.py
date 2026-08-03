"""Tests for Marketing Brief prompt-section composition."""

from __future__ import annotations

import unittest

from app.ai.prompt import PromptSection
from app.marketing_brief import (
    MarketingBrief,
    MarketingBriefEvidence,
    MarketingBriefPromptBuilder,
)


class MarketingBriefPromptBuilderTests(unittest.TestCase):
    """Validate deterministic Marketing Brief prompt adaptation."""

    def setUp(self) -> None:
        self.builder = MarketingBriefPromptBuilder()

    @staticmethod
    def make_brief(
        **overrides: object,
    ) -> MarketingBrief:
        values: dict[str, object] = {
            "brief_id": "brief-one",
            "tenant_id": "tenant-one",
            "brand_id": "brand-one",
            "name": "Workshop Acquisition",
            "objective": "Increase qualified enquiries",
            "audience": "Independent repair workshops",
        }
        values.update(overrides)

        return MarketingBrief(**values)

    def test_builder_rejects_invalid_brief(self) -> None:
        with self.assertRaises(TypeError):
            self.builder.build(object())  # type: ignore[arg-type]

    def test_builder_returns_prompt_sections(self) -> None:
        sections = self.builder.build(self.make_brief())

        self.assertTrue(sections)
        self.assertTrue(all(isinstance(section, PromptSection) for section in sections))

    def test_builder_uses_deterministic_order(self) -> None:
        brief = self.make_brief(
            offer="Priority parts sourcing",
            key_message="Dependable access to parts",
            call_to_action="Request a quote",
            channels=["Facebook", "Email"],
            deliverables=["Lead advert"],
            constraints=["No unsupported guarantees"],
            success_metrics=["Qualified enquiries"],
            evidence=[
                MarketingBriefEvidence(
                    source_type="customer_intelligence",
                    source_id="segment-one",
                    summary="Verified repair-workshop segment",
                    confidence=0.9,
                )
            ],
            assumptions=["Budget remains available"],
            notes="Use direct language.",
        )

        sections = self.builder.build(brief)

        self.assertEqual(
            [section.title for section in sections],
            [
                "Marketing Brief",
                "Audience",
                "Offer and Message",
                "Execution Requirements",
                "Constraints",
                "Success Metrics",
                "Supporting Evidence",
                "Explicit Assumptions",
                "Additional Notes",
            ],
        )

    def test_builder_omits_empty_optional_sections(self) -> None:
        sections = self.builder.build(self.make_brief())

        self.assertEqual(
            [section.title for section in sections],
            [
                "Marketing Brief",
                "Audience",
            ],
        )

    def test_overview_contains_core_identity(self) -> None:
        sections = self.builder.build(self.make_brief())
        rendered = sections[0].render()

        self.assertIn(
            "Brief: Workshop Acquisition",
            rendered,
        )
        self.assertIn(
            "Objective: Increase qualified enquiries",
            rendered,
        )
        self.assertIn(
            "Status: draft",
            rendered,
        )

    def test_audience_contains_segment_references(self) -> None:
        brief = self.make_brief(
            customer_segment_ids=[
                "segment-one",
                "segment-two",
            ]
        )

        sections = self.builder.build(brief)
        audience = next(section for section in sections if section.title == "Audience")

        self.assertIn(
            "Customer segment IDs: segment-one, segment-two",
            audience.render(),
        )

    def test_offer_section_preserves_product_references(self) -> None:
        brief = self.make_brief(
            offer="Priority parts sourcing",
            product_ids=["product-one"],
        )

        sections = self.builder.build(brief)
        offer = next(
            section for section in sections if section.title == "Offer and Message"
        )

        self.assertIn(
            "Offer: Priority parts sourcing",
            offer.render(),
        )
        self.assertIn(
            "Product IDs: product-one",
            offer.render(),
        )

    def test_execution_section_lists_deliverables(self) -> None:
        brief = self.make_brief(
            channels=["Facebook"],
            deliverables=[
                "Lead advert",
                "Landing page",
            ],
        )

        sections = self.builder.build(brief)
        execution = next(
            section for section in sections if section.title == "Execution Requirements"
        )

        self.assertIn(
            "Channels: Facebook",
            execution.render(),
        )
        self.assertIn(
            "- Lead advert",
            execution.render(),
        )
        self.assertIn(
            "- Landing page",
            execution.render(),
        )

    def test_evidence_and_assumptions_remain_separate(self) -> None:
        brief = self.make_brief(
            evidence=[
                MarketingBriefEvidence(
                    source_type="company_brain",
                    source_id="brand-one",
                    summary="Verified business objective",
                    confidence=1.0,
                )
            ],
            assumptions=["Budget remains available"],
        )

        sections = self.builder.build(brief)
        section_map = {section.title: section.render() for section in sections}

        self.assertIn(
            "Verified business objective",
            section_map["Supporting Evidence"],
        )
        self.assertNotIn(
            "Budget remains available",
            section_map["Supporting Evidence"],
        )
        self.assertIn(
            "Budget remains available",
            section_map["Explicit Assumptions"],
        )
        self.assertNotIn(
            "Verified business objective",
            section_map["Explicit Assumptions"],
        )

    def test_evidence_includes_source_and_confidence(self) -> None:
        brief = self.make_brief(
            evidence=[
                MarketingBriefEvidence(
                    source_type="customer_intelligence",
                    source_id="segment-one",
                    summary="High-intent segment",
                    confidence=0.875,
                )
            ]
        )

        sections = self.builder.build(brief)
        evidence = next(
            section for section in sections if section.title == "Supporting Evidence"
        )

        self.assertIn(
            "[customer_intelligence:segment-one]",
            evidence.render(),
        )
        self.assertIn(
            "confidence: 0.88",
            evidence.render(),
        )


if __name__ == "__main__":
    unittest.main()
