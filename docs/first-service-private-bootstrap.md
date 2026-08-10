# First-service private bootstrap

The bootstrap planner is pure and performs no cloud action. Read-only preflight
produces a `BootstrapObservation`; `plan_revision_creation` selects one safe
mode or refuses the operation.

| Observed state | Mode | New revision traffic | Invocation boundary |
| --- | --- | ---: | --- |
| Service absent | `FIRST_PRIVATE_REVISION` | unavoidable initial target | no public or pilot grant |
| Existing private service | `ZERO_TRAFFIC_REVISION` | 0% | existing private boundary |
| Public or ambiguous | `REFUSED` | none | no mutation |

The deployment operator must compare the current state hash with preflight,
perform no more than one authorized revision mutation, then verify and bind the
post-state. A mismatch or a second revision is a terminal refusal, not a repair.

Platform traffic, IAM invocation authority and pilot exposure are independent
controls. Passing `REVISION_CREATED` does not authorize pilot traffic.
