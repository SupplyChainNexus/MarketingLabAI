# MarketingLabAI Product Capability Map

## Review checkpoint

Reviewed after MLAI-027.6 and PDR-0003 Marketing Decision Doctrine.

## Maturity scale

| Level | Meaning |
|---|---|
| 0 — Concept | Direction exists but no implementation |
| 1 — Foundation | Initial models or infrastructure exist |
| 2 — Functional | Core use case works locally through services or tests |
| 3 — Integrated | Capability participates in a governed internal workflow |
| 4 — Production | Operational, monitored, secure, and customer-ready |
| 5 — Enterprise | Scalable, configurable, governed, and deeply auditable |

Level 4 remains unavailable because the customer pilot is founder-frozen and
deployment-specific identity, legal, privacy, and rehearsal evidence is absent.

## Current capability map

| Layer | Capability | Customer value | Maturity | Priority |
|---|---|---|---:|---|
| Company | Brand and voice profiles | Consistent identity and communication | 3 | Compose into pilot |
| Company | Business, commercial, market, operational, growth, and strategic context | Commercially grounded decisions | 3 | Compose into pilot |
| Company | Competitive context | Preserves known competitor evidence | 2 | Maintain |
| Customer | Segments and ICPs | Defines relevant customer groups | 3 | Compose into pilot |
| Customer | Personas, needs, motivations, triggers, objections, channels, and journeys | Improves relevance and persuasion | 3 | Compose into pilot |
| Product | Verified product and offer context | Prevents inaccurate offers and unsupported claims | 3 | Maintain; add lifecycle evidence after pilot |
| Positioning | Target selection, persona-product matching, differentiation, value proposition, alternatives, and proof | Establishes why a chosen customer should prefer the offer | 0 | After pilot gate; precedes Strategy |
| Strategy | Situation synthesis, business objectives, coherent marketing mix, channel roles, messaging hierarchy, and measurement plan | Turns intelligence into coordinated decisions | 0 | After Positioning; pilot uses approved brief scope |
| Environment | Evidence-backed political, economic, social, technological, legal, and environmental signals | Keeps decisions responsive to material market conditions | 0 | Define with Strategy without premature live feeds |
| Application | Canonical SQLite composition root | Gives future interfaces one governed runtime boundary | 3 | Maintain through MLAI-027 |
| Campaign | Campaign Plan lifecycle and validation | Makes coordinated campaigns reviewable | 3 | Maintain |
| Campaign | Asset planning, dependencies, readiness, and blocked-work reporting | Makes delivery work actionable | 3 | Maintain |
| Brief | Versioned Marketing Brief and Prompt Pack workflow | Preserves approved execution intent | 3 | Maintain |
| Generation | Provider-neutral orchestration and Company, Customer, Product, and memory context assembly | Produces governed marketing assets | 3 | Maintain through secure pilot |
| Compliance | Preventative guidance and independent evaluation | Reduces brand and policy risk | 3 | Expose in pilot |
| Memory | Provider, model, workflow, and event audit context | Preserves traceability | 2 | Extend in pilot |
| Identity | External identity boundary, tenant authorization, and revocable sessions | Protects customer data and actions | 3 | Select provider only when pilot is unfrozen |
| Interface | Authenticated pilot API contract | Gives the workspace one governed, retry-safe boundary | 3 | Maintain through MLAI-027.5/027.6 |
| Interface | Guided session-protected synthetic pilot workspace | Makes the governed vertical slice understandable and usable | 3 | Maintain while customer pilot is frozen |
| Operations | Deployment, health, safe logs, rate limits, backup, restore, CI, and incident process | Makes a future private pilot supportable | 3 | Rehearse only when pilot is unfrozen |
| Calendar | International Marketing Calendar | Coordinates time-based activity | 0 | Deferred MLAI-026 |
| Publishing | Connector-controlled execution | Reduces manual channel work | 0 | Post-pilot |
| Learning | Actual results, evidence-grounded campaign learning, adaptation, and experiments | Closes the marketing control loop | 0 | Post-real outcomes; never infer synthetic learning |
| Analytics | Performance, attribution, forecasting, and budget optimization | Explains and improves commercial impact | 0 | Post-data |
| Executive | Decision-ready executive intelligence | Supports leadership decisions | 0 | Future premium extension |

## Approved delivery sequence

1. MLAI-027.1 Canonical Application Composition
2. MLAI-027.2 Verified Product and Offer Context
3. MLAI-027.3 Identity and Tenant Authorization
4. MLAI-027.4 Pilot API and Workflow Contract
5. MLAI-027.5 Thin Pilot Workspace
6. MLAI-027.6 Pilot Operations and Release Gate
7. Founder-frozen customer-pilot checkpoint
8. Continue the approved product sequence until a customer-facing pilot is necessary
