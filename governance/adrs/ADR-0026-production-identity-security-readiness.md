# ADR-0026 — Production Identity and Security Readiness

## Status

Accepted for controlled synthetic rehearsal. Real-data activation remains frozen.

## Decision

MarketingLabAI will require fresh Google authentication, revalidate active
tenant membership whenever a session is used, and support audited revocation of
the current session or all sessions for an identity and tenant. Logout is
CSRF-protected. Request bodies are bounded and API responses use defensive
security and no-store headers.

Production-security readiness is a deterministic report combining runtime
configuration, required database controls, and explicit deployment/rehearsal
evidence. Missing or false evidence is a blocker. Evidence values are booleans;
secrets, tokens, customer records, and raw submitted content are prohibited.

## Required external evidence

- restricted browser API key
- controlled OAuth testing audience
- reviewed authorized domains
- enabled identity audit logging
- invalid-token rejection rehearsal
- session-revocation rehearsal
- tenant-isolation rehearsal

## Consequences

A passing report permits founder activation assessment only. It never
self-authorizes invitations, public signup, production activation, billing,
publishing, real-data learning, or real customer data. Those activities remain
frozen until later gates pass and the founder records an explicit decision.
