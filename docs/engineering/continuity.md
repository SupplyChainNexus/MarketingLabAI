# Engineering Continuity System

## Objective

Make a safe takeover possible without depending on access to an earlier chat or
the memory of one developer.

## Continuity layers

- Constitution: enduring product principles
- Decision records: rationale and supersession history
- Architecture: durable system boundaries
- Current state: implemented capability and immediate continuation point
- Validation evidence: proof that the checkpoint works
- Handover bundle: portable, secret-safe snapshot of the above

## Takeover procedure

1. Confirm branch, commit, remote synchronization, and clean working tree.
2. Read the mandatory documents in `AGENTS.md` order.
3. Run `tests/test_handover_system.ps1`.
4. Run focused and complete project regression gates.
5. Compare the active story with capability dependencies and accepted ADRs.
6. State the proposed next increment and Rabbit Rule classification before coding.
7. Preserve new decisions and validation evidence before handoff.

## Handover maintenance

`docs/handover/CURRENT_HANDOVER.md` is a living checkpoint, not a project diary.
Update it when an epic closes, the active direction changes, a material risk is
accepted, or the recommended next increment changes.

Build portable handover evidence with:

```powershell
& ".\scripts\build_handover.ps1" `
    -OutputRoot "C:\Ai Projects\ToolkitTemp\MarketingLabAIHandover"
```

The generator must include only tracked governance and engineering evidence and
must not collect secrets, databases, customer data, virtual environments,
generated build contexts, or earlier bundles.
