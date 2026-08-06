# ADR-0030 — Controlled Hosting and Durable Pilot Persistence

## Decision

Cloud Run is the preferred controlled application host, but the current SQLite
runtime must not be deployed there. Local Cloud Run files are replaceable and
the repository contains broad SQLite coupling, including governance evidence,
sessions, recovery and activation state.

Production-style hosting requires PostgreSQL, external secret bindings,
immutable commit and image identity, bounded scale and resources, cost controls,
backup/restore evidence and a complete repository compatibility result. The
runtime flag `MLAI_DURABLE_ADAPTER_VERIFIED` remains false until that evidence
exists. A request or configuration boolean cannot substitute for evidence.

Google API enablement, image build, infrastructure creation and deployment each
remain explicit founder decisions. Passing engineering checks never authorizes
an external invitation or real data.

## Consequences

MLAI-031.1 adds a default-deny hosting evaluator and a non-deployable evidence
template. It deliberately refuses SQLite, plaintext secret references,
unbounded scale, excessive resources and budgets above the controlled ceiling.
The next engineering increment must complete PostgreSQL compatibility before
any Cloud Run build is authorized.
