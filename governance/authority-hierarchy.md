# MarketingLabAI Authority Hierarchy

## Status

Locked governance policy

## Purpose

This hierarchy determines which evidence controls when code, documents,
backlogs, decision records, and conversational history disagree.

## Authority order

1. Founder-approved Product Constitution and locked product decisions
2. Accepted ADRs and PDRs within their stated scope
3. Current tested and committed implementation
4. Current roadmap, capability map, backlog, and handover record
5. Maintained product and engineering documentation
6. Story manifests and release evidence
7. Recovered conversations and historical planning material
8. Temporary scripts, generated contexts, transcripts, and uncommitted drafts

Higher authority does not automatically erase lower-level evidence. A conflict
must be recorded and reconciled through the appropriate decision process.

## Product and implementation authority

The Product Constitution controls product identity and enduring principles.
Accepted ADRs control durable technical boundaries. Tested code controls what
the system currently does. A chat transcript may explain intent but cannot
override later accepted and implemented decisions.

## Supersession

A decision is superseded only when a later ADR or PDR:

- names the decision being replaced;
- explains the evidence and consequences;
- records founder approval when product identity or commercial laws change;
- updates affected authority documents; and
- provides migration or compatibility treatment where required.

Absence of a decision from a new chat or handover does not revoke it.

## Founder reservation

Product identity, customer promise, core scope, commercial laws, and intentional
deferrals require founder approval. Engineers may recommend changes but may not
approve those changes on the founder's behalf.
