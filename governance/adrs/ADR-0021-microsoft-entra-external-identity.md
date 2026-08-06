# ADR-0021 — Microsoft Entra External ID

## Status

Accepted by founder on 2026-08-06.

## Decision

MarketingLabAI will use Microsoft Entra External ID for customer authentication.
The core remains provider-neutral: Entra validates identity, while MarketingLabAI
owns tenant membership, authorization, entitlements, invitations and audit
decisions. Only RS256 tokens from the configured external tenant, issuer and
application audience are accepted.

The initial deployment uses the free core offering, Microsoft-hosted
`ciamlogin.com` endpoints, non-SMS authentication and no premium add-ons. Azure
AD B2C is prohibited for new deployment. Paid features require evidence of
scale, revenue, security or contractual need and a separate approval.

## Consequences

Tenant and application identifiers remain environment configuration rather than
source-controlled secrets. No live tenant is required for offline contract and
security tests. The founder creates the Entra external tenant only after this
story passes locally. Real customer data and invitation delivery remain frozen.

Changing identity provider later requires an explicit identity-linking migration;
provider subjects must never be treated as tenant identifiers.
