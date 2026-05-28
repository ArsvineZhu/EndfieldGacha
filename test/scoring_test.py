import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from gacha_core import Counters, GlobalConfigLoader
from scheduler import Scheduler
from scheduler.baseline import BaselineEstimator
from scheduler.cache_db import BaselineCacheDB, preferences_hash
from scheduler.models import (
    LogMapConfig,
    Resource,
    ScoringPreferences,
    SixStarDistributionEstimate,
    StageTrace,
    StrategyGoal,
    StrategyScoreReport,
    StrategyTrace,
    calculate_trace_utility,
    log_map,
)
from scheduler.scoring import ScoringSystem
from scheduler.strategy_protocol import STRATEGY_PROTOCOL_VERSION, StrategyProtocolAdapter
from scheduler.strategy_rules import StrategyCondition, StrategyRuleEngine, StrategyRuleSet


def stop_after_draws(draw_count: int) -> StrategyRuleSet:
    return StrategyRuleSet(
        match="all",
        conditions=[StrategyCondition(kind="draws", operator=">=", value=draw_count)],
        tags=[f"draws>={draw_count}"],
    )


def stop_after_current_up_or_120_draws() -> StrategyRuleSet:
    return StrategyRuleSet(
        match="any",
        conditions=[
            StrategyCondition(kind="current_up", operator=">=", value=1),
            StrategyCondition(kind="draws", operator=">=", value=120),
        ],
        tags=["current-up-or-120-draws"],
    )


def make_trace(
    *,
    results,
    paid_draws,
    resource_left,
    start_counters=None,
    end_counters=None,
    config_name="config_3",
):
    stage = StageTrace(
        config_name=config_name,
        start_counters=start_counters or Counters(),
        end_counters=end_counters or Counters(total=paid_draws),
        paid_draws=paid_draws,
        bonus_draws=0,
        resource_left=resource_left,
        results=results,
    )
    return StrategyTrace(
        completed=True,
        total_paid_draws=paid_draws,
        total_bonus_draws=0,
        final_resource_left=resource_left,
        stages=[stage],
    )


def test_log_map_boundaries():
    config = LogMapConfig(low=0.5, high=2.0, curve=1.0)

    assert log_map(0.1, config) == 0.0
    assert log_map(0.5, config) == 0.0
    assert log_map(2.0, config) == 100.0
    assert 0.0 < log_map(1.0, config) < 100.0


def test_value_function_applies_potential_multiplier_and_linear_low_stars():
    prefs = ScoringPreferences()
    trace = make_trace(
        results=[
            {"name": "A", "star": 6, "is_current_up": True, "is_past_up": False},
            {"name": "A", "star": 6, "is_current_up": True, "is_past_up": False},
            {"name": "B", "star": 5, "is_current_up": False, "is_past_up": False},
            {"name": "C", "star": 4, "is_current_up": False, "is_past_up": False},
        ],
        paid_draws=20,
        resource_left=80,
    )

    value = calculate_trace_utility(trace, prefs)

    expected = (
        prefs.current_up_value * prefs.potential_multiplier(1)
        + prefs.five_star_value
        + prefs.four_star_value
    )
    assert value == pytest.approx(expected)


def test_score_traces_supports_and_goals_and_tail_risk():
    prefs = ScoringPreferences(
        alpha=1.0,
        utility_log_map=LogMapConfig(low=0.5, high=1.5, curve=1.0),
        resource_log_map=LogMapConfig(low=0.5, high=1.5, curve=1.0),
        opportunity_reference=100.0,
        tail_ratio=0.5,
        baseline_samples=8,
        baseline_seed=7,
        future_resource_income=0,
    )
    estimator = BaselineEstimator(config_dir="configs", samples=8, base_seed=7)
    goals = [
        StrategyGoal(kind="current_up", target=1),
        StrategyGoal(kind="resource_at_least", target=60),
        StrategyGoal(kind="stage_paid_draws_at_most", stage_index=0, target=60),
    ]

    traces = [
        make_trace(
            results=[
                {"name": "A", "star": 6, "is_current_up": True, "is_past_up": False}
            ],
            paid_draws=40,
            resource_left=80,
        ),
        make_trace(results=[], paid_draws=70, resource_left=20),
    ]

    report = ScoringSystem.score_traces(
        traces=traces,
        preferences=prefs,
        goals=goals,
        baseline_estimator=estimator,
    )

    assert isinstance(report, StrategyScoreReport)
    assert report.goal_completion_rate == 0.5
    assert report.goal_score == 50.0
    assert 0.0 <= report.risk_score <= 100.0
    assert report.raw_score >= 0.0


