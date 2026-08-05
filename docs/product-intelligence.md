# Verified Product and Offer Intelligence

MLAI-027.2 establishes the minimum Product Intelligence boundary required by
the secure pilot. It records only synthetic or explicitly approved facts and
routes them through the canonical application composition root.

## Model

A tenant and brand own one current `ProductIntelligenceProfile`. The profile
contains products or services with identity, description, features, benefits,
proof points, limitations, prohibited claims, and offers. Every product record
requires at least one named source.

Price, availability, and warranty are time-sensitive `VerifiedFact` values.
Each is either:

- `verified`, with a non-empty value and optional source evidence; or
- `unknown`, with no hidden value or evidence.

The deterministic context builder writes unknown offer facts as `Unknown`.
It never substitutes a guess, default price, implied availability, or warranty.

## Runtime boundary

`CanonicalApplication` owns the tenant-scoped SQLite repository and injects a
`ProductContextProvider` into `AIContextAssembler`. Provider requests receive a
separate `Verified Product and Offer Context` section and audit whether Product
Intelligence was included.

This story adds no API, user interface, authentication, positioning logic, or
real customer data. Identity and tenant authorization remain the next security
gate in MLAI-027.3.

## Persistence

Schema migration 10 adds `product_intelligence_profiles`, keyed by tenant and
brand. Saving validates that the brand belongs to the stated tenant. The row is
a current verified snapshot; historical offer versioning is deliberately
deferred until evidence from the secure pilot establishes the required
lifecycle.
