# Pilot Privacy and Data Handling

## Current authority

Only synthetic data is permitted. The customer pilot remains frozen. This
document defines controls for operational validation; it does not grant
permission to process customer data.

## Data classes

- Secrets: identity/provider credentials, session material, signing secrets.
- Customer content: Company, Customer, Product, plan, brief, prompt, generated
  asset, compliance evidence, and exports.
- Operational metadata: request ID, time, route, result, tenant/subject
  identifiers, provider/model identifiers, and integrity evidence.

Secrets live only in the deployment secret service and process environment.
Customer content stays in tenant-scoped SQLite persistence and authorized
exports. Operational logs use an allowlisted schema and redact sensitive keys.

## Retention and deletion

Synthetic pilot records are retained only for the active validation cycle.
Expired and revoked sessions must be purged during maintenance. Backups follow
the same classification and deletion decision as their source. Deletion must
cover the live database, approved exports, backups when their retention window
ends, and any support copies. Authorization and provider/model audit evidence
is retained long enough to explain the test result without retaining prompt or
generated content in logs.

Before any customer pilot, the founder must approve jurisdiction, controller/
processor roles, customer notice and consent, retention periods, deletion SLA,
subprocessors, data location, support access, and breach notification terms.
