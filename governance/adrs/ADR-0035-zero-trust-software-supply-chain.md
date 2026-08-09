# ADR-0035 — Zero-Trust Software Supply-Chain Authority

## Status

Accepted — founder authorized on 2026-08-09

## Context

The repository release controller correctly improved sequencing, but mutable
controller state and retrospective repair cannot provide independent release
authority. Missing authorization bindings exposed the risk of treating an
orchestrator as both record keeper and trust root.

## Decision

MarketingLabAI adopts a provenance-based zero-trust release architecture.
Controller state is observational and never deployment authority. Every
deployable artifact must be digest-pinned and supported by authentic build
provenance, independently signed in-toto gate attestations, exact RFC 3161
timestamp coverage, a versioned policy-bundle digest, and a final release
authorization signed by an identity that did not build or test the artifact.

Cloud Run must ultimately enforce the final authorization through Binary
Authorization and organization policy. A future GKE runtime must enforce the
same claims at admission using a cryptographic image-attestation verifier plus
policy evaluation. Pipeline credentials cannot disable enforcement, use signing
keys, or exercise break-glass authority.

Legacy controller runs remain historical and non-deployable. Backfills,
attestations created after the fact, or repaired controller state may document
a defect but cannot convert a legacy run or artifact into an authorized
release. The first enforced release must be rebuilt through the hardened path.

## Progressive implementation

1. Lock schemas, trust policy, separation of duties, and shadow verification.
2. Produce hosted-builder provenance, SBOMs, signatures, and timestamps.
3. Run independent evidence verification in shadow mode.
4. Establish an isolated final release authority.
5. observe Binary Authorization decisions on a synthetic canary.
6. Enforce Binary Authorization before routing private synthetic traffic.
7. Remove controller deployment authority and archive legacy ledgers.

Repository work in stages 1 through 3 performs no cloud mutation and cannot
issue release authorization. API enablement, KMS keys, attestors, organization
policy, deployment, traffic, public access, invitations, billing, publishing,
real-customer data, and real-data learning each remain separately authorized.

## Consequences

A misconfigured controller cannot make an artifact deployable. The system adds
key lifecycle, timestamp, evidence retention, and policy operations that must
be implemented and rehearsed before enforcement. SLSA Build Level 3 is the
target; the product will not claim a level unsupported by current evidence.
