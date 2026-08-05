# MarketingLabAI Risk Register

| ID | Category | Risk | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| RISK-001 | Product access | No customer-usable application surface exists. | Tested capabilities cannot produce customer evidence. | MLAI-027 API and thin pilot workspace. | Open |
| RISK-002 | Architecture | Legacy CLI paths remain available outside the canonical application root. | A future caller could still select the wrong runtime path. | Require future interfaces to use CanonicalApplication; retire or migrate legacy paths deliberately. | Reduced — monitor |
| RISK-003 | Security | A live identity provider and operational secret handling are not configured, although application authorization is enforced. | Misconfigured deployment could prevent or weaken trusted authentication. | Require MLAI-027.4 to use the authorized facade and MLAI-027.6 to validate provider configuration and secrets. | Reduced - monitor |
| RISK-004 | Data integrity | Legacy JSON data may require migration while SQLite is canonical for the pilot. | Incomplete migration or duplicate records could confuse operators. | Keep JSON compatibility outside CanonicalApplication and define explicit migration before customer import. | Reduced — monitor |
| RISK-005 | Product quality | Positioning and Strategy Intelligence remain incomplete; Product Intelligence is a minimum verified pilot slice. | Pilot outputs may be mistaken for the full MIOS promise. | Use verified Product/Offer context, honest pilot positioning, and retain the ordered roadmap. | Reduced - monitor |
| RISK-006 | Operations | No deployable service, monitoring, backup/restore, or incident process exists. | Unrecoverable data loss or undetected failure in a pilot. | MLAI-027.6 operational release gate. | Open |
| RISK-007 | Privacy | Logging and retention rules are not defined for real customer context and AI prompts. | Sensitive customer information may be retained or exposed incorrectly. | Data-handling, retention, deletion, and privacy-safe logging policy before pilot. | Open |
| RISK-008 | Commercial | Founding prices are not supported by unit economics or usage policy. | Unsustainable customer commitments. | Keep pricing hypothetical until cost and packaging review. | Deferred |
| RISK-009 | Product trust | Marketing Intelligence Score lacks a validated evidence model. | Misleading or gameable customer claims. | Keep future-only until explainability and validation requirements are met. | Deferred |
