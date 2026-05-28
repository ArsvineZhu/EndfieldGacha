# Endfield Gacha Mechanics

**Updated**: 2026-05-28

This document describes the behavior actually implemented in the repository. If it conflicts with older notes, the code wins.

---

## 1. Character Banner

### 1.1 Entry and Cost

- Class: `gacha_core.CharGacha`
- Mode: single pull
- Cost: 1 `chartered_permits` or 500 `oroberyl`

### 1.2 Base Rates

- 6★: 0.8%
- 5★: 8%
- 4★: 91.2%

Within a rarity, operators are split according to the `up_prob` values in the configuration. In `configs/config_1`, the sample banner name is `「熔火灼痕」` and the featured 6★ operator is `莱万汀`.

### 1.3 Pity Rules

- 5★ pity: every 10 pulls guarantees 5★+.
- 6★ soft pity: starts from pull 66, increases by 5% per pull, capped at 100%.
- 6★ hard pity: guaranteed on pull 80.
- Featured 6★ hard pity: guaranteed on pull 120, controlled by the `guarantee_used` state flag.

### 1.4 Rewards and Counters

Every character pull awards Arsenal Tickets:

- 6★: 2000
- 5★: 200
- 4★: 20

The current implementation of `get_accumulated_reward()` returns:

- 30 pulls: `加急招募`
- 60 pulls: `寻访情报书`
- every 240 pulls: the configured Type_C token reward

In `configs/config_1`, Type_C is `莱万汀的信物`.

---

## 2. Weapon Issue

### 2.1 Entry and Cost

- Class: `gacha_core.WeaponGacha`
- Mode: fixed 10-pull issue
- Cost: 1980 `arsenal_tickets`

### 2.2 Base Rates

- 6★: 4%
- 5★: 15%
- 4★: 81%

Within a rarity, weapons are split according to the `up_prob` values in the configuration. In `configs/config_1`, the sample banner name is `「熔铸申领」` and the featured weapon is `熔铸火焰`.

### 2.3 Pity Rules

- Single-issue pity: if no 5★+ appears in the 10 pulls, the last pull is replaced with a 5★+ result.
- 6★ pity: every 4 issues guarantees a 6★ result on the last pull.
- Featured 6★ pity: every 8 issues guarantees the featured weapon on the last pull.
- Priority: featured 6★ > 6★ > 5★

### 2.4 Rewards and Counters

Every weapon issue awards AIC Quota:

- 6★: 50
- 5★: 10
- 4★: 1

The current implementation of `get_accumulated_reward()` starts at the 10th issue and alternates Type_A and Type_B every 8 issues.

---

## 3. Web User State

### 3.1 Storage

- Entry: `web/user.py`
- Database: `data/userdata.db`
- User ID: MD5 of IP + User-Agent

### 3.2 Default Resources

New users start with:

- `chartered_permits`: 10
- `oroberyl`: 50000
- `arsenal_tickets`: 8000
- `origeometry`: 100
- `urgent_recruitment`: 0
- `urgent_used`: False

### 3.3 Recharge and Exchange

- Recharge tiers: 6 / 30 / 98 / 198 / 328 / 648
- `origeometry` can be exchanged to:
  - `oroberyl` at 1:75
  - `arsenal_tickets` at 1:25

The code does not implement a separate duplicate-operator or duplicate-weapon exchange system. Duplicate results only update collection counts and normal reward counters.

---

## 4. Configuration Files

The code only reads:

- `configs/constants.json`
- `configs/char_pool_base.json`
- `configs/config_*/char_banner.json`
- `configs/weapon_pool_base.json`
- `configs/config_*/weapon_banners.json`
- `configs/config_*/gacha_rules.json`
- `configs/arrangement`
- `configs/arrange1`

`configs/constants.json` provides shared probability, pity, quota, and default reward settings; `config_*/gacha_rules.json` only overrides per-banner differences.

---

## 5. Implementation Notes

- Pull results are returned as `GachaResult(name, star, quota, is_up_g, is_6_g, is_5_g)`
- Both banners use `BatchRandom` for pre-generated random numbers
- `disable_guarantee=True` is for pure probability validation
- The web app compresses static assets before startup unless dev mode (`--dev`) is requested


