# ADR-0037: Durable first-service private bootstrap

**Status:** Accepted and binding

## Context

Cloud Run cannot create a zero-traffic revision when the canonical service does
not yet exist. Treating platform traffic, IAM invocation authority and pilot
exposure as one control made the release catalogue impossible to execute
truthfully.

## Decision

`REVISION_CREATED` has two explicit modes. An absent canonical service uses
`FIRST_PRIVATE_REVISION`: one digest-pinned revision, private ingress, no public
principal and no pilot invoker grant. An existing private service uses
`ZERO_TRAFFIC_REVISION`: one digest-pinned revision receiving zero platform
traffic. Public, ambiguous or unreadable service state fails closed.

The pre- and post-mutation state hashes, creation mode, revision, digest,
traffic, ingress, principals, operation identifier and authorization are bound
into evidence. The legacy controller remains observational; external
attestation and deployment admission remain authoritative.

`PRIVATE_TRAFFIC_AUTHORIZED` remains a separate founder decision and
`PRIVATE_TRAFFIC_ROUTED` remains the only later gate that can expose the
validated revision to approved private pilot identities.

## Production prerequisites locked for later bounded stories

- Direct VPC subnet capacity is measured before Direct VPC activation.
- Cloud Run maximum scale is bounded by a documented database connection budget.
- Secure connectivity is not misrepresented as pooling; application pooling and
  Managed Connection Pooling or governed PgBouncer are required before scaling.
- Public ingress requires an external load balancer, Cloud Armor,
  `internal-and-cloud-load-balancing`, direct-endpoint negative tests and drift
  prevention.

## Consequences

Existing runs bound to the superseded catalogue remain historical, incomplete
and non-deployable. They are never repaired or backfilled. A new commit requires
a new image and provenance chain.
