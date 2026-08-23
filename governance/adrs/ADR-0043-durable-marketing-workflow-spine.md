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
Brief, publishing and learning authorities. They did not themselves authorize
implementation and select no numeric policy value, provider mechanism, queue,
cloud service or deployment architecture. The durable workflow foundation was
subsequently implemented and tested within those boundaries.

## MLAI-033.1 Clarified Implementation Contracts

These contracts clarified the first foundation increment and did not themselves
authorize application, test, persistence, provider, infrastructure, deployment
or release change. The durable workflow foundation was subsequently implemented
and tested; deferred capabilities retain their separate authority boundaries.

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

Command requests, command receipts and evidence use the versioned `MLAI-CJ`
canonical JSON profiles. Their shared encoding rules adopt RFC 8785 JSON
Canonicalization Scheme string escaping
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
- Every canonical envelope contains `canonicalization_version`,
  `schema_version` and one of the exact record-kind values defined below. The
  initial command-request, command-receipt and workflow-evidence schemas use
  `canonicalization_version: "MLAI-CJ-1"` and integer `schema_version: 1`.
  Their bytes, fields and meanings are frozen. In particular, version 1 keeps
  its exact `workflow_id` field; it is never renamed, replaced or reinterpreted.
- MLAI-CJ-2 command requests and command receipts use
  `canonicalization_version: "MLAI-CJ-2"` and integer `schema_version: 2`.
  New workflow-foundation request and receipt writers emit version 2. Readers
  dispatch on the exact pair of version fields, distinguish version 1 from
  version 2, and reject every unsupported or mismatched pair deterministically.
  They never silently convert, rewrite or rehash persisted canonical bytes.
  Workflow evidence remains on its frozen MLAI-CJ-1 version-1 schema unless a
  later governed evidence schema is approved. MLAI-CJ-2 uses the same escaping,
  NFC normalization, UTF-16 key ordering, restricted-number, omission, null,
  timestamp and UTF-8 rules above; its distinct version fields, domains and
  envelope schemas provide the version separation.

#### Domain separation and hash construction

The exact record kinds and ASCII domain strings are:

| Envelope and version | `record_kind` | Domain string |
|---|---|---|
| MLAI-CJ-1 command request, schema 1 | `command_request` | `earthonox/mlai-033.1/command-request/MLAI-CJ-1` |
| MLAI-CJ-1 command receipt, schema 1 | `command_receipt` | `earthonox/mlai-033.1/command-receipt/MLAI-CJ-1` |
| MLAI-CJ-1 workflow evidence, schema 1 | `workflow_evidence` | `earthonox/mlai-033.1/workflow-evidence/MLAI-CJ-1` |
| MLAI-CJ-2 command request, schema 2 | `command_request` | `earthonox/mlai-033.1/command-request/MLAI-CJ-2` |
| MLAI-CJ-2 command receipt, schema 2 | `command_receipt` | `earthonox/mlai-033.1/command-receipt/MLAI-CJ-2` |

For each envelope, the SHA-256 input is exactly the UTF-8 bytes of its domain
string, one LF byte `0x0A`, the ASCII bytes of its exact `record_kind`, one LF
byte `0x0A`, and the canonical JSON bytes for the envelope's declared MLAI-CJ
version. There is no trailing LF.
Store and compare the 32-byte SHA-256 digest as exactly 64 lowercase hexadecimal
characters.

#### Command request and receipt envelopes

The frozen MLAI-CJ-1 schema-1 command-request envelope contains exactly its
version fields and record kind plus `request_id`, `tenant_id`, `brand_id`,
`workflow_id`, `expected_workflow_version`, `command_kind`,
`idempotency_key_sha256`, `actor_ref`, `requested_at` and a versioned
`safe_command` object. Its frozen command-receipt envelope contains exactly its
version fields, `record_kind: "command_receipt"`, `receipt_id`, `request_id`,
`request_hash`, `tenant_id`, `brand_id`, `workflow_id`,
`workflow_version_before`, `workflow_version_after`, `command_kind`,
`idempotency_key_sha256`, `actor_ref`, `outcome`, nullable `failure_class`,
nullable `conflicts_with_receipt_id`, `requested_at`, `recorded_at` and
`safe_result_refs`, with the frozen meanings, value restrictions and sorting
rules governed before MLAI-CJ-2. MLAI-CJ-2 does not redefine those bytes.

