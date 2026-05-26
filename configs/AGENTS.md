# Configs Module Knowledge Base

**Generated:** 2026-05-26
**Module:** Configuration sets for the simulator

## Overview

`configs/` stores the configuration sets used by `GlobalConfigLoader`.

## Structure

```text
configs/
├── constants.json
├── char_pool_base.json
├── weapon_pool_base.json
├── arrangement
├── arrange1
├── config_1/
│   ├── char_banner.json
│   ├── weapon_banners.json
│   └── gacha_rules.json
├── config_2/
├── config_3/
├── config_4/
├── config_5/
├── config_6/
└── config_7/
```

## Where to look

| Task | Location | Notes |
|---|---|---|
| Modify shared gacha defaults | `constants.json` | Shared base_prob, pity, quota, default rewards |
| Modify the shared character pool | `char_pool_base.json` | Shared 6-star normals, 5-star pool, 4-star pool |
| Modify the shared weapon pool | `weapon_pool_base.json` | Shared 6-star normals, 5-star pool, 4-star pool |
| Modify one character banner | `config_*/char_banner.json` | `featured.current_up`, `featured.past_up`; common defaults come from `constants.json` |
| Modify one weapon config set | `config_*/weapon_banners.json` | One config can declare multiple weapon banners; common defaults come from `constants.json` |
| Modify per-config overrides | `config_*/gacha_rules.json` | Per-banner rewards and text overrides |
| Adjust default config order | `arrangement` | One config directory per line |
| Adjust scheduler order | `arrange1` | Scheduler-specific ordering |

## Current implementation facts

- `config_1` is the default example config
- `constants.json` provides shared gacha defaults
- `constants.json.banner_defaults` provides shared banner defaults for both banner types
- `gacha_rules.json` only stores per-config reward overrides
- Character banner config is mandatory; the runtime no longer reads `char_pool.json`
- Weapon banner config is mandatory; the runtime no longer reads `weapon_pool.json`
- `GlobalConfigLoader` reads the first line of `arrangement` when no explicit path is given

## Conventions

- Keep the JSON structure stable
- Do not add arbitrary extra fields unless the runtime reads them
- Keep `arrangement` and `arrange1` in sync with the configuration directories that are actually present
