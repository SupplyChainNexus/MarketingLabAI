# ADR-0024 — Controlled Pilot Development Unfreeze

## Status

Accepted by the founder on 2026-08-06. Supersedes the broad interpretation of
the founder-frozen customer pilot. It does not authorize real customer data or
external design-partner activation.

## Context

The original founder freeze prevented premature customer-data processing while
identity, privacy, recovery and support controls were incomplete. The phrase
became broad enough to discourage full client-interface development, realistic
browser rehearsal and reversible quality improvement even though those
activities can be performed with controlled identities and synthetic data.

## Decision

MarketingLabAI distinguishes three states:

1. **Engineering and quality development — authorized.**
2. **Controlled synthetic design-partner rehearsal — authorized.**
3. **Real-customer activation — frozen.**

Authorized activity includes complete application development, client-interface
work, controlled development deployment, approved Google OAuth test identities,
synthetic isolated Strand Auto Parts and Velani Wholesale tenants, synthetic
invitation claiming, browser and accessibility tests, logout, recovery,
revocation, backup, security and failure rehearsal, and free-tier services
already approved by ADR-0022.

Synthetic records must be invented. They may not copy customer, employee,
supplier, transaction or confidential operational information from either
business.

## Frozen activation boundary

Explicit founder approval remains required before:

- actual Strand Auto Parts or Velani Wholesale business data is processed;
- external design-partner invitations are delivered;
- public self-service signup or production access is enabled;
- the OAuth audience is published beyond its controlled test users;
- generated content is published to an external channel;
- real-data analytics or learning is activated;
- customer billing, paid identity extensions, SMS or Cloud Functions are
  enabled; or
- a destructive or irreversible production migration occurs.

## Runtime interpretation

Runtime and readiness reports use `synthetic_rehearsal_authorized` and
`real_data_activation_authorized` as separate facts. The real-data value remains
false. A successful readiness checklist means ready for an activation decision,
not activated.

The canonical status is `real_data_activation_frozen`; the former generic
`founder_frozen` status is superseded.

## Consequences

The freeze no longer blocks product completion or meaningful synthetic
rehearsal. It continues to protect privacy, production access, external partner
communications and commercial commitments. Synthetic rehearsal is engineering
evidence, not market validation or organizational learning.
