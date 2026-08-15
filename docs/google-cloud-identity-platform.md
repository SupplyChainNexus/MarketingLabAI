# Google Cloud Identity Platform deployment

Google Cloud Identity Platform is the selected customer authentication service.
It does not own MarketingLabAI tenants, memberships, invitations, entitlements,
billing state, or authorization.

## Existing Google Workspace

Supply Chain Nexus Enterprise's Workspace administration can own the Google
Cloud organization and controlled project. Workspace users are staff
administrators only. Strand Auto Parts and Velani Wholesale must sign up through
Identity Platform and must not be provisioned as Workspace users.

Google Workspace billing and Google Cloud billing are separate. No Workspace
upgrade is required for Identity Platform.

## Free-first boundary

- Use email/password or Google sign-in and TOTP where MFA is required.
- Keep SMS, SAML/OIDC enterprise federation, Cloud Functions, and paid add-ons
  disabled.
- Configure Cloud Billing budget alerts before browser rehearsal, even when
  expected usage remains inside the free allowance.
- Enable Identity Platform audit/activity logging before invitations.
- Use one external identity configuration; MarketingLabAI remains the authority
  for SME tenant separation.

## Activation order

1. Validate the local adapter and complete repository synchronization.
2. Create a dedicated Google Cloud project under the controlled organization.
3. Enable Identity Platform and approved sign-in methods only.
4. Configure authorized domains and local secrets outside version control.
5. Rehearse synthetic signup, invalid tokens, recovery, and account revocation.
6. Request founder approval before sending invitations or processing real data.

## Browser sign-in deployment

The controlled workspace loads Google Identity Services under a restrictive
Content Security Policy. It exchanges the Google credential directly with the
Identity Toolkit API for a Firebase ID token. The browser retains that token in
memory only and clears it after MarketingLabAI creates its own hashed,
tenant-bound session.

Browser-safe environment values are `MLAI_GOOGLE_CLOUD_PROJECT_ID`,
`MLAI_GOOGLE_WEB_API_KEY`, `MLAI_GOOGLE_OAUTH_CLIENT_ID`, and
`MLAI_GOOGLE_AUTH_DOMAIN`. The OAuth client secret is not required and must
never enter source control, JavaScript, logs, or a public response. The Firebase
browser key is restricted to the Identity Toolkit and Token Service APIs and to
approved HTTP referrers.

The local rehearsal origin is exactly `http://127.0.0.1:8080`. This loopback
HTTP exception is accepted only in `synthetic-pilot`; every other unproxied
runtime requires HTTPS.

The backend accepts only RS256 Firebase ID tokens with the configured project
issuer and audience, mandatory time and subject claims, a verified email, and
`google.com` as the Firebase sign-in provider. A Google identity is not a
MarketingLabAI tenant: invitation claiming and tenant authorization remain
separate application decisions.

`MLAI_GOOGLE_MAX_AUTH_AGE_SECONDS` bounds authentication age from 300 to 3600
seconds. The backend rejects missing, malformed, stale, or materially future
`auth_time` claims. Every MarketingLabAI session use rechecks the requested
tenant and current active membership; removing a membership therefore blocks
an otherwise unexpired session.

Logout uses `DELETE /v1/pilot/session`, requires the session tenant and CSRF
token, revokes the server-side session, audits the decision, and expires both
browser cookies. Operator-driven identity-and-tenant revocation invalidates all
matching sessions and is audited separately.

## Production-security evidence

Set `MLAI_SECURITY_EVIDENCE_JSON` only from recorded controlled rehearsal. It
is a JSON object of boolean values for the exact checks in ADR-0026. Missing or
false items remain blockers. Never store tokens, credentials, invitation codes,
customer records, or submitted content in this value.

A complete security report permits founder activation assessment only. It does
not authorize an OAuth production audience, external invitations, public
signup, customer data, billing, publishing, or production activation.

Login availability depends on the hosted Google Identity Services client.
Google may delete an OAuth client after six months of inactivity. An
administrative configuration response also exposed the unused SCRYPT signer
configuration during setup. No password users exist and password sign-in is
disabled; it must not be enabled without security review and fresh credential
treatment.

## High-assurance direction

ADR-0051 preserves Identity Platform as customer authentication authority and
Earthonox as tenant-authorization and server-session authority. The next
identity increments must add risk-based MFA and step-up, governed recovery,
provider-supported token revocation and evidence-backed session renewal without
persisting provider refresh credentials in Earthonox. Exact factors, durations
and provider settings require separately authorized implementation and
controlled rehearsal; this architecture lock does not enable them.
