# Controlled Private Synthetic Application Deployment

MLAI-031.3 makes the canonical WSGI runtime container-ready and defines a
default-deny Cloud Run deployment bound to the retained synthetic PostgreSQL
instance. Engineering and a private synthetic deployment are approved only after
the unchanged repository and external infrastructure gates pass.

## Locked resources

- Project `marketinglabai-identity-dev`, region `africa-south1`
- Service `marketinglabai-velani-pilot`, repository `mlai-synthetic`
- Runtime identity `mlai-synthetic-runtime@marketinglabai-identity-dev.iam.gserviceaccount.com`
- Cloud SQL `marketinglabai-identity-dev:africa-south1:mlai-synthetic-pg18-jhb`
- Scale zero to one; one CPU; 512 MiB; concurrency eight
- IAM-authenticated access only; never `allUsers` or `allAuthenticatedUsers`

## Secret and evidence boundary

Secret Manager holds only the database URL, session secret, synthetic invitation
hashes and Gemini API key. Values never enter Git, build arguments, images, logs,
evidence or packages. The exact commit, immutable image digest, non-root runtime,
IAM denial, health, database contract, tenant isolation, rollback, recovery and
cost must be recorded before the deployment gate passes.

## Still frozen

The deployment never self-authorizes Velani access, other invitations, public
signup, real-customer data, customer billing, publishing, production activation
or real-data learning. Each requires a later, separately scoped decision.
