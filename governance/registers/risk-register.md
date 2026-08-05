# MarketingLabAI Risk Register

| ID | Category | Risk | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| RISK-001 | Product access | The authenticated API exists, but no guided customer workspace exists. | Customers still cannot complete the pilot journey without engineering support. | Build MLAI-027.5 only over the pilot API contract. | Reduced - monitor |
| RISK-002 | Architecture | Legacy CLI paths remain available outside the canonical application root. | A future caller could still select the wrong runtime path. | Require future interfaces to use CanonicalApplication; retire or migrate legacy paths deliberately. | Reduced — monitor |
| RISK-003 | Security | The API uses the authorized facade, but a live identity provider and operational secret handling are not configured. | Misconfigured deployment could prevent or weaken trusted authentication. | MLAI-027.6 must validate provider configuration, credential transport, and secrets. | Reduced - monitor |
| RISK-004 | Data integrity | Legacy JSON data may require migration while SQLite is canonical for the pilot. | Incomplete migration or duplicate records could confuse operators. | Keep JSON compatibility outside CanonicalApplication and define explicit migration before customer import. | Reduced — monitor |
| RISK-005 | Product quality | Positioning and Strategy Intelligence remain incomplete; Product Intelligence is a minimum verified pilot slice. | Pilot outputs may be mistaken for the full MIOS promise. | Use verified Product/Offer context, honest pilot positioning, and retain the ordered roadmap. | Reduced - monitor |
| RISK-006 | Operations | No deployable service, monitoring, backup/restore, or incident process exists. | Unrecoverable data loss or undetected failure in a pilot. | MLAI-027.6 operational release gate. | Open |
| RISK-007 | Privacy | Logging and retention rules are not defined for real customer context and AI prompts. | Sensitive customer information may be retained or exposed incorrectly. | Data-handling, retention, deletion, and privacy-safe logging policy before pilot. | Open |
| RISK-008 | Commercial | Founding prices are not supported by unit economics or usage policy. | Unsustainable customer commitments. | Keep pricing hypothetical until cost and packaging review. | Deferred |
| RISK-009 | Product trust | Marketing Intelligence Score lacks a validated evidence model. | Misleading or gameable customer claims. | Keep future-only until explainability and validation requirements are met. | Deferred |
