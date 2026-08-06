# MLAI-030 — Founder Design Partner Onboarding

## Purpose

Evaluate signup, privacy, security, recovery, support, and acceptance before a
founder decides whether either design partner may use real business data.

## Current sequence

1. MLAI-030.1 — Founder Design Partner Signup and Tenant Provisioning — complete
2. MLAI-030.2 — External Identity Deployment and Signup Experience — complete
3. MLAI-030.3 — Pilot Privacy and Data Boundaries — complete
4. MLAI-030.4 — Production Identity and Security Readiness — active
5. MLAI-030.5 — Recovery, Monitoring and Support Readiness
6. MLAI-030.6 — Design-Partner Acceptance Rehearsal
7. MLAI-030.7 — Controlled Real-Data Activation

MLAI-030.4 hardens authentication freshness, tenant-bound session revalidation,
audited session revocation, request limits, security headers, and deterministic
production-security evidence. Passing code checks permits controlled security
rehearsal and founder activation assessment only. Deployment evidence must be
recorded explicitly; readiness never authorizes real data.

Strand Auto Parts and Velani Wholesale remain the only approved candidates.
Each has an isolated tenant and must pass every readiness gate independently.
Free full-feature entitlement keeps billing disabled and never grants real-data
permission.

Engineering and controlled synthetic rehearsal are authorized under ADR-0024.
Actual business data, external invitations, public or production activation,
external publishing, real-data learning, billing, unapproved paid services,
and destructive production changes remain frozen.
