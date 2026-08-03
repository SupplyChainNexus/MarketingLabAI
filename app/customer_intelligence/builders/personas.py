"""Customer persona context builders."""

from __future__ import annotations

from app.customer_intelligence.builders.base import (
    CustomerIntelligenceSectionBuilder,
)
from app.customer_intelligence.models import (
    CustomerIntelligenceProfile,
    CustomerPersona,
)


class CustomerPersonaBuilder(CustomerIntelligenceSectionBuilder):
    """Build customer persona identity and behaviour context."""

    title = "Customer Personas"

    def build(
        self,
        profile: CustomerIntelligenceProfile,
    ) -> list[str]:
        profile = self.require_profile(profile)
        lines: list[str] = []

        for persona in profile.personas:
            lines.extend(self._build_persona(persona))

        return lines

    def _build_persona(self, persona: CustomerPersona) -> list[str]:
        heading_details: list[str] = []

        if persona.role:
            heading_details.append(persona.role)

        if persona.segment_id:
            heading_details.append(f"segment: {persona.segment_id}")

        suffix = f" ({'; '.join(heading_details)})" if heading_details else ""
        lines = [f"- {persona.name} [{persona.persona_id}]{suffix}"]

        if persona.description:
            lines.append(f"  - Description: {persona.description}")

        fields = (
            ("Demographics", persona.demographics),
            ("Psychographics", persona.psychographics),
            ("Pain points", persona.pain_points),
            ("Desired outcomes", persona.desired_outcomes),
            ("Motivations", persona.motivations),
            ("Buying triggers", persona.buying_triggers),
            ("Objections", persona.objections),
            ("Decision criteria", persona.decision_criteria),
            ("Preferred channels", persona.preferred_channels),
            ("Journey stages", persona.journey_stages),
            ("Customer language", persona.language_terms),
            ("Trust factors", persona.trust_factors),
            ("Emotional drivers", persona.emotional_drivers),
            ("Customer questions", persona.customer_questions),
        )

        for label, values in fields:
            rendered = self.bullet(label, values)
            if rendered:
                lines.append(f"  {rendered}")

        return lines
