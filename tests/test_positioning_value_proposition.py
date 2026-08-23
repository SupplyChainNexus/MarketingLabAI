"""Tests for value proposition candidates and positioning lifecycle rules."""

import tempfile
import unittest
from pathlib import Path

from app.database.connection import SQLiteDatabase
from app.database.factory import bootstrap_database
from app.database.repositories import BrandRepository
from app.positioning_intelligence import (
    CandidateStatus,
    DifferentiationReport,
    DifferentiationSelection,
    PositioningDecision,
    PositioningEvidence,
    PositioningService,
    PositioningStatus,
    RelevanceMatch,
    TargetKind,
    TargetProductRelevance,
    ValuePropositionBuilder,
)
from app.positioning_intelligence.repository import PositioningRepository


class PositioningValuePropositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        database = SQLiteDatabase(Path(self.folder.name) / "db.sqlite")
        bootstrap_database(database)
        BrandRepository(database).save(
            {"brand_id": "brand", "tenant_id": "default", "name": "Brand"}
        )
        self.repository = PositioningRepository(database)
        self.service = PositioningService(self.repository)
        self.builder = ValuePropositionBuilder()

    def tearDown(self) -> None:
        self.folder.cleanup()

    @staticmethod
    def decision(**changes: object) -> PositioningDecision:
        values: dict[str, object] = {
            "positioning_id": "positioning",
            "version": 1,
            "tenant_id": "default",
            "brand_id": "brand",
            "target_kind": TargetKind.PERSONA,
            "target_id": "persona",
            "product_id": "product",
            "evidence": [
                PositioningEvidence(
                    "Founder review",
                    "Synthetic positioning review",
                    0.8,
                    True,
                )
            ],
        }
        values.update(changes)
        return PositioningDecision(**values)

    @staticmethod
    def relevance(**changes: object) -> TargetProductRelevance:
        values: dict[str, object] = {
            "positioning_id": "positioning",
            "positioning_version": 1,
            "target_name": "Owner",
            "product_name": "Workspace",
            "offer_name": "Guided offer",
            "matches": (
                RelevanceMatch(
                    "Consistent marketing decisions",
                    "Consistent marketing workflow",
                    ("consistent", "marketing"),
                    "Shared recorded terms: consistent, marketing",
                ),
            ),
            "limitations": ("Synthetic evidence only",),
            "prohibited_claims": ("Guaranteed revenue growth",),
        }
        values.update(changes)
        return TargetProductRelevance(**values)

    @staticmethod
    def differentiation(**changes: object) -> DifferentiationReport:
        values: dict[str, object] = {
            "positioning_id": "positioning",
            "positioning_version": 1,
            "selections": (
                DifferentiationSelection(
                    "Governed approval workflow",
                    ("Governed approval workflow",),
                    ("Synthetic workflow test",),
                    (),
                    ("Synthetic catalogue",),
                ),
            ),
        }
        values.update(changes)
        return DifferentiationReport(**values)

    def test_builds_traceable_candidate_ready_for_human_review(self) -> None:
        candidate = self.builder.build(
            self.decision(),
            self.relevance(),
            self.differentiation(),
        )
        self.assertEqual(candidate.status, CandidateStatus.READY_FOR_REVIEW)
        self.assertIn("For Owner, Workspace", candidate.statement)
        self.assertIn("Guided offer", candidate.offer_framing)
        self.assertEqual(candidate.confidence, 0.8)
        self.assertEqual(
            candidate.provenance,
            ("Founder review", "Synthetic catalogue"),
        )
        self.assertIn("Synthetic evidence only", candidate.limitations)
        self.assertIn("Guaranteed revenue growth", candidate.prohibited_claims)

    def test_missing_support_returns_incomplete_candidate_without_claim(self) -> None:
        candidate = self.builder.build(
            self.decision(evidence=[]),
            self.relevance(matches=()),
            self.differentiation(selections=()),
        )
        self.assertEqual(candidate.status, CandidateStatus.INCOMPLETE)
        self.assertEqual(candidate.statement, "")
        self.assertEqual(candidate.confidence, 0.0)
        self.assertEqual(
            {item.code for item in candidate.gaps},
            {
                "relevance_missing",
                "differentiation_missing",
                "verified_evidence_missing",
            },
        )

    def test_inputs_must_belong_to_same_immutable_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "different positioning versions"):
            self.builder.build(
                self.decision(),
                self.relevance(positioning_version=2),
                self.differentiation(),
            )

    def test_approval_requires_ready_candidate_and_recorded_statement(self) -> None:
        draft = self.service.create(self.decision())
        candidate = self.builder.build(
            draft,
            self.relevance(),
            self.differentiation(),
        )
        with self.assertRaisesRegex(ValueError, "record the reviewed"):
            self.service.approve_candidate(draft, candidate)
        reviewed = self.service.revise(
            draft,
            value_proposition=candidate.statement,
        )
        reviewed_candidate = self.builder.build(
            reviewed,
            self.relevance(positioning_version=2),
            self.differentiation(positioning_version=2),
        )
        approved = self.service.approve_candidate(reviewed, reviewed_candidate)
        self.assertEqual(approved.status, PositioningStatus.APPROVED)

    def test_incomplete_candidate_cannot_be_approved(self) -> None:
        draft = self.service.create(self.decision(evidence=[]))
        candidate = self.builder.build(
            draft,
            self.relevance(matches=()),
            self.differentiation(selections=()),
        )
        with self.assertRaisesRegex(ValueError, "ready"):
            self.service.approve_candidate(draft, candidate)

    def test_retirement_creates_new_immutable_version(self) -> None:
        draft = self.service.create(
            self.decision(value_proposition="Reviewed proposition")
        )
        approved = self.service.approve(draft)
        retired = self.service.retire(approved)
        self.assertEqual(retired.version, 3)
        self.assertEqual(retired.status, PositioningStatus.RETIRED)
        self.assertEqual(
            self.repository.get(
                tenant_id="default",
                positioning_id="positioning",
                version=2,
            ).status,
            PositioningStatus.APPROVED,
        )

    def test_replacement_requires_new_draft_identity_and_same_owner(self) -> None:
        draft = self.service.create(
            self.decision(value_proposition="Reviewed proposition")
        )
        retired = self.service.retire(self.service.approve(draft))
        replacement = self.decision(positioning_id="replacement")
        saved = self.service.replace(retired, replacement)
        self.assertEqual(saved.positioning_id, "replacement")
        with self.assertRaisesRegex(ValueError, "new draft"):
            self.service.replace(retired, self.decision())


if __name__ == "__main__":
    unittest.main()
