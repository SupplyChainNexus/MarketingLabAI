# ADR-0022 — Google Cloud Identity Platform

## Status

Accepted by founder on 2026-08-06. Supersedes ADR-0021 before live deployment.

## Decision

Google Cloud Identity Platform is the selected customer authentication provider.
It authenticates identities only. MarketingLabAI retains tenant membership,
authorization, invitations, founder entitlement, billing state and audit
decisions behind its provider-neutral boundary.

The initial deployment uses the 50,000-MAU core free allowance, the standard
authentication domain, email/password or Google sign-in, and TOTP where MFA is
required. SMS, SAML/OIDC enterprise federation, Cloud Functions and other paid
services remain disabled until justified and separately approved.

ID tokens must use RS256 and match the configured Google Cloud project issuer
and audience. Expiry, issue time, authentication time and subject are mandatory.

## Consequences

The existing Supply Chain Nexus Enterprise Google Workspace administrator may
own the Cloud organization and project, but Workspace users are administrators,
not MarketingLabAI customer accounts. A billing account may be linked while
usage remains within free allowances; budgets and alerts are required before
live configuration. No customer invitation or real data is authorized here.
