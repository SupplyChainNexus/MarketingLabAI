# Quality Gates

Every production increment must pass:

1. Formatting
2. Static analysis
3. Python compilation
4. Focused unit tests
5. Affected regression tests
6. Public import verification
7. Git scope review

Passing automated tests alone is not product readiness. Each increment must
also classify the applicability and result of usability, accessibility,
browser-journey, failure-recovery, maintainability, cost and operational gates.
An inapplicable gate requires a recorded reason; an incomplete applicable gate
remains a limitation or blocker.

Git scope review begins from an expected-path allowlist. Necessary adjacent
quality repairs are permitted under ADR-0023 when their evidence, tests,
documentation and separate scope reporting are complete.

A failed gate must be investigated before committing.

## Durable Remediation Gate

A failed gate is not closed by a one-off command correction alone. The change
must identify the underlying failure class, correct its authoritative source,
and add automated prevention where reasonably achievable. Temporary
containment must be labelled and tracked as incomplete; it may not weaken a
test, security boundary, authorization boundary, or evidence requirement.

## Strong controls + automated sequencing + simple operator experience

Material private-synthetic releases use the repository-owned gate catalogue and
release controller. Sequential phases may not be recorded before every declared
predecessor passes for the same commit, image digest, environment and immutable
release run. Independent safety assertions must not be represented as sequential
phases merely because they appear in a numbered report.

Every attempt receives a unique external evidence directory. Failed runs remain
failed and immutable; a correction starts a linked new run rather than overwriting
or relabelling evidence. Only catalogue gates that explicitly permit mutation may
record a cloud mutation, and they require a separate authorization reference.

The controller is an observational sequencing aid, not evidence or deployment
authority. Only independently verified cryptographic evidence and the final
release authority may satisfy infrastructure admission policy.

## Intelligence Quality Gates

### Domain Integrity

- Business rules must live in the responsible domain.
- Prompt builders must remain presentation adapters.
- Verified values must not be replaced with AI-generated assumptions.
- Derived metrics must identify and test their source calculations.
- Intelligence builders must omit unsupported conclusions.

### Context and Generation

- Available verified Company Brain context must be used by applicable
  generation workflows.
- Missing context must not be silently fabricated.
- Generation workflows must record material missing context where it affects
  output quality.
- AI-provider output must remain independently validated where deterministic
  validation exists.
- Compliance prompt guidance must not replace post-generation compliance
  evaluation.

### Architecture

- New domains must use existing generic extension points where suitable.
- Core orchestration must not import avoidable domain-specific models.
- Parallel Company Brain, prompt-composition, or workflow systems require an
  ADR.
- New abstractions require demonstrated lifecycle, querying, ownership, or
  integration needs.
- Tenant and brand boundaries must be tested.

### Testing

- New intelligence logic requires focused automated tests.
- Deterministic calculations require boundary and missing-input tests.
- Prompt rendering requires ordering and empty-section tests.
- Repository changes require persistence and isolation tests.
- Workflow changes require end-to-end integration tests.
- Affected regression suites must pass before commit.

### Documentation and Audit

- Material architecture changes require an ADR.
- Capability maturity must be reviewed after a major increment.
- AI-generated assets must preserve provider and model audit data.
- Technical debt and accepted risks must be recorded.
## Zero-trust supply-chain gate

Every change to release infrastructure must validate the versioned trust
policy and independent shadow verifier. CI covers `deployment` with Ruff and
Black. No repository test may claim that structural evidence validation is a
cryptographic signature, RFC 3161 verification, final release authorization,
Binary Authorization enforcement, or deployment permission.

## Marketing Efficiency and Operator Simplicity Gate

- Ordinary Company Brain workflows target no more than three meaningful
  operator decisions; extra decisions require a genuine conflict, risk or
  separation-of-duties reason.
- Technical identifiers, hashes, manifests and policy traces use progressive
  disclosure and do not become mandatory operator steps.
- Time comparisons use equivalent workflow boundaries and quality standards.
- Manual baseline, assisted time, review time, revisions and exceptions are
  retained in append-only measurement evidence.
- Synthetic benchmarks remain labelled synthetic and cannot validate customer
  or commercial claims.
