# Thin Secure Pilot Workspace

## Purpose

The workspace is MarketingLabAI's first guided customer-facing surface. It is a
synthetic private-pilot interface, not a production deployment. It turns the
authenticated API contract into one understandable marketing workflow without
exposing repositories, provider models, or publishing connectors.

## Guided journey

1. Connect an operator-provisioned synthetic identity, tenant, brand, Campaign
   Plan, and Marketing Brief.
2. Add or refresh minimum verified Company, Customer, and Product context.
3. Review explicit missing-context indicators.
4. Review, revise, and explicitly approve the Campaign Plan and Marketing
   Brief.
5. Generate only when both current versions are approved.
6. Review content separately from the independent compliance result.
7. Review limitations and provider, model, plan, brief, and timestamp metadata.
8. Authorize and download a safe JSON review record without publishing.

## Architecture

`PilotWorkspaceApplication` is a framework-neutral WSGI host. It serves static
same-origin HTML, CSS, and JavaScript, then delegates all operations to
`PilotWsgiApplication` and `PilotApiService`. Workspace presentation code does
not import `CanonicalApplication`, SQLite, repositories, or provider SDKs.

The API adds transport-safe onboarding, workflow-review, and revision
contracts. Authorized application methods own domain conversion and repository
access. Revision creates immutable successors; a revised Campaign Plan returns
to `planned`, and a revised Marketing Brief returns to `draft`. Generation is
locked until current versions are approved again.

## Security and limitations

- The page uses a restrictive same-origin Content Security Policy, `no-store`,
  and `nosniff` headers.
- Tenant IDs remain routing input, never proof of authorization.
- Credentials stay in page memory and are not persisted by workspace code.
- The temporary credential-entry field is synthetic-pilot scaffolding; live
  identity redirection and hardened session handling belong to MLAI-027.6.
- Export authorization never publishes content.
- Real customer data remains prohibited until the full private-pilot release
  gate passes.

## Local hosting

MLAI-027.6 will select and configure the hardened WSGI server, live identity
adapter, secrets, TLS, logs, monitoring, backup, and recovery procedures. This
story deliberately defines the usable surface without pretending it is ready
for public or customer-data deployment.
