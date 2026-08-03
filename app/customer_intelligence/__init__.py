"""Customer Intelligence domain components."""

from app.customer_intelligence.context import CustomerContextBuilder
from app.customer_intelligence.models import (
    CustomerEvidence,
    CustomerIntelligenceProfile,
    CustomerPersona,
    CustomerSegment,
    IdealCustomerProfile,
)
from app.customer_intelligence.service import CustomerIntelligenceService

__all__ = [
    "CustomerContextBuilder",
    "CustomerEvidence",
    "CustomerIntelligenceProfile",
    "CustomerIntelligenceService",
    "CustomerPersona",
    "CustomerSegment",
    "IdealCustomerProfile",
]
