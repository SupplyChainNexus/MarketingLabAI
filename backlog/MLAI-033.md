# MLAI-033: Durable Marketing Workflow Spine

## Status

Founder-locked core architecture epic

## Classification

Core. Not Rabbit.

## Purpose

MarketingLabAI needs one durable workflow spine for campaign planning,
approval, execution, recovery, evidence and later learning. Agents may
recommend or perform work, but workflow state, approval boundaries, retry
rules, budget limits and evidence belong to the product core.

## Scope

- Durable state model:
  `draft`, `planned`, `awaiting_approval`, `approved`, `running`, `blocked`,
  `failed`, `completed`, `superseded`, `cancelled`.
- Idempotency keys for customer-facing and cost-bearing actions.
- One approval model for publish, spend, boost, campaign launch, learning
  adoption and exception handling.
- Append-only workflow evidence ledger with actor, timestamp, input, output,
  source references, decision reason, failure reason, retry count and hashes.
- Failure taxonomy:
  `validation_failed`, `auth_required`, `provider_error`, `rate_limited`,
  `policy_blocked`, `budget_blocked`, `conflict_detected`,
  `needs_human_decision`.
- Operator status contract exposing current state, next action, blocked reason,
  available retry, required approval and evidence.
- Adapter boundary for Cloud Tasks, social channels, email, Shopify, analytics
  and future providers.
- Budget and risk guardrails for any paid or externally visible action.
- Learning hooks so completed workflows can later emit structured campaign
  learning evidence.

## Explicit Exclusions

- No autonomous paid optimization.
- No full attribution engine.
- No visual generation factory.
- No self-running growth agent.
- No real-customer automation until tenant, approval, budget and audit controls
  are proven.

## Acceptance

- The workflow spine is documented as a product architecture boundary.
- The Rabbit Rule classification is recorded.
- Agent, provider and Cloud Tasks execution remain adapters, not core state.
- The first implementation story starts with deterministic workflow state,
  idempotency, evidence and approval primitives before autonomous agents.
