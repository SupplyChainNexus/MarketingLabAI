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

ADR-0024 supersedes that broad phrase: engineering development and controlled
synthetic design-partner rehearsal are authorized. Only real-customer
activation and its reserved external, commercial and data actions remain
frozen.

MLAI-030.2 initially selected Microsoft Entra External ID, then reconciled the
decision before live deployment. Google Cloud Identity Platform is the current
selection because its free allowance, TOTP support, custom-domain route, and
fit with the existing Google Workspace administration better match the
free-first SME strategy. Strict issuer, project audience, RS256 signature,
expiry, issued-at, authentication-time, and subject validation remain behind
the provider-neutral adapter. SMS, enterprise federation, paid extensions,
live invitations, and real customer data remain disabled.

The application-side completion serves browser-safe Google identifiers from a
no-store endpoint, obtains a Google credential through Google Identity Services,
exchanges it for a project-audience Firebase ID token, and clears that token
after creating a tenant-bound session. Only verified Google email identities
are accepted. Local HTTP is permitted solely for the exact synthetic
`127.0.0.1` origin; deployed environments still require HTTPS. The OAuth secret
never enters browser configuration.
