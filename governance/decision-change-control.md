# Decision Change Control

## Decision classes

| Class | Examples | Required record | Approval |
|---|---|---|---|
| Product | Identity, promise, audience, tier philosophy, scope | PDR | Founder |
| Architecture | Domain boundaries, dependency direction, persistence, security model | ADR | Engineering review; founder when product direction changes |
| Delivery | Story sequencing, implementation technique, tooling | Backlog/story record; ADR only if durable | Engineering steward |
| Operational | Temporary command, diagnostic, generated artifact | Work evidence | Implementer |

## Required change process

1. Identify the current authoritative decision.
2. State the problem and new evidence.
3. Apply the Rabbit Rule: Core, Future, or Rabbit.
4. Describe alternatives, risks, migration, and affected documents.
5. Obtain the required approval.
6. Record supersession explicitly.
7. Update code, tests, documentation, roadmap, and handover together.

## Prohibited changes

- Silent reinterpretation of locked language
- Product drift hidden inside a technical refactor
- Treating an unverified AI recommendation as approval
- Replacing a domain because its existing implementation was not inspected
- Presenting deferred or hypothetical capabilities as implemented
- Changing quality, compliance, or correctness by subscription tier

## Emergency exception

An urgent reversible security or data-protection correction may precede its ADR.
The decision record and affected authority documents must be completed before
the change is considered closed.
