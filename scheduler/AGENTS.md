# Scheduler Module Knowledge Base

**Generated:** 2026-05-26
**Module:** Strategy scheduling and scoring

## Overview

`scheduler/` contains the structured strategy system, the scoring system, and the multi-process evaluation engine.

## Structure

```text
scheduler/
├── __init__.py
├── engine.py
├── scoring.py
├── strategy_protocol.py
├── strategy_rules.py
├── workers.py
└── display.py
```

## Where to look

| Task | Location | Notes |
|---|---|---|
| Build a structured strategy | `strategy_rules.py` | `StrategyCondition` / `StrategyRuleSet` |
| Parse or serialize the web strategy payload | `strategy_protocol.py` | `strategy-protocol-v1`, structured only |
| Review legacy magic strategy code | `legacy/scheduler/strategy.py` / `legacy/scheduler/strategy_magic.py` | Historical archive only |
| Run multi-strategy evaluation | `engine.py` | `Scheduler.evaluate_multiple_strategies()` |
| Adjust scoring behaviour | `scoring.py` | `ScoringSystem`, `BaselineEstimator`, `ScoringPreferences` |
| Inspect worker runtime | `workers.py` | Structured runtime only |
| Inspect formatted output | `display.py` | Display helpers and reports |
| Re-export public API | `__init__.py` | Package export surface |

## Current implementation facts

- `strategy_protocol.py` rejects `legacy_magic` payloads and old list-style strategy input
- `workers.py` wraps `StrategyRuleEngine` through `StrategyRuntime`
- `Scheduler.banner(...)` and `Scheduler.evaluate_multiple_strategies(...)` both normalize supported payloads through the adapter
- `SCORING_VERSION` is `2.3.0`
- `BaselineEstimator` defaults to `logs/scoring_cache.json`
- `ScoringSystem.score_traces(...)` only supports character-banner scoring at present
- Character score tagging now reads explicit `char_banner.json` labels through `GlobalConfigLoader`

## Conventions

- Use `StrategyRuleSet` and `StrategyCondition` for new strategy definitions
- Keep the public API import path as `from scheduler import ...`
- Do not add new magic strategy entry points to the runtime
- Keep scoring changes in `scoring.py`; do not embed scoring logic in `engine.py`

