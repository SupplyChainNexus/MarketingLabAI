# ADR-0014 - Pilot Operations and Release Gate

## Status

Accepted

## Date

2026-08-05

## Context

The canonical pilot journey was functionally usable with synthetic data but
lacked a hardened runtime, revocable browser sessions, rate limits,
privacy-safe logs, recovery evidence, health checks, CI, and operator policy.
The founder has separately frozen any customer pilot until a later explicit
decision.

## Decision

Run the controlled WSGI service with Waitress 3.0.2 behind HTTPS or a trusted
TLS terminator. Compose deployment through environment-selected external
identity and AI-provider factories; provider secrets never enter source.

Exchange verified upstream identity credentials for short-lived random pilot
sessions. Persist only keyed token and CSRF hashes, bind each session to its
tenant, use Secure/HttpOnly/SameSite cookies, require CSRF proof for mutations,
and support revocation. Keep membership authority inside MarketingLabAI and
external credential verification behind `IdentityProviderAdapter`.

Add process-local rate limiting for the initial single-instance pilot,
privacy-safe JSON events, liveness and evidence-based readiness endpoints,
online SQLite backup, integrity verification, restore-to-new-destination,
operator runbooks, and remote quality gates.

The engineering gate may report the synthetic pilot ready, but it always
reports the customer pilot unauthorized while the founder freeze remains.
`MLAI_ALLOW_REAL_CUSTOMER_DATA=true` is rejected rather than treated as an
ordinary deployment switch.

## Dependency direction

Operational composition depends on the canonical application, authorized API,
workspace, provider-neutral identity contract, and SQLite boundary. Domain
models do not depend on WSGI, Waitress, environment variables, sessions, or
deployment factories.

## Consequences

- Synthetic operations are repeatable, observable, recoverable, and gated.
- Raw upstream credentials are not retained in sessions or browser assets.
- A future approved identity adapter can be selected without changing domains.
- Multi-instance rate limiting and distributed sessions remain future work if
  pilot scale proves they are required.
- No real customer data is authorized by this story.

## Validation

Configuration, TLS, secret length, hashed sessions, tenant binding, CSRF,
revocation, rate limits, privacy redaction, migration 13, backup, restore,
integrity, health/readiness, continuity, focused regression, and complete
regression are automated.
