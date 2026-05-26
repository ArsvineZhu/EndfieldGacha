# Gacha Core Module Knowledge Base

**Generated:** 2026-05-26
**Module:** Core simulation engine and configuration loader

## Overview

`gacha_core/` is the active runtime package for the simulator. The old top-level `core.py` entrypoint has been removed.

## Structure

| File | Purpose |
|---|---|
| `__init__.py` | Public exports and package version |
| `config.py` | `GlobalConfigLoader` and config normalization |
| `char.py` | `CharGacha` |
| `weapon.py` | `WeaponGacha` |
| `models.py` | `GachaResult`, `Counters` |
| `randomizer.py` | `BatchRandom` |
| `pool_utils.py` | Shared pool helpers |

## Current implementation facts

- Project/package version is `2.0.0`
- Character config is loaded from `char_pool_base.json` + `config_*/char_banner.json`
- Weapon config is loaded from `weapon_pool_base.json` + `config_*/weapon_banners.json`
- `constants.json` provides shared pity rules, quota rules, reward defaults, and banner defaults
- `gacha_rules.json` only carries per-config reward overrides
- No runtime compatibility path remains for `char_pool.json`, `weapon_pool.json`, or the removed `core.py`

## Editing guidance

- Keep loader validation strict; reject malformed config early
- Do not reintroduce top-level compatibility shims
- If config shape changes, update `configs/AGENTS.md`, `README.md`, and `ref.md`
