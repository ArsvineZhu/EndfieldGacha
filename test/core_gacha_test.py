import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from gacha_core import CharGacha, Counters, GlobalConfigLoader, WeaponGacha


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_temp_config(
    tmp_path: Path,
    *,
    char_banner: dict | None = None,
    weapon_pool: dict | None = None,
    weapon_banner: dict | None = None,
    char_pool_base: dict | None = None,
) -> str:
    configs_root = tmp_path / "configs"
    config_dir = configs_root / "config_test"
    configs_root.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        configs_root / "constants.json",
        {
            "schema_version": "global-constants",
            "default_precision": 6,
            "banner_defaults": {
                "char": {
                    "schema_version": "char-banner",
                    "base_profile": "standard",
                    "featured": {"current_up": [], "past_up": [], "normal": []},
                    "rates": {"up_6star_total_prob": 0.5},
                    "pool_overrides": {},
                },
                "weapon": {
                    "schema_version": "weapon-banner",
                    "base_profile": "standard",
                    "rates": {"up_6star_total_prob": 0.25},
                    "pool_overrides": {"six_star_add": []},
                },
            },
            "char": {
                "base_prob": {"6": 0.008, "5": 0.08, "4": 0.912},
                "guarantee_5star_plus_draw": 10,
                "guarantee_6star_draw": 80,
                "6star_prob_increase_start": 65,
                "prob_increase": 0.05,
                "prob_upper_limit": 1.0,
                "up_guarantee_draw": 120,
                "quota_rule": {"6": 2000, "5": 200, "4": 20},
                "rewards": {"Type_A": "A", "Type_B": "B", "Type_C": "C"},
            },
            "weapon": {
                "base_prob": {"6": 0.04, "5": 0.15, "4": 0.81},
                "guarantee_6star_apply": 4,
                "up_guarantee_apply": 8,
                "quota_rule": {"6": 50, "5": 10, "4": 1},
                "rewards": {"Type_A": "A", "Type_B": "B", "cycle": 8, "start": 10},
                "per_apply_must_have": True,
                "apply_draws": 10,
            },
        },
    )
    _write_json(
        configs_root / "char_pool_base.json",
        char_pool_base
        or {
            "schema_version": "char-pool-base",
            "shared_pools": {
                "standard": {
                    "six_star_normal": ["OTHER-6"],
                    "five_star": ["FIVE-A", "FIVE-B"],
                    "four_star": ["FOUR-A", "FOUR-B"],
                }
            },
        },
    )
    _write_json(
        config_dir / "gacha_rules.json",
        {
            "schema_version": "gacha-rules",
            "char": {
                "rewards": {"Type_C": "C"},
            },
            "weapon": {
                "rewards": {"Type_A": "A", "Type_B": "B"},
            },
        },
    )
    if weapon_pool is None:
        weapon_pool = {
            "6": [
                {"name": "UP-WEAPON", "type": "单手剑", "up_prob": 0.25},
                {"name": "OTHER-6", "type": "单手剑", "up_prob": 0.0},
            ],
            "5": [
                {"name": "FIVE-A", "type": "单手剑", "up_prob": 0.0},
                {"name": "FIVE-B", "type": "单手剑", "up_prob": 0.0},
            ],
            "4": [
                {"name": "FOUR-A", "type": "单手剑", "up_prob": 0.0},
                {"name": "FOUR-B", "type": "单手剑", "up_prob": 0.0},
            ],
        }
    up_items = [item for item in weapon_pool["6"] if float(item.get("up_prob", 0.0)) > 0]
    if not up_items:
        raise ValueError("weapon_pool.6 需要至少一个 up_prob > 0 的条目")
    six_star_normal = [
        {"name": item["name"], "type": item.get("type", "单手剑")}
        for item in weapon_pool["6"]
        if float(item.get("up_prob", 0.0)) <= 0
    ]
    five_star = [
        {"name": item["name"], "type": item.get("type", "单手剑")}
        for item in weapon_pool["5"]
    ]
    four_star = [
        {"name": item["name"], "type": item.get("type", "单手剑")}
        for item in weapon_pool["4"]
    ]
    _write_json(
        configs_root / "weapon_pool_base.json",
        {
            "schema_version": "weapon-pool-base",
            "shared_pools": {
                "standard": {
                    "six_star_normal": six_star_normal,
                    "five_star": five_star,
                    "four_star": four_star,
                }
            },
        },
    )
    banner_payload = weapon_banner or {
        "id": "main",
        "pool_name": "Test Weapon Banner",
        "open_time": "",
        "close_time": "",
        "featured": {
            "current_up": [
                {"name": up_items[0]["name"], "type": up_items[0].get("type", "单手剑")}
            ]
        },
        "rates": {"up_6star_total_prob": float(up_items[0].get("up_prob", 0.25))},
        "primary_current_up": up_items[0]["name"],
    }
    if "id" not in banner_payload:
        banner_payload = {"id": "main", **banner_payload}

    _write_json(
        config_dir / "weapon_banners.json",
        {
            "schema_version": "weapon-banners",
            "default_banner_id": "main",
            "banners": [banner_payload],
        },
    )
    _write_json(
        config_dir / "char_banner.json",
        char_banner
        or {
            "schema_version": "char-banner",
            "base_profile": "standard",
            "pool_name": "Test Char Banner",
            "open_time": "",
            "close_time": "",
            "featured": {
                "current_up": ["UP-CHAR"],
                "past_up": [],
                "normal": [],
            },
            "rates": {"up_6star_total_prob": 0.5},
            "primary_current_up": "UP-CHAR",
            "pool_overrides": {},
        },
    )
    return str(config_dir)


