# Pilot Incident Response

## Trigger

Treat suspected tenant leakage, credential exposure, unauthorized access,
integrity failure, unrecoverable service failure, or sensitive logging as an
incident.

## Procedure

1. Stop pilot traffic and preserve non-sensitive timestamps and request IDs.
2. Revoke affected sessions and rotate relevant deployment secrets.
3. Keep the original database read-only; create and verify a backup before
   investigation.
4. Determine affected tenant, operation, data class, time window, and control.
5. Restore service only from a verified commit and verified database state.
6. Record cause, scope, corrective action, validation evidence, and owner.
7. Update risks, debt, tests, runbooks, and an ADR/PDR where a durable decision
   changes.

Because customer data is currently prohibited, discovery of real customer data
is itself an incident and the pilot stays stopped until founder review.
