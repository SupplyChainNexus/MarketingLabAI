# ADR-0025 — Pilot Privacy and Data Boundaries

## Status

Accepted for MLAI-030.3 on 2026-08-06. This decision defines synthetic
engineering controls; it does not approve a real-data privacy boundary.

## Context

Signup required two booleans but did not retain versioned acceptance evidence,
classify submitted data, or provide a tenant-specific default-deny decision.
Real-data retention, deletion, legal roles, subprocessors, location, and notice
remain founder-reserved decisions.

## Decision

- Define a provider-neutral `PilotPrivacyPolicy` for approved design-partner
  tenants.
- Allow only enumerated invented synthetic categories; deny unknown and real
  business categories by default.
- Record notice and boundary versions atomically with the claiming identity,
  tenant, and timestamp.
- Reject stale policy versions before tenant creation.
- Apply a 30-day synthetic validation-cycle retention and seven-day synthetic
  deletion target; leave all real-data periods unset.
- Expose authenticated policy, acceptance, and category-decision evidence.
- Keep `real_data_activation_authorized` false in every policy response.

## Consequences

Synthetic acceptance rehearsal is deterministic, tenant-scoped, auditable,
and retry-safe. It is not customer consent, legal approval, market validation,
or activation. A future founder decision must name the partner, allowed data,
users, features, period, owners, monitoring, stop conditions, and rollback.
