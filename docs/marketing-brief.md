# Marketing Brief Architecture

MarketingLabAI uses the Marketing Brief as the provider-neutral record of
marketing intent before prompt rendering and campaign generation.

## Flow

```text
Company and Customer Intelligence
        |
        v
Marketing Brief
        |
        +--> PromptSection adapter
        |
        +--> Versioned Prompt Pack mapping
        |
        v
Approved campaign workflow
        |
        v
Campaign generation
        |
        v
Post-generation compliance review
```

## Persistence

Marketing Briefs are stored as immutable versions. The persistence identity is
tenant ID, brief ID, and version. A stored version is never overwritten.

The repository validates that the tenant exists, the brand exists, and the
brand belongs to the supplied tenant.

## Lifecycle

The supported lifecycle is `draft`, `ready`, `approved`, and `retired`.
Only approved Marketing Briefs may enter the campaign workflow.

## Prompt integration

Marketing Brief values are mapped only into variables declared by the selected
Prompt Pack. Unsupported variables and required values that are empty are
rejected before provider execution.

## Auditability

Workflow results preserve Marketing Brief identity and version, Prompt Pack
identity and version, mapped variables, generated content, and compliance
results.