The MLAI-CJ-2 schema-2 canonical command-request envelope contains exactly its
version fields and record kind plus `request_id`, `tenant_id`, `brand_id`,
`request_workflow_id`,
`expected_workflow_version`, `command_kind`, `idempotency_key_sha256`,
`actor_ref`, `requested_at` and a versioned `safe_command` object. The request
hash excludes receipt identifiers, outcomes, result references, server-recorded
timestamps and evidence digests. `request_workflow_id` is the immutable workflow
identifier supplied by the caller. It participates in the canonical request
bytes and request hash and is never rewritten during replay, conflict handling,
recovery or persistence.

For MLAI-CJ-1, `idempotency_key_sha256` remains SHA-256 over the ASCII domain
string `earthonox/mlai-033.1/idempotency-key/MLAI-CJ-1`. For MLAI-CJ-2 it is
SHA-256 over `earthonox/mlai-033.1/idempotency-key/MLAI-CJ-2`. In each case the
domain is followed by one LF byte `0x0A` and the
shortest UTF-8 bytes of the NFC-normalized caller key, with no trailing LF. Its
representation is exactly 64 lowercase hexadecimal characters.

The complete MLAI-CJ-2 schema-2 canonical command-receipt envelope is separate
from the request envelope and contains exactly:

- the version fields and `record_kind: "command_receipt"`;
- `receipt_id`, `request_id`, `request_hash`, `tenant_id`, `brand_id`,
  `request_workflow_id`, `workflow_version_before`, `workflow_version_after`,
  `command_kind`, `idempotency_key_sha256` and `actor_ref`;
- `authoritative_workflow_id` exactly when an existing authoritative workflow
  differs from `request_workflow_id`; otherwise that field is omitted and is
  never encoded as null;
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
content or provider payload. In an MLAI-CJ-2 recovery-conflict receipt, the
existing-successor reference has exact `kind: "workflow"`, `id` equal to the
existing successor identifier and `version` equal to that successor's
authoritative optimistic workflow version when the conflict receipt is
created. The original-authoritative-receipt reference has exact
`kind: "command_receipt"`, `id` equal to that receipt identifier and
`version: 1`, where `1` is the immutable receipt-record version and is not an
MLAI-CJ envelope schema version. Sorting by normalized `kind`, normalized `id`
and integer `version` places `command_receipt` before `workflow`; no caller or
writer order is preserved.

An exact idempotent replay returns the original persisted receipt bytes and
digest; it creates no replacement receipt. Changed input under the same approved
idempotency scope produces a separately identified `conflict_detected` receipt
that references the original receipt and cannot replace the scope's original
receipt.

For failed-workflow recovery, the proposed successor identifier is always
`request_workflow_id` and is hashed as supplied. If successor `B` already owns
the failed predecessor and a request proposes successor `A`, the persisted
MLAI-CJ-2 conflict receipt contains `request_workflow_id: A`,
`authoritative_workflow_id: B`, `outcome: "conflict_detected"` and
`conflicts_with_receipt_id` equal to the original authoritative recovery
receipt. Its `safe_result_refs` contain exactly the safe workflow reference for
`B` and the safe command-receipt reference for that original receipt, using the
reference schema and ordering above. Both `workflow_version_before` and
`workflow_version_after` equal `B`'s authoritative optimistic workflow version
at the moment the receipt is written. No workflow mutation occurs, and no
receipt may state or imply that the original request targeted `B`.

The first request proposing `A` persists its conflict receipt under its own
approved idempotency scope. Exact replay of that request returns the original
persisted MLAI-CJ-2 conflict receipt bytes and digest. A request proposing a different successor
identifier has different canonical request bytes and its own deterministic
conflict receipt referencing `B`; it neither reuses nor rewrites the receipt
for `A`.

Receipt persistence ownership and foreign-key association are separate from
immutable request identity. When requested workflow `A` was never created and
authoritative workflow `B` exists, the storage-only ownership and foreign-key
association must bind the conflict receipt to `B`. The receipt must safely
reference `B` and `B`'s original authoritative receipt. That association binds
the receipt to the existing
`authoritative_workflow_id`; that association is not a canonical receipt field
and cannot alter `request_workflow_id` or its request hash. The canonical
receipt includes both identity fields whenever the authoritative identifier is
present. Authority lookup, ownership association, safe references and replay
remain tenant-and-brand scoped. A mismatch fails closed without returning
either workflow identity or the authoritative receipt identity across tenant or
brand boundaries.

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

### MLAI-033.2 planning-to-approval API orchestration

