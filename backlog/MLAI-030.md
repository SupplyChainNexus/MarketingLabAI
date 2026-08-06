# MLAI-030 — Founder Design Partner Onboarding

## Purpose

Evaluate signup, privacy, security, recovery, support, and acceptance before a
founder decides whether either design partner may use real business data.

## Current sequence

1. MLAI-030.1 — Founder Design Partner Signup and Tenant Provisioning — complete
2. MLAI-030.2 — External Identity Deployment and Signup Experience — complete
3. MLAI-030.3 — Pilot Privacy and Data Boundaries — complete
4. MLAI-030.4 — Production Identity and Security Readiness — complete
5. MLAI-030.5 — Recovery, Monitoring and Support Readiness — complete
6. MLAI-030.6 — Design-Partner Acceptance Rehearsal — complete
7. MLAI-030.7 — Controlled Real-Data Activation — active

MLAI-030.5 makes security, recovery, monitoring, incident and support evidence
immutable, environment- and commit-bound, expiring, and failure-preserving. It
adds deterministic operational alert state and a combined founder-assessment
gate. Passing permits controlled acceptance rehearsal only; readiness never
authorizes real data.

MLAI-030.6 adds a partner- and tenant-bound acceptance assessment over seven
synthetic end-to-end scenarios. It requires the complete MLAI-030.4 and
MLAI-030.5 persisted evidence gates plus current privacy acceptance. Caller
booleans cannot establish acceptance, and each partner passes independently.

Strand Auto Parts and Velani Wholesale remain the only approved candidates.
Each has an isolated tenant and must pass every readiness gate independently.
Free full-feature entitlement keeps billing disabled and never grants real-data
permission.

Engineering and controlled synthetic rehearsal are authorized under ADR-0024.
Actual business data, external invitations, public or production activation,
external publishing, real-data learning, billing, unapproved paid services,
and destructive production changes remain frozen.

MLAI-030.7 selects Velani Wholesale as the first candidate and implements a
two-stage, append-only activation boundary. Selection and passing evidence never
self-authorize activation. Stage one uses an approved external operator with
synthetic content; stage two is limited to explicitly enumerated company and
product categories. All other tenants and high-risk activities remain frozen.
