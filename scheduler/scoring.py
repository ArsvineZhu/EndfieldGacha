# -*- coding: utf-8 -*-
"""V2 评分系统与资源模型。"""

from __future__ import annotations

import atexit
import json
import os
import tempfile
import time
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import md5
from math import ceil, log, sqrt
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core import CharGacha, Counters, GlobalConfigLoader

SCORING_V2_VERSION = "2.3.0"
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
            f"scoring:{SCORING_V2_VERSION}",
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


def resource_to_standard_draws(resource: Resource | Dict[str, int]) -> int:
    """把资源折算为标准角色池抽数。"""

    if isinstance(resource, dict):
        resource = Resource(**resource)
    return (
        resource.chartered_permits
        + resource.oroberyl // 500
        + (resource.origeometry * 75) // 500
    )


class JsonFileCache:
    """简单 JSON 文件缓存。"""

    def __init__(self, cache_path: str, section: str, flush_interval: int = 32):
        self.cache_path = Path(cache_path)
        self.section = section
        self.flush_interval = max(1, int(flush_interval))
        self.cache_hits = 0
        self.cache_misses = 0
        self._dirty = False
        self._pending_writes = 0
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()
        self._data.setdefault("meta", {})
        self._data["meta"]["cache_version"] = SCORING_CACHE_VERSION
        self._data.setdefault(self.section, {})
        atexit.register(self.flush)

    def get(self, key: str) -> Any:
        section_data = self._data.get(self.section, {})
        if key in section_data:
            self.cache_hits += 1
            return section_data[key]
        self.cache_misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        self._data.setdefault("meta", {})
        self._data["meta"]["cache_version"] = SCORING_CACHE_VERSION
        self._data.setdefault(self.section, {})
        self._data[self.section][key] = value
        self._dirty = True
        self._pending_writes += 1
        if not self.cache_path.exists() or self._pending_writes >= self.flush_interval:
            self.flush()

    def flush(self) -> None:
        if not self._dirty:
            return
        self._save(self._data)
        self._dirty = False
        self._pending_writes = 0

    def _load(self) -> Dict[str, Any]:
        if not self.cache_path.exists():
            return {"meta": {"cache_version": SCORING_CACHE_VERSION}, self.section: {}}
        try:
            with self.cache_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            # 遇到损坏缓存时回退到空缓存，避免评分阶段阻塞。
            return {"meta": {"cache_version": SCORING_CACHE_VERSION}, self.section: {}}

    def _save(self, data: Dict[str, Any]) -> None:
        temp_fd, temp_name = tempfile.mkstemp(
            prefix=f"{self.cache_path.stem}.",
            suffix=".tmp",
            dir=str(self.cache_path.parent),
        )
        os.close(temp_fd)
        temp_path = Path(temp_name)
        try:
            with temp_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
            for attempt in range(5):
                try:
                    os.replace(temp_path, self.cache_path)
                    return
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass


