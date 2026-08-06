# Founder Design Partner Signup

MLAI-030.1 introduces provider-neutral signup for Strand Auto Parts and Velani
Wholesale. Accounts are not pre-created. An authenticated owner presents the
business invitation and accepts the privacy notice and synthetic-data boundary.
Acceptance records the exact `pilot-privacy-notice-v1` and
`synthetic-data-boundary-v1` versions with tenant, provider, subject, and time.
It authorizes synthetic rehearsal only and is not real-data consent.

The claim transaction creates the tenant and first `admin` membership together.
The same owner may retry safely; another identity cannot claim an owned tenant.
Only SHA-256 invitation hashes are configured through
`MLAI_FOUNDER_INVITATION_HASHES_JSON`; plaintext codes stay outside source,
logs, documentation, and support records. Codes must be generated from a
cryptographically secure random source and must not be human-chosen phrases.

Signup grants free full feature access with billing disabled. It never grants
real-data authority. Live browser signup remains blocked until MLAI-030.2 deploys
and rehearses the selected external identity provider.
