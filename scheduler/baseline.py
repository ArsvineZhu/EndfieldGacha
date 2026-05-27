# -*- coding: utf-8 -*-
"""固定种子、固定样本数的状态基准价值估计器。"""

from __future__ import annotations

import os
from copy import deepcopy
from hashlib import md5
from math import sqrt
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from gacha_core import CharGacha, Counters, GlobalConfigLoader

from .cache_db import BaselineCacheDB, preferences_hash
from .models import (
    SCORING_VERSION,
    ScoringPreferences,
    SixStarDistributionEstimate,
    calculate_results_value,
)

# numpy 数组列索引
_COL_PD = 0
_COL_EST = 1
_COL_TOTAL = 2
_COL_NO6 = 3
_COL_NO5P = 4
_COL_NOUP = 5
_COL_GUAR = 6
_COL_URG = 7

# state_distance 各维度的 scale（与 _state_distance 保持一致）
_SCALES = np.array([30.0, 15.0, 5.0, 30.0, 1.0, 1.0], dtype=np.float64)


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
        self.cache_path = cache_path or os.path.join("data", "baseline_cache.db")
        self._db = BaselineCacheDB(self.cache_path)
        # 内存缓存：每个 (config, pref_hash) 一组预计算数据
        self._config_data_cache: Dict[str, Optional[np.ndarray]] = {}

    @property
    def cache_hits(self) -> int:
        return self._db.cache_hits

    def flush_cache(self) -> None:
        self._db.flush()

    def _config_cache_key(self, config_name: str, preferences: ScoringPreferences) -> str:
        pref_hash = preferences_hash(preferences.theta_signature)
        return f"{config_name}:{self.samples}:{self.base_seed}:{pref_hash}"

    def _get_config_data(
        self, config_name: str, preferences: ScoringPreferences
    ) -> Optional[np.ndarray]:
        """惰性加载预计算数据到内存。

        返回 (N, 8) 的 float64 数组，列顺序见 _COL_* 常量。
        第一次访问时从 SQLite 加载该 config 的全部 76k 条目，
        后续调用直接返回内存副本。
        """
        key = self._config_cache_key(config_name, preferences)
        cached = self._config_data_cache.get(key)
        if cached is not None:
            return cached

        pref_hash = preferences_hash(preferences.theta_signature)
        # 复用 _db 的连接（已启用 WAL 模式）
        conn = self._db._get_conn()
        # sqlite3.Row → tuple → numpy（避免 Row 对象转换开销）
        arr = np.array(
            [tuple(r) for r in conn.execute(
                """SELECT paid_draws, estimate,
                          counters_total, counters_no_6star,
                          counters_no_5star_plus, counters_no_up,
                          counters_guarantee_used, counters_urgent_used
                   FROM baseline_estimates
                   WHERE config_name = ? AND samples = ? AND seed = ?
                     AND preferences_sig_hash = ?
                   ORDER BY paid_draws""",
                (config_name, self.samples, self.base_seed, pref_hash),
            )],
            dtype=np.float64,
        )

        if len(arr) == 0:
            self._config_data_cache[key] = None
            return None

        self._config_data_cache[key] = arr
        return arr

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
        cached = self._db.get_exact(cache_key)
        if cached is not None:
            return cached

        interpolated = self._interpolate_estimate(
            config_name, counters, paid_draws, preferences
        )
        if interpolated is not None:
            self._db.set_baseline(
                cache_key=cache_key,
                config_name=config_name,
                counters_signature=self._counters_signature(counters),
                paid_draws=paid_draws,
                preferences_sig_hash=preferences_hash(preferences.theta_signature),
                samples=self.samples,
                seed=self.base_seed,
                estimate=interpolated,
                source="spline",
                version=SCORING_VERSION,
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
        self._db.set_baseline(
            cache_key=cache_key,
            config_name=config_name,
            counters_signature=self._counters_signature(counters),
            paid_draws=paid_draws,
            preferences_sig_hash=preferences_hash(preferences.theta_signature),
            samples=self.samples,
            seed=self.base_seed,
            estimate=estimate,
            source="simulation",
            version=SCORING_VERSION,
        )
        return estimate

    def estimate_six_star_distribution(
        self,
        config_name: str,
        counters: Counters,
        paid_draws: int,
    ) -> SixStarDistributionEstimate:
        import json

        cache_key = self._cache_key(
            "distribution",
            config_name,
            counters,
            paid_draws,
            self.samples,
            self.base_seed,
        )
        cached = self._db.get_distribution_exact(cache_key)
        if cached is not None:
            return SixStarDistributionEstimate(
                expected_six_star_count=float(cached["expected_six_star_count"]),
                probabilities=json.loads(cached["probabilities_json"]),
                tail_probabilities=json.loads(cached["tail_probabilities_json"]),
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
            tail_probabilities[str(count)] = sum(
                1 for value in counts if value >= count
            ) / len(counts)

        expected = sum(counts) / len(counts)
        variance = sum((value - expected) ** 2 for value in counts) / len(counts)
        stderr = sqrt(variance / len(counts)) if counts else 0.0

        self._db.set_distribution(
            cache_key=cache_key,
            config_name=config_name,
            counters_signature=self._counters_signature(counters),
            paid_draws=paid_draws,
            samples=self.samples,
            seed=self.base_seed,
            expected_six_star_count=expected,
            probabilities=probabilities,
            tail_probabilities=tail_probabilities,
            stderr=stderr,
            version=SCORING_VERSION,
        )
        return SixStarDistributionEstimate(
            expected_six_star_count=round(expected, 6),
            probabilities={k: float(v) for k, v in probabilities.items()},
            tail_probabilities={k: float(v) for k, v in tail_probabilities.items()},
            stderr=round(stderr, 8),
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
        data = self._get_config_data(config_name, preferences)
        if data is None or len(data) == 0:
            return None

        # 目标状态向量：[total, no_6star, no_5star_plus, no_up, guarantee_used, urgent_used]
        target = np.array(
            [
                float(counters.total),
                float(counters.no_6star),
                float(counters.no_5star_plus),
                float(counters.no_up),
                float(counters.guarantee_used),
                float(counters.urgent_used),
            ],
            dtype=np.float64,
        )

        # 矢量化距离计算：data[:, _COL_TOTAL:_COL_URG+1] 取列 2..7
        diffs = data[:, _COL_TOTAL : _COL_URG + 1] - target
        dists = np.sqrt(np.sum((diffs / _SCALES) ** 2, axis=1))

        # 筛选近邻
        nearest = float(np.min(dists))
        max_dist = max(1.5, nearest + 0.75)
        mask = dists <= max_dist
        if np.sum(mask) < 3:
            # 候选不足：按距离排序取 top 8
            top_n = min(8, len(dists))
            if top_n < 3:
                return None
            top_idx = np.argpartition(dists, top_n - 1)[:top_n]
            filtered = data[top_idx]
            filtered_dists = dists[top_idx]
        else:
            filtered = data[mask]
            filtered_dists = dists[mask]

        # 按距离升序排序（用于去重：同 pd 保留最近邻）
        order = np.argsort(filtered_dists)
        filtered = filtered[order]
        filtered_dists = filtered_dists[order]

        # 去重：每个 pd 保留距离最小的候选
        seen_pds: set[int] = set()
        pd_map: dict[int, float] = {}  # pd -> estimate (best distance)
        for row in filtered:
            pd_val = int(row[_COL_PD])
            if pd_val not in seen_pds:
                seen_pds.add(pd_val)
                pd_map[pd_val] = float(row[_COL_EST])

        if len(pd_map) < 3:
            return None

        # 按 pd 升序排列（CubicSpline 要求 x 严格递增）
        best_pds = sorted(pd_map.keys())
        best_ests = [pd_map[pd] for pd in best_pds]

        # 检查待插值的 pd 是否在范围内
        if paid_draws <= min(best_pds) or paid_draws >= max(best_pds):
            return None

        try:
            from scipy.interpolate import CubicSpline
        except ImportError:
            return None

        spline = CubicSpline(best_pds, best_ests, extrapolate=False)
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
        for target, candidate, scale in zip(
            target_signature, candidate_signature, scales
        ):
            target_value = (
                float(bool(target)) if isinstance(target, bool) else float(target)
            )
            candidate_value = (
                float(bool(candidate))
                if isinstance(candidate, bool)
                else float(candidate)
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


__all__ = ["BaselineEstimator"]
