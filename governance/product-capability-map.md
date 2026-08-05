# MarketingLabAI Product Capability Map

## Review checkpoint

Reviewed at `ee5da24` after MLAI-027.1 Canonical Application Composition.

## Maturity scale

| Level | Meaning |
|---|---|
| 0 — Concept | Direction exists but no implementation |
| 1 — Foundation | Initial models or infrastructure exist |
| 2 — Functional | Core use case works locally through services or tests |
| 3 — Integrated | Capability participates in a governed internal workflow |
| 4 — Production | Operational, monitored, secure, and customer-ready |
| 5 — Enterprise | Scalable, configurable, governed, and deeply auditable |

No capability is rated level 4 because MarketingLabAI does not yet have a
secure deployed customer workflow.

## Current capability map

| Layer | Capability | Customer value | Maturity | Priority |
|---|---|---|---:|---|
| Company | Brand and voice profiles | Consistent identity and communication | 3 | Compose into pilot |
| Company | Business, commercial, market, operational, growth, and strategic context | Commercially grounded decisions | 3 | Compose into pilot |
| Company | Competitive context | Preserves known competitor evidence | 2 | Maintain |
| Customer | Segments and ICPs | Defines relevant customer groups | 3 | Compose into pilot |
| Customer | Personas, needs, motivations, triggers, objections, channels, and journeys | Improves relevance and persuasion | 3 | Compose into pilot |
| Product | Verified product and offer context | Prevents inaccurate offers and unsupported claims | 0 | MLAI-027.2 |
| Positioning | Persona-product matching and differentiated offer | Selects relevant benefits and proof | 0 | After Product foundation |
| Strategy | Objectives, channel choice, messaging hierarchy, and measurement plan | Turns intelligence into coordinated decisions | 0 | After Positioning; pilot uses approved brief scope |
| Application | Canonical SQLite composition root | Gives future interfaces one governed runtime boundary | 3 | Maintain through MLAI-027 |
| Campaign | Campaign Plan lifecycle and validation | Makes coordinated campaigns reviewable | 3 | Maintain |
| Campaign | Asset planning, dependencies, readiness, and blocked-work reporting | Makes delivery work actionable | 3 | Maintain |
| Brief | Versioned Marketing Brief and Prompt Pack workflow | Preserves approved execution intent | 3 | Maintain |
| Generation | Provider-neutral orchestration and Company, Customer, and memory context assembly | Produces governed marketing assets | 3 | Extend with Product context in MLAI-027.2 |
| Compliance | Preventative guidance and independent evaluation | Reduces brand and policy risk | 3 | Expose in pilot |
| Memory | Provider, model, workflow, and event audit context | Preserves traceability | 2 | Extend in pilot |
| Identity | User authentication and tenant authorization | Protects customer data and actions | 0 | MLAI-027.3 |
| Interface | Pilot API and guided workspace | Makes capability usable without an engineer | 0 | MLAI-027.4/027.5 |
| Operations | Deployment, monitoring, backup, restore, and incident process | Makes private pilot safe and supportable | 0 | MLAI-027.6 |
| Calendar | International Marketing Calendar | Coordinates time-based activity | 0 | Deferred MLAI-026 |
| Publishing | Connector-controlled execution | Reduces manual channel work | 0 | Post-pilot |
| Learning | Evidence-grounded campaign learning and experiments | Improves future decisions | 0 | Post-real outcomes |
| Analytics | Performance, attribution, forecasting, and budget optimization | Explains and improves commercial impact | 0 | Post-data |
| Executive | Decision-ready executive intelligence | Supports leadership decisions | 0 | Future premium extension |

## Approved delivery sequence

1. MLAI-027.1 Canonical Application Composition
2. MLAI-027.2 Verified Product and Offer Context
3. MLAI-027.3 Identity and Tenant Authorization
4. MLAI-027.4 Pilot API and Workflow Contract
5. MLAI-027.5 Thin Pilot Workspace
6. MLAI-027.6 Pilot Operations and Release Gate
7. Controlled pilot evidence review
8. Reconsider MLAI-026 and remaining Product, Positioning, and Strategy depth
