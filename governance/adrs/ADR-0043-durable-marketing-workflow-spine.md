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

## MLAI-033.1 Clarified Implementation Contracts

These contracts clarify the first foundation increment. They authorize no
application, test, persistence, provider, infrastructure, deployment or release
change.

### State-transition contract

The transition validator is default-deny. The complete allowed matrix is:

| Current state | Allowed next states |
|---|---|
| `draft` | `planned`, `cancelled`, `superseded` |
| `planned` | `draft`, `awaiting_approval`, `blocked`, `cancelled`, `superseded` |
| `awaiting_approval` | `planned`, `approved`, `blocked`, `cancelled`, `superseded` |
| `approved` | `awaiting_approval`, `running`, `blocked`, `cancelled`, `superseded` |
| `running` | `blocked`, `failed`, `completed`, `cancelled`, `superseded` |
| `blocked` | its recorded resume state, `failed`, `cancelled`, `superseded` |
| `failed` | none |
| `completed` | none |
| `superseded` | none |
| `cancelled` | none |

`failed`, `completed`, `superseded` and `cancelled` are terminal. Every
unlisted edge, every self-transition and every transition out of a terminal
state is invalid. Exact idempotent replay returns the recorded command outcome
and is not a self-transition.

An invalid transition returns `validation_failed`, preserves the workflow state
and optimistic version, and records only a privacy-safe refusal receipt and
evidence atomically. Changed input under an existing idempotency scope returns
`conflict_detected` before transition evaluation. A tenant or brand mismatch is
denied without confirming that the workflow exists.

Cancellation may occur from every non-terminal state. It stops new local work
but does not claim to reverse an external effect. Supersession may occur from
every non-terminal state only when an immutable successor-workflow reference is
recorded atomically. Both transitions preserve evidence and invalidate pending
approvals.

Entry to `blocked` records the exact non-terminal resume state. Recovery is an
explicit, authorized manual-intervention command that resolves the blocking
condition and may return only to that recorded state after all current
preconditions are re-evaluated. It creates a command receipt and evidence; it
is never an automatic retry. A `failed` workflow is not revived: later recovery
requires a separately created workflow with an immutable predecessor reference;
the failed workflow remains unchanged.

### Canonical encoding and hashing contract

Command requests, command receipts and evidence use the `MLAI-CJ-1` canonical
JSON profile. It adopts RFC 8785 JSON Canonicalization Scheme string escaping
and UTF-16 key ordering after the additional NFC normalization below, while
using a restricted numeric profile so business decimals never depend on binary
floating-point.

#### Strings and UTF-8 bytes

- Normalize every object member name and string value to Unicode NFC before
  duplicate-name detection, ordering or escaping. Reject lone UTF-16 surrogates
  and any non-Unicode-scalar input.
- Escape quotation mark as `\"` and reverse solidus as `\\`. Escape U+0008,
  U+0009, U+000A, U+000C and U+000D as `\b`, `\t`, `\n`, `\f` and `\r`.
  Escape every other U+0000 through U+001F control character as `\u00xx` using
  lowercase hexadecimal digits.
- Do not escape solidus or any other Unicode scalar. Encode all remaining
  characters directly as their shortest valid UTF-8 byte sequence.
- Encode exactly one JSON value with no byte-order mark, leading or trailing
  bytes, line ending or insignificant whitespace.

#### Numbers

- JSON numeric tokens are permitted only for integers in the inclusive I-JSON
  safe range `-9007199254740991` through `9007199254740991`. Encode zero as
  `0`; otherwise use an optional minus sign followed by the shortest base-10
  digits, with no plus sign or leading zero. JSON `-0` is forbidden.
- Quantities not encoded as JSON safe integers, including decimal-valued
  quantities, are JSON strings. Their grammar is an optional minus sign, an
  integer part of `0` or a non-zero digit followed by digits, and an optional
  fractional part consisting of `.` followed by one or more digits.
  A fractional part must end in a non-zero digit. The minus sign is permitted
  only when the mathematical value is non-zero. Therefore leading zeros,
  trailing fractional zeros, negative zero, exponent notation and a trailing
  decimal point are forbidden; canonical zero is the string `"0"`.
