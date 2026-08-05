# MarketingLabAI Technical Debt Register

| ID | Area | Description | Priority | Status |
|---|---|---|---|---|
| TD-001 | Persistence | Legacy JSON services remain for compatibility, but SQLite is now canonical inside the pilot composition root. | High | Reduced at ee5da24; migration and retirement remain |
| TD-002 | Application composition | CLI generation bypassed Campaign Planner, versioned Marketing Brief, Prompt Pack selection, and independent compliance review. | Critical | Resolved by CanonicalApplication at ee5da24 |
| TD-003 | Tenant boundary | Some repositories retrieve by globally supplied brand ID rather than an authorized tenant context. | Critical | Open — MLAI-027.3 |
| TD-008 | Campaign artifacts | Generated content and compliance reports require an injected artifact service and do not yet have a canonical relational repository. | High | Open — design before pilot export |
| TD-004 | Health checks | Operational liveness and canonical readiness now exist; legacy local health remains for compatibility. | Medium | Reduced by MLAI-027.6; retire legacy check deliberately |
| TD-005 | Release metadata | `pyproject.toml` references a missing root README and contains stale version/description metadata. | Medium | Open |
| TD-006 | Delivery automation | Tracked Linux quality and Windows continuity jobs now define remote gates. | Medium | Resolved by MLAI-027.6; enforce branch protection separately |
| TD-007 | Governance accuracy | Capability maturity previously lagged implemented Customer Intelligence and Campaign Planner evidence. | Medium | Addressed by MLAI-027 adoption review; maintain each epic |
| TD-009 | Product Intelligence | Current Product/Offer profiles are mutable snapshots without offer expiry or approval history. | Low | Define version, review, and expiry lifecycle from pilot evidence after MLAI-027.2 |
| TD-010 | Identity operations | Provider-neutral live adapter factories and hardened sessions exist; the actual identity vendor and controlled bootstrap deployment remain unselected. | High | Select and rehearse only when customer pilot is unfrozen |
| TD-011 | API operations | Waitress, TLS-aware config, single-process rate limiting, health and logs exist. Distributed rate limiting is intentionally absent. | Low | Revisit only if deployment becomes multi-instance |
| TD-012 | Workspace identity | Temporary credential entry was removed and browser operations require server session plus CSRF. | Critical | Resolved by MLAI-027.6 |
| TD-013 | Positioning references | Positioning target, product, and offer identifiers are validated against Customer and Product Intelligence repositories. | High | Resolved by MLAI-028.2 |
| TD-014 | Product use cases | Product Intelligence has no governed use-case field, so relevance reports the gap rather than inferring use cases. | Medium | Open — preserve as a limitation through MLAI-028.5 |
| TD-015 | Alternative evidence persistence | Reviewed alternative evidence is provider-neutral input to differentiation but has no canonical repository or expiry lifecycle. | Medium | Define with future research evidence; do not persist synthetic fixtures as market truth |
| TD-016 | Positioning replacement linkage | Replacement preserves immutable retired history but does not yet store an explicit predecessor identifier. | Low | Add when canonical integration demonstrates a downstream audit requirement |
| TD-017 | Positioning applicability policy | Draft plans may omit positioning for backward compatibility; governed generation requires an explicit approved reference. | Medium | Define domain-specific applicability rules when Marketing Strategy is introduced |
