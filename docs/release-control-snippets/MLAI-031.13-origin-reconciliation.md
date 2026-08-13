## MLAI-031.13: Durable first-service origin reconciliation

When a first private Cloud Run service is created with the bootstrap origin,
startup verification must stop until the real service URL is reconciled.

Required order:

1. `REVISION_CREATED` records the first private revision.
2. Read-only startup-origin inspection captures the generated Cloud Run URL.
3. `ORIGIN_RECONCILED` renders a new manifest using that real URL.
4. Exactly one approved Cloud Run service replacement may apply the manifest.
5. `STARTUP_VERIFIED` becomes eligible only after the real origin is observed.

This is a permanent release-control transition, not a pilot-specific patch.

