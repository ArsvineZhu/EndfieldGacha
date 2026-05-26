# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- `uv sync` — install dependencies
- `uv run run.py demo` — gacha demo & statistics
- `uv run run.py eval` — strategy evaluation
- `uv run run.py exam` — probability verification
- `uv run run.py server` — start web server (port 5000)
- `uv run server.py --dev` — web dev mode (no static compression)
- `uv run server.py --waitress --port 5000` — production mode
- `uv run pytest test/ -v` — run all tests
- `uv run pytest test/scoring_test.py -v -k test_name` — run a single test
- `uv run ruff check .` — lint
- `uv run pyright` — type check
- `uv run python app/utils/compress.py` — compress static files

## Project Structure

Python 3.10+ project using uv. Web server: Flask (dev) or Waitress (prod). Visualization: rich (CLI), matplotlib (charts).

### Core Modules

- **`gacha_core/`** — CharGacha and WeaponGacha simulation. Key classes: `BatchRandom` (numpy-based batch RNG), `GachaResult`, `Counters` (pity/state counters), `GlobalConfigLoader` (reads configs/ JSON files, assembles pool data from base + banner configs). `CharGacha.attempt()` returns a single `GachaResult`; `WeaponGacha.attempt()` returns `List[GachaResult]` (10 per apply).

- **`scheduler/`** — Strategy planning and evaluation system.
  - `strategy_rules.py`: `StrategyCondition` (kind, operator, value) and `StrategyRuleSet` (match="all"|"any", nested conditions). The rules engine evaluates draw state to determine when to stop.
  - `strategy_protocol.py`: Converts between frontend JSON payloads (strategy-protocol-v1) and backend `StrategyRuleSet`. Only supports "structured" kind; rejects legacy_magic and list payloads.
  - `workers.py`: `StrategyRuntime` wraps rules for simulation. Single-thread simulation loop with resource management, urgent gacha handling, and per-banner state tracking.
  - `scoring.py`: ScoringSystem v2.3.0 — four dimensions (goal, utility, resource, risk). `BaselineEstimator` uses Monte Carlo with file caching and cubic spline interpolation for near-state estimates. `ScoringPreferences` configures weights, value mapping, and risk parameters.
  - `engine.py`: `Scheduler` orchestrates multi-banner plans. `evaluate()` runs parallel simulations via multiprocessing.Pool. `evaluate_multiple_strategies()` compares strategies side by side.
  - `display.py`: Rich-formatted console output (tables, panels, progress bars).

- **`server/`** — Flask application. SQLite user data in `userdata.db`. User identity: MD5 of IP + UA. Routes: gacha, urgent recruitment, recharge, exchange, history, pool info, rewards. Routes are long (inline resource logic in `routes.py`).

- **`tools/`** — `demo.py` (demonstrations), `evaluation.py` (reads `evaluation_examples.json`), `examination.py` (probability verification with guarantees disabled).

- **`configs/`** — JSON configs: `constants.json` (shared defaults), `char_pool_base.json` / `weapon_pool_base.json` (shared rosters), `config_N/char_banner.json` / `weapon_banners.json` / `gacha_rules.json` (per-banner overrides). `arrangement` file determines default config directory (first line). `gacha_rules.json` merges into `constants.json` at runtime.

### Key Implementation Notes

- The scheduler is character-banner only (weapons excluded from scoring)
- `BaselineEstimator` cache lives at `logs/scoring_cache.json` by default
- Scoring requires at least one `StrategyGoal` (default: obtain 1 current-up character)
- The protocol layer (`strategy_protocol.py`) auto-normalizes rules passed to `Scheduler.banner()` — callers can pass raw dicts, StrategyRuleSet, or protocol payloads
- `disable_guarantee=True` on `attempt()` freezes pity state (only total increments) — used for pure probability distribution analysis
- Web static files are minified via rcssmin; dev mode (`--dev` flag) skips compression
- Recharge amounts: 6/30/98/198/328/648 only. Exchange: origeometry → oroberyl or origeometry → arsenal_tickets
