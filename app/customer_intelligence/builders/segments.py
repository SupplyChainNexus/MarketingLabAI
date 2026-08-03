"""Customer segment and ideal-customer-profile builders."""

from __future__ import annotations

from app.customer_intelligence.builders.base import (
    CustomerIntelligenceSectionBuilder,
)
from app.customer_intelligence.models import CustomerIntelligenceProfile


class CustomerSegmentBuilder(CustomerIntelligenceSectionBuilder):
    """Build customer segment context."""

    title = "Customer Segments"

    def build(
        self,
        profile: CustomerIntelligenceProfile,
    ) -> list[str]:
        profile = self.require_profile(profile)
        lines: list[str] = []

        for segment in profile.segments:
            details: list[str] = []

            if segment.description:
                details.append(segment.description)

            if segment.characteristics:
                details.append("Characteristics: " + ", ".join(segment.characteristics))

            suffix = f" — {'; '.join(details)}" if details else ""
            lines.append(f"- {segment.name} [{segment.segment_id}]{suffix}")

        return lines


class IdealCustomerProfileBuilder(CustomerIntelligenceSectionBuilder):
    """Build ideal-customer-profile context."""

    title = "Ideal Customer Profiles"

    def build(
        self,
        profile: CustomerIntelligenceProfile,
    ) -> list[str]:
        profile = self.require_profile(profile)
        lines: list[str] = []

        for item in profile.ideal_customer_profiles:
            lines.append(f"- {item.name} [{item.icp_id}]")

            fields = (
                ("Description", [item.description] if item.description else []),
                ("Industries", item.industries),
                ("Company sizes", item.company_sizes),
                ("Regions", item.regions),
                ("Needs", item.needs),
                ("Buying criteria", item.buying_criteria),
            )

            for label, values in fields:
                rendered = self.bullet(label, values)
                if rendered:
                    lines.append(f"  {rendered}")

        return lines
