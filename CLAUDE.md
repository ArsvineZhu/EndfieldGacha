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
- `uv run pytest test/server_routes_test.py test/eval_routes_test.py -v` — web route tests
- `node test/eval_render_test.cjs` — eval render snapshot test (Node.js)
- `uv run ruff check .` — lint
- `uv run pyright` — type check
- `npm install` — install pinned frontend compression tools
- `uv run python build/compress.py` — compress static files
- `uv run python build/precompute_cache.py` — pre-compute baseline value cache (offline)
- `uv run python test/compress_test.py` — verify compression output

## Project Structure

```
EndfieldGacha/
├── run.py                  # Unified CLI entrypoint
├── pyproject.toml          # Project metadata & dependencies
├── .env.example            # Environment variable template
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
│   ├── scoring.py          # ScoringSystem v2.4.0 (goal/utility/resource/risk)
│   ├── baseline.py         # BaselineEstimator (MC + SQLite cache + spline)
│   ├── cache_db.py         # BaselineCacheDB (SQLite/WAL cache backend)
│   ├── models.py           # Data models (Resource, StageTrace, ScoreReport, etc.)
│   ├── workers.py          # Simulation runtime + multiprocessing worker
│   ├── display.py          # Rich-formatted console output
│   ├── strategy_rules.py   # StrategyCondition / StrategyRuleSet engine
│   └── strategy_protocol.py# strategy-protocol-v1 adapter
├── web/                    # Flask web application
│   ├── __init__.py         # Package marker
│   ├── app.py              # App factory + static file serving
│   ├── routes/             # API route modules
│   │   ├── __init__.py     # Route registration + manifest helper
│   │   ├── gacha.py        # Gacha, urgent recruitment, rewards APIs
│   │   ├── info.py         # Home page, user data, pool info APIs
│   │   ├── resources.py    # Recharge & exchange APIs
│   │   └── eval.py         # Evaluation job & comparison APIs
│   ├── resource.py         # Recharge/exchange/consume logic
│   ├── user.py             # SQLite user storage (IP+UA based identity)
│   ├── eval_jobs.py        # Background evaluation job manager (thread pool)
│   ├── evaluator.py        # Web evaluation helpers + payload validation
│   ├── templates/          # HTML templates (index.html, eval.html)
│   └── static/             # Source static files (CSS, JS, manifest, favicons)
│       ├── pages/gacha/    # Gacha page assets
│       └── pages/eval/     # Evaluation page assets
├── cli/                    # CLI tools
│   ├── demo.py             # GachaTestTool entry + main function
│   ├── _demo_char.py       # Character banner demo & statistics
│   ├── _demo_weapon.py     # Weapon banner demo & statistics
│   ├── _demo_ui.py         # Color/display helpers
│   ├── evaluation.py       # Strategy evaluation runner
│   ├── examination.py      # Probability distribution verification
│   └── evaluation_examples.json
├── build/                  # Build utilities
│   ├── compress.py         # JS/CSS minification + hashing + manifest
│   └── precompute_cache.py # Offline baseline cache pre-computation
├── configs/                # JSON configuration files
│   ├── constants.json      # Global defaults (probabilities, pity, quotas)
│   ├── char_pool_base.json # Shared character rosters
│   ├── weapon_pool_base.json # Shared weapon rosters
│   ├── arrangement         # Banner order (config_1..config_7) — first line = default
│   ├── arrange1            # Scheduler default subset (config_3..config_7)
│   ├── config_1/           # Example banner: char_banner, weapon_banners, gacha_rules
│   ├── config_2/ ...       # Additional banner configurations
│   └── config_7/
├── data/                   # Runtime data (baseline_cache.db, userdata.db) [gitignored]
├── deploy/                 # Deployment templates
│   └── nginx/static-compression.conf
├── doc/                    # Documentation
├── scripts/                # Startup scripts
│   ├── start.bat
│   ├── start.ps1
│   └── start.sh
├── test/                   # pytest tests
│   ├── core_gacha_test.py
│   ├── scoring_test.py
│   ├── display_test.py
│   ├── server_routes_test.py
│   ├── eval_routes_test.py
│   ├── compress_test.py
│   └── eval_render_test.cjs   # Node.js render snapshot test
└── legacy/                 # Archived old code & configs
```

### Key Implementation Notes

- The scheduler is character-banner only (weapons excluded from scoring)
- `BaselineEstimator` cache lives at `data/baseline_cache.db` (SQLite, WAL mode). Use `uv run python build/precompute_cache.py` to pre-compute anchor state values offline.
- Scoring requires at least one `StrategyGoal` (default: obtain 1 current-up character)
- The protocol layer (`strategy_protocol.py`) auto-normalizes rules passed to `Scheduler.banner()` — callers can pass raw dicts, StrategyRuleSet, or protocol payloads
- `disable_guarantee=True` on `attempt()` freezes pity state (only total increments) — used for pure probability distribution analysis
- Web static files are minified via terser (JS) + lightningcss (CSS), with `.gz/.br` precompressed variants; build artifacts go to `dist/static`, and dev mode (`--dev` flag) keeps using source files under `web/static`
- Recharge amounts: 6/30/98/198/328/648 only. Exchange: origeometry → oroberyl (1:75) or origeometry → arsenal_tickets (1:25)
- Production mode requires `ENDFIELD_SECRET_KEY` env var; falls back to a dev-only key in dev mode
- Web app loads `.env` from project root via `_load_env_file()` if present (no python-dotenv dependency)
- `configs/arrangement` lists all 7 config dirs (first line = default config); `configs/arrange1` is the scheduler's default subset (config_3..config_7)
- `web/static/` is reorganized into `pages/gacha/` and `pages/eval/` subdirectories
- Evaluation web endpoints use a background `EvaluationJobManager` (thread pool) — POST `/api/eval/jobs` returns immediately with a job_id, pollable via GET `/api/eval/jobs/<job_id>`
- The `/api/eval/compare` endpoint is synchronous (server-side rate-limited to 2 concurrent evals)
- `CharGacha` also handles urgent recruitment (10-pull mode via `attempt_urgent()`)
- `scheduler/__init__` exports `is_structured_strategy` for runtime type checking
