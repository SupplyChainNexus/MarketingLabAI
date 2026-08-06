# Repository Integrity Protocol

## Status

Locked engineering governance from MLAI-029.6, refined by ADR-0023 on
2026-08-06.

## Purpose

Prevent story commits from silently omitting, mixing, or losing behaviorally
significant work.

## Required controls

Every installable story and commit procedure must:

1. verify the expected baseline commit before installation;
2. begin with an explicit expected-path allowlist and require evidence,
   testing, documentation and separate reporting for every necessary adjacent
   path added during implementation;
3. refuse unexpected pre-existing tracked or untracked changes;
4. report tracked, untracked, staged, and remaining paths;
5. run focused, continuity, complete regression, migration, Ruff, Black, and
   whitespace gates where applicable;
6. classify every failure as story defect, pre-existing defect, environmental
   problem, validator defect, or governance conflict before repair;
7. permit reversible constitution-preserving quality improvements under
   ADR-0023, while requiring explicit founder approval for reserved product,
   activation, commercial, privacy, destructive or irreversible changes;
8. stop a commit when an intended path remains unstaged or untracked;
9. verify a clean worktree and local/remote commit equality after push; and
10. retain story manifests, ADRs, handover state, and validation evidence.

Warnings are evidence to evaluate. They may be accepted only when their cause,
impact, and treatment are explicit. Generated archives and temporary audit files
remain outside the repository.

An added path is not automatically scope creep, and an allowlisted path is not
automatically justified. Scope integrity is proven by the reason for each
change, its relationship to the active work, its validation evidence and the
absence of unrelated mutations.
