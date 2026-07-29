"""Business intelligence and decision-support components."""

from app.intelligence.models import BusinessIntelligenceProfile
from app.intelligence.service import BusinessIntelligenceService

__all__ = [
    "BusinessIntelligenceProfile",
    "BusinessIntelligenceService",
]
