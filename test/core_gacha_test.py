import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core import CharGacha, Counters, GlobalConfigLoader, WeaponGacha


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_temp_config(tmp_path: Path, *, char_pool: dict | None = None, weapon_pool: dict | None = None) -> str:
    config_dir = tmp_path / "configs" / "config_test"
    config_dir.mkdir(parents=True)
    _write_json(
        config_dir / "gacha_rules.json",
        {
            "pool_info": {},
            "default_precision": 6,
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
                "up_char_name": "UP-CHAR",
            },
            "weapon": {
                "base_prob": {"6": 0.04, "5": 0.15, "4": 0.81},
                "guarantee_6star_apply": 4,
                "up_guarantee_apply": 8,
                "quota_rule": {"6": 50, "5": 10, "4": 1},
                "rewards": {"Type_A": "A", "Type_B": "B", "cycle": 8, "start": 10},
                "per_apply_must_have": True,
                "apply_draws": 10,
                "up_weapon_name": "UP-WEAPON",
            },
        },
    )
    _write_json(
        config_dir / "char_pool.json",
        char_pool
        or {
            "6": [{"name": "UP-CHAR", "up_prob": 0.5}, {"name": "OTHER-6", "up_prob": 0.0}],
            "5": [{"name": "FIVE-A", "up_prob": 0.0}, {"name": "FIVE-B", "up_prob": 0.0}],
            "4": [{"name": "FOUR-A", "up_prob": 0.0}, {"name": "FOUR-B", "up_prob": 0.0}],
        },
    )
    _write_json(
        config_dir / "weapon_pool.json",
        weapon_pool
        or {
            "6": [{"name": "UP-WEAPON", "up_prob": 0.25}, {"name": "OTHER-6", "up_prob": 0.0}],
            "5": [{"name": "FIVE-A", "up_prob": 0.0}, {"name": "FIVE-B", "up_prob": 0.0}],
            "4": [{"name": "FOUR-A", "up_prob": 0.0}, {"name": "FOUR-B", "up_prob": 0.0}],
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
        char_pool={
            "6": [{"name": "UP-CHAR", "up_prob": 0.8}, {"name": "OTHER-6", "up_prob": 0.4}],
            "5": [{"name": "FIVE-A", "up_prob": 0.0}],
            "4": [{"name": "FOUR-A", "up_prob": 0.0}],
        },
    )
    config = GlobalConfigLoader(config_path)

    with pytest.raises(ValueError, match="UP 概率"):
        CharGacha(config=config)


def test_missing_normal_pool_for_partial_up_probability_raises_value_error(tmp_path):
    config_path = _make_temp_config(
        tmp_path,
        char_pool={
            "6": [{"name": "UP-CHAR", "up_prob": 0.5}],
            "5": [{"name": "FIVE-A", "up_prob": 0.0}],
            "4": [{"name": "FOUR-A", "up_prob": 0.0}],
        },
    )
    config = GlobalConfigLoader(config_path)

    with pytest.raises(ValueError, match="普通池"):
        CharGacha(config=config)
