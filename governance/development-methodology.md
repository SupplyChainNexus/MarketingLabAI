# MarketingLabAI Enterprise Development Methodology

Every significant sprint follows this lifecycle.

1. Documentation Discovery
2. Architecture Discovery
3. Architecture Review
4. Architecture Decision (ADR if required)
5. Implementation Plan
6. Implementation
7. Verification
8. Architecture Ledger Update
9. Commit
10. Push

## Core Rules

- Discover before designing.
- Extend before replacing.
- Deterministic before AI.
- Architecture before implementation.
- Build buyer-ready by default.
- Preserve architectural history.
- Every commit should tell one engineering story.

## Intelligence-Led Development

MarketingLabAI develops business capabilities rather than disconnected
features.

Every proposed capability must identify:

- its intelligence layer;
- the marketing function it supports;
- its customer value;
- its dependencies;
- its measurable success criteria;
- its effect on platform and enterprise value.

Development should follow this sequence:

1. Inspect the complete affected system.
2. Confirm existing responsibilities and extension points.
3. Record material architectural decisions.
4. Implement the smallest coherent capability.
5. Protect the capability with focused tests.
6. Run affected regression suites.
7. Update governance, roadmap, and capability maturity where applicable.
8. Commit one understandable architectural increment.

Every major capability should strengthen an intelligence layer or measurably
improve the quality, safety, reliability, or usability of an existing layer.

Prompt construction must not be used to hide missing domain architecture.
Business reasoning belongs in the applicable intelligence domain.
