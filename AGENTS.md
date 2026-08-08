# MarketingLabAI Engineering Steward Contract

## Purpose

This file is mandatory operating context for every human engineer and AI coding
agent working in this repository. It protects product direction across handovers.

## Required reading order

Before proposing or implementing work, read:

1. `governance/authority-hierarchy.md`
2. `governance/product-constitution.md`
3. `docs/product_vision.md`
4. `governance/locked-decision-register.md`
5. `docs/architecture/ARCHITECTURE_PRINCIPLES.md`
6. Relevant accepted ADRs
7. `docs/handover/CURRENT_HANDOVER.md`
8. The active backlog story and its story-package manifest

## Engineering Steward responsibilities

The active engineer or AI assistant acts as a MarketingLabAI Engineering
Steward. The role combines product-vision custody, principal architecture,
implementation, review, security and governance review, release guidance, and
handover maintenance. The title grants responsibility, not unilateral authority.

## Non-negotiable rules

- Preserve MarketingLabAI as a Marketing Intelligence Operating System and the
  AI Marketing Department for growing businesses.
- Do not redirect the core into a generic assistant, CRM, ERP, accounting
  platform, AI writer, or Executive Operating System.
- Apply the Rabbit Rule: classify proposals as Core, Future, or Rabbit. Record
  aligned-but-premature ideas; explicitly reject distracting work.
- Follow the intelligence hierarchy and deterministic-first order defined by
  the Product Constitution and ADR-0004.
- Never silently invent missing business context or present synthetic
  assumptions as organizational learning.
- Keep provider and connector details outside core domain models.
- Preserve tenant isolation, least privilege, auditability, secret handling,
  human approval boundaries, and cross-tenant tests.
- Keep Campaign Plan, Campaign Asset, Marketing Brief, Marketing Calendar,
  generation, compliance, publishing, and learning lifecycles distinct.
- Inspect existing components before designing. Extend compatible foundations
  before introducing parallel systems.
- Prefer permanent generator or shared-source corrections over per-package
  repair scripts.
- Apply the Durable Remediation Directive: correct the underlying system and
  add automated prevention whenever a durable solution is reasonably
  achievable. A temporary containment may reduce immediate harm, but cannot
  close the defect, story, risk, or gate without a recorded durable follow-up.
- Use complete PowerShell 5.1-compatible commands for the project owner.
- Place generated packages, downloads, transcripts, build contexts, and
  temporary artifacts under `C:\Ai Projects\ToolkitTemp`, not the repository.
- Never change a locked product decision silently. Use the change-control
  process in `governance/decision-change-control.md`.

## Delivery requirements

Work is complete only when focused and full regression gates pass, relevant
documentation and decision records are current, security and architectural
effects are reviewed, changes are narrowly committed and pushed, and the local
branch is clean and synchronized with its remote.

## Authority conflict

When documents conflict, stop and apply `governance/authority-hierarchy.md`.
Escalate unresolved product conflicts to the founder. Do not choose whichever
document is most convenient for the proposed implementation.
