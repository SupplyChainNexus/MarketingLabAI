# Private Synthetic Release Automation

MarketingLabAI uses **Strong controls + automated sequencing + simple operator experience**
for the private synthetic release lifecycle.

The canonical state machine is `deployment/private_synthetic_release_gates.json`.
`deployment/release_controller.py` validates prerequisites and writes immutable
release identity plus append-only, hash-chained events to a unique directory
outside the repository. `scripts/release_private_synthetic.ps1` is the supported
PowerShell 5.1 operator entry point.

The controller does not execute cloud commands. A mutation-capable gate can only
record a mutation when its catalog entry permits it and the operator supplies a
separate authorization reference. Public access, real-customer data, invitations,
billing, publishing, and real-data learning remain false in every run.

Typical operation:

1. Run `-Action Validate`.
2. Run `-Action Start` with the full commit, digest-qualified image, and operator.
3. Use `-Action Status` to display the next eligible gate.
4. Run the gate's separately reviewed procedure.
5. Record `passed` or `failed`; failures require classification, remediation, and
   the next safe action.
6. Run `-Action Verify` before relying on the evidence chain.

Release evidence belongs under `C:\Ai Projects\ToolkitTemp`, never in Git.
