# Controlled Hosting and Durable Pilot Persistence

## Decision state

MLAI-031.1 records the controlled Cloud Run target and refuses an unsafe
deployment. It does not enable Google APIs, create infrastructure, build an
image, deploy a revision, invite Velani Wholesale, or authorize real data.

The preflight confirmed project `marketinglabai-identity-dev` is active and
billing-enabled. Cloud Run, Artifact Registry, Cloud Build and Secret Manager
were disabled at assessment time. Their disabled state is preserved until an
explicit founder cloud-deployment decision.

## Persistence finding

The application has 144 SQLite references across repositories, identity,
sessions, readiness, recovery and activation paths. Cloud Run local storage is
not durable. A Dockerfile or source deployment over the current SQLite runtime
would therefore risk losing governance evidence and tenant state.

Cloud Run must use PostgreSQL through a completely tested database contract.
`MLAI_DURABLE_ADAPTER_VERIFIED` must remain `false` until every repository,
migration, transaction, integrity, backup and restore path passes against the
selected PostgreSQL service. Configuration claims alone are not evidence.

## Controlled target

- Project: `marketinglabai-identity-dev`
- Service: `marketinglabai-velani-pilot`
- Proposed region: `africa-south1`, subject to availability and price evidence
- Minimum instances: zero
- Maximum instances: one
- CPU: one
- Memory: no more than 512 MiB
- Concurrency: no more than eight
- Initial monthly budget ceiling: no more than R500, requiring founder approval
- Database credentials, session secrets and invitation hashes: Secret Manager
- Deployment identity: immutable image digest and full Git commit

The deployment template is deliberately non-deployable: its authorization
annotation and durable-adapter flag are false and its immutable resource
references are unresolved.

## Required evidence before API enablement or build

1. PostgreSQL adapter and schema migration pass every applicable repository test.
2. A clean synthetic export/import rehearsal preserves tenant isolation and
   immutable privacy, readiness and activation evidence.
3. Backup, point-in-time recovery and isolated restore are rehearsed.
4. Cloud SQL region, availability, backup retention and cost are approved.
5. Secret names and runtime service account are approved without secret values
   entering Git, logs or story packages.
6. Budget alerts and a maximum-spend response are approved.
7. The founder records an explicit decision authorizing the exact APIs and
   controlled build. Deployment remains a separate decision.

## Activity still frozen

External invitations, real business data, public signup, customer billing,
direct publishing, real-data learning and Strand Auto Parts activation remain
frozen. Engineering readiness never self-authorizes cloud mutation.
