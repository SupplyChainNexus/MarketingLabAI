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
4. Review the approved Positioning and Strategy governing the workflow.
5. Review, revise, and explicitly approve the Campaign Plan and Marketing
   Brief.
6. Generate only when Strategy, Positioning, Plan, and Brief are aligned and
   current.
7. Review content separately from the independent compliance result.
8. Review limitations and provider, model, plan, brief, and timestamp metadata.
9. Authorize and download a safe JSON review record without publishing.

The workspace also provides a Founder Design Partner readiness checklist. It
reports blockers and entitlement separately from activation. Strand Auto Parts
is the proposed first partner, with full feature access and billing disabled;
the customer pilot remains founder-frozen until a separate activation decision.

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
- Browser operations use the hardened server session and CSRF boundary from
  MLAI-027.6; workspace code does not persist credentials.
- Export authorization never publishes content.
- Real customer data remains prohibited until the full private-pilot release
  gate passes.

## Local hosting

MLAI-027.6 supplies hardened WSGI configuration, session controls, safe logs,
backup, recovery, and release checks. Deployment-specific identity, privacy,
support, and recovery evidence must still pass before any real-data decision.