def test_scheduler_evaluate_returns_reproducible_report():
    prefs = ScoringPreferences(baseline_samples=6, baseline_seed=11)

    scheduler_a = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )
    scheduler_a.banner(stop_after_current_up_or_120_draws(), name="config_3")

    scheduler_b = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )
    scheduler_b.banner(stop_after_current_up_or_120_draws(), name="config_3")

    report_a = scheduler_a.evaluate(
        scale=12,
        workers=1,
        show_progress=False,
        preferences=prefs,
        goals=[StrategyGoal(kind="current_up", target=1)],
        return_traces=True,
    )
    report_b = scheduler_b.evaluate(
        scale=12,
        workers=1,
        show_progress=False,
        preferences=prefs,
        goals=[StrategyGoal(kind="current_up", target=1)],
        return_traces=True,
    )

    assert isinstance(report_a, StrategyScoreReport)
    assert report_a.raw_score == report_b.raw_score
    assert report_a.goal_completion_rate == report_b.goal_completion_rate
    assert len(report_a.traces) == 12


def test_global_config_loader_reads_char_banner_featured_names():
    config = GlobalConfigLoader("configs/config_3")

    featured = config.get_char_featured_names()
    pool_data = config.get_pool_data("char")

    assert featured["current_up"] == ["伊冯"]
    assert featured["past_up"] == ["洁尔佩塔", "莱万汀"]
    assert "余烬" in featured["normal"]
    assert sum(item["up_prob"] for item in pool_data["6"]) == pytest.approx(0.5)


