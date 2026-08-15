# ADR-0051: Defense-in-Depth Customer Identity, Session and Platform Security

Status: Accepted architecture direction; implementation remains separately gated

## Context

Earthonox already uses Google Cloud Identity Platform for customer
authentication, application-owned tenant authorization, hashed and revocable
server sessions, PostgreSQL persistence, private Cloud Run ingress and a
zero-trust release-control architecture. These controls are compatible but do
not yet form a complete high-assurance security operating model.

The current repository validates short-lived Google ID tokens, bounds
authentication age, revalidates tenant membership on each session use, protects
state-changing requests with CSRF tokens and supports current-session and
identity-and-tenant session revocation. It does not yet implement renewable and
rotating server sessions, risk-based step-up authentication, full provider-token
revocation orchestration, edge enforcement, centralized detection delivery or
the complete security-CI and incident-recovery evidence required for a mature
customer service.

## Decision

Earthonox will evolve the existing architecture through fourteen coordinated
defense-in-depth layers. No layer is a substitute for another, and a passing
repository test does not prove an external control is deployed or effective.

1. **Security governance and data classification** - threat models, asset and
   data classification, control ownership, risk acceptance, evidence expiry and
   activation gates are explicit and reviewable.
2. **Edge, DNS and transport protection** - managed DNS, TLS, load-balancer-only
   ingress, DDoS protection, web application firewall policy, bot and abuse
   controls and distributed rate limits protect public entry points.
3. **Customer authentication** - Google Cloud Identity Platform remains the
   selected customer authentication provider behind the provider-neutral
   adapter. Issuer, audience, signature, expiry, issue time, authentication time
   and subject validation remain mandatory.
4. **MFA, account recovery and step-up authentication** - phishing-resistant
   factors are preferred where supported. MFA enrollment, recovery and
   sensitive-operation step-up are risk-based, audited and protected against
   account-recovery bypass.
5. **Token lifecycle and revocation** - identity tokens are short-lived;
   refresh credentials remain in the approved provider/client boundary, are
   rotated where supported, never enter logs or application persistence, and
   can be revoked after logout, compromise, recovery or administrator action.
6. **Server-session security** - Earthonox continues to exchange a validated
   identity token for an opaque, hashed, tenant-bound server session. Sessions
   have idle and absolute expiry, rotate on login, renewal and privilege or
   authentication-state change, detect replay where practical, and are
   invalidated by membership, identity, security and administrator events.
7. **Tenant authorization and resource isolation** - caller-supplied tenant and
   object identifiers remain filters, never authority. Membership, role,
   ownership and operation are checked server-side with default deny and
   cross-tenant regression coverage.
8. **Application and API protection** - strict validation, request bounds,
   secure cookies, CSRF protection, security headers, safe CORS, output
   encoding, abuse controls and privacy-safe errors are enforced at shared
   application boundaries.
9. **Secrets, workload identity and least privilege** - secrets remain outside
   source and logs; workloads use dedicated identities and short-lived
   credentials; service-account key files and broad reusable credentials are
   forbidden.
10. **Network and runtime isolation** - private Cloud Run ingress, controlled
    egress, hardened immutable containers, bounded resources and explicit
    service-to-service authorization preserve the existing hosting boundary.
11. **Data and PostgreSQL protection** - tenant-scoped access, encryption,
    migration safety, connection limits, backup, restore, retention and
    deletion evidence protect the canonical PostgreSQL datastore. Cloud SQL
    remains the initial managed provider under ADR-0048.
12. **Software supply chain and security CI** - protected review, secret
    scanning, SAST, dependency and license review, SBOM and artifact scanning,
    infrastructure-policy testing, provenance verification, adversarial
    tenant/session tests and fail-closed release gates run at defined stages.
13. **Centralized audit, detection and response telemetry** - authentication,
    authorization, tenant, session, administrative, edge, runtime, database and
    release signals are centralized with privacy-safe correlation, alert
    ownership, severity, response targets and evidence retention.
14. **Incident response, resilience and recovery** - tested playbooks cover
    containment, credential and session revocation, tenant communication,
    forensic evidence preservation, backup restoration, disaster recovery,
    post-incident review and control improvement.

### Session and token contract

- The browser may hold the upstream ID token only long enough to establish the
  server session. The application must not persist provider refresh tokens.
- Server-session renewal is explicit, bounded and evidence-backed. Renewal must
  rotate the session identifier and CSRF secret and must not extend the absolute
  lifetime indefinitely.
- Privilege changes, MFA changes, password or provider-account recovery,
  suspicious activity and administrator revocation invalidate applicable
  sessions. Provider token revocation is invoked where the provider supports it
  and remains distinct from server-session revocation.
- Sensitive actions require recent authentication and, according to recorded
  risk, step-up authentication. Exact durations and factor policies require a
  separate implementation story and controlled rehearsal; they are not guessed
  in this governance lock.

### Assurance and activation contract

Each layer is reported as `documented`, `implemented`, `externally configured`,
`rehearsed` and `operationally evidenced`. A layer cannot be promoted by prose,
an unsupported boolean or a green unit test. Evidence is environment-, commit-
and control-version-bound, expires, retains failures and names an owner.

Real-customer activation requires the applicable layers and residual risks to
pass their authorized gates. Defense in depth reduces risk; it does not justify
a claim of perfect security or zero possibility of compromise.

## Preserved decisions

- ADR-0011 remains authoritative for provider-neutral identity and tenant
  authorization.
- ADR-0022 remains authoritative for Google Cloud Identity Platform.
- ADR-0026 and ADR-0027 remain authoritative for identity, security, monitoring
  and recovery evidence.
- ADR-0030, ADR-0038 and ADR-0048 remain authoritative for Cloud Run,
  PostgreSQL and private ingress.
- ADR-0035, ADR-0039 and ADR-0047 remain authoritative for zero-trust release,
  orchestration and cloud execution identities.

## Consequences

Security work now has one target model and one evidence vocabulary instead of
isolated controls. The target adds cost and operational responsibility, so
controls are introduced progressively before the risk boundary they protect
opens. Implementation must extend current components where sound and requires
separately authorized stories, threat models, tests, external configuration and
rehearsal. This ADR performs no authentication, cloud, IAM, Identity Platform,
Secret Manager, database, deployment or release-state mutation.
