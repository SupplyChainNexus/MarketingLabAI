# MLAI-027.6 Release Gate Matrix

| Gate | Automated evidence | Result after story |
|---|---|---|
| Canonical application and SQLite | Complete regressions | Pass |
| External identity boundary | Factory contract and adapter tests | Pass for configured deployment |
| Tenant authorization | Cross-tenant regression | Pass |
| Hardened sessions | Hash, TTL, tenant, CSRF, cookie, revocation tests | Pass |
| Environment secrets and TLS | Strict configuration tests | Pass |
| Rate limits | Deterministic limiter tests | Pass for single instance |
| Privacy-safe logs | Recursive redaction tests | Pass |
| Backup/restore/integrity | Online backup and restore tests | Pass |
| Health/readiness | Operational WSGI tests | Pass |
| CI and continuity | Linux quality and Windows PowerShell jobs | Configured |
| Synthetic vertical slice | Workspace/API/security/full suite | Pass target |
| Real customer data | Founder decision | Frozen / prohibited |

MLAI-027.6 closes the engineering foundation for a controlled pilot. It does
not activate that pilot. Reconsideration requires a customer-facing identity
deployment, completed legal/privacy choices, an operational rehearsal, and a
new explicit founder decision.
