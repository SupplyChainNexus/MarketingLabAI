# Zero-Trust Software Supply Chain

ADR-0035 makes the pipeline controller an untrusted coordinator. The permanent
trust path is commit -> hardened build -> digest and provenance -> independently
signed and RFC 3161-timestamped gate attestations -> policy verification ->
separately signed release authorization -> Binary Authorization enforcement.

The repository currently implements only the binding policy and a no-mutation
shadow verifier. `deployment/zero_trust_supply_chain.py` cannot sign, deploy,
create authorization, or treat controller events as cryptographic evidence.

## Required identity binding

Every gate statement binds the run ID, full Git commit, exact image digest,
environment, gate ID, result, policy-bundle digest, evidence digests, executor
identity, and dependency-attestation digests. The RFC 3161 message imprint must
equal the SHA-256 of the exact signed DSSE envelope.

## Enforcement destination

Cloud Run will require Google Binary Authorization with a dedicated final
release attestor and organization-policy enforcement. The ordinary builder,
controller, deployer, and runtime identities receive no release-signing or
break-glass authority. Images are deployed by digest only.

## Legacy boundary

Existing controller ledgers are retained unchanged as historical evidence.
They are not repaired into deployable releases. The current 7e45958 release run
and its image remain non-deployable under the new architecture. The first
enforced artifact must be rebuilt under the hardened provenance path.
