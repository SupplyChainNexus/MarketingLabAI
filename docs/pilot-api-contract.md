# Secure Pilot API Contract

## Purpose

The pilot API is the authenticated transport boundary for MarketingLabAI's
approved vertical slice. It is intentionally smaller than the domain model and
does not expose repositories, SQLite records, provider requests, or provider
SDK objects.

## Transport

`PilotWsgiApplication` is a dependency-free WSGI JSON adapter. Deployment
server selection, TLS termination, live identity configuration, rate limits,
and operational logging remain MLAI-027.6 responsibilities.

Every request uses `Authorization: Bearer <credential>`. `X-Tenant-ID` selects
the requested scope but never proves access; the trusted identity adapter and
stored membership determine authorization. Mutating and retryable operations
require `Idempotency-Key`.

## Endpoints

| Method and path | Purpose |
|---|---|
| `POST /v1/pilot/context` | Read tenant-authorized context and explicit missing indicators. |
| `POST /v1/pilot/generate` | Generate from named approved Campaign Plan and Marketing Brief versions. |
| `POST /v1/pilot/campaign-plans/{id}/approve` | Approve the expected current plan version. |
| `POST /v1/pilot/marketing-briefs/{id}/approve` | Approve the expected current brief version. |
| `POST /v1/pilot/exports/authorize` | Authorize and audit a safe export boundary. |

Generation requires `brand_id`, `campaign_id`, `campaign_version`, `brief_id`,
`brief_version`, `task`, and optional `instructions`. Both governance artifacts
must be approved and belong to the authenticated tenant and requested brand.

## Errors and retries

Errors use `{ "error": { "code": ..., "message": ... } }`. Authentication is
`401`; authorization is `403`; missing resources are `404`; stale lifecycle
versions, unapproved governance, and idempotency-key reuse are `409`.

Idempotency records are scoped by tenant, identity provider, subject,
operation, and key. An exact replay returns the stored response with
`replayed: true`; the operation and AI provider are not invoked again.

## Security boundary

The transport depends on `PilotApiService`, which obtains only a tenant-bound
`AuthorizedTenantApplication` for each request. Raw repositories never enter a
public request or response contract. Synthetic test data is the only data used
until the private-pilot release gates pass.
