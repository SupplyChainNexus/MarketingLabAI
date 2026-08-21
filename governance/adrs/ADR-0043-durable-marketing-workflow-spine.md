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

## MLAI-033.1 Founder-Approved Foundation Decisions

The founder approved the following implementation boundaries on 2026-08-21:

1. One workflow per executable governed marketing-work instance.
2. Campaign Plan and workflow retain independent lifecycles; workflow stores
   immutable references to specific Campaign Plan versions and never mutates
   Campaign Plan state.
3. Approvals are immutable and bound to workflow version and action. Separation
   of duties applies to high-impact actions.
4. No automatic retries until retry ceilings and timing are separately approved.
5. Workflow command idempotency is scoped to tenant, brand, workflow, command
   kind, and caller-supplied key, using canonical request hashing.
6. Evidence is versioned, canonical, privacy-safe, append-only, hash-linked,
   sequence-ordered, and committed atomically with authority-changing state.
7. Cancellation and supersession are terminal transitions that preserve
   evidence and invalidate pending approvals.
8. Execution fails closed when canonical artifact persistence is unavailable.
9. Operator status exposes safe business state first, with technical details
   progressively disclosed only when authorized.

These decisions preserve the separate Campaign Plan, Campaign Asset, Marketing
Brief, publishing and learning authorities. They authorize no implementation
and select no numeric policy value, provider mechanism, queue, cloud service or
deployment architecture.

## Consequences

- MLAI-033 is Core, not Rabbit.
- Autonomous paid optimization, full attribution, visual generation factories
  and self-running growth agents remain future work.
- The first implementation must build deterministic workflow state,
  idempotency, approval and evidence primitives before agent autonomy.
- Workflow evidence must support later closed-loop learning without treating
  synthetic or incomplete results as proven customer learning.
