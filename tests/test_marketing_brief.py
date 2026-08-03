"""Tests for the structured Marketing Brief domain."""

from __future__ import annotations

import unittest

from app.marketing_brief import (
    BriefStatus,
    MarketingBrief,
    MarketingBriefEvidence,
)


class MarketingBriefEvidenceTests(unittest.TestCase):
    """Validate Marketing Brief evidence records."""

    def test_evidence_cleans_values(self) -> None:
        evidence = MarketingBriefEvidence(
            source_type=" customer_intelligence ",
            source_id=" segment-one ",
            summary=" High-intent repeat buyers ",
            confidence=0.8,
        )

        self.assertEqual(
            evidence.source_type,
            "customer_intelligence",
        )
        self.assertEqual(
            evidence.source_id,
            "segment-one",
        )
        self.assertEqual(
            evidence.summary,
            "High-intent repeat buyers",
        )

    def test_evidence_rejects_boolean_confidence(self) -> None:
        with self.assertRaises(TypeError):
            MarketingBriefEvidence(
                source_type="customer_intelligence",
                source_id="segment-one",
                summary="Evidence",
                confidence=True,
            )

    def test_evidence_rejects_out_of_range_confidence(self) -> None:
        with self.assertRaises(ValueError):
            MarketingBriefEvidence(
                source_type="customer_intelligence",
                source_id="segment-one",
                summary="Evidence",
                confidence=1.1,
            )

    def test_evidence_round_trip(self) -> None:
        evidence = MarketingBriefEvidence(
            source_type="company_brain",
            source_id="brand-one",
            summary="Verified business objective",
            metadata={"field": "business_goals"},
        )

        restored = MarketingBriefEvidence.from_dict(evidence.to_dict())

        self.assertEqual(
            restored.to_dict(),
            evidence.to_dict(),
        )


class MarketingBriefTests(unittest.TestCase):
    """Validate Marketing Brief behaviour."""

    @staticmethod
    def make_brief(
        **overrides: object,
    ) -> MarketingBrief:
        values: dict[str, object] = {
            "brief_id": "brief-one",
            "tenant_id": "tenant-one",
            "brand_id": "brand-one",
            "name": "Spring Acquisition Campaign",
            "objective": "Increase qualified enquiries",
            "audience": "Independent repair workshops",
        }
        values.update(overrides)

        return MarketingBrief(**values)

    def test_brief_requires_core_identity(self) -> None:
        with self.assertRaises(ValueError):
            self.make_brief(brief_id=" ")

    def test_brief_cleans_and_deduplicates_lists(self) -> None:
        brief = self.make_brief(
            channels=[
                " Facebook ",
                "facebook",
                "",
                "Email",
            ],
            deliverables=[
                "Lead advert",
                " lead advert ",
            ],
        )

        self.assertEqual(
            brief.channels,
            ["Facebook", "Email"],
        )
        self.assertEqual(
            brief.deliverables,
            ["Lead advert"],
        )

    def test_brief_converts_evidence_dictionaries(self) -> None:
        brief = self.make_brief(
            evidence=[
                {
                    "source_type": "customer_intelligence",
                    "source_id": "segment-one",
                    "summary": "Verified customer segment",
                    "confidence": 0.9,
                }
            ]
        )

        self.assertIsInstance(
            brief.evidence[0],
            MarketingBriefEvidence,
        )
        self.assertTrue(brief.has_grounding)

    def test_draft_can_be_incomplete(self) -> None:
        brief = self.make_brief()

        self.assertEqual(
            brief.status,
            BriefStatus.DRAFT,
        )
        self.assertFalse(brief.is_execution_ready)

    def test_ready_status_requires_execution_fields(self) -> None:
        with self.assertRaises(ValueError):
            self.make_brief(status=BriefStatus.READY)

    def test_mark_ready_validates_and_updates_status(self) -> None:
        brief = self.make_brief(
            channels=["Facebook"],
            deliverables=["Lead advert"],
            key_message="Fast access to dependable parts",
            call_to_action="Request a quote",
        )

        brief.mark_ready()

        self.assertEqual(
            brief.status,
            BriefStatus.READY,
        )
        self.assertTrue(brief.is_execution_ready)

    def test_approve_requires_execution_readiness(self) -> None:
        brief = self.make_brief()

        with self.assertRaises(ValueError):
            brief.approve()

    def test_approve_sets_approved_status(self) -> None:
        brief = self.make_brief(
            channels=["Email"],
            deliverables=["Email campaign"],
            key_message="Reliable parts availability",
            call_to_action="Contact the sales team",
        )

        brief.approve()

        self.assertEqual(
            brief.status,
            BriefStatus.APPROVED,
        )

    def test_retire_preserves_brief_and_changes_status(self) -> None:
        brief = self.make_brief()

        brief.retire()

        self.assertEqual(
            brief.status,
            BriefStatus.RETIRED,
        )

    def test_brief_round_trip_preserves_nested_evidence(self) -> None:
        brief = self.make_brief(
            channels=["Facebook"],
            deliverables=["Lead advert"],
            key_message="Reliable supply",
            call_to_action="Request a quote",
            evidence=[
                MarketingBriefEvidence(
                    source_type="company_brain",
                    source_id="brand-one",
                    summary="Verified business objective",
                )
            ],
            assumptions=["Budget remains available"],
        )

        restored = MarketingBrief.from_dict(brief.to_dict())

        self.assertEqual(
            restored.to_dict(),
            brief.to_dict(),
        )

    def test_from_dict_rejects_invalid_input(self) -> None:
        with self.assertRaises(TypeError):
            MarketingBrief.from_dict([])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
