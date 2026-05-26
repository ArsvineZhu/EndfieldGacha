# -*- coding: utf-8 -*-
"""固定种子、固定样本数的状态基准价值估计器。"""

from __future__ import annotations

import os
from copy import deepcopy
from hashlib import md5
from math import sqrt
from typing import Any, Dict, List, Optional, Tuple

from gacha_core import CharGacha, Counters, GlobalConfigLoader

from .cache import JsonFileCache
from .models import (
    SCORING_VERSION,
    ScoringPreferences,
    SixStarDistributionEstimate,
    calculate_results_value,
)


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
        self.cache_path = cache_path or os.path.join("logs", "scoring_cache.json")
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
                    "version": SCORING_VERSION,
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
        featured_names = config.get_char_featured_names()
        current_up_names = set(featured_names["current_up"])
        past_up_names = set(featured_names["past_up"])
        for index in range(self.samples):
            seed = self._build_seed(cache_key, index)
            gacha = CharGacha(config=config, seed=seed)
            gacha.counters = deepcopy(counters)
            results: List[Dict[str, Any]] = []
            for _ in range(paid_draws):
                result = gacha.attempt()
                results.append(
                    {
                        "name": result.name,
                        "star": result.star,
                        "is_current_up": result.name in current_up_names,
                        "is_past_up": result.name in past_up_names,
                    }
                )
            sample_values.append(calculate_results_value(results, preferences))

        estimate = sum(sample_values) / len(sample_values)
        self._baseline_cache.set(
            cache_key,
            {
                "estimate": round(estimate, 6),
                "config_name": config_name,
                "paid_draws": paid_draws,
                "samples": self.samples,
                "seed": self.base_seed,
                "version": SCORING_VERSION,
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
            "version": SCORING_VERSION,
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


__all__ = ["BaselineEstimator"]
