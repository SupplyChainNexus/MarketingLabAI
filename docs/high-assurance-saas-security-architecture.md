# Earthonox High-Assurance SaaS Security Architecture

## Purpose and status

This document is the governance target established by MLAI-031.18B and
ADR-0051. It preserves the system that exists today and defines the evidence
needed to evolve it into a mature high-assurance SaaS platform. It is not a
claim that every control is implemented or externally configured.

## Preserved architecture

- Google Cloud Identity Platform authenticates customer identities.
- Earthonox owns tenant membership, roles, invitations, entitlements and audit.
- The browser exchanges a validated Google ID token for an opaque, hashed,
  tenant-bound server session.
- PostgreSQL is the canonical hosted datastore; Cloud SQL is the initial managed
  provider and AlloyDB is evidence-triggered future work.
- Cloud Run remains private behind the canonical load-balancer ingress contract.
- The release controller is observational; independent provenance and admission
  controls remain the release authority target.

## Fourteen-layer target

| Layer | Control domain | Required outcome |
|---:|---|---|
| 1 | Governance and classification | Assets, data, threats, owners, residual risk and evidence expiry are explicit. |
| 2 | Edge, DNS and transport | TLS, load-balancer-only ingress, WAF, DDoS, bot and distributed abuse controls protect entry points. |
| 3 | Customer authentication | Identity Platform tokens are cryptographically and semantically validated. |
| 4 | MFA, recovery and step-up | Strong factors and recent authentication protect high-risk actions and recovery. |
| 5 | Token lifecycle | Short-lived tokens, safe refresh boundaries, rotation and revocation are enforced and rehearsed. |
| 6 | Server sessions | Opaque sessions rotate, expire by idle and absolute limits, resist replay and revoke promptly. |
| 7 | Tenant authorization | Server-side membership, role, ownership and operation checks default deny at every boundary. |
| 8 | Application and API | Validation, CSRF, cookies, headers, CORS, error privacy, request and abuse limits are shared controls. |
| 9 | Secrets and workload identity | No source secrets or static service-account keys; least-privilege short-lived identity is standard. |
| 10 | Network and runtime | Private ingress, controlled egress, hardened images, resource bounds and service authorization apply. |
| 11 | PostgreSQL and data | Tenant isolation, encryption, safe migration, retention, backup and restore are evidenced. |
| 12 | Supply chain and security CI | Code, dependencies, secrets, artifacts, infrastructure policy and provenance fail closed. |
| 13 | Detection and telemetry | Central privacy-safe audit, correlation, alerting, ownership and response targets are operational. |
| 14 | Incident response and recovery | Containment, revocation, evidence, communications, restore, DR and lessons are rehearsed. |

## Identity, token and session target

Identity Platform remains authentication authority; it does not become tenant
authorization authority. Upstream ID tokens remain short-lived and are checked
for algorithm, issuer, audience, expiry, issue time, authentication time and
subject. Refresh credentials remain inside the approved provider/client
boundary, are never logged or written to Earthonox persistence and are rotated
or revoked where supported.

Earthonox server sessions remain opaque and hashed at rest. The implementation
target adds idle expiry, absolute expiry, identifier and CSRF rotation at
renewal, rotation after authentication or privilege changes, concurrency and
replay controls appropriate to measured risk, and fast identity-, tenant- and
session-scoped revocation. Renewal may not create an unlimited sliding session.

MFA and step-up are risk controls, not universal friction. Enrollment,
recovery, factor replacement, administrative operations, exports, billing,
security settings and other high-impact actions require policy-defined recent
authentication or step-up. Phishing-resistant factors are preferred where the
selected provider and customer context support them. Exact factors and timing
are selected only after threat modelling and controlled rehearsal.

## Security CI target

The governed pipeline must make missing coverage visible. Applicable stages
include formatting and static checks, secret scanning, SAST, dependency and
license policy, SBOM creation, container and artifact scanning, infrastructure
policy tests, cross-tenant and authorization regressions, session/token
adversarial tests, provenance verification and deployment-policy evaluation.
Every required control reports `passed`, `failed`, `not_applicable` with a
reason, or `not_implemented`; silent omission is failure.

CI is necessary evidence, not proof of deployed effectiveness. Edge, identity,
logging, backup, incident and recovery controls require environment-bound
inspection and rehearsal after separately authorized configuration.

## Detection, incident and recovery target

Identity, authorization, session, administrative, tenant, edge, runtime,
PostgreSQL and release events feed centralized privacy-safe detection. Alerts
have an owner, severity, response target, escalation path, runbook and evidence
retention rule. Customer secrets and submitted content are excluded from routine
security telemetry.

Incident response covers detection, triage, containment, session and credential
revocation, evidence preservation, affected-tenant analysis, required
communication, recovery, validation and post-incident corrective action. Backup
existence is insufficient: isolated restore and disaster-recovery objectives
must be rehearsed and tied to the deployed commit and data boundary.

## Assurance maturity

For every layer, track these separate states:

1. `documented`
2. `implemented`
3. `externally_configured`
4. `rehearsed`
5. `operationally_evidenced`

No state is inferred from a later state in another environment. Evidence binds
the control version, environment, deployment commit, observation time, expiry,
owner and sanitized reference. Failures remain visible until a durable repair
and fresh evidence close them.

## Current gaps and sequence boundary

Current foundations already cover strict token verification, bounded sessions,
hashed session storage, CSRF, secure cookies, membership revalidation, tenant
authorization, session revocation and readiness evidence. The next authorized
security implementation must begin with a repository-confirmed threat model and
session/token lifecycle design. Edge, detection delivery, incident rehearsal
and security-CI expansion follow as explicit evidence-gated stories. No control
in this document authorizes cloud configuration, customer activation or release
state changes.