- Until representative pilot evidence passes, 5-10 hours saved per week and
  40-60% less repeatable campaign-preparation time remain qualified targets
  rather than guaranteed or proven outcomes.
## Durable first-service private bootstrap

- FIRST_PRIVATE_REVISION is permitted only when the canonical service is absent,
  ingress is private, and public and pilot invoker grants are both zero.
- ZERO_TRAFFIC_REVISION is required for an existing private canonical service.
- Ambiguous or public service state fails closed. Platform routing, IAM invocation
  authority and pilot exposure remain separate controls.
- Direct VPC subnet capacity, database connection budget and load-balancer-only
  Cloud Armor ingress are binding production prerequisites in their applicable phases.

## MLAI-031.7 canonical private ingress

- The canonical Cloud Run template must declare exactly one
  `internal-and-cloud-load-balancing` ingress annotation.
- Public, internal-only, missing, duplicated or malformed ingress fails closed.
- The manifest validator and first-service bootstrap planner must agree before
  configuration validation or revision creation.
- Run `run-20260810T210334Z-6f68e3ad` and the 9630fad image remain historical,
  incomplete and non-deployable; they are never repaired, migrated or backfilled.

## Unified release-control gate

- `scripts/mlai_release.ps1` is the only supported operator entry point.
- Python and dependency versions are pinned and verified before release work.
- Every transition has one deterministic plan and one approval bound to its
  SHA-256 digest.
- External state uses atomic writes, integrity sidecars and a process lock.
- A repeated or interrupted apply resumes the same transition and cannot append
  a duplicate terminal gate result.
- The observational ledger, orchestration control plane and cryptographic
  admission authority remain distinct.
- CI runs `python -m tools.release_control validate-repository`.
- A fresh commit-bound image and release run are required after this correction.

## Read-only cloud-preflight gate

- `CLOUD_PREFLIGHT_PASSED` runs only inside `tools.release_control` after an
  exact plan-bound approval.
- Only exact read-only `gcloud` verbs are permitted; native binaries use
  `shell=False`, the Windows batch entry uses the tested ADR-0041 adapter, and
  JSON formatting is owned by the executor.
- Pinned APIs, identities, immutable artifact, database, secret metadata/access
  and canonical Cloud Run target state must all match.
- Secret payload access, cloud mutation, deployment and admission authority are
  prohibited; public or ambiguous target state fails closed.
- Tests must prove mutating nested command verbs are rejected before execution.

## Provenance-bound Cloud CLI adapter gate

- Windows batch execution must be tested with a space-containing executable path.
- Account, configuration, project, quiet and JSON flags are adapter-owned.
- Unsafe argument tokens fail before process execution.
- The same adapter must pass local context diagnostics before journaling cloud work.
- Plans must bind clean repository and executor provenance.
- Executor drift requires formal supersession and a fresh approval.
- Supersession must preserve evidence and modify neither gate nor cloud state.

## Private revision-preparation gate

- `REVISION_CREATED` preparation is allowed only after
  `CLOUD_PREFLIGHT_PASSED`.
- The rendered manifest must be outside the repository and hash-indexed.
- The manifest must remain digest-pinned, private-ingress only and bound to the
  canonical service, runtime identity, Cloud SQL attachment, resource limits and
  Secret Manager bindings.
- Secret Manager payloads, public IAM principals, rebuilds, traffic routing and
  admission-authority claims are prohibited during preparation.
- The command intent is evidence; it is not executed until a separate mutation
  approval exists.

## ORIGIN_RECONCILED

ORIGIN_RECONCILED is required after first private revision creation when the bootstrap origin is still configured. It may authorize exactly one Cloud Run service replacement after plan-bound approval and must not grant public IAM, read secret values, rebuild images, or claim admission authority.

## Release tooling hardening

Release tooling passes only when public CLI transition commands are tested, JSON
configuration files are UTF-8 without BOM, and release PowerShell scripts do not
embed Python.

## Non-interactive cloud auth

Release tooling passes only when the repository validates the pinned release
executor identity, forbids service-account key files, and exposes a tested
auth doctor before mutation.

## Release executor identity bootstrap

The bootstrap tooling passes only when missing identity is handled as evidence,
user-managed keys block planning, the plan digest is deterministic, the mutation
count is bounded, and installation executes no Cloud CLI command.
