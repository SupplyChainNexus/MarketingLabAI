# Campaign Planner

The Campaign Planner is MarketingLabAI's provider-neutral domain for defining,
reviewing, approving, executing, and retaining coordinated marketing campaigns.
It is independent from Marketing Brief, asset, prompt, publishing, and provider
lifecycles.

## Domain model

`CampaignPlan` owns campaign identity, version, tenant and brand ownership,
objective, audience, timeline, channels, success metrics, owner, notes, status,
and audit timestamps. Its controlled lifecycle is:

`Draft -> Planned -> Approved -> Active -> Completed -> Archived`

Planned plans may return to Draft and approved plans may return to Planned.
Briefs are associated through immutable `CampaignBriefReference` values; assets
retain their own lifecycle and dependency graph.

## Versioned persistence

`CampaignPlanRepository` stores every `(campaign_id, version)` as an immutable
SQLite row. Saving the same version twice fails. Reads are always tenant-scoped
and can retrieve a specific version, the latest version, complete ascending
history, or the latest version of every campaign for a brand. Save validates
that the tenant exists and the brand belongs to that tenant.

Use `CampaignPlanningService.create_next_version(plan, **changes)` to construct
a detached successor. The original object and stored row remain unchanged.

```python
repository.save(plan)
successor = service.create_next_version(plan, name="September Acquisition")
repository.save(successor)
latest = repository.get(plan.campaign_id, tenant_id=plan.tenant_id)
history = repository.list_versions(plan.campaign_id, tenant_id=plan.tenant_id)
```

## Boundary rules

- Keep planning deterministic and provider-neutral.
- Do not embed Marketing Briefs or provider payloads in Campaign Plans.
- Require matching tenant and brand identifiers across integrations.
- Preserve campaign, brief, asset, and generation lifecycles independently.
- Use immutable versions for audit history; never update stored plan rows.
