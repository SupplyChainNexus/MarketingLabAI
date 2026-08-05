# MarketingLabAI Technical Debt Register

| ID | Area | Description | Priority | Status |
|---|---|---|---|---|
| TD-001 | Persistence | Legacy JSON services remain for compatibility, but SQLite is now canonical inside the pilot composition root. | High | Reduced at ee5da24; migration and retirement remain |
| TD-002 | Application composition | CLI generation bypassed Campaign Planner, versioned Marketing Brief, Prompt Pack selection, and independent compliance review. | Critical | Resolved by CanonicalApplication at ee5da24 |
| TD-003 | Tenant boundary | Some repositories retrieve by globally supplied brand ID rather than an authorized tenant context. | Critical | Open — MLAI-027.3 |
| TD-008 | Campaign artifacts | Generated content and compliance reports require an injected artifact service and do not yet have a canonical relational repository. | High | Open — design before pilot export |
| TD-004 | Health checks | Local health check validates legacy folders and optional Gemini access rather than the canonical database and governed workflow. | High | Open — MLAI-027.6 |
| TD-005 | Release metadata | `pyproject.toml` references a missing root README and contains stale version/description metadata. | Medium | Open |
| TD-006 | Delivery automation | No tracked CI workflow validates tests, formatting, static analysis, migrations, or continuity on remote changes. | High | Open — MLAI-027.6 |
| TD-007 | Governance accuracy | Capability maturity previously lagged implemented Customer Intelligence and Campaign Planner evidence. | Medium | Addressed by MLAI-027 adoption review; maintain each epic |
