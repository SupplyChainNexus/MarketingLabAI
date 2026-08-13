# MarketingLabAI Technical Debt Register

| ID | Area | Description | Priority | Status |
|---|---|---|---|---|
| TD-001 | Persistence | Legacy JSON services remain for compatibility, but SQLite is now canonical inside the pilot composition root. | High | Reduced at ee5da24; migration and retirement remain |
| TD-002 | Application composition | CLI generation bypassed Campaign Planner, versioned Marketing Brief, Prompt Pack selection, and independent compliance review. | Critical | Resolved by CanonicalApplication at ee5da24 |
| TD-003 | Tenant boundary | Some repositories retrieve by globally supplied brand ID rather than an authorized tenant context. | Critical | Open Ã¢â‚¬â€ MLAI-027.3 |
| TD-008 | Campaign artifacts | Generated content and compliance reports require an injected artifact service and do not yet have a canonical relational repository. | High | Open Ã¢â‚¬â€ design before pilot export |
| TD-004 | Health checks | Operational liveness and canonical readiness now exist; legacy local health remains for compatibility. | Medium | Reduced by MLAI-027.6; retire legacy check deliberately |
| TD-005 | Release metadata | `pyproject.toml` references a missing root README and contains stale version/description metadata. | Medium | Open |
| TD-006 | Delivery automation | Tracked Linux quality and Windows continuity jobs now define remote gates. | Medium | Resolved by MLAI-027.6; enforce branch protection separately |
| TD-007 | Governance accuracy | Capability maturity previously lagged implemented Customer Intelligence and Campaign Planner evidence. | Medium | Addressed by MLAI-027 adoption review; maintain each epic |
| TD-009 | Product Intelligence | Current Product/Offer profiles are mutable snapshots without offer expiry or approval history. | Low | Define version, review, and expiry lifecycle from pilot evidence after MLAI-027.2 |
| TD-010 | Identity operations | Runtime authentication freshness, tenant revalidation, audited revocation and deterministic evidence checks exist; deployment evidence remains operator-supplied. | High | Complete and record every controlled security rehearsal before founder assessment; keep real data and public activation frozen |
| TD-011 | API operations | Waitress, TLS-aware config, single-process rate limiting, health and logs exist. Distributed rate limiting is intentionally absent. | Low | Revisit only if deployment becomes multi-instance |
| TD-012 | Workspace identity | Temporary credential entry was removed and browser operations require server session plus CSRF. | Critical | Resolved by MLAI-027.6 |
| TD-013 | Positioning references | Positioning target, product, and offer identifiers are validated against Customer and Product Intelligence repositories. | High | Resolved by MLAI-028.2 |
| TD-014 | Product use cases | Product Intelligence has no governed use-case field, so relevance reports the gap rather than inferring use cases. | Medium | Open Ã¢â‚¬â€ preserve as a limitation through MLAI-028.5 |
| TD-015 | Alternative evidence persistence | Reviewed alternative evidence is provider-neutral input to differentiation but has no canonical repository or expiry lifecycle. | Medium | Define with future research evidence; do not persist synthetic fixtures as market truth |
| TD-016 | Positioning replacement linkage | Replacement preserves immutable retired history but does not yet store an explicit predecessor identifier. | Low | Add when canonical integration demonstrates a downstream audit requirement |
| TD-017 | Positioning applicability policy | Draft plans may omit positioning for backward compatibility; governed generation requires an explicit approved reference. | Medium | Define domain-specific applicability rules when Marketing Strategy is introduced |
| TD-018 | Strategy evidence depth | Strategy accepts time-stamped environmental evidence as evaluator input but has no canonical research repository or expiry lifecycle. | Medium | Define with future Research Intelligence; defer live feeds and preserve visible gaps |
| TD-019 | Objective baselines | Objective targets are governed human inputs, but canonical baseline and outcome repositories do not yet exist. | Medium | Preserve explicit inputs until real execution and Learning Intelligence exist |
| TD-020 | Mix persistence | Marketing-mix and measurement reports are deterministic evaluator outputs but do not yet have separate canonical persistence. | Medium | Integrate through the immutable Strategy lifecycle in MLAI-029.5 before adding another repository |
| TD-021 | Design-partner operations | The readiness evaluator is deterministic, but deployed identity, jurisdiction-specific privacy choices, support ownership, and recovery evidence are not yet configured. | High | Resolve and rehearse before requesting founder approval for real-data activation |
| TD-022 | Signup experience | Provider-neutral tenant claiming exists, but no external identity vendor or browser redirect/callback flow is deployed. | Critical | Resolve in MLAI-030.2 before inviting either business |
| TD-023 | Identity portability | Memberships use provider plus subject as the identity key rather than a separate internal user identifier and identity-link table. | Medium | Add a tested identity-link migration before supporting provider switching or account linking |
| TD-024 | OAuth inactivity lifecycle | Google may delete an OAuth client after six months of inactivity. | Medium | Add an operator-owned lifecycle check in MLAI-030.4 before a prolonged pilot pause or production promotion |
| TD-025 | Real-data privacy configuration | Synthetic policy and acceptance evidence exist, but jurisdiction, legal roles, real-data categories, retention, deletion SLA, subprocessors, location, support access, and breach terms are unset. | Critical | Founder must approve partner-specific choices before MLAI-030.7 can authorize real data |
| TD-026 | Distributed security controls | Request limits and rate limits are process-local and the pilot is single-instance. | Medium | Reassess shared enforcement only if the selected production topology becomes multi-instance |
| TD-027 | Monitoring delivery | Privacy-safe signal state is deterministic and testable, but no selected hosting alert transport exists. | High | Select and rehearse the alert transport in the controlled deployment before MLAI-030.6 acceptance |
| TD-028 | Acceptance execution | The assessment and evidence model are implemented, but controlled browser evidence has not yet been recorded for either partner tenant. | High | Run every unchanged synthetic scenario independently after the 17 prerequisite checks pass; classify and remediate every failure |
| TD-029 | Activation legal configuration | Runtime activation scope is enforceable, but final operator agreement, hosting/subprocessor schedule, retention, deletion and incident contacts require recorded approval. | Critical | Complete the Velani activation pack before any limited real-business-data decision is recorded |
| TD-030 | Durable persistence | Canonical PostgreSQL selection, schema translation and transactional synthetic migration now have live local and controlled Cloud contract, migration, backup and isolated-restore evidence. | Critical | Resolved at b09055a for controlled synthetic hosting; rerun before any changed schema, adapter, target or real-data cutover |
| TD-031 | Hosted composition | The environment runtime existed, but its provider factory and container entry point were absent and settings required a local `.env` file. | Critical | Resolved by MLAI-031.3 engineering; complete immutable build and private deployment evidence externally |
| TD-032 | Deployment command drift | Manual Cloud Run commands duplicated the tracked configuration contract and produced successive failed revisions. | Critical | Resolved in repository by canonical manifest rendering, configuration invariants, PowerShell 5.1 validation and CI enforcement; external deployment evidence remains pending |
| TD-033 | Manual release sequencing | Deployment gates were individually sound but lacked one machine-enforced progression and operator status surface. | Critical | Resolved by MLAI-031.4's ordered gate catalog, release controller, PowerShell wrapper, hash-chained evidence and CI regression |
| TD-034 | Cryptographic signing, RFC 3161 verification, isolated release authority and Binary Authorization are not yet implemented; the repository verifier is shadow-only. | High | Complete ADR-0035 phases before any new private traffic is routed. | Open |
| TD-035 | Release execution depended on mixed Python/PowerShell orchestration, stale story-numbered paths and temporary scripts. | Critical | Replaced by ADR-0039's one Python control plane and thin pinned launcher; validate the full Windows operator journey before closure. | In validation |
| TD-036 | Read-only cloud preflight was not implemented in the paved control plane and would require temporary operator scripts. | Critical | Resolved in repository by ADR-0040's exact command allowlist, pinned observations and idempotent plan/apply/resume integration; Windows execution remains to be validated. | In validation |
| TD-037 | The live Windows `gcloud.cmd` adapter and executor-approval provenance were absent from the test contract. | Critical | ADR-0041 adds the real Windows batch adapter, same-adapter doctor, provenance-bound plans and formal supersession. | In remediation |

## MLAI-031.7 retired ingress mismatch

- The manifest/bootstrap ingress mismatch is retired only after this correction is
  committed and CI passes. The old run and image remain non-deployable evidence.

- MLAI-031.13 resolves the temporary first-service origin bootstrap gap by adding an explicit reconciliation transition before startup verification.

- MLAI-031.14 removes embedded Python from release PowerShell wrappers and promotes origin reconciliation to the public release-control CLI.