def test_char_disable_guarantee_does_not_mutate_pity_state():
    config = GlobalConfigLoader("configs/config_1")
    gacha = CharGacha(config=config, seed=1)
    original = Counters(total=12, no_6star=79, no_5star_plus=9, no_up=119, guarantee_used=False)
    gacha.counters = Counters(**vars(original))

    for _ in range(20):
        gacha.attempt(disable_guarantee=True)

    assert gacha.counters.total == original.total + 20
    assert gacha.counters.no_6star == original.no_6star
    assert gacha.counters.no_5star_plus == original.no_5star_plus
    assert gacha.counters.no_up == original.no_up
    assert gacha.counters.guarantee_used is original.guarantee_used


def test_weapon_disable_guarantee_does_not_mutate_pity_state():
    config = GlobalConfigLoader("configs/config_1")
    gacha = WeaponGacha(config=config, seed=1)
    original = Counters(total=3, no_6star=3, no_5star_plus=0, no_up=7, guarantee_used=False)
    gacha.counters = Counters(**vars(original))

    for _ in range(10):
        gacha.attempt(disable_guarantee=True)

    assert gacha.counters.total == original.total + 10
    assert gacha.counters.no_6star == original.no_6star
    assert gacha.counters.no_5star_plus == original.no_5star_plus
    assert gacha.counters.no_up == original.no_up
    assert gacha.counters.guarantee_used is original.guarantee_used


def test_seeded_char_instances_are_reproducible_when_interleaved():
    config = GlobalConfigLoader("configs/config_1")
    solo_a = CharGacha(config=config, seed=11)
    solo_b = CharGacha(config=config, seed=29)
    inter_a = CharGacha(config=config, seed=11)
    inter_b = CharGacha(config=config, seed=29)

    expected_a = [solo_a.attempt().name for _ in range(20)]
    expected_b = [solo_b.attempt().name for _ in range(20)]
    actual_a = []
    actual_b = []
    for _ in range(20):
        actual_a.append(inter_a.attempt().name)
        actual_b.append(inter_b.attempt().name)

    assert actual_a == expected_a
    assert actual_b == expected_b


def test_seeded_weapon_instances_are_reproducible_when_interleaved():
    config = GlobalConfigLoader("configs/config_1")
    solo_a = WeaponGacha(config=config, seed=11)
    solo_b = WeaponGacha(config=config, seed=29)
    inter_a = WeaponGacha(config=config, seed=11)
    inter_b = WeaponGacha(config=config, seed=29)

    expected_a = [[item.name for item in solo_a.attempt()] for _ in range(8)]
    expected_b = [[item.name for item in solo_b.attempt()] for _ in range(8)]
    actual_a = []
    actual_b = []
    for _ in range(8):
        actual_a.append([item.name for item in inter_a.attempt()])
        actual_b.append([item.name for item in inter_b.attempt()])

    assert actual_a == expected_a
    assert actual_b == expected_b


