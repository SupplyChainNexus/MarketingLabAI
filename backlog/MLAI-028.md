# MLAI-028 - Positioning Intelligence

## Status

MLAI-028.5 implemented - governed synthetic workflow integration

## Product authority

- `governance/product-constitution.md`
- `governance/pdrs/PDR-0003-marketing-decision-doctrine.md`
- `governance/adrs/ADR-0015-positioning-intelligence-foundation.md`
- `governance/product-capability-map.md`

## Objective

Establish evidence-grounded Positioning Intelligence that explains why a
verified product or offer is relevant to a selected customer, what makes it
meaningfully different, which proof supports the decision, and which unknowns
or assumptions remain before Marketing Strategy is developed.

## Delivery plan

### MLAI-028.1 - Positioning Intelligence Foundation

- [x] Define tenant- and brand-owned positioning decisions.
- [x] Keep target, product, and offer references explicit.
- [x] Preserve evidence, confidence, assumptions, and unknowns separately.
- [x] Add immutable version history and controlled approval.
- [x] Add SQLite migration 14 and cross-tenant persistence tests.
- [x] Record the architectural boundary in ADR-0015.
- [x] Keep the customer pilot frozen and use synthetic evidence only.

### MLAI-028.2 - Target-Product Relevance

- [x] Validate target references against Customer Intelligence.
- [x] Validate product and offer references against Product Intelligence.
- [x] Map recorded needs, outcomes, decision criteria, features, and benefits.
- [x] Produce deterministic relevance explanations and explicit gaps.
- [x] Preserve limitations, prohibited claims, and the unmodelled use-case gap.

### MLAI-028.3 - Differentiation and Proof

- [x] Model relevant alternatives and competitor context.
- [x] Select defensible differentiators and proof points.
- [x] Prevent prohibited, unsupported, or contradictory claims.
- [x] Preserve evidence provenance and review status.

### MLAI-028.4 - Value Proposition and Positioning Decisions

- [x] Build evidence-grounded value propositions and offer framing.
- [x] Support positioning statements with confidence and limitations.
- [x] Add review, approval, retirement, and replacement rules.

### MLAI-028.5 - Governed Workflow Integration

- [x] Compose approved positioning through CanonicalApplication.
- [x] Expose provider-neutral positioning context to generation.
- [x] Require Campaign Plans and Marketing Briefs to reference approved
      positioning where applicable.
- [x] Add authorized API/workspace review without unfreezing the pilot.

## Epic acceptance criteria

- [x] Positioning consumes validated Company, Customer, and Product context.
- [x] Target and product relevance are explainable and evidence-linked.
- [x] Unknowns and assumptions cannot appear as verified facts.
- [x] Approval and version history are tenant-scoped and auditable.
- [x] Generation consumes only approved positioning decisions.
- [x] Focused and complete regressions pass.
- [x] Governance, capability maturity, risk, debt, and handover remain current.

## Explicitly deferred

- Marketing Strategy Intelligence
- Live research feeds and autonomous competitor monitoring
- Customer-pilot activation or real customer data
- Direct publishing, billing, and public self-service
- Learning, attribution, analytics, and Marketing Intelligence Score
