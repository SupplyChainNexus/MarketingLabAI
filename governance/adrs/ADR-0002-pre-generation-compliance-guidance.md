# ADR-0002 — Pre-Generation Compliance Guidance

## Status

Accepted

## Date

2026-08-02

## Context

The campaign review workflow currently generates content first and evaluates
compliance afterward.

MarketingLabAI now also has:

- ComplianceRequirementTranslator
- CompliancePromptBuilder
- PromptSection
- AIOrchestrator additional prompt sections

These components make it possible to guide generation with the same structured
rules later used for deterministic validation.

The existing CampaignReviewPipeline already coordinates campaign generation,
compliance evaluation, and persistence. Creating a parallel campaign-generation
pipeline would duplicate workflow ownership.

## Decision

Extend CampaignReviewPipeline to accept an optional RulePack.

When supplied, the pipeline will:

1. Translate the RulePack entries into ComplianceRequirement objects.
2. Build generic PromptSection objects.
3. Pass those sections to CampaignEngine.
4. Generate campaign content.
5. Evaluate the generated content through ComplianceEngine.
6. Persist the content and compliance report.

CampaignEngine will accept optional generic PromptSection objects and forward
them to AIOrchestrator.

CampaignEngine will not import RulePack, ComplianceRequirement,
ComplianceRequirementTranslator, or CompliancePromptBuilder.

## Dependency direction

Caller / Composition Root
    -> CampaignReviewPipeline
        -> Compliance translator
        -> Compliance prompt builder
        -> CampaignEngine
            -> AIOrchestrator
        -> ComplianceEngine
        -> CampaignService

## Alternatives considered

### Create CampaignGenerationPipeline

Rejected because CampaignReviewPipeline already owns generation, review, and
persistence orchestration.

### Load rule-pack files inside CampaignReviewPipeline

Rejected because file discovery and configuration loading belong to the
application composition root.

### Translate rules inside CampaignEngine

Rejected because CampaignEngine should remain focused on campaign generation
and generic AI prompt sections.

### Remove post-generation compliance review

Rejected because prompt guidance reduces failures but does not guarantee
compliance.

## Consequences

### Positive

- Existing workflow becomes governed before and after generation.
- No duplicate campaign pipeline is created.
- CampaignEngine stays compliance-domain-neutral.
- Rule-pack definitions remain the shared source for guidance and validation.
- Existing callers remain compatible when no RulePack is supplied.

### Negative

- CampaignReviewPipeline gains explicit knowledge of compliance prompt
  translation as part of its orchestration responsibility.
- Callers must supply the same applicable RulePack used to configure
  deterministic compliance evaluation.

## Success criteria

- Existing campaign generation works without a RulePack.
- A supplied RulePack produces a Compliance Requirements prompt section.
- CampaignEngine forwards additional sections unchanged.
- Generated content is still evaluated after generation.
- Internal compliance metadata is not exposed in the provider prompt.
- Existing campaign and compliance regression tests remain green.

## Related components

- app/campaigns/campaign_engine.py
- app/campaigns/review_pipeline.py
- app/compliance/translator.py
- app/compliance/prompt_builder.py
- app/ai/orchestrator.py
