# Marketing Strategy Intelligence

MLAI-029.1 introduces the governed source of truth for marketing strategy.
Strategy follows approved Positioning Intelligence and precedes Campaign Plans,
Marketing Briefs, governed generation, execution, and learning.

## Foundation contract

A `StrategyDecision` records immutable ownership and dependency references plus
business objectives, strategic choices, explicit non-choices, assumptions,
unknowns, evidence, confidence, planning horizon, and lifecycle metadata.

Drafts may be incomplete. Approval requires verified evidence, at least one
business objective, and the exact referenced Positioning decision to be
approved for the same tenant and brand. Approval does not claim that the
strategy will succeed.

## Deliberate limits

MLAI-029.1 does not synthesize a situation, recommend an opportunity, create a
marketing mix, forecast results, expose a customer interface, or call an AI
provider. Those capabilities remain in the locked MLAI-029.2 through MLAI-029.6
sequence. Environmental evidence will initially be user-supplied and
time-stamped; live research feeds remain deferred.

The customer pilot remains frozen and tests use synthetic evidence only.

## Situation and opportunity synthesis

MLAI-029.2 adds a deterministic `SituationSynthesizer`. It validates that the
strategy references the supplied approved positioning version and rejects
cross-tenant Product Intelligence. Recorded positioning strengths, business
goals, capacity constraints, and user-supplied PESTLE signals become traceable
findings, opportunities, constraints, and risks.

Every environmental signal requires a factor, declared effect, source,
observation timestamp, confidence, and verification state. Missing Company,
Customer, Product, or PESTLE evidence becomes an explicit gap. The report is
not a forecast, recommendation score, market validation, or learning record.

## Objectives and strategic choices

MLAI-029.3 adds measurable objective and strategic-choice contracts. Objectives
record outcome, metric, human-supplied target, timeframe, method, and evidence
references. Choices record rationale, confidence, constraints, and explicit
non-choices. The evaluator requires the same immutable Situation Report and
reports unlinked inputs as gaps. Targets are not forecasts or promised results.
