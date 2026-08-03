# ADR-0007 — International Marketing Calendar Architecture

## Status

Accepted

## Date

2026-08-04

## Context

MarketingLabAI is intended to operate internationally across tenants, brands,
countries, regions, languages, locales, and time zones. Future annual marketing
calendars may need to account for public holidays, regional observances,
commercial events, industry dates, business milestones, campaign windows,
approval deadlines, publishing dates, review cycles, seasons, and advisory
weather signals.

Implementing the complete calendar capability during MLAI-025 would over-expand
the current Campaign Planning work. Leaving the architecture undefined would,
however, create a risk that country-specific rules, external calendar APIs,
time-zone assumptions, or review logic become scattered across campaign and UI
code.

## Decision

MarketingLabAI will introduce a dedicated Marketing Calendar domain in the
future MLAI-026 epic.

This ADR locks the architectural responsibilities, boundaries, dependency
direction, internationalisation rules, versioning principles, and provider
extension points for that future domain.

No Marketing Calendar implementation is required during MLAI-025.

## Architectural Position

The preferred long-term flow is:

```text
Company Intelligence
        +
Customer Intelligence
        +
Market and location settings
        |
        v
Annual Marketing Calendar
        |
        v
Campaign Planning
        |
        v
Marketing Brief
        |
        v
Campaign Generation
        |
        v
Compliance and Approval
        |
        v
Publishing and Execution
        |
        v
Performance Review and Learning
```

The Marketing Calendar determines strategic periods, planned initiatives,
review cycles, and campaign windows. Campaign Planning determines campaign
structure and assets. A Marketing Brief records the approved marketing
requirements for an individual campaign. These domains must remain separate.

## Responsibilities

The future Marketing Calendar domain will be responsible for:

- annual, quarterly, and monthly marketing planning;
- campaign-window scheduling;
- public-holiday and observance awareness;
- regional and market-specific date awareness;
- commercial, industry, seasonal, and business events;
- approval and publishing deadlines;
- review-cycle scheduling;
- workload and schedule-conflict detection;
- calendar versioning;
- external calendar synchronisation boundaries.

It will not be responsible for:

- generating content;
- executing AI-provider requests;
- selecting Prompt Packs;
- evaluating compliance;
- publishing content directly;
- calculating campaign performance;
- silently changing approved plans;
- treating external calendars as the system of record.

## Future Domain Contracts

The following concepts are reserved for future implementation:

```text
MarketingCalendar
CalendarVersion
CalendarEvent
CampaignWindow
CampaignSeason
ReviewCycle
BusinessMilestone
MarketLocation
HolidayProvider
CalendarSyncProvider
SeasonalSignalProvider
WeatherSignalProvider
```

These names reserve responsibilities only. MLAI-025 must not create empty
packages, placeholder classes, unused interfaces, or premature database tables.
Concrete contracts will be finalised when MLAI-026 begins.

## Calendar Layers

A calendar may contain independently filterable layers for:

1. public holidays;
2. regional holidays;
3. religious and cultural observances;
4. commercial marketing events;
5. industry events;
6. business milestones;
7. seasons and trading periods;
8. campaign windows;
9. asset and approval deadlines;
10. publishing dates;
11. review cycles;
12. optional advisory weather signals.

Imported events do not automatically become campaigns. They may be classified
as relevant, potentially relevant, excluded, or not yet reviewed.

## Internationalisation

Every market-sensitive record must support explicit context where applicable:

- ISO country code;
- regional subdivision code;
- IANA time-zone identifier;
- locale;
- language;
- local date and time;
- UTC representation for precise times.

The platform must not assume that headquarters and target markets share a time
zone, that a holiday applies nationally, that seasons align across hemispheres,
that English is the market language, or that one country has only one relevant
calendar.

## Holiday and Event Providers

Holiday, observance, industry, and commercial event data must be obtained
through provider-neutral adapters.

A future `HolidayProvider` may supply supported countries and subdivisions,
public holidays, observed dates, classifications, local names, source metadata,
and provider update timestamps.

MarketingLabAI must store the imported snapshot or normalised records needed
for stable planning and auditing. Users must be able to review, correct, and
override provider data. Opening a calendar must not depend on a live provider
request succeeding.

## External Calendar Synchronisation

MarketingLabAI remains the authoritative source for strategy, calendar
versions, campaign windows, review cycles, and approval state.

External systems may be synchronisation targets, including Google Calendar,
Microsoft 365 or Outlook, iCalendar-compatible applications, and future project
or publishing platforms.

Synchronisation must use a provider-neutral `CalendarSyncProvider` boundary.
Users choose which categories are synchronised. External calendars must not own
MarketingLabAI strategy or version history.