Resumable planning-to-approval API operations use a provider-neutral durable
orchestration root plus operation-level child claims. The root remains the
workflow reservation; each child owns only its durable request claim,
server-determined workflow identity reference, original canonical subcommand
material, progress state and final safe HTTP response. Neither level is a workflow aggregate,
approval authority, workflow-evidence store, authorization-audit record,
Campaign Plan owner or Marketing Brief owner.

The existing API idempotency boundary remains a completed-response cache.
Workflow command receipts and workflow evidence remain the authoritative domain
records. Before the first authority-changing command, orchestration persistence
must durably claim a client-generated idempotency key containing at least 128
bits of entropy and store the workflow identity plus the original canonical
subcommand request IDs,
timestamps, command kinds, expected workflow versions and privacy-safe command
material. Workflow identity uses a separately versioned, domain-separated
derivation. `mwf_` output is 32 lowercase hexadecimal characters after the
prefix, and a fixed golden input, canonical preimage and digest are mandatory.
The pseudonymous `act_` reference uses a separate versioned domain over
authenticated provider and subject identity, with a fixed golden vector;
display names, sessions, CSRF values and tenant membership are excluded. Raw
keys must not be logged or returned. Client keys require at least 128 bits of
entropy; accepted encoding, format and length are implementation-validated and
golden-tested.

An exact retry reuses the original canonical command bytes and reconciles only
steps not already proven by authoritative workflow records. Changed input under
the same orchestration authority returns a deterministic conflict. Recovery
after an immutable approval exists must reuse that approval and apply only a
missing transition; orchestration state cannot recreate, replace or reinterpret
approval authority.

The HTTP contract version, MLAI-CJ-2 envelope `schema_version: 2`, and workflow
safe-command `schema_version: 1` are independent version domains. No dispatcher,
retry or migration may silently convert, reinterpret or rehash persisted
canonical bytes. Planning-to-approval POST operations retain existing session
and CSRF enforcement. Technical details are omitted, rather than disclosed, for
callers without `APPROVE`.

This boundary ends at `approved`. It cannot initiate `running`, generation,
publishing, spend, provider activity, external effects or learning. A future
schema migration is required, but historical migrations remain unchanged and
this decision creates no migration authority. Retention and archival remain
deferred for separate governance.

The six implementation contracts are resolved by this boundary. Implementation
remains separately unauthorized and must be split into: A canonical identity
contracts and vectors; B orchestration persistence and migration; C API
orchestration; D approval evidence reconciliation; and E customer workspace.
Sub-command IDs and command-key digests are versioned and domain-separated;
original timestamps and canonical bytes are immutable. Orchestration claims are
tenant/brand/actor/operation/key-digest unique, monotonic and fail-closed on
recovery discrepancies. Approval evidence requires exact scoped selection,
canonical digest and chain validation. Legacy API idempotency remains readable;
new orchestration records store only digests and safe material.

#### Operation-claim amendment

This amendment supersedes the earlier `workflow_api_orchestrations`-only
design for operation-level claims. `workflow_api_orchestrations` remains the
workflow-level root; `workflow_api_operation_claims` is now required for
operation-scoped claims. The revised C1–C4 sequence supersedes the earlier C/D
sequence. Exact replay, approval recovery and concurrent approval guarantees
depend on migration 20 and the child-claim table.

`workflow_api_orchestrations` remains the workflow-level reservation/root;
`workflow_api_operation_claims` is the operation-level child boundary. Each
operation claim has immutable command-plan material, progress, optimistic
version, idempotency digest and final safe response. Claims are unique by
tenant, brand, actor reference, operation and client-key digest, while parent
workflow reservation uniqueness remains unchanged. Exact replay returns the
stored original response bytes. Approval recovery reconciles the approval,
receipt, evidence, workflow state and child progress; contradictory state fails
closed without mutation.

Migration 20 is additive, SQLite-canonical, PostgreSQL-compatible and
non-cascading, with schema-readiness and disposable rehearsal validation.
Retention and archival remain deferred. The revised implementation sequence is
C1 migration 20 and child-claim persistence; C2 create/plan/status/request-
approval and exact replay; C3 approval/rejection and evidence-bound recovery;
and C4 concurrency, rehearsal, regression and acceptance. This amendment adds
no execution, publishing, provider, spend, learning, workspace, SOC 2, cloud,
deployment or release authority.

## Consequences

- MLAI-033 is Core, not Rabbit.
- Autonomous paid optimization, full attribution, visual generation factories
  and self-running growth agents remain future work.
- The implemented and tested foundation provides deterministic workflow state,
  idempotency, approval and evidence primitives before agent autonomy.
- Workflow evidence must support later closed-loop learning without treating
  synthetic or incomplete results as proven customer learning.