class BaselineEstimator:
    """固定种子、固定样本数的状态基准价值估计器。"""

    def __init__(
        self,
        config_dir: str = "configs",
        samples: int = 64,
        base_seed: int = 0,
        cache_path: Optional[str] = None,
    ):
        self.config_dir = config_dir
        self.samples = samples
        self.base_seed = base_seed
        self.cache_path = cache_path or os.path.join("logs", "scoring_v2_cache.json")
        self._baseline_cache = JsonFileCache(self.cache_path, "baseline")
        self._distribution_cache = JsonFileCache(self.cache_path, "six_star_distribution")

    @property
    def cache_hits(self) -> int:
        return self._baseline_cache.cache_hits + self._distribution_cache.cache_hits

    def flush_cache(self) -> None:
        self._baseline_cache.flush()
        self._distribution_cache.flush()

    def estimate(
        self,
        config_name: str,
        counters: Counters,
        paid_draws: int,
        preferences: ScoringPreferences,
    ) -> float:
        if paid_draws <= 0:
            return 0.0

        cache_key = self._cache_key(
            "baseline",
            config_name,
            counters,
            paid_draws,
            preferences.theta_signature,
            self.samples,
            self.base_seed,
        )
        cached = self._baseline_cache.get(cache_key)
        if cached is not None:
            return float(cached["estimate"])
        interpolated = self._interpolate_estimate(config_name, counters, paid_draws, preferences)
        if interpolated is not None:
            self._baseline_cache.set(
                cache_key,
                {
                    "estimate": round(interpolated, 6),
                    "config_name": config_name,
                    "paid_draws": paid_draws,
                    "samples": self.samples,
                    "seed": self.base_seed,
                    "version": SCORING_V2_VERSION,
                    "counters_signature": list(self._counters_signature(counters)),
                    "preferences_signature": self._signature_to_jsonable(
                        preferences.theta_signature
                    ),
                    "source": "spline",
                },
            )
            return interpolated

        config = GlobalConfigLoader(f"{self.config_dir}/{config_name}")
        sample_values: List[float] = []
        for index in range(self.samples):
            seed = self._build_seed(cache_key, index)
            gacha = CharGacha(config=config, seed=seed)
            gacha.counters = deepcopy(counters)
            results: List[Dict[str, Any]] = []
            up_names = set(gacha.star_up_prob.get(6, ([], []))[0])
            for _ in range(paid_draws):
                result = gacha.attempt()
                results.append(
                    {
                        "name": result.name,
                        "star": result.star,
                        "is_current_up": result.name in up_names,
                        "is_past_up": result.name in preferences.past_up_character_names,
                    }
                )
            sample_values.append(
                ScoringSystem.calculate_results_value(results, preferences)
            )

        estimate = sum(sample_values) / len(sample_values)
        self._baseline_cache.set(
            cache_key,
            {
                "estimate": round(estimate, 6),
                "config_name": config_name,
                "paid_draws": paid_draws,
                "samples": self.samples,
                "seed": self.base_seed,
                "version": SCORING_V2_VERSION,
                "counters_signature": list(self._counters_signature(counters)),
                "preferences_signature": self._signature_to_jsonable(
                    preferences.theta_signature
                ),
                "source": "simulation",
            },
        )
        return estimate

    def estimate_six_star_distribution(
        self,
        config_name: str,
        counters: Counters,
        paid_draws: int,
    ) -> SixStarDistributionEstimate:
        cache_key = self._cache_key(
            "distribution",
            config_name,
            counters,
            paid_draws,
            self.samples,
            self.base_seed,
        )
        cached = self._distribution_cache.get(cache_key)
        if cached is not None:
            return SixStarDistributionEstimate(
                expected_six_star_count=float(cached["expected_six_star_count"]),
                probabilities={k: float(v) for k, v in cached["probabilities"].items()},
                tail_probabilities={
                    k: float(v) for k, v in cached["tail_probabilities"].items()
                },
                stderr=float(cached["stderr"]),
                samples=int(cached["samples"]),
                seed=int(cached["seed"]),
                cache_hit=True,
            )

        config = GlobalConfigLoader(f"{self.config_dir}/{config_name}")
        counts: List[int] = []
        for index in range(self.samples):
            seed = self._build_seed(cache_key, index)
            gacha = CharGacha(config=config, seed=seed)
            gacha.counters = deepcopy(counters)
            six_count = 0
            for _ in range(paid_draws):
                if gacha.attempt().star == 6:
                    six_count += 1
            counts.append(six_count)

        probabilities: Dict[str, float] = {}
        tail_probabilities: Dict[str, float] = {}
        for count in sorted(set(counts)):
            probabilities[str(count)] = counts.count(count) / len(counts)
        for count in sorted(set(counts)):
            tail_probabilities[str(count)] = sum(1 for value in counts if value >= count) / len(
                counts
            )

        expected = sum(counts) / len(counts)
        variance = sum((value - expected) ** 2 for value in counts) / len(counts)
        stderr = sqrt(variance / len(counts)) if counts else 0.0

        payload = {
            "expected_six_star_count": round(expected, 6),
            "probabilities": probabilities,
            "tail_probabilities": tail_probabilities,
            "stderr": round(stderr, 8),
            "samples": self.samples,
            "seed": self.base_seed,
            "version": SCORING_V2_VERSION,
        }
        self._distribution_cache.set(cache_key, payload)
        return SixStarDistributionEstimate(
            expected_six_star_count=payload["expected_six_star_count"],
            probabilities={k: float(v) for k, v in probabilities.items()},
            tail_probabilities={k: float(v) for k, v in tail_probabilities.items()},
            stderr=payload["stderr"],
            samples=self.samples,
            seed=self.base_seed,
            cache_hit=False,
        )

    def _cache_key(self, *parts: Any) -> str:
        return md5(repr(parts).encode("utf-8")).hexdigest()

    def _build_seed(self, cache_key: str, index: int) -> int:
        payload = f"{self.base_seed}|{cache_key}|{index}".encode("utf-8")
        return int(md5(payload).hexdigest()[:8], 16)

    def _interpolate_estimate(
        self,
        config_name: str,
        counters: Counters,
        paid_draws: int,
        preferences: ScoringPreferences,
    ) -> Optional[float]:
        cache_data = self._baseline_cache._data.get("baseline", {})
        counters_signature = self._counters_signature(counters)
        preferences_signature = self._signature_to_jsonable(preferences.theta_signature)
        candidates: List[Dict[str, float]] = []
        for entry in cache_data.values():
            if entry.get("config_name") != config_name:
                continue
            if entry.get("samples") != self.samples or entry.get("seed") != self.base_seed:
                continue
            if entry.get("preferences_signature") != preferences_signature:
                continue
            state_distance = self._state_distance(
                counters_signature,
                tuple(entry.get("counters_signature", [])),
            )
            if state_distance is None:
                continue
            candidates.append(
                {
                    "paid_draws": float(entry["paid_draws"]),
                    "estimate": float(entry["estimate"]),
                    "state_distance": state_distance,
                }
            )

        if len(candidates) < 3:
            return None

        nearest_distance = min(candidate["state_distance"] for candidate in candidates)
        max_distance = max(1.5, nearest_distance + 0.75)
        nearby_candidates = [
            candidate
            for candidate in candidates
            if candidate["state_distance"] <= max_distance
        ]
        if len(nearby_candidates) < 3:
            nearby_candidates = sorted(
                candidates,
                key=lambda candidate: (
                    candidate["state_distance"],
                    abs(candidate["paid_draws"] - paid_draws),
                ),
            )[:8]

        unique_candidates_map: Dict[float, Dict[str, float]] = {}
        for candidate in sorted(
            nearby_candidates,
            key=lambda item: (
                item["state_distance"],
                abs(item["paid_draws"] - paid_draws),
            ),
        ):
            draw_key = candidate["paid_draws"]
            current = unique_candidates_map.get(draw_key)
            if current is None or candidate["state_distance"] < current["state_distance"]:
                unique_candidates_map[draw_key] = candidate

        unique_candidates = sorted(unique_candidates_map.items())
        if len(unique_candidates) < 3:
            return None

        x_values = [item[0] for item in unique_candidates]
        if paid_draws <= min(x_values) or paid_draws >= max(x_values):
            return None
        y_values = [item[1]["estimate"] for item in unique_candidates]
        try:
            from scipy.interpolate import CubicSpline
        except ImportError:
            return None
        spline = CubicSpline(x_values, y_values, extrapolate=False)
        result = float(spline(paid_draws))
        if result != result:  # NaN
            return None
        return result

    @staticmethod
    def _state_distance(
        target_signature: Tuple[Any, ...],
        candidate_signature: Tuple[Any, ...],
    ) -> Optional[float]:
        if len(target_signature) != len(candidate_signature):
            return None

        scales = (30.0, 15.0, 5.0, 30.0, 1.0, 1.0)
        distance = 0.0
        for target, candidate, scale in zip(target_signature, candidate_signature, scales):
            target_value = float(bool(target)) if isinstance(target, bool) else float(target)
            candidate_value = (
                float(bool(candidate)) if isinstance(candidate, bool) else float(candidate)
            )
            delta = (target_value - candidate_value) / scale
            distance += delta * delta
        return sqrt(distance)

    @staticmethod
    def _counters_signature(counters: Counters) -> Tuple[Any, ...]:
        return (
            counters.total,
            counters.no_6star,
            counters.no_5star_plus,
            counters.no_up,
            counters.guarantee_used,
            counters.urgent_used,
        )

    @staticmethod
    def _signature_to_jsonable(signature: Tuple[Any, ...]) -> List[Any]:
        jsonable: List[Any] = []
        for item in signature:
            if isinstance(item, tuple):
                jsonable.append(BaselineEstimator._signature_to_jsonable(item))
            else:
                jsonable.append(item)
        return jsonable