- Reject binary floating-point inputs, NaN, positive or negative infinity and
  every exponent-form input before canonicalization. JSON booleans remain
  booleans and are never treated as integers.

#### Keys, structures and timestamps

- After NFC normalization, reject duplicate object member names and sort names
  lexicographically by unsigned UTF-16 code units as required by RFC 8785. Apply
  the rule recursively to every object.
- Preserve array element order exactly; producers must apply any domain-specific
  sorting before canonicalization.
- Omit an optional field when it is absent. Include `null` only when the
  versioned record schema names that field as nullable and null has distinct
  meaning; reject null for every other field. Null and omission are never
  interchangeable.
- Encode timestamps as UTC RFC 3339 `YYYY-MM-DDTHH:MM:SS.ffffffZ`, with exactly
  six fractional digits, no leap second and no timezone offset other than `Z`.
- Every canonical envelope contains `canonicalization_version: "MLAI-CJ-1"`,
  `schema_version` and one of the exact record-kind values defined below. The
  initial command-request, command-receipt and workflow-evidence schemas each
  use integer `schema_version: 1`. A future value requires a separately governed
  schema and never changes the bytes or meaning of version `1`.

#### Domain separation and hash construction

The exact record kinds and ASCII domain strings are:

| Envelope | `record_kind` | Domain string |
|---|---|---|
| Command request | `command_request` | `earthonox/mlai-033.1/command-request/MLAI-CJ-1` |
| Command receipt | `command_receipt` | `earthonox/mlai-033.1/command-receipt/MLAI-CJ-1` |
| Workflow evidence | `workflow_evidence` | `earthonox/mlai-033.1/workflow-evidence/MLAI-CJ-1` |

For each envelope, the SHA-256 input is exactly the UTF-8 bytes of its domain
string, one LF byte `0x0A`, the ASCII bytes of its exact `record_kind`, one LF
byte `0x0A`, and the `MLAI-CJ-1` canonical JSON bytes. There is no trailing LF.
Store and compare the 32-byte SHA-256 digest as exactly 64 lowercase hexadecimal
characters.

#### Command request and receipt envelopes

The canonical command-request envelope contains exactly the version fields and
record kind above plus `request_id`, `tenant_id`, `brand_id`, `workflow_id`,
`expected_workflow_version`, `command_kind`, `idempotency_key_sha256`,
`actor_ref`, `requested_at` and a versioned `safe_command` object. The request
hash excludes receipt identifiers, outcomes, result references, server-recorded
timestamps and evidence digests.

`idempotency_key_sha256` is SHA-256 over the ASCII domain string
`earthonox/mlai-033.1/idempotency-key/MLAI-CJ-1`, one LF byte `0x0A` and the
shortest UTF-8 bytes of the NFC-normalized caller key, with no trailing LF. Its
representation is exactly 64 lowercase hexadecimal characters.

The complete canonical command-receipt envelope is separate from the request
envelope and contains exactly:

- the version fields and `record_kind: "command_receipt"`;
- `receipt_id`, `request_id`, `request_hash`, `tenant_id`, `brand_id`,
  `workflow_id`, `workflow_version_before`, `workflow_version_after`,
  `command_kind`, `idempotency_key_sha256` and `actor_ref`;
- `outcome`, whose only values are `applied`, `rejected` and
  `conflict_detected`;
- nullable `failure_class` and `conflicts_with_receipt_id`, where null is
  meaningful and permitted: `failure_class` is null only for `applied`, and
  `conflicts_with_receipt_id` is non-null only for `conflict_detected`;
- for a `conflict_detected` outcome, `failure_class` is exactly
  `conflict_detected`; for `rejected`, it is the applicable ADR-0043 failure
  class;
- `requested_at`, `recorded_at`; and
- `safe_result_refs`, sorted before canonicalization by normalized `kind`,
  normalized `id` and integer `version`.

Each safe result or source reference is an object containing exactly `kind`,
`id` and positive integer `version`; it contains no display name, URL, customer
content or provider payload.

An exact idempotent replay returns the original persisted receipt bytes and
digest; it creates no replacement receipt. Changed input under the same approved
idempotency scope produces a separately identified `conflict_detected` receipt
that references the original receipt and cannot replace the scope's original
receipt.