def test_rule_config_is_isolated_from_cached_json():
    config = GlobalConfigLoader("configs/config_1")

    rules_a = config.get_rule_config("char")
    rules_a["quota_rule"][6] = 9999
    rules_a["base_prob"][6] = rules_a["base_prob"][6] * 2

    rules_b = config.get_rule_config("char")

    assert rules_b["quota_rule"][6] == 2000
    assert rules_b["base_prob"][6] == Decimal("0.008")


def test_char_soft_pity_distribution_matches_readme_assumption():
    config = GlobalConfigLoader("configs/config_1")
    gacha = CharGacha(config=config, seed=7, size=8192)
    sample_count = 40000
    counts = {4: 0, 5: 0, 6: 0}

    for _ in range(sample_count):
        gacha.counters = Counters(total=0, no_6star=68, no_5star_plus=0, no_up=0, guarantee_used=False)
        counts[gacha.attempt().star] += 1

    assert counts[6] / sample_count == pytest.approx(0.208, abs=0.02)
    assert counts[5] / sample_count == pytest.approx(0.0638, abs=0.015)
    assert counts[4] / sample_count == pytest.approx(0.7281, abs=0.02)


def test_char_hard_pity_triggers_on_80th_draw():
    config = GlobalConfigLoader("configs/config_1")
    gacha = CharGacha(config=config, seed=3)
    gacha.counters = Counters(total=79, no_6star=79, no_5star_plus=0, no_up=0, guarantee_used=False)

    result = gacha.attempt()

    assert result.star == 6
    assert result.is_6_g is True


def test_char_up_pity_triggers_on_120th_draw():
    config = GlobalConfigLoader("configs/config_1")
    gacha = CharGacha(config=config, seed=3)
    gacha.counters = Counters(total=119, no_6star=0, no_5star_plus=0, no_up=119, guarantee_used=False)

    result = gacha.attempt()

    assert result.star == 6
    assert result.name == gacha.up_char_name
    assert result.is_up_g is True


def test_weapon_hard_pity_triggers_on_fourth_apply(tmp_path):
    config_path = _make_temp_config(
        tmp_path,
        weapon_pool={
            "6": [{"name": "UP-WEAPON", "up_prob": 0.25}, {"name": "OTHER-6", "up_prob": 0.0}],
            "5": [{"name": "FIVE-A", "up_prob": 0.0}],
            "4": [{"name": "FOUR-A", "up_prob": 0.0}],
        },
    )
    config = GlobalConfigLoader(config_path)
    gacha = WeaponGacha(config=config, seed=5)
    gacha.counters = Counters(total=3, no_6star=3, no_5star_plus=0, no_up=0, guarantee_used=False)
    gacha.rule_config["base_prob"] = {6: 0, 5: 0, 4: 1}

    results = gacha.attempt()

    assert results[-1].star == 6
    assert results[-1].is_6_g is True


def test_weapon_up_pity_takes_priority_over_hard_pity(tmp_path):
    config_path = _make_temp_config(tmp_path)
    config = GlobalConfigLoader(config_path)
    gacha = WeaponGacha(config=config, seed=5)
    gacha.counters = Counters(total=7, no_6star=3, no_5star_plus=0, no_up=7, guarantee_used=False)
    gacha.rule_config["base_prob"] = {6: 0, 5: 0, 4: 1}

    results = gacha.attempt()

    assert results[-1].name == gacha.up_weapon_name
    assert results[-1].star == 6
    assert results[-1].is_up_g is True
    assert results[-1].is_6_g is False


