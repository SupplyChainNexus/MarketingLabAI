# ADR-0011 - Identity and Tenant Authorization

## Status

Accepted

## Date

2026-08-05

## Context

MarketingLabAI has tenant-owned persistence but previously trusted tenant IDs
supplied by callers. A tenant identifier is routing data, not authorization
evidence. Building an API on that assumption could expose another tenant's
intelligence, plans, briefs, generated work, or audit history.

## Decision

External identity providers own credential verification behind a provider-
neutral `IdentityProviderAdapter`. Successful verification produces an
`AuthenticatedPrincipal` containing the provider and stable subject identifier.

MarketingLabAI owns tenant memberships and role permissions. The canonical
application resolves a principal to an active membership and returns a tenant-
bound `AuthorizedTenantApplication`. Permissions are default-deny. Resource
ownership must match the bound tenant independently of role.

Roles are Viewer, Marketer, Approver, and Admin. The authorized application
facade governs context access, generation, approval, export authorization, and
membership administration. Future interfaces may not receive raw canonical
repositories as their runtime contract.

Every identity binding and authorization decision is persisted with subject,
provider, tenant, action, resource, outcome, and timestamp. Denied decisions
are audited without requiring the asserted tenant to exist.

## Dependency direction

Identity models and the adapter contract do not depend on a provider SDK,
SQLite, API framework, or user interface. Membership and audit repositories
depend on the domain. The authorization service depends on those repositories.
The tenant-bound facade depends on authorization and canonical application
services. Future API adapters depend on this facade.

## Alternatives considered

### Trust a tenant ID from each API request

Rejected because knowledge of an identifier does not prove tenant membership.

### Put authorization only in repository queries

Rejected because generation, approval, export, and membership administration
also require authorization and auditable intent.

### Select a live identity vendor in this story

Rejected because provider choice, secrets, callback transport, and deployment
belong to the API and operational gates. The adapter boundary preserves choice.

### Give future interfaces the raw CanonicalApplication

Rejected because it exposes repositories and unbound tenant parameters that can
bypass authorization.

## Consequences

### Positive

- tenant IDs are no longer treated as proof of access;
- authorization is bound once and rechecked per operation;
- cross-tenant ownership mismatch is denied even for admins;
- allowed and denied actions are auditable;
- identity providers remain replaceable;
- future API work has one secure application contract.

### Negative

- a live identity provider still must be selected and configured;
- membership provisioning requires a controlled bootstrap process;
- real customer data remains prohibited until operational gates also pass.

## Validation

- provider adapter and trusted-principal contract;
- role-permission and inactive-membership behavior;
- membership and audit persistence under migration 11;
- default-deny missing membership;
- cross-tenant denial for context, generation, plan approval, brief approval,
  export, and membership administration;
- identity-bound generation metadata; and
- focused and complete regressions.