#### Evidence envelope and chain

The canonical workflow-evidence envelope contains exactly the version fields
and record kind above plus `evidence_id`, `tenant_id`, `brand_id`, `workflow_id`,
`workflow_version`, `sequence`, `predecessor_sha256`, `actor_ref`, `action`,
`occurred_at`, nullable `from_state`, nullable `to_state`, nullable
`failure_class`, nullable `command_receipt_id`, nullable `approval_ref`, nullable
`artifact_ref`, `reason_code`, `safe_source_refs`, `sanitized_input_sha256` and
`sanitized_output_sha256`. The named nullable fields use null only for their
schema-defined not-applicable meaning. Safe source references use the same
sorting rule as safe result references.

Evidence sequence starts at integer `1` for each tenant-, brand- and
workflow-scoped chain and increments by exactly one without gaps. At sequence
`1`, `predecessor_sha256` is exactly 64 ASCII zero characters. Every later
record contains the lowercase SHA-256 digest of the immediately preceding
canonical evidence envelope. The record's own digest is not a field in its
canonical hash body.

#### Sensitive-field exclusion

All three canonical envelopes exclude raw prompts; credentials; passwords; API
keys; access, refresh and identity tokens; authorization and cookie headers;
session and CSRF values; provider request or response payloads; binary artifact
contents; raw customer-content bodies; direct personal contact details; and any
customer content not necessary to prove the governed action. They use bounded
opaque actor references, canonical artifact references, safe source references
and sanitized content digests instead. A caller-supplied idempotency key must be
a bounded opaque non-secret value; only its lowercase SHA-256 digest is stored
in a canonical envelope without changing the approved idempotency scope.

### Canonical artifact-availability contract

`approved` to `running`, `blocked` back to `running`, and `running` to
`completed` are execution-oriented transitions. Any future command that causes
a paid, publishing, provider or other external side effect is also
execution-oriented even when it does not introduce a new workflow state.

The workflow stores only an immutable canonical artifact reference containing
tenant ID, brand ID, artifact ID, artifact version and repository revision. A
persisted artifact proof also contains its content SHA-256 digest. This
reference does not transfer Campaign Asset or artifact-lifecycle ownership to
the workflow.

A separately implemented `CanonicalArtifactAvailability` repository interface
is the only authority for resolving that reference. Given the expected tenant,
brand and immutable reference, it returns either a tenant-owned, accessible,
non-superseded `reserved` persistence target or a tenant-owned, accessible,
non-superseded `persisted` artifact with an integrity digest. The interface is a
read-only workflow dependency; this decision does not implement it.

Entry to `running` requires a `reserved` or `persisted` proof. Entry to
`completed`, and any future externally visible side effect, requires a
`persisted` proof. A missing repository, missing reference, superseded artifact,
inaccessible artifact, integrity mismatch, or tenant/brand mismatch causes no
workflow-state change and no external action. Tenant/brand mismatch is denied
without disclosing artifact existence. Any privacy-safe refusal receipt and
evidence must be committed without weakening that denial.

### High-impact action classification

Separation of duties is required for:

- authorizing or initiating a paid action, spend reservation or spend
  consumption;
- publishing, campaign launch or externally visible distribution;
- adopting evidence as organizational learning;
- granting a policy, compliance, privacy, tenant-security, approval or hard-limit
  exception or override;
- invoking a provider or connector command that creates, changes or deletes
  external state; and
- cancelling or superseding work after a paid or external side effect has
  started when the command can affect that external state.

The actor requesting one of these actions cannot approve the same workflow
version and action. Ordinary internal planning transitions and read-only
operator-status viewing are not high-impact. An action not explicitly
classified by current governance is `policy_blocked`, makes no state change or
external call and requires later classification authority; its name, adapter or
provider must not be used to infer classification.

## Consequences

- MLAI-033 is Core, not Rabbit.
- Autonomous paid optimization, full attribution, visual generation factories
  and self-running growth agents remain future work.
- The first implementation must build deterministic workflow state,
  idempotency, approval and evidence primitives before agent autonomy.
- Workflow evidence must support later closed-loop learning without treating
  synthetic or incomplete results as proven customer learning.
