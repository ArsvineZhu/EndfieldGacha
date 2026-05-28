# Endfield Gacha | 终末地卡池

**Updated**: 2026-05-28

**Project version**: `2.5.0`

[中文](README.md) | [English](README_en.md)

---

Endfield Gacha is a simulator for *Arknights: Endfield* headhunting and issue systems. The current repository implements the character banner, weapon banner, web service, structured strategy evaluation, scoring, and statistical tools. This document follows the actual code.

## What is implemented

- `CharGacha`: character banner simulation
- `WeaponGacha`: weapon issue simulation
- `GlobalConfigLoader`: configuration loader
- `GachaResult`: pull result data model
- `Counters`: pull state counters
- `web/`: Flask web application and user storage
- `scheduler/`: structured strategy scheduling and scoring
- `cli/`: demo, evaluation, and verification scripts

## Repository layout

```text
EndfieldGacha/
├── run.py              # Unified CLI entrypoint
├── pyproject.toml      # Project metadata & dependencies
├── gacha_core/         # Gacha simulation engine
├── scheduler/          # Strategy planning and scoring
├── web/                # Flask web application
├── cli/                # CLI tools
├── build/              # Build utilities
├── configs/            # JSON configuration files
├── deploy/             # Deployment templates
├── doc/                # Documentation
├── scripts/            # Startup scripts
├── test/               # Tests
├── data/               # Runtime data (gitignored)
└── legacy/             # Archived code
```

## Entrypoints

```bash
uv sync

uv run run.py          # help
uv run run.py demo     # demo and statistics
uv run run.py eval     # strategy evaluation
uv run run.py exam     # probability verification
uv run run.py server   # start the web app (http://localhost:5000)

uv run run.py server --dev                                  # dev mode
uv run run.py server --waitress --port 5000                 # production (Waitress)
```

`run.py` is the unified CLI entrypoint. The default web port is `5000`. Production mode requires the `ENDFIELD_SECRET_KEY` environment variable.

## Core implementation

### `gacha_core/`

- `gacha_core/randomizer.py`: `BatchRandom`
- `gacha_core/config.py`: `GlobalConfigLoader`
- `gacha_core/char.py`: `CharGacha`
- `gacha_core/weapon.py`: `WeaponGacha`
- `gacha_core/models.py`: `GachaResult`, `Counters`

### Character banner

- Single pull cost: 1 Chartered Headhunting Permit or 500 Oroberyl
- Base rates: 6★ 0.8%, 5★ 8%, 4★ 91.2%
- 5★ pity: every 10 pulls
- 6★ soft pity: starts after pull 66, +5% per pull, guaranteed on pull 80
- Featured 6★ hard pity: 120 pulls
- Rewards from pulls: 6★ 2000 Arsenal Tickets, 5★ 200, 4★ 20
- Accumulated rewards: urgent recruitment at 30 pulls, dossier at 60 pulls, repeated featured token every 240 pulls
- Urgent recruitment via 10 consecutive `attempt()` calls (web endpoint `/api/urgent_recruitment`)

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

- `scheduler/strategy_rules.py` only supports structured rule trees
- `scheduler/strategy_protocol.py` uses `strategy-protocol-v1`
- legacy magic strategies remain as archives and are not accepted by the protocol layer
- `Scheduler.banner(...)` and `Scheduler.evaluate_multiple_strategies(...)` automatically adapt supported payloads

### Scoring

- Main scoring implementation: `scheduler/scoring.py`
- Current scoring version: `SCORING_VERSION = 2.4.0`
- Four scoring dimensions: goal, utility, resource, and risk
- `BaselineEstimator` uses file caching and near-state cubic-spline interpolation
- The current scoring path is character-banner only

### Web service

- App factory: `web/app.py`
- Routes: `web/routes/` (gacha, info, resources, eval)
- Background evaluation: `web/eval_jobs.py` (thread pool with job_id polling)
- Storage: SQLite database `data/userdata.db`
- User identity: MD5 hash of IP + User-Agent
- Supported operations: recharge, exchange, gacha, urgent recruitment
- Evaluation endpoints: `/api/eval/jobs` (async), `/api/eval/compare` (sync)
- Production mode serves pre-compressed `.br`/`.gz` static assets

### CLI tools

- `cli/demo.py`: `GachaTestTool` wrapping character/weapon demos and statistics (delegates to `_demo_char.py`, `_demo_weapon.py`)
- `cli/evaluation.py`: scenario-based strategy evaluation from `evaluation_examples.json`
- `cli/examination.py`: probability distribution verification (guarantee-disabled mode)

## Configuration

The code actually reads:

- `configs/constants.json`
- `configs/char_pool_base.json`
- `configs/config_*/char_banner.json`
- `configs/weapon_pool_base.json`
- `configs/config_*/weapon_banners.json`
- `configs/config_*/gacha_rules.json`
- `configs/arrangement`
- `configs/arrange1`

The first line of `configs/arrangement` determines the default config directory. `configs/arrange1` is used for scheduler ordering. Seven config directories exist (`config_1` through `config_7`). Both banner types use explicit banner files; legacy `char_pool.json` and `weapon_pool.json` are archived under `legacy/configs/`. `gacha_rules.json` only stores per-config reward overrides; shared rules and banner defaults come from `configs/constants.json`.

## Documentation map

- [Chinese mechanics](doc/mechanics.md)
- [English mechanics](doc/mechanics_en.md)
- [Strategy protocol](doc/strategy_protocol.md)
- [Developer reference](doc/developer-reference.md)
- [Evaluation page design](doc/cross-pool-evaluation-result-page-design.md)
- [Character config migration record](doc/implementation_records/2026-05-26-char-config.md)
- [Runtime package split record](doc/implementation_records/2026-05-26-runtime-package-split.md)
- [Scoring follow-up record](doc/implementation_records/2026-05-26-scoring-followup.md)
- [Legacy scoring design archive](legacy/doc/策略评分系统设计方案.md)

## Development commands

```bash
uv run pytest test/ -v
uv run ruff check .
uv run pyright
npm install
uv run python build/compress.py
```

Static compression notes:
- `build/compress.py` uses pinned local tools: `terser` + `javascript-obfuscator` (JS) and `lightningcss` (CSS).
- The build generates `.gz` and `.br` precompressed variants for text assets (Nginx with `gzip_static on; brotli_static on;`).
- Build artifacts are written to `dist/static`, while source static files stay in `web/static` (production serves `dist/static` by default).
- In production mode (including Waitress), static responses prefer `.br` / `.gz` by `Accept-Encoding` and set `Vary: Accept-Encoding`.
- Nginx template is provided at `deploy/nginx/static-compression.conf`.
- Obfuscation is enabled by default (`ENABLE_ASSET_OBFUSCATION=1`): JS gets a second obfuscation pass, and source maps strip `sourcesContent`; set `ENABLE_ASSET_OBFUSCATION=0` to disable.

## Important implementation notes

- The code does not implement separate duplicate-operator or duplicate-weapon exchange systems; duplicates only update collection and resource counters
- The current sample banners in `configs/config_1` are `「熔火灼痕」` and `「熔铸申领」`
- `gacha_rules.json` only keeps per-config overrides; shared defaults come from `configs/constants.json`
- The protocol layer no longer accepts `legacy_magic` payloads
- Production mode requires the `ENDFIELD_SECRET_KEY` environment variable
- Background evaluations run via `EvaluationJobManager` (thread pool), with at most 2 concurrent evaluation jobs
