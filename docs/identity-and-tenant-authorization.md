# Identity and Tenant Authorization

MLAI-027.3 establishes the security boundary required before any pilot API,
workspace, or real customer data.

## Trust boundary

An external identity provider validates credentials through
`IdentityProviderAdapter` and returns an `AuthenticatedPrincipal`. MarketingLabAI
does not interpret passwords, tokens, sessions, or caller-supplied tenant IDs as
proof of access.

The canonical application resolves that trusted principal against an active
tenant membership. Access is default-deny. A successful check returns an
`AuthorizedTenantApplication` bound to exactly one tenant.

## Roles

- Viewer: view tenant resources.
- Marketer: view, generate, and export.
- Approver: marketer permissions plus approval.
- Admin: all permissions, including membership administration.

Inactive and missing memberships grant no permissions. Resource ownership must
match the bound tenant even when the principal has an admin role.

## Authorized operations

The tenant-bound facade controls context assembly, generation, Campaign Plan
approval, Marketing Brief approval, export authorization, and membership
administration. Cross-tenant resources are denied before repositories or AI
providers perform the requested action.

Every identity binding and every allowed or denied action is recorded in the
authorization audit ledger. Generation metadata also records the authenticated
subject and identity provider.

## Deferred

No live provider, credential transport, API, browser session, UI, secret
management, or real customer data is introduced here. MLAI-027.4 will select an
API contract over this boundary; operational secret and privacy gates remain in
MLAI-027.6.

## High-assurance continuity

ADR-0051 does not move tenant authority into Identity Platform. Authentication,
MFA and step-up establish identity confidence; Earthonox still checks current
membership, role, tenant ownership and operation with default deny. Session
renewal and token revocation must preserve this separation and cross-tenant
regression coverage.
