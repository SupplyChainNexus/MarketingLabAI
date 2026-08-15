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

1. Text is UTF-8 without BOM. Git stores canonical normalized text and
   `.gitattributes` materializes platform-appropriate checkout endings; LF is
   the default and Windows command files use CRLF. `.editorconfig` expresses
   the matching editor rule. Checkout line endings, including mixed
   materialization in a clean Windows checkout, are presentation and are not
   treated as repository corruption.
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
