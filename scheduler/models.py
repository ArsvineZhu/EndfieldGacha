# -*- coding: utf-8 -*-
"""评分数据模型与价值计算函数。"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import log
from typing import Any, Dict, Iterable, List, Optional, Tuple

from gacha_core import Counters

SCORING_VERSION = "2.3.0"
SCORING_CACHE_VERSION = "score-cache-v1"


@dataclass
class Resource:
    """抽卡资源描述。"""

    chartered_permits: int = 0
    oroberyl: int = 0
    arsenal_tickets: int = 0
    origeometry: int = 0


@dataclass(frozen=True)
class LogMapConfig:
    """对数映射配置。"""

    low: float
    high: float
    curve: float = 1.0

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "LogMapConfig":
        return cls(
            low=float(payload["low"]),
            high=float(payload["high"]),
            curve=float(payload.get("curve", 1.0)),
        )


@dataclass(frozen=True)
class StrategyGoal:
    """策略目标定义。"""

    kind: str
    target: int | float
    stage_index: Optional[int] = None
    character_name: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "StrategyGoal":
        return cls(
            kind=str(payload["kind"]),
            target=payload["target"],
            stage_index=payload.get("stage_index"),
            character_name=payload.get("character_name"),
        )


@dataclass
class StageTrace:
    """单阶段模拟轨迹。"""

    config_name: str
    start_counters: Counters
    end_counters: Counters
    paid_draws: int
    bonus_draws: int
    resource_left: int
    results: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_draws(self) -> int:
        return self.paid_draws + self.bonus_draws


@dataclass
class StrategyTrace:
    """单次完整策略轨迹。"""

    completed: bool
    total_paid_draws: int
    total_bonus_draws: int
    final_resource_left: int
    stages: List[StageTrace] = field(default_factory=list)
    failure_reason: Optional[str] = None

    @property
    def total_draws(self) -> int:
        return self.total_paid_draws + self.total_bonus_draws


@dataclass(frozen=True)
class ScoringPreferences:
    """评分偏好参数。"""

    goal_weight: float = 0.35
    utility_weight: float = 0.30
    resource_weight: float = 0.20
    risk_weight: float = 0.15
    alpha: float = 1.0
    current_up_value: float = 100.0
    past_up_value: float = 70.0
    normal_six_value: float = 45.0
    five_star_value: float = 6.0
    four_star_value: float = 1.0
    utility_log_map: LogMapConfig = LogMapConfig(low=0.60, high=1.40, curve=1.0)
    utility_absolute_log_map: LogMapConfig = LogMapConfig(
        low=0.60, high=1.40, curve=1.0
    )
    utility_absolute_reference: float = 700.0
    utility_mix_weight: float = 0.5
    resource_log_map: LogMapConfig = LogMapConfig(low=0.60, high=1.50, curve=1.0)
    opportunity_reference: float = 60.0
    risk_utility_weight: float = 0.6
    tail_ratio: float = 0.1
    future_resource_income: int = 0
    baseline_samples: int = 64
    baseline_seed: int = 20260525
    preset_name: str = "balanced"
    past_up_character_names: Tuple[str, ...] = ()
    owned_character_potentials: Dict[str, int] = field(default_factory=dict)
    questionnaire_status: str = "pending"
    future_value_policy: str = "current"

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ScoringPreferences":
        data = dict(payload)
        if "utility_log_map" in data and isinstance(data["utility_log_map"], dict):
            data["utility_log_map"] = LogMapConfig.from_dict(data["utility_log_map"])
        if "utility_absolute_log_map" in data and isinstance(
            data["utility_absolute_log_map"], dict
        ):
            data["utility_absolute_log_map"] = LogMapConfig.from_dict(
                data["utility_absolute_log_map"]
            )
        if "resource_log_map" in data and isinstance(data["resource_log_map"], dict):
            data["resource_log_map"] = LogMapConfig.from_dict(data["resource_log_map"])
        if "past_up_character_names" in data and isinstance(
            data["past_up_character_names"], list
        ):
            data["past_up_character_names"] = tuple(
                str(name) for name in data["past_up_character_names"]
            )
        if "owned_character_potentials" in data and isinstance(
            data["owned_character_potentials"], dict
        ):
            data["owned_character_potentials"] = {
                str(name): int(value)
                for name, value in data["owned_character_potentials"].items()
            }
        return cls(**data)

    @classmethod
    def from_json_file(cls, path: str) -> "ScoringPreferences":
        import json

        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        if not isinstance(payload, dict):
            raise TypeError("评分配置文件必须是 JSON 对象")
        if "preferences" in payload and isinstance(payload["preferences"], dict):
            payload = payload["preferences"]
        return cls.from_dict(payload)

    def potential_multiplier(self, potential: int) -> float:
        mapping = {
            0: 1.00,
            1: 1.11,
            2: 1.17,
            3: 1.28,
            4: 1.34,
            5: 1.50,
        }
        return mapping[min(max(potential, 0), 5)]

    @property
    def theta_signature(self) -> Tuple[Any, ...]:
        return (
            self.current_up_value,
            self.past_up_value,
            self.normal_six_value,
            self.five_star_value,
            self.four_star_value,
            tuple(sorted(self.past_up_character_names)),
            tuple(sorted(self.owned_character_potentials.items())),
        )

    @property
    def parameter_tags(self) -> List[str]:
        return [
            f"scoring:{SCORING_VERSION}",
            f"preset:{self.preset_name}",
            f"o_ref:{self.opportunity_reference}",
            f"u_ref:{self.utility_absolute_reference}",
            f"u_mix:{self.utility_mix_weight}",
            f"baseline_samples:{self.baseline_samples}",
            f"baseline_seed:{self.baseline_seed}",
            f"questionnaire:{self.questionnaire_status}",
            f"future_value:{self.future_value_policy}",
            f"past_up_count:{len(self.past_up_character_names)}",
            f"owned_potential_count:{len(self.owned_character_potentials)}",
            "weapon:excluded",
            "goal_mode:and",
            "baseline_interp:near-state-cubic-spline",
            "extensions:enabled",
        ]


@dataclass
class SixStarDistributionEstimate:
    """6 星分布解释数据。"""

    expected_six_star_count: float
    probabilities: Dict[str, float]
    tail_probabilities: Dict[str, float]
    stderr: float
    samples: int
    seed: int
    cache_hit: bool


@dataclass
class StrategyScoreReport:
    """策略评分输出。"""

    raw_score: float
    goal_score: float
    utility_score: float
    resource_score: float
    risk_score: float
    goal_completion_rate: float
    mean_utility: float
    mean_baseline: float
    utility_ratio: float
    mean_opportunity: float
    opportunity_ratio: float
    tail_risk_mean: float
    simulations: int
    grade: str
    grade_name: str
    baseline_samples: int
    baseline_seed: int
    scoring_version: str
    parameter_tags: List[str]
    cache_tags: List[str]
    rank: Optional[int] = None
    percentile: Optional[float] = None
    score_delta_from_best: Optional[float] = None
    goal_delta_from_best: Optional[float] = None
    opportunity_delta_from_best: Optional[float] = None
    traces: Optional[List[StrategyTrace]] = None


# ---------------------------------------------------------------------------
# 价值计算函数（纯函数，仅依赖模型类型）
# ---------------------------------------------------------------------------


def log_map(value: float, config: LogMapConfig) -> float:
    """对数映射：将 value 在 [low, high] 区间映射为 0-100 分。"""
    if value <= 0 or config.low <= 0 or config.high <= config.low:
        return 0.0
    if value <= config.low:
        return 0.0
    if value >= config.high:
        return 100.0
    normalized = (log(value) - log(config.low)) / (log(config.high) - log(config.low))
    normalized = max(0.0, min(1.0, normalized))
    return round(100.0 * (normalized ** config.curve), 4)


def mixed_utility_score(
    utility_ratio: float,
    utility_absolute_ratio: float,
    preferences: ScoringPreferences,
) -> float:
    """混合相对与绝对收益分数。"""
    relative_score = log_map(utility_ratio, preferences.utility_log_map)
    absolute_score = log_map(
        utility_absolute_ratio, preferences.utility_absolute_log_map
    )
    relative_norm = max(0.0, min(1.0, relative_score / 100.0))
    absolute_norm = max(0.0, min(1.0, absolute_score / 100.0))
    mix_weight = max(0.0, min(1.0, preferences.utility_mix_weight))
    if relative_norm <= 0.0 or absolute_norm <= 0.0:
        return 0.0
    return round(
        100.0
        * ((relative_norm ** mix_weight) * (absolute_norm ** (1.0 - mix_weight))),
        4,
    )


def _resolve_six_star_value(
    result: Dict[str, Any], preferences: ScoringPreferences
) -> float:
    if result.get("is_current_up"):
        return preferences.current_up_value
    if result.get("is_past_up"):
        return preferences.past_up_value
    return preferences.normal_six_value


def _calculate_six_star_incremental_value(
    name: str,
    count: int,
    base_value: float,
    preferences: ScoringPreferences,
) -> float:
    existing_potential = preferences.owned_character_potentials.get(name)
    if existing_potential is None:
        final_potential = min(max(count - 1, 0), 5)
        return base_value * preferences.potential_multiplier(final_potential)

    final_potential = min(existing_potential + count, 5)
    before = preferences.potential_multiplier(existing_potential)
    after = preferences.potential_multiplier(final_potential)
    return base_value * max(after - before, 0.0)


def calculate_results_value(
    results: Iterable[Dict[str, Any]], preferences: ScoringPreferences
) -> float:
    """Calculate total value of gacha results given preferences (potentials, valuation)."""
    six_star_copies: Dict[str, Dict[str, float]] = {}
    total_value = 0.0

    for result in results:
        star = int(result.get("star", 0))
        if star == 6:
            name = result.get("name", "")
            base_value = _resolve_six_star_value(result, preferences)
            six_star_entry = six_star_copies.setdefault(
                name, {"count": 0, "base_value": base_value}
            )
            six_star_entry["count"] += 1
            six_star_entry["base_value"] = max(
                six_star_entry["base_value"], base_value
            )
        elif star == 5:
            total_value += preferences.five_star_value
        elif star == 4:
            total_value += preferences.four_star_value

    for name, entry in six_star_copies.items():
        total_value += _calculate_six_star_incremental_value(
            name=name,
            count=int(entry["count"]),
            base_value=float(entry["base_value"]),
            preferences=preferences,
        )

    return round(total_value, 4)


def _flatten_results(trace: StrategyTrace) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for stage in trace.stages:
        results.extend(stage.results)
    return results


def calculate_trace_utility(
    trace: StrategyTrace, preferences: ScoringPreferences
) -> float:
    """Calculate total value of all gacha results in a trace."""
    return calculate_results_value(_flatten_results(trace), preferences)


def resource_to_standard_draws(resource: Resource | Dict[str, int]) -> int:
    """把资源折算为标准角色池抽数。"""

    if isinstance(resource, dict):
        resource = Resource(**resource)
    return (
        resource.chartered_permits
        + resource.oroberyl // 500
        + (resource.origeometry * 75) // 500
    )


__all__ = [
    "LogMapConfig",
    "Resource",
    "SCORING_CACHE_VERSION",
    "SCORING_VERSION",
    "ScoringPreferences",
    "SixStarDistributionEstimate",
    "StageTrace",
    "StrategyGoal",
    "StrategyScoreReport",
    "StrategyTrace",
    "calculate_results_value",
    "calculate_trace_utility",
    "log_map",
    "mixed_utility_score",
    "resource_to_standard_draws",
]