def test_global_config_loader_rejects_missing_char_banner(tmp_path):
    config_dir = tmp_path / "configs" / "broken"
    config_dir.mkdir(parents=True)
    (tmp_path / "configs" / "constants.json").write_text(
        json.dumps(
            {
                "schema_version": "global-constants",
                "default_precision": 6,
                "pool_info": {},
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
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "configs" / "char_pool_base.json").write_text(
        json.dumps(
            {
                "schema_version": "char-pool-base",
                "shared_pools": {
                    "standard": {
                        "six_star_normal": ["N"],
                        "five_star": ["F5"],
                        "four_star": ["F4"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (config_dir / "gacha_rules.json").write_text(
        json.dumps(
            {
                "schema_version": "gacha-rules",
                "char": {
                    "rewards": {"Type_C": "C"},
                },
                "weapon": {
                    "rewards": {"Type_A": "A", "Type_B": "B"},
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "configs" / "weapon_pool_base.json").write_text(
        json.dumps(
            {
                "schema_version": "weapon-pool-base",
                "shared_pools": {
                    "standard": {
                        "six_star_normal": [{"name": "W2", "type": "施术单元"}],
                        "five_star": [{"name": "F5", "type": "施术单元"}],
                        "four_star": [{"name": "F4", "type": "施术单元"}],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (config_dir / "weapon_banners.json").write_text(
        json.dumps(
            {
                "schema_version": "weapon-banners",
                "default_banner_id": "main",
                "banners": [
                    {
                        "id": "main",
                        "pool_name": "W",
                        "open_time": "",
                        "close_time": "",
                        "featured": {"current_up": [{"name": "W", "type": "施术单元"}]},
                        "rates": {"up_6star_total_prob": 0.25},
                        "primary_current_up": "W",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    config = GlobalConfigLoader(str(config_dir))

    with pytest.raises(FileNotFoundError, match="char_banner.json"):
        config.get_pool_data("char")


def test_evaluate_multiple_strategies_preserves_raw_scores_and_adds_rankings():
    prefs = ScoringPreferences(baseline_samples=6, baseline_seed=13)
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    reports = scheduler.evaluate_multiple_strategies(
        strategies=[stop_after_current_up_or_120_draws(), stop_after_draws(30)],
        scale=10,
        workers=1,
        show_progress=False,
        preferences=prefs,
        goals=[StrategyGoal(kind="current_up", target=1)],
    )

    assert len(reports) == 2
    assert all(isinstance(report, StrategyScoreReport) for report in reports)
    assert all(report.raw_score >= 0.0 for report in reports)
    assert sorted(report.rank for report in reports) == [1, 2]
    assert all(report.percentile >= 50.0 for report in reports)


def test_baseline_estimator_uses_file_cache(tmp_path):
    cache_path = tmp_path / "baseline-cache.json"
    prefs = ScoringPreferences(baseline_samples=4, baseline_seed=17)
    estimator_a = BaselineEstimator(
        config_dir="configs",
        samples=4,
        base_seed=17,
        cache_path=str(cache_path),
    )
    value_a = estimator_a.estimate("config_3", Counters(), 10, prefs)

    estimator_b = BaselineEstimator(
        config_dir="configs",
        samples=4,
        base_seed=17,
        cache_path=str(cache_path),
    )
    value_b = estimator_b.estimate("config_3", Counters(), 10, prefs)

    assert cache_path.exists()
    assert value_a == value_b
    assert estimator_b.cache_hits >= 1


def test_baseline_estimator_interpolates_from_nearby_cached_points(tmp_path):
    cache_path = tmp_path / "baseline-cache.db"
    prefs = ScoringPreferences(baseline_samples=4, baseline_seed=17)
    pref_hash = preferences_hash(prefs.theta_signature)

    db = BaselineCacheDB(str(cache_path))
    for pd, est in [(10, 100.0), (20, 200.0), (30, 300.0), (40, 400.0)]:
        db.set_baseline(
            cache_key=f"test_{pd}",
            config_name="config_3",
            counters_signature=(0, 0, 0, 0, False, False),
            paid_draws=pd,
            preferences_sig_hash=pref_hash,
            samples=4,
            seed=17,
            estimate=est,
            source="simulation",
            version="2.4.0",
        )
    db.close()

    estimator = BaselineEstimator(
        config_dir="configs",
        samples=4,
        base_seed=17,
        cache_path=str(cache_path),
    )
    value = estimator.estimate("config_3", Counters(), 25, prefs)

    assert value == pytest.approx(250.0)


def test_baseline_estimator_interpolates_from_nearby_states(tmp_path):
    cache_path = tmp_path / "baseline-cache-near-state.db"
    prefs = ScoringPreferences(baseline_samples=4, baseline_seed=17)
    pref_hash = preferences_hash(prefs.theta_signature)

    db = BaselineCacheDB(str(cache_path))
    entries = [
        (10, 100.0, (34, 14, 2, 19, False, False)),
        (20, 200.0, (35, 15, 2, 20, False, False)),
        (30, 300.0, (36, 15, 3, 21, False, False)),
        (40, 400.0, (35, 16, 2, 20, False, False)),
    ]
    for idx, (pd, est, sig) in enumerate(entries):
        db.set_baseline(
            cache_key=f"test_{idx}",
            config_name="config_3",
            counters_signature=sig,
            paid_draws=pd,
            preferences_sig_hash=pref_hash,
            samples=4,
            seed=17,
            estimate=est,
            source="simulation",
            version="2.4.0",
        )
    db.close()

    estimator = BaselineEstimator(
        config_dir="configs",
        samples=4,
        base_seed=17,
        cache_path=str(cache_path),
    )
    target_counters = Counters(total=35, no_6star=15, no_5star_plus=2, no_up=20)
    value = estimator.estimate("config_3", target_counters, 25, prefs)

    assert value == pytest.approx(250.0)


def test_six_star_distribution_uses_file_cache(tmp_path):
    cache_path = tmp_path / "distribution-cache.json"
    estimator_a = BaselineEstimator(
        config_dir="configs",
        samples=4,
        base_seed=17,
        cache_path=str(cache_path),
    )
    dist_a = estimator_a.estimate_six_star_distribution("config_3", Counters(), 10)

    estimator_b = BaselineEstimator(
        config_dir="configs",
        samples=4,
        base_seed=17,
        cache_path=str(cache_path),
    )
    dist_b = estimator_b.estimate_six_star_distribution("config_3", Counters(), 10)

    assert isinstance(dist_a, SixStarDistributionEstimate)
    assert cache_path.exists()
    assert dist_a.expected_six_star_count == dist_b.expected_six_star_count
    assert dist_b.cache_hit is True


def test_owned_potential_records_use_incremental_value():
    prefs = ScoringPreferences(
        owned_character_potentials={"A": 0},
        past_up_character_names=(),
    )
    trace = make_trace(
        results=[{"name": "A", "star": 6, "is_current_up": True, "is_past_up": False}],
        paid_draws=10,
        resource_left=90,
    )

    value = calculate_trace_utility(trace, prefs)
    expected = prefs.current_up_value * (
        prefs.potential_multiplier(1) - prefs.potential_multiplier(0)
    )
    assert value == pytest.approx(expected)


def test_past_up_name_list_drives_value_classification():
    prefs = ScoringPreferences(past_up_character_names=("PastA",))
    trace = make_trace(
        results=[{"name": "PastA", "star": 6, "is_current_up": False, "is_past_up": False}],
        paid_draws=10,
        resource_left=90,
    )
    estimator = BaselineEstimator(config_dir="configs", samples=2, base_seed=5)

    report = ScoringSystem.score_traces(
        traces=[trace],
        preferences=prefs,
        goals=[StrategyGoal(kind="six_star_count", target=1)],
        baseline_estimator=estimator,
        include_traces=True,
    )

    assert report.mean_utility == pytest.approx(prefs.past_up_value)
    assert report.traces[0].stages[0].results[0]["is_past_up"] is True


def test_report_contains_version_and_parameter_tags():
    prefs = ScoringPreferences()
    estimator = BaselineEstimator(config_dir="configs", samples=2, base_seed=5)
    report = ScoringSystem.score_traces(
        traces=[make_trace(results=[], paid_draws=0, resource_left=60)],
        preferences=prefs,
        goals=[StrategyGoal(kind="resource_at_least", target=60)],
        baseline_estimator=estimator,
    )

    assert report.scoring_version
    assert "o_ref:60.0" in report.parameter_tags
    assert "baseline_interp:near-state-cubic-spline" in report.parameter_tags
    assert any(tag.startswith("preset:") for tag in report.parameter_tags)
    assert "baseline_interp:near-state-cubic-spline" in report.cache_tags


def test_strategy_rule_engine_supports_structured_rules_without_magic():
    rule_set = StrategyRuleSet(
        match="all",
        conditions=[
            StrategyCondition(kind="draws", operator=">=", value=50),
            StrategyCondition(kind="current_up", operator=">=", value=1),
        ],
    )
    state = {"current_up": 1, "resource_left": 80}

    assert StrategyRuleEngine.should_stop(rule_set, draw_count=50, state=state) is True
    assert StrategyRuleEngine.should_stop(rule_set, draw_count=40, state=state) is False


def test_strategy_rule_engine_supports_legacy_semantic_flags():
    rule_set = StrategyRuleSet(
        match="all",
        conditions=[
            StrategyCondition(kind="urgent_recruitment", operator="==", value=True),
            StrategyCondition(kind="dossier", operator="==", value=True),
            StrategyCondition(kind="soft_pity", operator="==", value=True),
            StrategyCondition(kind="up_oprt", operator="==", value=True),
            StrategyCondition(kind="oprt", operator="==", value=True),
            StrategyCondition(kind="hard_pity", operator=">=", value=80),
        ],
    )
    state = {
        "urgent": True,
        "dossier": True,
        "soft_pity": True,
        "up_oprt": True,
        "oprt": True,
    }

    assert StrategyRuleEngine.should_stop(rule_set, draw_count=80, state=state) is True
    assert StrategyRuleEngine.should_stop(rule_set, draw_count=79, state=state) is False


def test_strategy_rule_engine_supports_nested_groups():
    rule_set = StrategyRuleSet(
        match="all",
        conditions=[
            StrategyRuleSet(
                match="any",
                conditions=[
                    StrategyCondition(kind="dossier", operator="==", value=True),
                    StrategyCondition(kind="oprt", operator="==", value=True),
                ],
            ),
            StrategyCondition(kind="urgent", operator="==", value=True),
        ],
    )

    assert StrategyRuleEngine.should_stop(
        rule_set,
        draw_count=30,
        state={"dossier": True, "oprt": False, "urgent": True},
    ) is True
    assert StrategyRuleEngine.should_stop(
        rule_set,
        draw_count=30,
        state={"dossier": False, "oprt": True, "urgent": True},
    ) is True
    assert StrategyRuleEngine.should_stop(
        rule_set,
        draw_count=30,
        state={"dossier": False, "oprt": False, "urgent": True},
    ) is False
    assert StrategyRuleEngine.should_stop(
        rule_set,
        draw_count=30,
        state={"dossier": True, "oprt": False, "urgent": False},
    ) is False


def test_score_traces_requires_at_least_one_goal():
    prefs = ScoringPreferences()
    estimator = BaselineEstimator(config_dir="configs", samples=2, base_seed=5)

    with pytest.raises(ValueError, match="至少需要一个目标"):
        ScoringSystem.score_traces(
            traces=[make_trace(results=[], paid_draws=0, resource_left=60)],
            preferences=prefs,
            goals=[],
            baseline_estimator=estimator,
        )


def test_score_traces_requires_explicit_goals_when_none():
    prefs = ScoringPreferences()
    estimator = BaselineEstimator(config_dir="configs", samples=2, base_seed=5)

    with pytest.raises(ValueError, match="goals 不能为空"):
        ScoringSystem.score_traces(
            traces=[make_trace(results=[], paid_draws=0, resource_left=60)],
            preferences=prefs,
            goals=None,
            baseline_estimator=estimator,
        )


def test_scheduler_evaluate_accepts_structured_strategy_rules():
    prefs = ScoringPreferences(baseline_samples=4, baseline_seed=19)
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )
    scheduler.banner(
        StrategyRuleSet(
            match="all",
            conditions=[StrategyCondition(kind="draws", operator=">=", value=10)],
            tags=["structured"],
        ),
        name="config_3",
    )

    report = scheduler.evaluate(
        scale=6,
        workers=1,
        show_progress=False,
        preferences=prefs,
        goals=[StrategyGoal(kind="stage_paid_draws_at_most", stage_index=0, target=10)],
    )

    assert isinstance(report, StrategyScoreReport)
    assert report.goal_completion_rate == pytest.approx(1.0)


def test_scheduler_evaluate_accepts_nested_structured_strategy_rules():
    prefs = ScoringPreferences(baseline_samples=4, baseline_seed=23)
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )
    scheduler.banner(
        StrategyRuleSet(
            match="all",
            conditions=[
                StrategyRuleSet(
                    match="any",
                    conditions=[
                        StrategyCondition(kind="dossier", operator="==", value=True),
                        StrategyCondition(kind="oprt", operator="==", value=True),
                    ],
                ),
                StrategyCondition(kind="urgent", operator="==", value=True),
            ],
            tags=["nested-structured"],
        ),
        name="config_3",
    )

    report = scheduler.evaluate(
        scale=4,
        workers=1,
        show_progress=False,
        preferences=prefs,
        goals=[StrategyGoal(kind="six_star_count", target=1)],
    )

    assert isinstance(report, StrategyScoreReport)
    assert report.simulations == 4


def test_strategy_protocol_adapter_parses_nested_structured_payload():
    payload = {
        "protocol_version": STRATEGY_PROTOCOL_VERSION,
        "kind": "structured",
        "rule": {
            "node_type": "group",
            "match": "all",
            "children": [
                {
                    "node_type": "group",
                    "match": "any",
                    "children": [
                        {
                            "node_type": "condition",
                            "kind": "dossier",
                            "operator": "==",
                            "value": True,
                        },
                        {
                            "node_type": "condition",
                            "kind": "oprt",
                            "operator": "==",
                            "value": True,
                        },
                    ],
                },
                {
                    "node_type": "condition",
                    "kind": "urgent",
                    "operator": "==",
                    "value": True,
                },
            ],
        },
    }

    parsed = StrategyProtocolAdapter.from_payload(payload)

    assert isinstance(parsed, StrategyRuleSet)
    assert StrategyRuleEngine.should_stop(
        parsed,
        draw_count=30,
        state={"dossier": True, "oprt": False, "urgent": True},
    ) is True


def test_strategy_protocol_adapter_rejects_legacy_magic_payload():
    payload = {
        "protocol_version": STRATEGY_PROTOCOL_VERSION,
        "kind": "legacy_magic",
        "rules": [[1], [30]],
    }

    with pytest.raises(ValueError, match="不再支持旧版魔数策略协议"):
        StrategyProtocolAdapter.from_payload(payload)


def test_scheduler_banner_rejects_legacy_magic_rule_list():
    scheduler = Scheduler(config_dir="configs", arrange="arrange1")

    with pytest.raises(TypeError, match="仅支持结构化策略规则"):
        scheduler.banner([30], name="config_3")


def test_scheduler_accepts_strategy_protocol_payload():
    prefs = ScoringPreferences(baseline_samples=4, baseline_seed=29)
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )
    scheduler.banner(
        {
            "protocol_version": STRATEGY_PROTOCOL_VERSION,
            "kind": "structured",
            "rule": {
                "node_type": "group",
                "match": "all",
                "children": [
                    {
                        "node_type": "group",
                        "match": "any",
                        "children": [
                            {
                                "node_type": "condition",
                                "kind": "dossier",
                                "operator": "==",
                                "value": True,
                            },
                            {
                                "node_type": "condition",
                                "kind": "oprt",
                                "operator": "==",
                                "value": True,
                            },
                        ],
                    },
                    {
                        "node_type": "condition",
                        "kind": "urgent",
                        "operator": "==",
                        "value": True,
                    },
                ],
            },
        },
        name="config_3",
    )

    report = scheduler.evaluate(
        scale=4,
        workers=1,
        show_progress=False,
        preferences=prefs,
        goals=[StrategyGoal(kind="six_star_count", target=1)],
    )

    assert isinstance(report, StrategyScoreReport)


def test_scoring_preferences_supports_structured_dict_and_file(tmp_path):
    payload = {
        "preferences": {
            "goal_weight": 0.4,
            "utility_weight": 0.25,
            "resource_weight": 0.2,
            "risk_weight": 0.15,
            "utility_log_map": {"low": 0.5, "high": 1.8, "curve": 1.1},
            "utility_absolute_log_map": {"low": 0.4, "high": 1.6, "curve": 1.0},
            "resource_log_map": {"low": 0.6, "high": 1.6, "curve": 1.0},
            "past_up_character_names": ["A", "B"],
            "owned_character_potentials": {"A": 2},
        }
    }
    config_path = tmp_path / "scoring-preferences.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    by_dict = ScoringSystem.normalize_preferences(payload["preferences"])
    by_file = ScoringSystem.normalize_preferences(str(config_path))

    assert isinstance(by_dict, ScoringPreferences)
    assert isinstance(by_file, ScoringPreferences)
    assert by_dict.goal_weight == 0.4
    assert by_dict.utility_log_map.low == 0.5
    assert by_dict.past_up_character_names == ("A", "B")
    assert by_file.owned_character_potentials["A"] == 2


def test_scheduler_evaluate_accepts_structured_preferences_and_goals(tmp_path):
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )
    scheduler.banner(stop_after_current_up_or_120_draws(), name="config_3")

    prefs = {
        "baseline_samples": 4,
        "baseline_seed": 23,
        "utility_absolute_reference": 300.0,
    }
    goals_payload = {
        "goals": [
            {"kind": "current_up", "target": 1},
            {"kind": "resource_at_least", "target": 20},
        ]
    }
    goals_path = tmp_path / "goals.json"
    goals_path.write_text(json.dumps(goals_payload), encoding="utf-8")

    report = scheduler.evaluate(
        scale=8,
        workers=1,
        show_progress=False,
        preferences=prefs,
        goals=str(goals_path),
    )

    assert isinstance(report, StrategyScoreReport)
    assert report.raw_score >= 0.0


def test_utility_score_ignores_deprecated_absolute_reference():
    traces = [
        make_trace(
            results=[{"name": "A", "star": 6, "is_current_up": True, "is_past_up": False}],
            paid_draws=40,
            resource_left=80,
        )
    ]
    goals = [StrategyGoal(kind="current_up", target=1)]
    estimator = BaselineEstimator(config_dir="configs", samples=4, base_seed=31)
    prefs_a = ScoringPreferences(utility_absolute_reference=100.0, utility_mix_weight=0.1)
    prefs_b = ScoringPreferences(utility_absolute_reference=9999.0, utility_mix_weight=0.9)

    report_a = ScoringSystem.score_traces(
        traces=traces,
        preferences=prefs_a,
        goals=goals,
        baseline_estimator=estimator,
    )
    report_b = ScoringSystem.score_traces(
        traces=traces,
        preferences=prefs_b,
        goals=goals,
        baseline_estimator=estimator,
    )

    assert report_a.utility_score == pytest.approx(report_b.utility_score)
    assert report_a.raw_score == pytest.approx(report_b.raw_score)


def test_scoring_preferences_marks_deprecated_fields_for_tags():
    prefs = ScoringPreferences.from_dict(
        {
            "utility_absolute_reference": 700.0,
            "utility_absolute_log_map": {"low": 0.6, "high": 1.4, "curve": 1.0},
            "utility_mix_weight": 0.5,
        }
    )
    assert "deprecated:utility_absolute_reference_ignored" in prefs.deprecation_tags
    assert "deprecated:utility_absolute_log_map_ignored" in prefs.deprecation_tags
    assert "deprecated:utility_mix_weight_ignored" in prefs.deprecation_tags


