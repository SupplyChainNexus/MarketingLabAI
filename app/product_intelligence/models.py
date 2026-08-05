"""Provider-neutral Product and Offer Intelligence models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def _required(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string.")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} is required.")
    return value


def _optional(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("optional product values must be strings.")
    return value.strip()


def _unique_text(values: list[str]) -> list[str]:
    if not isinstance(values, list):
        raise TypeError("product collections must be lists.")
    cleaned: list[str] = []
    for value in values:
        value = _required(value, "collection value")
        if value not in cleaned:
            cleaned.append(value)
    return cleaned


class FactStatus(StrEnum):
    UNKNOWN = "unknown"
    VERIFIED = "verified"


class ProductType(StrEnum):
    PRODUCT = "product"
    SERVICE = "service"


@dataclass(slots=True)
class ProductEvidence:
    source: str
    summary: str = ""
    observed_at: str = ""

    def __post_init__(self) -> None:
        self.source = _required(self.source, "source")
        self.summary = _optional(self.summary)
        self.observed_at = _optional(self.observed_at)


@dataclass(slots=True)
class VerifiedFact:
    """A fact that is either explicitly unknown or evidence-backed."""

    status: FactStatus = FactStatus.UNKNOWN
    value: str = ""
    evidence: list[ProductEvidence] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.status = FactStatus(self.status)
        self.value = _optional(self.value)
        if not isinstance(self.evidence, list) or any(
            not isinstance(item, ProductEvidence) for item in self.evidence
        ):
            raise TypeError("evidence must contain ProductEvidence objects.")
        if self.status is FactStatus.UNKNOWN and (self.value or self.evidence):
            raise ValueError("unknown facts cannot contain a value or evidence.")
        if self.status is FactStatus.VERIFIED and not self.value:
            raise ValueError("verified facts require a value.")


@dataclass(slots=True)
class VerifiedOffer:
    offer_id: str
    name: str
    price: VerifiedFact = field(default_factory=VerifiedFact)
    availability: VerifiedFact = field(default_factory=VerifiedFact)
    warranty: VerifiedFact = field(default_factory=VerifiedFact)
    limitations: list[str] = field(default_factory=list)
    prohibited_claims: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.offer_id = _required(self.offer_id, "offer_id")
        self.name = _required(self.name, "offer name")
        for name in ("price", "availability", "warranty"):
            if not isinstance(getattr(self, name), VerifiedFact):
                raise TypeError(f"{name} must be a VerifiedFact.")
        self.limitations = _unique_text(self.limitations)
        self.prohibited_claims = _unique_text(self.prohibited_claims)


@dataclass(slots=True)
class ProductRecord:
    product_id: str
    name: str
    product_type: ProductType
    description: str = ""
    evidence: list[ProductEvidence] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    benefits: list[str] = field(default_factory=list)
    proof_points: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    prohibited_claims: list[str] = field(default_factory=list)
    offers: list[VerifiedOffer] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.product_id = _required(self.product_id, "product_id")
        self.name = _required(self.name, "product name")
        self.product_type = ProductType(self.product_type)
        self.description = _optional(self.description)
        if not isinstance(self.evidence, list) or any(
            not isinstance(item, ProductEvidence) for item in self.evidence
        ):
            raise TypeError("evidence must contain ProductEvidence objects.")
        if not self.evidence:
            raise ValueError("product records require source evidence.")
        for name in (
            "features",
            "benefits",
            "proof_points",
            "limitations",
            "prohibited_claims",
        ):
            setattr(self, name, _unique_text(getattr(self, name)))
        if not isinstance(self.offers, list) or any(
            not isinstance(item, VerifiedOffer) for item in self.offers
        ):
            raise TypeError("offers must contain VerifiedOffer objects.")
        if len({item.offer_id for item in self.offers}) != len(self.offers):
            raise ValueError("offer_id values must be unique within a product.")


@dataclass(slots=True)
class ProductIntelligenceProfile:
    tenant_id: str
    brand_id: str
    products: list[ProductRecord] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        self.tenant_id = _required(self.tenant_id, "tenant_id")
        self.brand_id = _required(self.brand_id, "brand_id")
        if not isinstance(self.products, list) or any(
            not isinstance(item, ProductRecord) for item in self.products
        ):
            raise TypeError("products must contain ProductRecord objects.")
        if len({item.product_id for item in self.products}) != len(self.products):
            raise ValueError("product_id values must be unique.")
        self.updated_at = _required(self.updated_at, "updated_at")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProductIntelligenceProfile":
        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary.")
        payload = dict(data)
        products = []
        for item in payload.get("products", []):
            item = dict(item)
            item["evidence"] = [
                ProductEvidence(**entry) for entry in item.get("evidence", [])
            ]
            offers = []
            for offer in item.get("offers", []):
                offer = dict(offer)
                for name in ("price", "availability", "warranty"):
                    fact = dict(offer.get(name, {}))
                    fact["evidence"] = [
                        ProductEvidence(**entry) for entry in fact.get("evidence", [])
                    ]
                    offer[name] = VerifiedFact(**fact)
                offers.append(VerifiedOffer(**offer))
            item["offers"] = offers
            products.append(ProductRecord(**item))
        payload["products"] = products
        return cls(**payload)
