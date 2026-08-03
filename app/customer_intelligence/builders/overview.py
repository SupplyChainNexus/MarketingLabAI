"""Customer overview context builder."""

from __future__ import annotations

from app.customer_intelligence.builders.base import (
    CustomerIntelligenceSectionBuilder,
)
from app.customer_intelligence.models import CustomerIntelligenceProfile


class CustomerOverviewBuilder(CustomerIntelligenceSectionBuilder):
    """Build the high-level customer overview section."""

    title = "Customer Overview"

    def build(
        self,
        profile: CustomerIntelligenceProfile,
    ) -> list[str]:
        profile = self.require_profile(profile)
        lines: list[str] = []

        if profile.summary:
            lines.append(f"- Summary: {profile.summary}")

        if profile.primary_segment_id:
            lines.append(f"- Primary segment ID: {profile.primary_segment_id}")

        if profile.segments:
            lines.append(f"- Segment count: {len(profile.segments)}")

        if profile.ideal_customer_profiles:
            lines.append(
                "- Ideal customer profile count: "
                f"{len(profile.ideal_customer_profiles)}"
            )

        if profile.personas:
            lines.append(f"- Persona count: {len(profile.personas)}")

        return lines
