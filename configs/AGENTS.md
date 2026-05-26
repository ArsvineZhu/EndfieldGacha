# Configs Module Knowledge Base

**Generated:** 2026-05-26
**Module:** Configuration sets for the simulator

## Overview

`configs/` stores the configuration sets used by `GlobalConfigLoader`.

## Structure

```text
configs/
├── arrangement
├── arrange1
├── config_1/
│   ├── char_pool.json
│   ├── weapon_pool.json
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
| Modify the character pool | `config_*/char_pool.json` | `name`, `remove_after`, `up_prob` |
| Modify the weapon pool | `config_*/weapon_pool.json` | `name`, `type`, `up_prob` |
| Modify gacha rules | `config_*/gacha_rules.json` | Rates, pity, quotas, rewards |
| Adjust default config order | `arrangement` | One config directory per line |
| Adjust scheduler order | `arrange1` | Scheduler-specific ordering |

## Current implementation facts

- There is no `constants.json` file in the actual repository layout
- `config_1` is the default example config
- `gacha_rules.json` is the only place where pity, quota, and reward rules are defined
- `GlobalConfigLoader` reads the first line of `arrangement` when no explicit path is given

## Conventions

- Keep the JSON structure stable
- Do not add arbitrary extra fields unless the runtime reads them
- Keep `arrangement` and `arrange1` in sync with the configuration directories that are actually present