class ScoringSystem:
    """V2 评分系统。"""

    GRADE_THRESHOLDS: List[Tuple[float, str, str]] = [
        (90.0, "S", "极佳"),
        (80.0, "A", "优秀"),
        (70.0, "B", "良好"),
        (60.0, "C", "一般"),
        (50.0, "D", "较差"),
        (0.0, "E", "失败"),
    ]

    @staticmethod
    def default_preferences() -> ScoringPreferences:
        return ScoringPreferences()

    @staticmethod
    def default_goals() -> List[StrategyGoal]:
        return [StrategyGoal(kind="current_up", target=1)]

    @staticmethod
    def normalize_preferences(
        preferences: Optional[ScoringPreferences | Dict[str, Any] | str],
    ) -> ScoringPreferences:
        if preferences is None:
            return ScoringSystem.default_preferences()
        if isinstance(preferences, ScoringPreferences):
            return preferences
        if isinstance(preferences, dict):
            return ScoringPreferences.from_dict(preferences)
        if isinstance(preferences, str):
            return ScoringPreferences.from_json_file(preferences)
        raise TypeError(f"不支持的 preferences 类型: {type(preferences)}")

    @staticmethod
    def normalize_goals(
        goals: Optional[List[StrategyGoal] | List[Dict[str, Any]] | str],
    ) -> List[StrategyGoal]:
        if goals is None:
            return ScoringSystem.default_goals()
        if isinstance(goals, str):
            with open(goals, "r", encoding="utf-8") as file:
                payload: Any = json.load(file)
            if isinstance(payload, dict):
                payload = payload.get("goals")
            if not isinstance(payload, list):
                raise TypeError("goals JSON 文件必须是列表或包含 goals 列表字段")
            goals = payload
        if not isinstance(goals, list):
            raise TypeError("goals 必须是列表或 JSON 文件路径")
        normalized: List[StrategyGoal] = []
        for item in goals:
            if isinstance(item, StrategyGoal):
                normalized.append(item)
            elif isinstance(item, dict):
                normalized.append(StrategyGoal.from_dict(item))
            else:
                raise TypeError(f"不支持的 goal 节点类型: {type(item)}")
        return normalized

    @staticmethod
    def log_map(value: float, config: LogMapConfig) -> float:
        if value <= 0 or config.low <= 0 or config.high <= config.low:
            return 0.0
        if value <= config.low:
            return 0.0
        if value >= config.high:
            return 100.0
        normalized = (log(value) - log(config.low)) / (log(config.high) - log(config.low))
        normalized = max(0.0, min(1.0, normalized))
        return round(100.0 * (normalized ** config.curve), 4)

    @staticmethod
    def mixed_utility_score(
        utility_ratio: float,
        utility_absolute_ratio: float,
        preferences: ScoringPreferences,
    ) -> float:
        relative_score = ScoringSystem.log_map(utility_ratio, preferences.utility_log_map)
        absolute_score = ScoringSystem.log_map(
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

    @staticmethod
    def calculate_results_value(
        results: Iterable[Dict[str, Any]], preferences: ScoringPreferences
    ) -> float:
        six_star_copies: Dict[str, Dict[str, float]] = {}
        total_value = 0.0

        for result in results:
            star = int(result.get("star", 0))
            if star == 6:
                name = result.get("name", "")
                base_value = ScoringSystem._resolve_six_star_value(result, preferences)
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
            total_value += ScoringSystem._calculate_six_star_incremental_value(
                name=name,
                count=int(entry["count"]),
                base_value=float(entry["base_value"]),
                preferences=preferences,
            )

        return round(total_value, 4)

    @staticmethod
    def calculate_trace_utility(
        trace: StrategyTrace, preferences: ScoringPreferences
    ) -> float:
        return ScoringSystem.calculate_results_value(
            ScoringSystem._flatten_results(trace), preferences
        )

    @staticmethod
    def score_traces(
        traces: List[StrategyTrace],
        preferences: Optional[ScoringPreferences] = None,
        goals: Optional[List[StrategyGoal]] = None,
        baseline_estimator: Optional[BaselineEstimator] = None,
        include_traces: bool = False,
    ) -> StrategyScoreReport:
        if not traces:
            raise ValueError("traces不能为空")

        preferences = ScoringSystem.normalize_preferences(preferences)
        goals = ScoringSystem.normalize_goals(goals)
        if not goals:
            raise ValueError("至少需要一个目标")

        baseline_estimator = baseline_estimator or BaselineEstimator(
            samples=preferences.baseline_samples,
            base_seed=preferences.baseline_seed,
        )
        ScoringSystem._annotate_past_up_flags(traces, preferences)

        scored_samples = [
            ScoringSystem._score_single_trace(
                trace=trace,
                preferences=preferences,
                goals=goals,
                baseline_estimator=baseline_estimator,
            )
            for trace in traces
        ]

        goal_completion_rate = sum(sample["goal_met"] for sample in scored_samples) / len(
            scored_samples
        )
        goal_score = round(100.0 * (goal_completion_rate ** preferences.alpha), 4)

        mean_utility = sum(sample["utility"] for sample in scored_samples) / len(
            scored_samples
        )
        mean_baseline = sum(sample["baseline"] for sample in scored_samples) / len(
            scored_samples
        )
        utility_ratio = mean_utility / mean_baseline if mean_baseline > 0 else 0.0
        utility_absolute_ratio = (
            mean_utility / preferences.utility_absolute_reference
            if preferences.utility_absolute_reference > 0
            else 0.0
        )
        utility_score = (
            ScoringSystem.mixed_utility_score(
                utility_ratio, utility_absolute_ratio, preferences
            )
            if mean_baseline > 0 and preferences.utility_absolute_reference > 0
            else 0.0
        )

        mean_opportunity = sum(sample["opportunity"] for sample in scored_samples) / len(
            scored_samples
        )
        opportunity_ratio = (
            mean_opportunity / preferences.opportunity_reference
            if preferences.opportunity_reference > 0
            else 0.0
        )
        resource_score = (
            ScoringSystem.log_map(opportunity_ratio, preferences.resource_log_map)
            if preferences.opportunity_reference > 0
            else 0.0
        )

        tail_count = max(1, ceil(len(scored_samples) * preferences.tail_ratio))
        tail_quality = sorted(sample["quality"] for sample in scored_samples)[:tail_count]
        tail_risk_mean = sum(tail_quality) / len(tail_quality)
        risk_score = round(tail_risk_mean, 4)

        raw_score = round(
            preferences.goal_weight * goal_score
            + preferences.utility_weight * utility_score
            + preferences.resource_weight * resource_score
            + preferences.risk_weight * risk_score,
            4,
        )
        grade, grade_name = ScoringSystem.get_grade(raw_score)

        cache_tags = [
            f"cache:{SCORING_CACHE_VERSION}",
            f"baseline_cache:{baseline_estimator.cache_path}",
            f"distribution_cache:{baseline_estimator.cache_path}",
            f"cache_hits:{baseline_estimator.cache_hits}",
            "baseline_interp:near-state-cubic-spline",
        ]

        return StrategyScoreReport(
            raw_score=raw_score,
            goal_score=goal_score,
            utility_score=round(utility_score, 4),
            resource_score=round(resource_score, 4),
            risk_score=round(risk_score, 4),
            goal_completion_rate=round(goal_completion_rate, 4),
            mean_utility=round(mean_utility, 4),
            mean_baseline=round(mean_baseline, 4),
            utility_ratio=round(utility_ratio, 4),
            mean_opportunity=round(mean_opportunity, 4),
            opportunity_ratio=round(opportunity_ratio, 4),
            tail_risk_mean=round(tail_risk_mean, 4),
            simulations=len(traces),
            grade=grade,
            grade_name=grade_name,
            baseline_samples=baseline_estimator.samples,
            baseline_seed=baseline_estimator.base_seed,
            scoring_version=SCORING_V2_VERSION,
            parameter_tags=preferences.parameter_tags,
            cache_tags=cache_tags,
            traces=traces if include_traces else None,
        )

    @staticmethod
    def rank_reports(reports: List[StrategyScoreReport]) -> List[StrategyScoreReport]:
        if not reports:
            return reports

        ranked = sorted(
            enumerate(reports),
            key=lambda item: item[1].raw_score,
            reverse=True,
        )
        best_score = ranked[0][1].raw_score
        best_goal = ranked[0][1].goal_completion_rate
        best_opportunity = ranked[0][1].mean_opportunity
        total = len(ranked)

        for rank, (_, report) in enumerate(ranked, start=1):
            report.rank = rank
            report.percentile = round(((total - rank + 1) / total) * 100.0, 2)
            report.score_delta_from_best = round(report.raw_score - best_score, 4)
            report.goal_delta_from_best = round(
                report.goal_completion_rate - best_goal, 4
            )
            report.opportunity_delta_from_best = round(
                report.mean_opportunity - best_opportunity, 4
            )

        return reports

    @staticmethod
    def get_grade(score: float) -> Tuple[str, str]:
        for threshold, grade, grade_name in ScoringSystem.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade, grade_name
        return "E", "失败"

    @staticmethod
    def _score_single_trace(
        trace: StrategyTrace,
        preferences: ScoringPreferences,
        goals: List[StrategyGoal],
        baseline_estimator: BaselineEstimator,
    ) -> Dict[str, Any]:
        utility = ScoringSystem.calculate_trace_utility(trace, preferences)
        baseline = sum(
            baseline_estimator.estimate(
                stage.config_name,
                stage.start_counters,
                stage.paid_draws,
                preferences,
            )
            for stage in trace.stages
        )
        goal_met = all(ScoringSystem._evaluate_goal(trace, goal) for goal in goals)

        if trace.stages:
            final_stage = trace.stages[-1]
            future_draws = trace.final_resource_left + preferences.future_resource_income
            opportunity = baseline_estimator.estimate(
                final_stage.config_name,
                final_stage.end_counters,
                future_draws,
                preferences,
            )
        else:
            opportunity = 0.0

        utility_ratio = utility / baseline if baseline > 0 else 0.0
        utility_absolute_ratio = (
            utility / preferences.utility_absolute_reference
            if preferences.utility_absolute_reference > 0
            else 0.0
        )
        opportunity_ratio = (
            opportunity / preferences.opportunity_reference
            if preferences.opportunity_reference > 0
            else 0.0
        )

        quality_utility = (
            ScoringSystem.mixed_utility_score(
                utility_ratio, utility_absolute_ratio, preferences
            )
            if baseline > 0 and preferences.utility_absolute_reference > 0
            else 0.0
        )
        quality_resource = (
            ScoringSystem.log_map(opportunity_ratio, preferences.resource_log_map)
            if preferences.opportunity_reference > 0
            else 0.0
        )
        quality = (
            preferences.risk_utility_weight * quality_utility
            + (1.0 - preferences.risk_utility_weight) * quality_resource
        )

        return {
            "utility": utility,
            "baseline": baseline,
            "opportunity": opportunity,
            "goal_met": int(goal_met),
            "quality": quality,
        }

    @staticmethod
    def _evaluate_goal(trace: StrategyTrace, goal: StrategyGoal) -> bool:
        results = ScoringSystem._flatten_results(trace)

        if goal.kind == "current_up":
            if goal.character_name:
                count = sum(
                    1
                    for result in results
                    if result.get("is_current_up") and result.get("name") == goal.character_name
                )
            elif goal.stage_index is not None and 0 <= goal.stage_index < len(trace.stages):
                count = sum(
                    1
                    for result in trace.stages[goal.stage_index].results
                    if result.get("is_current_up")
                )
            else:
                count = sum(1 for result in results if result.get("is_current_up"))
            return count >= goal.target

        if goal.kind == "past_up":
            count = sum(1 for result in results if result.get("is_past_up"))
            return count >= goal.target

        if goal.kind == "resource_at_least":
            return trace.final_resource_left >= goal.target

        if goal.kind == "stage_paid_draws_at_most":
            if goal.stage_index is None or goal.stage_index >= len(trace.stages):
                return False
            return trace.stages[goal.stage_index].paid_draws <= goal.target

        if goal.kind == "six_star_count":
            count = sum(1 for result in results if int(result.get("star", 0)) == 6)
            return count >= goal.target

        if goal.kind == "character_count":
            if not goal.character_name:
                raise ValueError("character_count 目标必须提供 character_name")
            count = sum(1 for result in results if result.get("name") == goal.character_name)
            return count >= goal.target

        raise ValueError(f"不支持的目标类型: {goal.kind}")

    @staticmethod
    def _flatten_results(trace: StrategyTrace) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for stage in trace.stages:
            results.extend(stage.results)
        return results

    @staticmethod
    def _resolve_six_star_value(
        result: Dict[str, Any], preferences: ScoringPreferences
    ) -> float:
        if result.get("is_current_up"):
            return preferences.current_up_value
        if result.get("is_past_up"):
            return preferences.past_up_value
        return preferences.normal_six_value

    @staticmethod
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

    @staticmethod
    def _annotate_past_up_flags(
        traces: List[StrategyTrace], preferences: ScoringPreferences
    ) -> None:
        known_past_up_names = set(preferences.past_up_character_names)
        for trace in traces:
            for stage in trace.stages:
                for result in stage.results:
                    if result.get("star") != 6:
                        result["is_past_up"] = False
                        continue
                    result["is_past_up"] = (
                        not result.get("is_current_up", False)
                        and result.get("name") in known_past_up_names
                    )


__all__ = [
    "BaselineEstimator",
    "JsonFileCache",
    "LogMapConfig",
    "Resource",
    "ScoringPreferences",
    "ScoringSystem",
    "SixStarDistributionEstimate",
    "StageTrace",
    "StrategyGoal",
    "StrategyScoreReport",
    "StrategyTrace",
    "resource_to_standard_draws",
    "SCORING_V2_VERSION",
]
