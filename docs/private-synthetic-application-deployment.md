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

## Canonical deployment contract

`deployment/cloud-run.private-synthetic.yaml.template` is the single tracked
source for the service name, runtime identity, Cloud SQL attachment, resource
bounds, application variables, and Secret Manager bindings. Validate it through
the pinned repository control plane:

```powershell
& ".\scripts\mlai_release.ps1" validate-repository
```

Render a commit-bound manifest only through a repository-owned Python process
selected by the pinned launcher. The output must be
outside the repository and must use the immutable `marketinglabai-pilot` image
digest. Do not manually reconstruct or patch environment variables in a
`gcloud run deploy` or `gcloud run services update` command.

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

Failed revisions remain evidence. Classify each failure, correct the canonical
source, add automated recurrence prevention, and rerun only after separate
authorization. This is the Durable Remediation requirement in ADR-0033.
