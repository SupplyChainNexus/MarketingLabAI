"""Customer evidence context builder."""

from __future__ import annotations

from app.customer_intelligence.builders.base import (
    CustomerIntelligenceSectionBuilder,
)
from app.customer_intelligence.models import (
    CustomerEvidence,
    CustomerIntelligenceProfile,
)


class CustomerEvidenceBuilder(CustomerIntelligenceSectionBuilder):
    """Build traceable evidence and confidence context."""

    title = "Customer Evidence"

    def build(
        self,
        profile: CustomerIntelligenceProfile,
    ) -> list[str]:
        profile = self.require_profile(profile)
        records: list[tuple[str, CustomerEvidence]] = []

        for segment in profile.segments:
            records.extend(
                (f"Segment {segment.name}", item) for item in segment.evidence
            )

        for icp in profile.ideal_customer_profiles:
            records.extend((f"ICP {icp.name}", item) for item in icp.evidence)

        for persona in profile.personas:
            records.extend(
                (f"Persona {persona.name}", item) for item in persona.evidence
            )

        lines: list[str] = []
        seen: set[tuple[str, str, float, bool, str]] = set()

        for owner, evidence in records:
            key = (
                evidence.source,
                evidence.summary,
                evidence.confidence,
                evidence.verified,
                evidence.observed_at,
            )

            if key in seen:
                continue

            seen.add(key)
            verification = "verified" if evidence.verified else "unverified"
            detail = (
                evidence.summary
                if evidence.summary
                else "No evidence summary supplied."
            )
            line = (
                f"- {owner}: {detail} "
                f"(source: {evidence.source}; "
                f"confidence: {evidence.confidence:.2f}; "
                f"{verification}"
            )

            if evidence.observed_at:
                line += f"; observed: {evidence.observed_at}"

            lines.append(line + ")")

        return lines
