# ADR-0043: Durable Marketing Workflow Spine

## Status

Accepted

## Context

MarketingLabAI's long-term promise is an AI Marketing Department for growing
businesses. The product cannot safely reach that promise through isolated
agents, ad hoc publishing calls or provider-specific execution flows.

Recent release-control work showed the same architectural lesson at the
infrastructure layer: reliable automation needs one state model, one approval
surface, idempotent resume, explicit failure classes and machine-verifiable
evidence. Campaign execution needs the same discipline before autonomous
distribution, boosting, attribution or closed-loop learning can scale.

## Decision

MarketingLabAI will introduce a durable marketing workflow spine as a core
architecture epic. The workflow spine owns campaign and marketing-work state,
approval boundaries, idempotency, evidence, retries, failure classification,
budget guardrails and operator status.

Agents and external systems do not own core workflow state. Intent routing,
visual formatting, opportunity detection, attribution, Cloud Tasks, social
platforms, email providers, Shopify and analytics tools are adapters that act
through the workflow spine.

## Required Workflow States

- `draft`
- `planned`
- `awaiting_approval`
- `approved`
- `running`
- `blocked`
- `failed`
- `completed`
- `superseded`
- `cancelled`

## Failure Taxonomy

- `validation_failed`
- `auth_required`
- `provider_error`
- `rate_limited`
- `policy_blocked`
- `budget_blocked`
- `conflict_detected`
- `needs_human_decision`

## Consequences

- MLAI-033 is Core, not Rabbit.
- Autonomous paid optimization, full attribution, visual generation factories
  and self-running growth agents remain future work.
- The first implementation must build deterministic workflow state,
  idempotency, approval and evidence primitives before agent autonomy.
- Workflow evidence must support later closed-loop learning without treating
  synthetic or incomplete results as proven customer learning.
