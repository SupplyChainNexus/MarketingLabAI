# Repository Integrity Protocol

## Status

Locked engineering governance from MLAI-029.6.

## Purpose

Prevent story commits from silently omitting, mixing, or losing behaviorally
significant work.

## Required controls

Every installable story and commit procedure must:

1. verify the expected baseline commit before installation;
2. use an explicit allowlist of intended changed paths;
3. refuse unexpected pre-existing tracked or untracked changes;
4. report tracked, untracked, staged, and remaining paths;
5. run focused, continuity, complete regression, migration, Ruff, Black, and
   whitespace gates where applicable;
6. classify every failure as story defect, pre-existing defect, environmental
   problem, validator defect, or governance conflict before repair;
7. require explicit approval for material scope or boundary changes;
8. stop a commit when an intended path remains unstaged or untracked;
9. verify a clean worktree and local/remote commit equality after push; and
10. retain story manifests, ADRs, handover state, and validation evidence.

Warnings are evidence to evaluate. They may be accepted only when their cause,
impact, and treatment are explicit. Generated archives and temporary audit files
remain outside the repository.
