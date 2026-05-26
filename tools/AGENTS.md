# Tools Module Knowledge Base

**Generated:** 2026-05-26
**Module:** Demo, statistics, evaluation, and verification utilities

## Overview

`tools/` contains the runnable scripts used for demo output, statistical analysis, strategy evaluation, and probability verification.

## Structure

```text
tools/
├── __init__.py
├── demo.py
├── evaluation.py
└── examination.py
```

## Where to look

| Task | Location | Notes |
|---|---|---|
| Character banner demo | `demo.py` | `demo_char_draw()` |
| Weapon issue demo | `demo.py` | `demo_weapon_apply()` |
| Character quota stats | `demo.py` | `stats_char_quota()` |
| Weapon quota stats | `demo.py` | `stats_weapon_quota()` |
| UP pull distribution | `demo.py` | `stats_char_up_prob()` |
| Character potential stats | `demo.py` | `stats_char_potential()` |
| Scenario-based evaluation | `evaluation.py` | Reads `evaluation_examples.json` |
| Pure probability verification | `examination.py` | Uses `disable_guarantee=True` |

## Conventions

- The default statistical sample size in the demo helpers is 50,000
- Weapon issue stats count 10-pull applications, not individual pulls
- Demo and verification scripts should not change core gacha behaviour
- Use `GlobalConfigLoader` for configuration access instead of hardcoding paths

