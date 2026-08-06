# Governance Drag Audit — 2026-08-06

## Purpose

Test whether the former narrow interpretation of story path allowlists caused or
concealed product-quality damage. This audit does not assume that every defect
was caused by governance. It separates direct evidence, plausible contribution,
intentional constraint and absence of evidence.

## Method

The audit examined:

- current authority, integrity, definition-of-done and quality-gate documents;
- continuity assertions and their recorded false-failure history;
- application and test structure;
- browser workspace markup, scripting and security boundaries;
- current handover, risk and technical-debt state;
- selected and superseded identity-provider surfaces; and
- focused and complete regression evidence.

Each finding is classified as:

- **Confirmed damage:** a current defect or false control with direct evidence;
- **Probable governance drag:** a quality gap the narrow rule plausibly
  reinforced, without proving sole causation;
- **Intentional constraint:** a deliberate safety or product boundary;
- **No evidence of damage:** inspected area remains coherent.

## Findings

| ID | Classification | Evidence | Product effect | Proposed treatment |
| --- | --- | --- | --- | --- |
| GDA-001 | Confirmed damage | `tests/test_handover_system.ps1` contains 65 text-regex boundary checks. During MLAI-030.2, exact wording and whitespace produced false failures while the intended boundary was present. | Delivery delay and pressure to edit tests or prose rather than behaviour. | Retain a small constitutional continuity test; migrate detailed behavioural claims to structured manifests and executable tests. Never weaken a boundary merely to pass. |
| GDA-002 | Confirmed damage | The workspace visibly duplicates steps 2 and 4 and places step 8 before steps 6 and 7. | The first client journey is harder to understand and appears unfinished. | Renumber from one canonical journey model and add an executable navigation-order assertion. |
| GDA-003 | Confirmed damage | TD-010 still says project creation and billing controls remain, although the controlled Google project, budgets, provider and restrictions are configured. | The next engineer may repeat completed work or misjudge readiness. | Reconcile TD-010 to distinguish completed cloud setup from remaining browser, recovery, logging and activation rehearsal. |
| GDA-004 | Probable governance drag | No Playwright, Selenium, WebDriver, axe-core or equivalent browser/accessibility suite exists. Existing workspace tests inspect assets and WSGI responses. | Unit success cannot prove the Google popup, token exchange, keyboard journey, visible errors or session transition works in a browser. | Add a local browser journey and automated accessibility smoke gate before pilot activation. |
| GDA-005 | Probable governance drag | Definition of Done previously required tests and Git scope but did not explicitly require usability, accessibility, recovery or browser evidence. | Engineering completion can precede client-experience completion. | ADR-0023, Definition of Done and Quality Gates now make applicability and limitations explicit. |
| GDA-006 | Probable governance drag | Repeated story packages overwrite broad handover and governance files, while validators assert exact phrases. | Governance churn can consume story capacity and create brittle coupling. | Prefer structured decision metadata and fewer behaviourally meaningful continuity assertions; retain prose for explanation. |
| GDA-007 | Intentional constraint | Synthetic-only data, controlled OAuth test users, disabled public signup, SMS, password auth, paid extensions and publishing. | Limits market evidence and production realism. | Preserve until founder activation gates pass; these constraints currently reduce risk rather than product quality. |
| GDA-008 | Intentional complexity | Entra adapter and tests remain after Google superseded it. ADR-0021 and LDR-049 explicitly retain the adapter behind a provider-neutral boundary. | Some maintenance surface remains. | Do not remove without measured maintenance or security cost; validate that only Google is selected at runtime. |
| GDA-009 | No evidence of damage | Full regression passes and tenant, approval, immutable-version, identity and frozen-pilot boundaries have focused coverage. | Core deterministic and security behaviour remains coherent. | Preserve these gates while improving experience evidence. |
| GDA-010 | No evidence of omitted executable work | The prior repository-integrity and unreachable-object audits found superseded governance revisions, not missing executable behaviour. | No current basis for reconstructing lost code. | Do not perform speculative recovery. Continue commit-level integrity checks. |

## Causation conclusion

The audit found quality damage and governance drag, but not evidence of broad
architectural corruption or lost executable behaviour. The strongest effect is
**completion bias**: work could be repository-correct and test-green while the
client journey, accessibility and recovery rehearsal remained immature.

The narrow governance rule was a contributing condition, not the sole cause.
The synthetic founder freeze, incremental roadmap and absence of a deployed
browser test environment also explain part of the gap.

## Prioritized remediation proposal

1. **Now, before MLAI-030.2 installation:** retain ADR-0023 and its continuity
   gate; reconcile TD-010 in the application-side package.
2. **Next quality increment:** correct journey numbering and introduce a
   browser-level synthetic Google signup/session test with keyboard and basic
   accessibility checks.
3. **Before invitation approval:** rehearse invalid identity, cancellation,
   expired invitation, recovery, revocation and Google unavailability in the
   actual browser/runtime boundary.
4. **Governance refactor after the pilot flow is stable:** reduce prose-regex
   continuity assertions by moving machine-verifiable state into structured
   manifests, while retaining high-authority constitutional assertions.

No real-data activation, paid dependency, public publishing or destructive
change is authorized by this audit.
