"""Deterministic Product Intelligence prompt context."""

from app.product_intelligence.models import FactStatus, ProductIntelligenceProfile


class ProductContextBuilder:
    def build(self, profile: ProductIntelligenceProfile) -> str:
        if not isinstance(profile, ProductIntelligenceProfile):
            raise TypeError("profile must be a ProductIntelligenceProfile.")
        sections: list[str] = []
        if not profile.products:
            return "No verified products or services are recorded."
        for product in profile.products:
            lines = [f"Name: {product.name}", f"Type: {product.product_type.value}"]
            if product.description:
                lines.append(f"Description: {product.description}")
            lines.append(
                "Verified sources: "
                + ", ".join(evidence.source for evidence in product.evidence)
            )
            for label, values in (
                ("Features", product.features),
                ("Benefits", product.benefits),
                ("Proof points", product.proof_points),
                ("Limitations", product.limitations),
                ("Prohibited claims", product.prohibited_claims),
            ):
                if values:
                    lines.append(f"{label}: {', '.join(values)}")
            if not product.offers:
                lines.append("Offers: None recorded")
                lines.append("Price: Unknown")
                lines.append("Availability: Unknown")
                lines.append("Warranty: Unknown")
            for offer in product.offers:
                lines.append(f"Offer: {offer.name}")
                for label, fact in (
                    ("Price", offer.price),
                    ("Availability", offer.availability),
                    ("Warranty", offer.warranty),
                ):
                    value = (
                        fact.value if fact.status is FactStatus.VERIFIED else "Unknown"
                    )
                    lines.append(f"{label}: {value}")
                    if fact.status is FactStatus.VERIFIED and fact.evidence:
                        lines.append(
                            f"{label} source: "
                            + ", ".join(item.source for item in fact.evidence)
                        )
                if offer.limitations:
                    lines.append(f"Offer limitations: {', '.join(offer.limitations)}")
                if offer.prohibited_claims:
                    lines.append(
                        f"Offer prohibited claims: {', '.join(offer.prohibited_claims)}"
                    )
            sections.append("\n".join(lines))
        return "\n\n".join(sections)
