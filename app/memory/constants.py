"""Standard event types used by the MarketingLabAI memory engine."""

from enum import StrEnum


class MemoryEventType(StrEnum):
    """Recognised institutional memory event types."""

    CAMPAIGN_CREATED = "campaign.created"
    CAMPAIGN_APPROVED = "campaign.approved"
    CAMPAIGN_PUBLISHED = "campaign.published"
    CAMPAIGN_PERFORMANCE_RECORDED = "campaign.performance_recorded"
    COMPLIANCE_PASSED = "compliance.passed"
    COMPLIANCE_FAILED = "compliance.failed"
    COMPANY_BRAIN_UPDATED = "company_brain.updated"
    VOICE_UPDATED = "voice.updated"
    RESEARCH_IMPORTED = "research.imported"
    CUSTOMER_FEEDBACK_ADDED = "customer_feedback.added"
