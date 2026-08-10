# Canonical private ingress contract

The committed Cloud Run template, its Python validator and the durable
first-service bootstrap planner must agree on one ingress value:
`internal-and-cloud-load-balancing`.

Validation rejects public, internal-only, absent, duplicate and malformed
annotations. CI runs the same validator on every change.

The 9630fad image and release run remain immutable historical evidence and are
not deployable. A new commit, successful CI run, immutable image and release run
are required before configuration validation or revision creation resumes.
