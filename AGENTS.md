# Endfield Gacha AGENTS

**Updated:** 2026-05-26

**Project version:** `2.0.0`

This file is a repository guide for agents and contributors. It reflects the current codebase, not the historical state.

## Stack

- Python 3.10+
- Flask
- numpy
- matplotlib
- scipy
- rich

## Validation commands

| What | Command |
|---|---|
| Install dependencies | `uv sync` |
| Run tests | `uv run pytest test/ -v` |
| Lint | `uv run ruff check .` |
| Typecheck | `uv run pyright` |
| Compress web assets | `uv run python app/utils/compress.py` |

## Entry points

| Command | Purpose |
|---|---|
| `uv run run.py` | Show help |
| `uv run run.py demo` | Demo and statistics |
| `uv run run.py eval` | Strategy evaluation |
| `uv run run.py exam` | Probability verification |
| `uv run run.py server` | Start the web app |
| `uv run server.py --dev` | Start web app in dev mode |
| `uv run server.py --waitress --port 5000` | Start Waitress server |

## Repository facts

- Only two banner types are implemented: character and weapon
- `gacha_core/` contains the simulation engine and configuration loader
- `server/` contains the Flask app factory, routes, user storage, and resource helpers
- `scheduler/` contains structured strategy evaluation and the scoring system
- `tools/` contains demo, evaluation, and verification scripts
- `configs/` contains the actual JSON configuration sets
- `config_1` is the default example config
- `configs/arrangement` and `configs/arrange1` control config order
- `configs/constants.json` contains shared pity, probability, quota, and reward defaults
- Character banner configs are explicit-tag based: `char_pool_base.json` + `config_*/char_banner.json`
- Weapon banner configs are explicit-tag based: `weapon_pool_base.json` + `config_*/weapon_banners.json`
- Old runtime files and deprecated config snapshots live under `legacy/`
- User state is stored in SQLite `userdata.db`; the old JSON-only description is no longer accurate

## Scheduler facts

- `scheduler/strategy_rules.py` is the only supported runtime strategy format
- `scheduler/strategy_protocol.py` only accepts `strategy-protocol-v1` structured payloads
- `legacy_magic` payloads and old list-style strategy input are rejected
- `scheduler/scoring.py` currently reports `SCORING_VERSION = 2.3.0`
- Scoring currently targets the character banner only

## Web facts

- User ID is derived from IP + User-Agent
- Recharge tiers are `6 / 30 / 98 / 198 / 328 / 648`
- `origeometry` can be exchanged for `oroberyl` or `arsenal_tickets`
- Character draws award `arsenal_tickets`
- Weapon issues always consume 1980 `arsenal_tickets`

## Config and tooling facts

- `ruff` config: line-length=120, select=E/F/I, test files ignore E402
- `pyright`: typeCheckingMode=basic, checks `gacha_core`, `server`, `scheduler`, `tools` (excludes `test/`)
- `tools/evaluation.py` reads strategies and parameters from `tools/evaluation_examples.json`
- `run.py server` always runs static compression; use `server.py --dev` for a no-compress dev workflow
- Per-module `AGENTS.md` files live in `gacha_core/`, `scheduler/`, `server/`, `tools/`, `app/`, `configs/`

## Editing guidance

- Do not add a third banner type
- Keep public APIs type-annotated and documented
- Update docs when code behaviour changes
- After code changes, always run `ruff` and `pyright`

