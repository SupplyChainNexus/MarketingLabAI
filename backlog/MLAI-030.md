# MLAI-030 — Founder Design Partner Onboarding

## Purpose

Evaluate signup and onboarding rather than bypassing them with manually created accounts.

## Locked sequence

1. MLAI-030.1 — Founder Design Partner Signup and Tenant Provisioning
2. MLAI-030.2 — External Identity Deployment and Signup Experience
3. MLAI-030.3 — Guided Business Onboarding and Consent Evidence
4. MLAI-030.4 — Founder Activation Review and Operational Rehearsal

MLAI-030.1 approves Strand Auto Parts and Velani Wholesale as the only candidates.
Each must authenticate and claim a separate invitation. Tenant and owner creation
must be atomic and retry-safe. Both receive free full access with billing disabled,
while real customer data remains founder-frozen.

MLAI-030.2 initially selected Microsoft Entra External ID, then reconciled the
decision before live deployment. Google Cloud Identity Platform is the current
selection because its free allowance, TOTP support, custom-domain route, and
fit with the existing Google Workspace administration better match the
free-first SME strategy. Strict issuer, project audience, RS256 signature,
expiry, issued-at, authentication-time, and subject validation remain behind
the provider-neutral adapter. SMS, enterprise federation, paid extensions,
live invitations, and real customer data remain disabled.
