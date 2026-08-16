# ADR-0050: Canonical Infrastructure Contract and Coherence Enforcement

Status: Accepted

## Context

Repository maintenance had multiple competing authorities: a PowerShell hygiene
script rewrote files through an encoding-sensitive read/write cycle, CI omitted
critical infrastructure tooling, story manifests used incompatible identity
fields, and inherited governance defects could be changed without a single
coherence gate. Green CI therefore did not prove repository integrity.

Existing corruption must not be silently normalized because doing so would mix
unreviewed content repair with infrastructure work. Equally, inherited defects
must not allow new corruption to enter unnoticed.

## Decision

The repository has one canonical, machine-enforced infrastructure contract:

1. Text is UTF-8 without BOM. Git stores canonical normalized text. LF is the
   default and is required for PowerShell; only Windows batch command files
   (`.bat` and `.cmd`) use CRLF. `.gitattributes` and `.editorconfig` express
   the same rule. Checkout presentation cannot become evidence authority.
2. `python -m tools.infrastructure_coherence check` is the authoritative,
   read-only repository integrity check. The PowerShell hygiene script is only a
   thin launcher and never reads, rewrites or formats repository content.
3. Inherited findings are non-blocking only when path, finding code and SHA-256
   exactly match the reviewed legacy baseline. A changed byte invalidates the
   acknowledgement and blocks CI.
4. Repairs are separate operations. A plan binds repository commit, baseline,
   target path, current bytes and replacement bytes. Application revalidates all
   bindings, applies atomically and rolls back if coherence fails.
5. Story manifest schema version 2 uses `story_id` as its canonical identity.
   Legacy manifests remain exact-hash debt and must be migrated when modified.
6. ADR and register identifiers are validated for filename/header consistency
   and uniqueness. CI runs coherence, formatting, whitespace and focused tests
   across application and infrastructure tooling.
7. The checker and repair engine perform no Cloud CLI, credential, IAM,
   database, deployment, traffic, release-state or release-ledger operation.
8. Repository-wide checks inspect Git-tracked paths plus explicitly declared
   package targets. Ignored local backups, runtime data, caches and other
   untracked workstation state are outside the repository integrity verdict.
9. Installer validation writes Python bytecode outside the repository. Failed
   installation rolls back files and removes directories created by that
   installation so Git cleanliness and import-state cleanliness agree.
10. Evidence exports read every selected file from its committed Git blob with
    `git cat-file`, never from the working tree and never through `git archive`.
    Every intake uses an explicit versioned path manifest. The completed ZIP is
    reopened and its exact path set and each archived SHA-256 are verified
    before it can be reported as complete.
11. Corrective work outside the inherited baseline uses a separate plan bound
    to repository commit, explicit path manifest, exact current existence and
    SHA-256, and exact replacement SHA-256. Planning and application remain
    distinct authorization boundaries.
12. Git configuration diagnosis is read-only. It reports origin, scope and
    effective text settings but never changes system, global or local config.
    Configuration compatibility is an operator warning; committed attributes,
    raw Git objects and completed-artifact verification are authoritative.
13. An intake ZIP is a sibling of its output directory and is derived by
    appending `.zip` to the complete directory name. Export refuses existing
    directory or ZIP destinations, ambiguous ZIP-named roots and any source /
    output overlap before creating files. ZIP creation is exclusive, so an
    unrelated artifact can never be truncated by suffix replacement or retry.

## Consequences

- A green build proves that no unapproved integrity defect has appeared and no
  acknowledged legacy defect has silently changed.
- Formatting tools no longer act as a general-purpose repair authority.
- Existing corrupted files require a separately reviewed, exact-hash repair
  plan and cannot be swept into unrelated stories.
- The baseline is a debt ledger, not a waiver: removed findings stay resolved,
  while adding or rebasing entries requires governance review.
- Later coherence stories can extend the same contract to generator retirement,
  release-gate completeness, unified cloud execution and tenant-neutral release
  topology without creating parallel validators.

## Corrective amendment: canonical Git object export and LF PowerShell

The 2026-08-15 evidence-intake diagnostic proved that `git archive` may apply
export-time attributes and change newline bytes even when the index and working
tree are clean. The export was recoverable because all transformations were
newline-only and the affected ToolkitTemp files were restored from exact blobs,
but an evidence pipeline must not need post-hoc restoration. This amendment
makes raw Git-object export and completed-ZIP verification mandatory and aligns
PowerShell with LF across Git and editor policy. It does not authorize Git
configuration changes or any cloud, release, deployment or security mutation.

The 2026-08-16 MLAI-031.18C intake exposed a separate path-derivation defect:
`Path.with_suffix(".zip")` treated the story identifier in a dotted output-root
name as a suffix and reduced the destination to `MLAI-031.zip`. Recovery proved
the selected blobs were correct, but containment cannot close an overwrite
hazard. Canonical export now appends `.zip`, preflights both destinations and
their relationship to the repository, refuses ambiguity and uses exclusive ZIP
creation with adversarial collision tests.
