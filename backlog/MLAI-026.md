# MLAI-026 — International Marketing Calendar Intelligence

## Status

Deferred — reaffirmed by PDR-0002

## Architectural Authority

- `governance/adrs/ADR-0007-international-marketing-calendar-architecture.md`
- `governance/pdrs/PDR-0002-secure-pilot-vertical-slice.md`

## Priority decision

The Launch Readiness and Vertical-Slice Review found that secure application
composition is more urgent than another planning domain. MLAI-027 is the active
epic. Reconsider MLAI-026 only after controlled-pilot evidence is reviewed.

## Objective

Create an international, tenant-aware, and versioned Marketing Calendar domain
that supports annual planning, periodic reviews, campaign windows,
country-specific and regional events, business milestones, external calendar
synchronisation, and optional seasonal or weather signals.

MLAI-026 is deliberately deferred until MLAI-025 Campaign Planning has been
implemented and validated.

## Product Outcome

MarketingLabAI users will eventually be able to:

- create annual marketing calendars;
- review calendars monthly, quarterly, by campaign, or annually;
- plan across countries, regions, brands, languages, and time zones;
- import and review public holidays and observances;
- add commercial, company, seasonal, and industry events;
- define campaign windows, deadlines, and review cycles;
- version approved calendars;
- synchronise selected events with external calendars;
- use seasonal and near-term weather data as advisory signals;
- compare planned, revised, approved, executed, and completed activity.

## Delivery Plan

### MLAI-026.1 — Calendar Domain Foundation

- [ ] Define Marketing Calendar lifecycle.
- [ ] Define calendar-event taxonomy.
- [ ] Define market, country, region, locale, language, and time-zone context.
- [ ] Define campaign windows and business milestones.
- [ ] Add validation and serialisation.
- [ ] Add focused unit tests.

### MLAI-026.2 — Holiday and Event Provider Boundaries

- [ ] Define provider-neutral holiday contracts.
- [ ] Support national and regional records.
- [ ] Preserve provider and source metadata.
- [ ] Support imported snapshots and user overrides.
- [ ] Add adapter contract tests.

### MLAI-026.3 — Annual Calendar Builder

- [ ] Build annual planning workflow.
- [ ] Support quarterly and monthly planning views.
- [ ] Add relevance classification.
- [ ] Add workload and schedule-conflict detection.
- [ ] Preserve user approval boundaries.
- [ ] Add deterministic builder tests.

### MLAI-026.4 — Review and Revision Workflows

- [ ] Add monthly review workflow.
- [ ] Add quarterly review workflow.
- [ ] Add campaign-specific review workflow.
- [ ] Add annual review workflow.
- [ ] Preserve decisions and rationale.
- [ ] Create new versions from approved changes.

### MLAI-026.5 — Calendar Synchronisation

- [ ] Define `CalendarSyncProvider` contract.
- [ ] Support selective event synchronisation.
- [ ] Add iCalendar export.
- [ ] Add Google Calendar adapter.
- [ ] Add Microsoft Calendar adapter.
- [ ] Preserve MarketingLabAI as the system of record.

### MLAI-026.6 — Seasonal and Weather Intelligence

- [ ] Define seasonal-signal boundary.
- [ ] Define weather-signal boundary.
- [ ] Separate historical seasonality from near-term forecasts.
- [ ] Keep weather recommendations advisory.
- [ ] Add explicit approval and automation boundaries.

### MLAI-026.7 — Persistence and Completion

- [ ] Add immutable calendar-version persistence.
- [ ] Add tenant and brand ownership checks.
- [ ] Add market and regional query support.
- [ ] Complete documentation and engineering review.
- [ ] Run complete regression validation.
- [ ] Commit and release.

## Acceptance Criteria

- [ ] MarketingLabAI is the source of truth for marketing calendars.
- [ ] External calendars remain synchronisation targets.
- [ ] Calendar data is tenant-isolated.
- [ ] Country, region, locale, language, and time-zone context is explicit.
- [ ] Approved calendar versions are immutable.
- [ ] Reviews preserve recommendations, decisions, and rationale.
- [ ] Imported events do not automatically become campaigns.
- [ ] Weather and seasonal signals remain advisory.
- [ ] Provider-specific models do not enter the calendar domain.
- [ ] Existing campaign, Marketing Brief, compliance, and intelligence workflows
      remain compatible.

## Deferral Rule

No MLAI-026 implementation work should begin until:

1. MLAI-025 Campaign Planning reaches its agreed completion milestone.
2. The Campaign Plan and Marketing Brief relationship has been validated.
3. Calendar implementation is prioritised against launch requirements.
4. ADR-0007 is reviewed for continued suitability.

Until those conditions are met, MLAI-026 remains a documented future capability
rather than active implementation work.