def test_invalid_up_probability_raises_value_error(tmp_path):
    config_path = _make_temp_config(
        tmp_path,
        char_banner={
            "schema_version": "char-banner",
            "base_profile": "standard",
            "pool_name": "Broken Banner",
            "open_time": "",
            "close_time": "",
            "featured": {
                "current_up": ["UP-CHAR"],
                "past_up": [],
                "normal": [],
            },
            "rates": {"up_6star_total_prob": 1.2},
            "primary_current_up": "UP-CHAR",
            "pool_overrides": {},
        },
    )
    config = GlobalConfigLoader(config_path)

    with pytest.raises(ValueError, match="up_6star_total_prob"):
        config.get_pool_data("char")


def test_missing_char_banner_raises_file_not_found_error(tmp_path):
    config_path = _make_temp_config(
        tmp_path,
    )
    os.remove(os.path.join(config_path, "char_banner.json"))
    config = GlobalConfigLoader(config_path)

    with pytest.raises(FileNotFoundError, match="char_banner.json"):
        config.get_pool_data("char")


def test_invalid_primary_current_up_raises_value_error(tmp_path):
    config_path = _make_temp_config(
        tmp_path,
        char_banner={
            "schema_version": "char-banner",
            "base_profile": "standard",
            "pool_name": "Broken Banner",
            "open_time": "",
            "close_time": "",
            "featured": {
                "current_up": ["UP-CHAR"],
                "past_up": [],
                "normal": [],
            },
            "rates": {"up_6star_total_prob": 0.5},
            "primary_current_up": "OTHER-6",
            "pool_overrides": {},
        },
    )
    config = GlobalConfigLoader(config_path)

    with pytest.raises(ValueError, match="primary_current_up"):
        config.get_pool_data("char")


def test_char_banner_defaults_apply_and_zero_current_up_is_supported():
    config = GlobalConfigLoader("configs/config_7")

    featured = config.get_char_featured_names()
    pool_data = config.get_pool_data("char")
    rules = config.get_rule_config("char")

    assert featured["current_up"] == []
    assert featured["past_up"] == ["莱万汀", "洁尔佩塔"]
    assert featured["normal"][:2] == ["艾尔黛拉", "骏卫"]
    assert len(pool_data["6"]) == 4
    assert sum(item["up_prob"] for item in pool_data["6"]) == pytest.approx(0.0)
    assert rules["up_char_name"] == ""

    gacha = CharGacha(config=config, seed=5)
    result = gacha.attempt()
    assert result.star in {4, 5, 6}


def test_banner_defaults_allow_minimal_banner_payloads(tmp_path):
    config_path = _make_temp_config(
        tmp_path,
        char_banner={
            "schema_version": "char-banner",
            "pool_name": "Minimal Char Banner",
            "open_time": "",
            "close_time": "",
            "featured": {"current_up": ["UP-CHAR"]},
        },
        weapon_banner={
            "schema_version": "weapon-banner",
            "pool_name": "Minimal Weapon Banner",
            "open_time": "",
            "close_time": "",
            "featured": {"current_up": [{"name": "UP-WEAPON", "type": "单手剑"}]},
        },
    )

    config = GlobalConfigLoader(config_path)

    assert config.get_rule_config("char")["up_char_name"] == "UP-CHAR"
    assert config.get_rule_config("weapon")["up_weapon_name"] == "UP-WEAPON"


def test_weapon_banner_supports_multiple_current_up_items():
    config = GlobalConfigLoader("configs/config_7")

    banners = config.get_weapon_banners()
    assert [banner["id"] for banner in banners] == ["forge", "swift"]
    assert config.get_active_weapon_banner_id() == "forge"

    pool_data = config.get_pool_data("weapon")
    up_items = [item for item in pool_data["6"] if item["up_prob"] > 0]
    assert {item["name"] for item in up_items} == {"熔铸火焰"}
    assert sum(item["up_prob"] for item in up_items) == pytest.approx(0.25)

    forge_gacha = WeaponGacha(config=config, seed=9)
    swift_config = GlobalConfigLoader("configs/config_7", weapon_banner_id="swift")
    swift_gacha = WeaponGacha(config=swift_config, seed=9)
    assert forge_gacha.star_up_prob[6][0] == ["熔铸火焰"]
    assert swift_gacha.star_up_prob[6][0] == ["使命必达"]

