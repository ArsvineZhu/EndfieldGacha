# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- `uv sync` — install dependencies
- `uv run run.py demo` — gacha demo & statistics
- `uv run run.py eval` — strategy evaluation
- `uv run run.py exam` — probability verification
- `uv run run.py server` — start web server (port 5000)
- `uv run run.py server --dev` — dev mode (no static compression)
- `uv run run.py server --waitress --port 5000` — production mode
- `uv run pytest test/ -v` — run all tests
- `uv run pytest test/scoring_test.py -v -k test_name` — run a single test
- `uv run ruff check .` — lint
- `uv run pyright` — type check
- `uv run python build/compress.py` — compress static files

## Project Structure

```
EndfieldGacha/
├── run.py                  # Unified CLI entrypoint
├── gacha_core/             # Gacha simulation engine
│   ├── char.py             # CharGacha — character banner logic
│   ├── weapon.py           # WeaponGacha — weapon issue logic
│   ├── config.py           # GlobalConfigLoader — config I/O & banner building
│   ├── models.py           # GachaResult, Counters data classes
│   ├── randomizer.py       # BatchRandom (numpy-based batch RNG)
│   ├── pool_utils.py       # _normalize_star_pool helper
│   └── _schemas.py         # Schema constants + normalization utilities
├── scheduler/              # Strategy planning, simulation & scoring
│   ├── engine.py           # Scheduler orchestrator
│   ├── scoring.py          # ScoringSystem v2.3.0 (goal/utility/resource/risk)
│   ├── baseline.py         # BaselineEstimator (MC + cache + spline)
│   ├── cache.py            # JsonFileCache utility
│   ├── models.py           # Data models (Resource, StageTrace, ScoreReport, etc.)
│   ├── workers.py          # Simulation runtime + multiprocessing worker
│   ├── display.py          # Rich-formatted console output
│   ├── strategy_rules.py   # StrategyCondition / StrategyRuleSet engine
│   └── strategy_protocol.py# strategy-protocol-v1 adapter
├── web/                    # Flask web application
│   ├── app.py              # App factory
│   ├── routes.py           # API routes (gacha, recharge, exchange, info)
│   ├── resource.py         # Recharge/exchange logic
│   ├── user.py             # SQLite user storage (IP+UA based identity)
│   ├── templates/          # HTML templates
│   └── static/             # CSS, JS, manifest
├── cli/                    # CLI tools
│   ├── demo.py             # GachaTestTool (demo + statistics)
│   ├── evaluation.py       # Strategy evaluation runner
│   ├── examination.py      # Probability distribution verification
│   └── evaluation_examples.json
├── build/                  # Build utilities
│   └── compress.py         # JS/CSS minification + hashing
├── configs/                # JSON configuration files
│   ├── constants.json      # Global defaults
│   ├── char_pool_base.json # Shared character rosters
│   ├── weapon_pool_base.json # Shared weapon rosters
│   ├── arrangement         # Banner order + default config dir
│   └── config_N/           # Per-banner configs (char_banner, weapon_banners, gacha_rules)
├── data/                   # Runtime data (gitignored)
├── doc/                    # Documentation
├── scripts/                # Startup scripts (bat/ps1/sh)
├── test/                   # pytest tests
└── legacy/                 # Archived old code & configs
```

### Key Implementation Notes

- The scheduler is character-banner only (weapons excluded from scoring)
- `BaselineEstimator` cache lives at `data/scoring_cache.json` by default
- Scoring requires at least one `StrategyGoal` (default: obtain 1 current-up character)
- The protocol layer (`strategy_protocol.py`) auto-normalizes rules passed to `Scheduler.banner()` — callers can pass raw dicts, StrategyRuleSet, or protocol payloads
- `disable_guarantee=True` on `attempt()` freezes pity state (only total increments) — used for pure probability distribution analysis
- Web static files are minified via rcssmin; dev mode (`--dev` flag) skips compression
- Recharge amounts: 6/30/98/198/328/648 only. Exchange: origeometry → oroberyl or origeometry → arsenal_tickets
