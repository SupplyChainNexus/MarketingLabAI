# Pilot Privacy and Data Handling

## Authority and status

MLAI-030.3 defines the versioned privacy and data-boundary controls used for
controlled synthetic rehearsal. It does not grant permission to process real
customer data. `real_data_activation_authorized` remains false and readiness
never self-authorizes activation.

## Versioned acceptance pack

- Privacy notice: `pilot-privacy-notice-v1`
- Data boundary: `synthetic-data-boundary-v1`
- Acceptance is bound to tenant, identity provider, subject, both versions,
  and an immutable timestamp.
- Acceptance is recorded atomically with invitation claiming and initial owner
  membership. A stale version is rejected before tenant creation.

The acceptance proves that a controlled test identity accepted the synthetic
rehearsal terms. It is not consent for real-data processing.

## Allowed synthetic categories

- Invented business profiles
- Invented customer personas
- Invented product catalogues
- Invented campaign material
- Synthetic operational metadata

Synthetic records must be invented and must not be copied, lightly altered, or
derived from actual Strand Auto Parts or Velani Wholesale records.

## Prohibited categories

- Personal data
- Employee data
- Customer records
- Supplier records
- Transaction data
- Confidential business data
- Credentials and secrets in customer workflows
- External publishing payloads
- Real-outcome learning

Unknown categories are denied. Both approved design-partner tenants are checked
independently; an unapproved tenant cannot obtain a policy decision.

## Retention and deletion

Synthetic rehearsal records have a 30-day maximum validation-cycle retention
and a seven-day deletion target after an approved synthetic deletion request.
Deletion scope includes live SQLite data, approved exports, temporary support
copies, and backups as their retention window expires. Authorization and audit
evidence may retain identifiers and decisions without retaining prompt or
generated customer content in logs.

Real-data retention and deletion periods are intentionally unset. Before any
real-data activation, the founder must approve jurisdiction, controller and
processor roles, notice, lawful basis or consent mechanism, permitted data,
retention, deletion SLA, subprocessors, data location, support access, breach
notification, rollback, and partner-specific acceptance.

## Runtime evidence

`POST /v1/pilot/privacy/pack` returns the authenticated tenant's policy and
identity-bound acceptance status. `POST /v1/pilot/privacy/authorize` evaluates
one named data category with a default-deny decision. Neither endpoint can set
real-data authorization.
