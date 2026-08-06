# Pilot Operations Runbook

## Release state

MLAI-030.5 supports production-security and operational validation with approved test identities
and invented records only. Customer activation remains frozen. Do not load real
customer data until every later gate passes and the founder records an explicit
activation decision.

## Runtime

1. Install `requirements.txt` in the project virtual environment.
2. Supply every `MLAI_*` variable shown in `.env.example` from the deployment
   secret/configuration service. Never commit `.env`.
3. Implement the configured external identity-adapter and provider-registry
   factories outside core domains.
4. Terminate TLS before the application and forward only trusted proxy headers.
5. Run `scripts/run_pilot.ps1`; it starts Waitress on `127.0.0.1:8080`.
6. Confirm `/health/live` and `/health/ready`. Readiness must say
   `synthetic_pilot_ready=true` and `private_customer_pilot_authorized=false`.

The identity integration exchanges a verified external credential at
`POST /v1/pilot/session`. The response issues a Secure, HttpOnly, SameSite
session cookie and a separate CSRF token. Workspace mutations require both.
`DELETE /v1/pilot/session` requires both, revokes the session, writes a
privacy-safe audit event, and expires both cookies.

## Security readiness rehearsal

1. Keep `MLAI_SECURITY_EVIDENCE_JSON={}`; legacy booleans do not satisfy readiness.
2. Verify the browser key restrictions, OAuth testing audience, authorized
   domains, and identity audit logging in the controlled Google project.
3. Rehearse invalid-token rejection, logout/session revocation, and cross-tenant
   isolation using approved test identities and invented data.
4. Record only successful checks as boolean `true`; retain failure evidence and
   remediate before rerunning the unchanged check.
5. Evaluate the release gate. Any missing or false item must block
   `production_identity_security_ready`.

The evidence setting must contain no secrets, tokens, invitation codes, email
addresses, submitted content, or customer records. A passing report permits a
founder assessment; it never changes the real-data freeze.

## Immutable readiness evidence

Set `MLAI_DEPLOYMENT_COMMIT` to the exact deployed Git commit. After each
unchanged controlled check, record its result with:

`python -m app.operations.cli record-evidence <check> <operator> <pass|fail> <sanitized-reference>`

Use `--failure-classification` and `--remediation` for every failed result.
References point to sanitized files under `ToolkitTemp`; they must not contain
credentials or customer content. Evidence expires after 30 days by default and
may never exceed 90 days. Rerun a check after deployment, environment, or
material configuration changes.

Required operational checks are backup creation and verification, restore,
rollback, readiness/authentication/rate-limit/database alerts, incident
response, assigned support ownership, and approved response targets.

## Backup and restore

- Run `scripts/backup_pilot.ps1` before migration, deployment, and daily while
  synthetic pilot work is active.
- Store backup output outside the repository with restricted access.
- Record its SHA-256 and integrity result in the release evidence.
- Test restoration with `scripts/restore_pilot.ps1 -BackupPath <file>
  -DestinationPath <new-file>`; restore never overwrites an existing database.
- Validate the restored database before any traffic is switched.

## Deployment and rollback

Deploy from a tested commit, preserve the prior package and database backup,
run migrations idempotently, then check readiness. If readiness or a smoke test
fails, stop traffic, restore the prior package, and—only if data compatibility
requires it—restore the verified pre-deployment backup to a new path. Record
the decision and evidence.

## Monitoring and support

Alert on readiness failure, repeated authentication failure, rate-limit spikes,
database integrity failure, backup failure, and elevated 5xx responses. Logs
may include request ID, route, method, outcome, tenant ID, provider identifier,
and timing. They must not include credentials, cookies, prompts, generated
content, customer context, instructions, or secrets.

The support record must name an accountable operator role and approved response
targets without storing personal contact details in readiness evidence. Every
incident rehearsal records detection, classification, containment, recovery,
verification, communication decision, and follow-up ownership.
