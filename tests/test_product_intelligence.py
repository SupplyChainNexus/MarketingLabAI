"""Tests for verified Product and Offer Intelligence models."""

import unittest

from app.product_intelligence import (
    FactStatus,
    ProductEvidence,
    ProductIntelligenceProfile,
    ProductRecord,
    ProductType,
    VerifiedFact,
    VerifiedOffer,
)


class ProductIntelligenceTests(unittest.TestCase):
    def evidence(self) -> ProductEvidence:
        return ProductEvidence(source="Synthetic approved catalogue")

    def test_unknown_fact_cannot_smuggle_a_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown facts"):
            VerifiedFact(value="R100")

    def test_verified_fact_requires_a_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "require a value"):
            VerifiedFact(status=FactStatus.VERIFIED, evidence=[self.evidence()])

    def test_product_requires_source_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "source evidence"):
            ProductRecord("p1", "Service", ProductType.SERVICE)

    def test_profile_round_trip_preserves_verified_and_unknown_facts(self) -> None:
        profile = ProductIntelligenceProfile(
            tenant_id="tenant-one",
            brand_id="brand-one",
            updated_at="2026-08-05T12:00:00+00:00",
            products=[
                ProductRecord(
                    product_id="service-one",
                    name="Priority sourcing",
                    product_type=ProductType.SERVICE,
                    description="Synthetic pilot service.",
                    evidence=[self.evidence()],
                    prohibited_claims=["Never claim guaranteed delivery."],
                    offers=[
                        VerifiedOffer(
                            offer_id="offer-one",
                            name="Pilot offer",
                            price=VerifiedFact(
                                status=FactStatus.VERIFIED,
                                value="R500 synthetic setup fee",
                                evidence=[self.evidence()],
                            ),
                        )
                    ],
                )
            ],
        )

        restored = ProductIntelligenceProfile.from_dict(profile.to_dict())

        self.assertEqual(restored, profile)
        self.assertEqual(
            restored.products[0].offers[0].availability.status, FactStatus.UNKNOWN
        )

    def test_duplicate_product_and_offer_ids_are_rejected(self) -> None:
        evidence = [self.evidence()]
        offer = VerifiedOffer("offer", "Offer")
        with self.assertRaisesRegex(ValueError, "offer_id"):
            ProductRecord(
                "p", "P", ProductType.PRODUCT, evidence=evidence, offers=[offer, offer]
            )
        product = ProductRecord("p", "P", ProductType.PRODUCT, evidence=evidence)
        with self.assertRaisesRegex(ValueError, "product_id"):
            ProductIntelligenceProfile("t", "b", [product, product])


if __name__ == "__main__":
    unittest.main()
