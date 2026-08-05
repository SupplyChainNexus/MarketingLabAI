# MarketingLabAI Risk Register

| ID | Category | Risk | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| RISK-001 | Product access | No customer-usable application surface exists. | Tested capabilities cannot produce customer evidence. | MLAI-027 API and thin pilot workspace. | Open |
| RISK-002 | Architecture | Legacy CLI paths remain available outside the canonical application root. | A future caller could still select the wrong runtime path. | Require future interfaces to use CanonicalApplication; retire or migrate legacy paths deliberately. | Reduced — monitor |
| RISK-003 | Security | Tenant identifiers are not authenticated authorization evidence. | Cross-tenant data exposure or unauthorized action. | Trusted identity adapter, application-service authorization, and denial tests before customer data. | Open |
| RISK-004 | Data integrity | Legacy JSON data may require migration while SQLite is canonical for the pilot. | Incomplete migration or duplicate records could confuse operators. | Keep JSON compatibility outside CanonicalApplication and define explicit migration before customer import. | Reduced — monitor |
| RISK-005 | Product quality | Product, Positioning, and Strategy Intelligence layers are incomplete. | Pilot outputs may be mistaken for the full MIOS promise. | Minimum verified Product/Offer context and honest pilot positioning; retain ordered roadmap. | Open |
| RISK-006 | Operations | No deployable service, monitoring, backup/restore, or incident process exists. | Unrecoverable data loss or undetected failure in a pilot. | MLAI-027.6 operational release gate. | Open |
| RISK-007 | Privacy | Logging and retention rules are not defined for real customer context and AI prompts. | Sensitive customer information may be retained or exposed incorrectly. | Data-handling, retention, deletion, and privacy-safe logging policy before pilot. | Open |
| RISK-008 | Commercial | Founding prices are not supported by unit economics or usage policy. | Unsustainable customer commitments. | Keep pricing hypothetical until cost and packaging review. | Deferred |
| RISK-009 | Product trust | Marketing Intelligence Score lacks a validated evidence model. | Misleading or gameable customer claims. | Keep future-only until explainability and validation requirements are met. | Deferred |
