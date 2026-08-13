# Definition of Done

A feature is complete only when:

- Existing architecture was reviewed.
- No duplicate subsystem was introduced.
- Public interfaces are documented.
- Tests have been added or updated.
- Regression tests pass.
- Formatting passes.
- Python compilation passes.
- Git scope contains only intended files.
- Documentation reflects the implementation.
- Risks and technical debt have been considered.
- Applicable usability, accessibility, browser-journey, failure-recovery and
  operational gates have passed or are explicitly recorded as incomplete or
  inapplicable.
- Necessary adjacent paths are justified, tested and separately reported under
  ADR-0023.
- Durable Remediation identifies and corrects the underlying failure path and
  adds an automated prevention check where reasonably achievable.
- A temporary containment is recorded as incomplete and cannot close the
  defect, story, risk, technical debt, or gate without its durable follow-up.
- Applicable release phases apply **Strong controls + automated sequencing + simple operator experience** through the versioned gate catalogue for orchestration,
  but controller state is never deployment authority. Deployable artifacts
  require the independent evidence and infrastructure controls in ADR-0035.
- A deployment phase cannot be closed by an out-of-order manual command or by
  evidence bound to a different commit, image, environment or release run.
- Customer-facing efficiency claims identify whether they are targets,
  synthetic benchmarks, pilot observations or validated commercial evidence.
- Operator workflows expose business decisions and genuine exceptions while
  infrastructure and governance mechanics use progressive disclosure.

## Continuity gate

An epic or material product increment is not complete until:

- authority documents affected by the change are updated;
- ADRs or PDRs record material durable decisions;
- `docs/handover/CURRENT_HANDOVER.md` reflects the new checkpoint;
- known risks, debt, and deferred decisions are current;
- focused and complete validation evidence is recorded;
- the handover regression test passes;
- a new handover bundle can be generated outside the repository; and
- the committed branch is clean, pushed, and synchronized.

## Intelligence Capability Checklist

A new intelligence capability is not complete until the applicable items below
are satisfied:

- [ ] Intelligence layer is identified.
- [ ] Traditional marketing function or workflow is identified.
- [ ] Customer value and intended outcome are documented.
- [ ] Dependencies on lower intelligence layers are explicit.
- [ ] Missing context is handled without invented facts.
- [ ] Business reasoning is not hidden inside prompt formatting.
- [ ] Deterministic rules and calculations are tested.
- [ ] Tenant and brand ownership boundaries are preserved.
- [ ] Audit metadata is retained where relevant.
- [ ] Public interfaces are documented.
- [ ] Focused automated tests pass.
- [ ] Affected regression suites pass.
- [ ] Architectural decisions are recorded where material.
- [ ] Product Capability Map maturity is reviewed.
- [ ] Risks and technical debt are recorded when unresolved.
- [ ] Documentation matches the implemented behaviour.
## Zero-trust release evidence

- Controller state is never accepted as deployment authority.
- Deployable artifacts are digest-pinned and have authentic build provenance.
- Gate evidence is independently signed, RFC 3161-timestamped and policy-bound.
- A separate final release authority and infrastructure admission control are
  required before deployment or traffic routing.
- Legacy or incomplete runs remain non-deployable and are not repaired into
  compliance.
- A cloud-preflight implementation allowlists exact read-only verbs, hashes
  minimized observations, never reads secret values and proves mutation verbs
  are rejected before subprocess execution.
- Passing read-only preflight does not authorize revision creation, deployment,
  IAM changes, traffic routing or admission.

## Customer Outcome Evidence Checklist

- [ ] The workflow and start/end boundaries are named.
- [ ] Manual baseline and assisted time use the same task and quality bar.
- [ ] Total operator minutes, review time and revision cycles are retained.
- [ ] Sample size, business type, user role and measurement period are stated.
- [ ] Mean, median and range are reported without selecting only the best run.
- [ ] Synthetic evidence is labelled and never presented as customer evidence.
- [ ] Public wording matches the achieved evidence level.
- [ ] Human approval and compliance-review time remain included.
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

## Unified release-control completion

- [ ] The operator uses one supported launcher and one Python control plane.
- [ ] Runtime and dependency locks verify.
- [ ] Plan generation is deterministic and stale plans fail closed.
- [ ] Approval binds the exact plan, release identity and gate.
- [ ] Evidence records and their SHA-256 sidecars verify.
- [ ] Apply and resume tests prove duplicate prevention after interruption.
- [ ] No local approval or controller record claims admission authority.
- [ ] The complete PowerShell 5.1 and Python regression suite passes.
- [ ] Windows Cloud SDK execution passes its real adapter contract.
- [ ] Every executable plan is commit- and executor-bound.
- [ ] Interrupted incompatible operations are formally superseded and preserved.
- A fresh commit-bound image and release run are required after this correction.

- First-service origin reconciliation is complete only when the observed Cloud Run service URL replaces the bootstrap placeholder and evidence is recorded before startup verification.

- Release tooling hardening is done only when transition requirements and planning are exposed through tested Python CLI commands.

- Release tooling hardening is done only when transition requirements and planning are exposed through tested Python CLI commands.

- Release tooling hardening is done only when transition requirements and planning are exposed through tested Python CLI commands.

- Release tooling hardening is done only when transition requirements and planning are exposed through tested Python CLI commands.
