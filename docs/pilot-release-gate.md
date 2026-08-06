# MLAI-030.4 Production Identity and Security Gate Matrix

| Gate | Automated evidence | Result after story |
|---|---|---|
| Canonical application and SQLite | Complete regressions | Pass |
| External identity boundary | RS256, issuer, audience, expiry, issued-at, fresh authentication-time, provider and verified-email tests | Pass locally; deployment evidence required |
| Tenant authorization | Cross-tenant and current-membership regression | Pass |
| Hardened sessions | Hash, TTL, tenant, CSRF, cookie, audited current and bulk revocation tests | Pass |
| Environment secrets and TLS | Strict configuration tests | Pass |
| Rate limits | Deterministic limiter tests | Pass for single instance |
| Request/resource boundary | Configured request-size rejection tests | Pass for single instance |
| Privacy-safe logs | Recursive redaction tests | Pass |
| Backup/restore/integrity | Online backup and restore tests | Pass |
| Health/readiness | Operational WSGI tests | Pass |
| CI and continuity | Linux quality and Windows PowerShell jobs | Configured |
| Synthetic vertical slice | Workspace/API/security/full suite | Pass target |
| Google deployment and security rehearsal | Seven explicit boolean evidence checks | Missing or false evidence blocks readiness |
| Real customer data | Founder decision | Frozen / prohibited |

MLAI-030.4 can make the production-security report ready for founder activation
assessment. It does not activate the pilot. Every report keeps
`real_data_activation_authorized=false`; later privacy, recovery, support,
acceptance, and founder-decision gates remain mandatory.
