# MarketingLabAI Reconciliation Register

Status: Draft â€” decisions below must be resolved before repository adoption

## R-001 â€” AI CMO, MIOS, or AI Marketing Department

Earlier language described MarketingLabAI as an â€œAI Chief Marketing Officer.â€
Later locked decisions refined this to a Marketing Intelligence Operating System
and the AI Marketing Department for growing businesses.

**Recommended authority:** Use **Marketing Intelligence Operating System** as
the category and **AI Marketing Department for growing businesses** as the
customer promise. Treat â€œAI CMOâ€ as historical positioning, not the full product
identity.

## R-002 â€” Executive Operating System expansion

One conversation branch proposed a founder-focused Executive Operating System.
The user explicitly identified this as a rabbit-risk and later locked the
marketing core against that drift.

**Recommended authority:** Executive Intelligence remains a future premium
extension built on a commercially successful MarketingLabAI core. It does not
replace or redirect the current product.

## R-003 â€” Tier names

Two naming systems appear:

- Launch / Growth / Scale / Enterprise
- Starter / Growth / Professional / Executive

The second system appears in a later Product Constitution discussion, while the
first is tied to founding prices and marketing-maturity positioning.

**Decision required:** Confirm the canonical tier names. Do not hard-code either
set into product logic until confirmed.

## R-004 â€” Capability versus capacity

An earlier product law said each higher tier must unlock a fundamentally new
capability. A later, stronger constitution said every tier receives a complete
Marketing Department and upgrades unlock capacity, scale, collaboration,
automation, analytics depth, and strategic intelligenceâ€”not quality.

**Recommended reconciliation:** Every tier is complete for its intended
customer. Higher tiers may introduce organizational capabilities needed only at
greater maturity, but must never make core output quality, correctness,
compliance, or usefulness artificially inferior.

## R-005 â€” Founding prices

R399, R999, R2,499, and custom pricing were explicitly locked as founding
offers, but no current commercial-policy document was confirmed in the supplied
repository evidence.

**Decision required:** Preserve these as historical founding-price candidates,
not active public prices, until costs, market validation, taxes, billing,
fair-use policy, and current packaging are reviewed.

## R-006 â€” â€œEvery sprint requires an ADRâ€

The Enterprise Architecture Office discussion proposed an ADR for every sprint.
Later practical work created ADRs for material architectural decisions while
using backlog stories, manifests, tests, and documentation for routine changes.

**Recommended authority:** ADRs are mandatory for material architectural
decisions, boundaries, or durable trade-offsâ€”not for every code change.

## R-007 â€” â€œNo monolithic installersâ€

The locked intent was to stop giant scripts containing embedded source code,
not to eliminate installers. The MarketingLabAI story-package generator now generates small package installers
that copy explicit payloads and run validation.

**Recommended authority:** Keep package installers; prohibit huge embedded-code
repair scripts and one-off patches. Fix generator defects at the source.

## R-008 â€” Roadmap and sprint numbering

The conversation contains multiple obsolete sprint sequences because the
project evolved. The repository has since completed MLAI-025 through commit
`6da6157`.

**Recommended authority:** Preserve strategic sequencing, not old sprint
numbers. The live roadmap and Git history determine current execution order.

## R-009 â€” Security documents

Security-by-design was explicitly locked, including an ADR-0001 label in the
conversation. Repository evidence supplied here confirms tenant-aware work but
does not confirm whether the exact security ADR and gates are currently present.

**Action required:** Inventory existing governance and ADR files before creating
or renumbering any security record. Never overwrite an existing ADR number.

## R-010 â€” Marketing Intelligence Score

MIS was strongly locked as a future signature concept. It is not evidence of a
validated scoring model.

**Recommended authority:** Preserve as a future product hypothesis. Before
implementation, define evidence, weighting, explainability, anti-gaming rules,
and validation. Do not present a fabricated score as objective intelligence.

## R-011 â€” Global domain identity

The conversation proposed `marketinglab.ai` and related domains if available.
Availability and ownership are time-sensitive and were not verified as part of
this recovery.

**Recommended authority:** Treat domain names as an unresolved commercial task,
not a locked asset claim.

## R-012 â€” Current code health versus historical failures

The old chat contains many temporary import, PowerShell, migration, and
formatting failures. These are historical incidents, not current defects. The
current checkpoint passed 69 focused and 683 complete-suite tests.

**Recommended authority:** Keep lessons in engineering history where useful;
do not list resolved incidents as active technical debt.

## R-013 â€” Repository versus chat authority

The chat contains draft code, temporary paths, old test totals, old branch
states, and superseded instructions.

**Rule:** Current tested code, accepted ADRs, committed backlog state, current
documentation, and Git history outrank conversational implementation details.
The chat remains evidence for intent and rationale.
