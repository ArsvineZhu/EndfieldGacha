# Endfield Gacha | 终末地卡池

**Updated**: 2026-05-26

[中文](README.md) | [English](README_en.md)

---

Endfield Gacha is a simulator for *Arknights: Endfield* headhunting and issue systems. The current repository implements the character banner, weapon banner, web service, structured strategy evaluation, V2 scoring, and statistical tools. This document follows the actual code.

## What is implemented

- `CharGacha`: character banner simulation
- `WeaponGacha`: weapon issue simulation
- `GlobalConfigLoader`: configuration loader
- `GachaResult`: pull result data model
- `Counters`: pull state counters
- `server/`: Flask web application and user storage
- `scheduler/`: structured strategy scheduling and scoring
- `tools/`: demo, evaluation, and verification scripts

## Repository layout

```text
EndfieldGacha/
├── run.py
├── core.py
├── server.py
├── server/
├── scheduler/
├── tools/
├── app/
├── configs/
├── doc/
├── test/
├── pic/
└── ref.md
```

## Entrypoints

```bash
uv sync

uv run run.py          # help
uv run run.py demo     # demo and statistics
uv run run.py eval     # strategy evaluation
uv run run.py exam     # probability verification
uv run run.py server   # start the web app

uv run server.py --dev
uv run server.py --waitress --port 5000
```

`run.py` is the unified CLI entrypoint. `server.py` is the web server wrapper. The default web port is `5000`.

## Core implementation

### `core.py`

- `BatchRandom`: batch random-number generator with reproducible seeds
- `GlobalConfigLoader`: loads `gacha_rules.json`, `char_pool.json`, and `weapon_pool.json`
- `CharGacha`: character banner logic
- `WeaponGacha`: weapon issue logic
- `GachaResult`: result dataclass
- `Counters`: pull counters

### Character banner

- Single pull cost: 1 Chartered Headhunting Permit or 500 Oroberyl
- Base rates: 6★ 0.8%, 5★ 8%, 4★ 91.2%
- 5★ pity: every 10 pulls
- 6★ soft pity: starts after pull 65, +5% per pull, guaranteed on pull 80
- Featured 6★ hard pity: 120 pulls
- Rewards from pulls: 6★ 2000 Arsenal Tickets, 5★ 200, 4★ 20
- Accumulated rewards in the current implementation: urgent recruitment at 30 pulls, dossier at 60 pulls, and repeated featured token rewards every 240 pulls

### Weapon issue

- One issue = 10 pulls, costs 1980 Arsenal Tickets
- Base rates: 6★ 4%, 5★ 15%, 4★ 81%
- `per_apply_must_have=true` guarantees at least one 5★+ result per issue
- 6★ pity: every 4 issues
- Featured 6★ pity: every 8 issues
- Priority: featured 6★ > 6★ > 5★
- Rewards from pulls: 6★ 50 AIC Quota, 5★ 10, 4★ 1
- Accumulated rewards start at the 10th issue and alternate every 8 issues

### Structured strategy

- `scheduler/strategy_v2.py` only supports structured rule trees
- `scheduler/strategy_protocol.py` uses `strategy-protocol-v1`
- legacy magic strategies remain as archives and are not accepted by the protocol layer
- `Scheduler.banner(...)` and `Scheduler.evaluate_multiple_strategies(...)` automatically adapt supported payloads

### V2 scoring

- Main scoring implementation: `scheduler/scoring.py`
- Current scoring version: `SCORING_V2_VERSION = 2.3.0`
- Four scoring dimensions: goal, utility, resource, and risk
- `BaselineEstimator` uses file caching and near-state cubic-spline interpolation
- The current V2 scoring path is character-banner only

### Web service

- App factory: `server/app.py`
- Routes: `server/routes.py`
- Storage: SQLite database `userdata.db`
- User identity: MD5 hash of IP + User-Agent
- Supported operations: recharge, exchange, gacha, urgent recruitment

### Tooling

- `tools/demo.py`: `demo_char_draw()`, `demo_weapon_apply()`, `stats_char_quota()`, `stats_weapon_quota()`, `stats_char_up_prob()`, `stats_char_potential()`
- `tools/evaluation.py`: scenario-based strategy evaluation from `evaluation_examples.json`
- `tools/examination.py`: probability distribution verification

## Configuration

The code actually reads:

- `configs/config_*/char_pool.json`
- `configs/config_*/weapon_pool.json`
- `configs/config_*/gacha_rules.json`
- `configs/arrangement`
- `configs/arrange1`

`configs/config_1` is the default config directory, and the first line of `configs/arrangement` can also define the default.

## Documentation map

- [Chinese mechanics](doc/mechanics.md)
- [English mechanics](doc/mechanics_en.md)
- [Strategy protocol](doc/strategy_protocol.md)
- [Scoring follow-up record](doc/implementation_records/2026-05-26-scoring-v2-followup.md)
- [Legacy scoring design archive](doc/策略评分系统设计方案legacy.md)
- [Developer reference](ref.md)

## Development commands

```bash
uv run pytest test/ -v
uv run ruff check .
uv run pyright
uv run python app/utils/compress.py
```

## Important implementation notes

- The code does not implement separate duplicate-operator or duplicate-weapon exchange systems; duplicates only update collection and resource counters
- The current sample banners in `configs/config_1` are `「熔火灼痕」` and `「熔铸申领」`
- There is no extra `constants.json` file in the actual config layout
- The protocol layer no longer accepts `legacy_magic` payloads