## Versioning and Approval

Approved annual and periodic calendars are immutable. Changes create a new
version.

```text
2027 Marketing Calendar v1
        |
        v
Q1 Review
        |
        v
2027 Marketing Calendar v2
        |
        v
Midyear Review
        |
        v
2027 Marketing Calendar v3
```

Version history must preserve the original and revised plans, the review that
initiated the change, approved and rejected recommendations, decision rationale,
responsible users, and timestamps.

The platform must eventually compare what was planned, revised, approved,
executed, published, and achieved.

## Review Cycles

Reviews will be first-class workflow concepts rather than generic reminders.
Supported forms may include monthly operational reviews, quarterly strategic
reviews, campaign-specific reviews, six-month reviews, and annual reviews.

A review may record planned, completed, postponed, and cancelled activities;
performance observations; recommendations; decisions; approval state; rationale;
and the resulting calendar version. Reviews must not rewrite approved history.

## Seasonal and Weather Signals

Seasonal planning and weather forecasting are separate concerns.

Annual planning may use hemisphere, normal seasons, historical climate patterns,
configured trading periods, and previous campaign outcomes. Near-term execution
may use forecasts through a future `WeatherSignalProvider`.

Weather and seasonal inputs are advisory. They must not automatically publish,
cancel campaigns, change approved dates, make factual promises, or override
approval and compliance. Any automatic weather-based action requires a separate,
tenant-owned automation policy and architectural decision.

## Dependency Direction

```text
Application Composition Root
        |
        +--> HolidayProvider adapters
        +--> CalendarSyncProvider adapters
        +--> SeasonalSignalProvider adapters
        +--> WeatherSignalProvider adapters
        |
        v
Marketing Calendar services
        |
        v
Marketing Calendar domain models
```

Domain models must not import Google, Microsoft, holiday-provider,
weather-provider, AI-provider, or campaign-generation SDK models. Adapters
translate external data into provider-neutral domain records.

## Tenant and Market Isolation

Every Marketing Calendar belongs to a tenant. Brand-specific calendars also
belong to a brand. Access and persistence must enforce tenant and brand
ownership.

A tenant may maintain global, country, regional, brand, and campaign-specific
calendar views. Data from one tenant must never be visible to another tenant.

## Alternatives Considered

### Build full calendar support during MLAI-025

Rejected because it would materially expand Campaign Planning and delay its
validation.

### Ignore calendars until international launch

Rejected because date ownership, review cycles, and time-zone handling could
then emerge through incompatible local implementations.

### Use Google Calendar or Microsoft Outlook as the source of truth

Rejected because external calendars do not own MarketingLabAI strategy,
approval state, campaign relationships, or version history.

### Hardcode public holidays by country

Rejected because holiday rules change, regional dates differ, and observed
dates vary.

### Automatically create campaigns for every imported event

Rejected because relevance depends on brand, market, audience, industry,
strategy, capacity, and commercial objectives.

### Let weather control campaigns automatically

Rejected because forecasts are uncertain and must remain advisory unless a
separate governed automation policy is adopted.

### Create placeholder calendar classes immediately

Rejected because unused abstractions add maintenance burden without validated
lifecycle, query, persistence, or integration requirements.

## Consequences

### Positive

- International calendar support has a clear future architecture.
- MLAI-025 remains focused on Campaign Planning.
- External providers cannot dictate internal domain models.
- Tenant, market, locale, and time-zone requirements are explicit.
- MarketingLabAI remains the strategy and version-history system of record.
- Reviews and calendar revisions will be auditable.
- Premature implementation is explicitly avoided.

### Negative

- International calendar functionality is intentionally deferred.
- MLAI-026 will require dedicated domain, persistence, workflow, provider, and
  user-interface design.
- External synchronisation will require provider authentication and monitoring.
- Imported event data will require governance and refresh policies.

## Implementation Timing

ADR-0007 does not authorise immediate calendar implementation. Implementation
begins only when MLAI-026 is prioritised.

Until then:

- no Marketing Calendar package is required;
- no holiday provider is required;
- no external calendar integration is required;
- no weather integration is required;
- no calendar persistence schema is required;
- MLAI-025 remains the active Campaign Planning story.

## Success Criteria

This decision is locked when:

- ADR-0007 is accepted and committed;
- MLAI-026 exists as a deferred backlog epic;
- MLAI-025 remains focused on Campaign Planning;
- future date-aware features reference this ADR;
- external calendars remain synchronisation targets;
- country, region, locale, language, and time-zone requirements remain explicit;
- no premature calendar implementation is introduced.
