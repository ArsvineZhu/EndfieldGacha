# -*- coding: utf-8 -*-
"""离线预计算基线价值缓存。

生成锚点状态网格，对每个状态 × 配置 × paid_draws ∈ [1, N] 计算基线估计。
结果写入 data/baseline_cache.db，运行时 BaselineEstimator 自动命中。

用法：
    uv run python build/precompute_cache.py
    uv run python build/precompute_cache.py --configs config_3
    uv run python build/precompute_cache.py --configs config_3,config_4 --paid-draws 300 --samples 128
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from copy import deepcopy
from hashlib import md5
from itertools import product
from multiprocessing import Pool, cpu_count
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gacha_core import CharGacha, Counters, GlobalConfigLoader  # noqa: E402
from scheduler.cache_db import BaselineCacheDB, preferences_hash  # noqa: E402
from scheduler.models import (  # noqa: E402
    SCORING_VERSION,
    ScoringPreferences,
    calculate_results_value,
)

# ---------------------------------------------------------------------------
# 锚点状态网格
# ---------------------------------------------------------------------------
# 6 维计数器不可能全遍历，只采样最关键的维度：
#   - no_6star（保底计数器，scale=15）: 均匀采样
#   - no_up（UP 保底计数器，scale=30）: 均匀采样
#   - guarantee_used（硬保底，scale=1）: 开关
# 以下维度对 baseline 价值估计无影响，固定为 0/False：
#   - total、no_5star_plus、urgent_used

NO_6STAR_VALUES = [
    0, 10, 20, 30, 40, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100,
]
NO_UP_VALUES = [0, 30, 60, 90, 120]
GUARANTEE_VALUES = [False, True]


def _build_state_counters(
    no_6star: int, no_up: int, guarantee_used: bool
) -> Counters:
    return Counters(
        total=0,
        no_6star=no_6star,
        no_5star_plus=0,
        no_up=no_up,
        guarantee_used=guarantee_used,
        urgent_used=False,
    )


# ---------------------------------------------------------------------------
# 种子与 cache_key 生成（与 BaselineEstimator 保持一致）
# ---------------------------------------------------------------------------


def _cache_key(*parts: Any) -> str:
    return md5(repr(parts).encode("utf-8")).hexdigest()


def _build_seed(base_seed: int, cache_key: str, index: int) -> int:
    payload = f"{base_seed}|{cache_key}|{index}".encode("utf-8")
    return int(md5(payload).hexdigest()[:8], 16)


# ---------------------------------------------------------------------------
# 单任务：一个 (config, anchor_state, paid_draws_max, samples, seed) 组合
# ---------------------------------------------------------------------------


def _precompute_task(args: Tuple) -> List[Dict[str, Any]]:
    """计算一个 (config_name, anchor_state) 组合的所有 pd 值。

    返回 [(cache_key, estimate, ...), ...] 列表。
    """
    (
        config_dir,
        config_name,
        no_6star,
        no_up,
        guarantee_used,
        paid_draws_max,
        samples,
        base_seed,
        preferences_dict,
    ) = args

    preferences = ScoringPreferences.from_dict(preferences_dict)
    pref_hash = preferences_hash(preferences.theta_signature)
    counters = _build_state_counters(no_6star, no_up, guarantee_used)
    counters_sig = (
        counters.total,
        counters.no_6star,
        counters.no_5star_plus,
        counters.no_up,
        counters.guarantee_used,
        counters.urgent_used,
    )

    config = GlobalConfigLoader(os.path.join(config_dir, config_name))
    featured_names = config.get_char_featured_names()
    current_up_names = set(featured_names["current_up"])
    past_up_names = set(featured_names["past_up"])

    # 为这个 (config, state) 预计算 paid_draws=1..max 的所有值
    # 对每个 sample，一次模拟跑完所有 pd，记录累积值
    # 避免为每个 pd 重新初始化 gacha

    # 先确定要计算的 paid_draws 列表
    pd_values = list(range(1, paid_draws_max + 1))

    # 按 paid_draws 组织每个 sample 的累积值
    # pd_cumulative[pd] = [sample_0_value_at_pd, sample_1_value_at_pd, ...]
    pd_cumulative: Dict[int, List[float]] = {pd: [] for pd in pd_values}

    for sample_idx in range(samples):
        # 构造 cache_key 与运行时一致（用于 seed 派生）
        ck = _cache_key(
            "baseline",
            config_name,
            counters,
            0,  # 临时值，build_seed 只用 cache_key 和 index
            preferences.theta_signature,
            samples,
            base_seed,
        )
        seed = _build_seed(base_seed, ck, sample_idx)
        gacha = CharGacha(config=config, seed=seed)
        gacha.counters = deepcopy(counters)

        results: List[Dict[str, Any]] = []
        for pd in pd_values:
            result = gacha.attempt()
            results.append(
                {
                    "name": result.name,
                    "star": result.star,
                    "is_current_up": result.name in current_up_names,
                    "is_past_up": result.name in past_up_names,
                }
            )
            val = calculate_results_value(results, preferences)
            pd_cumulative[pd].append(val)

    # 平均每个 pd
    entries: List[Dict[str, Any]] = []
    for pd in pd_values:
        estimates = pd_cumulative[pd]
        estimate = sum(estimates) / len(estimates)

        full_ck = _cache_key(
            "baseline",
            config_name,
            counters,
            pd,
            preferences.theta_signature,
            samples,
            base_seed,
        )

        entries.append(
            {
                "cache_key": full_ck,
                "config_name": config_name,
                "counters_sig": counters_sig,
                "paid_draws": pd,
                "pref_hash": pref_hash,
                "samples": samples,
                "seed": base_seed,
                "estimate": estimate,
                "source": "simulation",
                "version": SCORING_VERSION,
            }
        )

    return entries


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="离线预计算基线价值缓存",
    )
    parser.add_argument(
        "--configs",
        default=None,
        help="逗号分隔的配置名列表（默认从 configs/arrangement 读取）",
    )
    parser.add_argument(
        "--paid-draws",
        type=int,
        default=480,
        help="最大付费抽数（默认 480）",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=64,
        help="每个状态的 Monte Carlo 样本数（默认 64）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260525,
        help="基准随机种子（默认 20260525）",
    )
    parser.add_argument(
        "--db-path",
        default="data/baseline_cache.db",
        help="SQLite 缓存路径（默认 data/baseline_cache.db）",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="并行进程数（默认使用 CPU 核心数）",
    )
    return parser.parse_args()


def resolve_configs(configs_arg: Optional[str]) -> List[str]:
    if configs_arg:
        return [name.strip() for name in configs_arg.split(",")]
    arrangement_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "configs", "arrangement"
    )
    configs: List[str] = []
    with open(arrangement_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                configs.append(line)
    return configs


def main() -> None:
    args = parse_args()
    configs = resolve_configs(args.configs)
    paid_draws_max = args.paid_draws
    samples = args.samples
    base_seed = args.seed
    workers = args.workers or max(1, cpu_count())
    db_path = args.db_path

    print(f"配置: {configs}")
    print(f"最大抽数: {paid_draws_max}, 样本数: {samples}, 种子: {base_seed}")
    print(f"Worker 数: {workers}")
    print()

    preferences = ScoringPreferences()

    # 构建任务列表
    tasks: List[Tuple] = []
    for config_name, no_6star, no_up, guarantee_used in product(
        configs, NO_6STAR_VALUES, NO_UP_VALUES, GUARANTEE_VALUES
    ):
        tasks.append(
            (
                "configs",
                config_name,
                no_6star,
                no_up,
                guarantee_used,
                paid_draws_max,
                samples,
                base_seed,
                {
                    "current_up_value": preferences.current_up_value,
                    "past_up_value": preferences.past_up_value,
                    "normal_six_value": preferences.normal_six_value,
                    "five_star_value": preferences.five_star_value,
                    "four_star_value": preferences.four_star_value,
                    "past_up_character_names": list(preferences.past_up_character_names),
                    "owned_character_potentials": dict(preferences.owned_character_potentials),
                },
            )
        )

    total_tasks = len(tasks)
    print(f"锚点状态组合: {len(configs)} 配置 × {len(NO_6STAR_VALUES)} no_6star"
          f" × {len(NO_UP_VALUES)} no_up × {len(GUARANTEE_VALUES)} guarantee"
          f" = {total_tasks} 任务, 预计 {total_tasks * paid_draws_max} 条目")
    print(f"预计条目数: {total_tasks} × {paid_draws_max} pd = {total_tasks * paid_draws_max}")
    print()

    start_time = time.time()

    db = BaselineCacheDB(db_path)

    # 使用多进程 + 逐任务写入 DB（避免单进程内存爆炸）
    with Pool(processes=min(workers, total_tasks)) as pool:
        for idx, entries in enumerate(pool.imap_unordered(_precompute_task, tasks), 1):
            for entry in entries:
                db.set_baseline(
                    cache_key=entry["cache_key"],
                    config_name=entry["config_name"],
                    counters_signature=entry["counters_sig"],
                    paid_draws=entry["paid_draws"],
                    preferences_sig_hash=entry["pref_hash"],
                    samples=entry["samples"],
                    seed=entry["seed"],
                    estimate=entry["estimate"],
                    source=entry["source"],
                    version=entry["version"],
                )

            elapsed = time.time() - start_time
            eta = (elapsed / idx) * (total_tasks - idx) if idx > 0 else 0
            print(
                f"  [{idx}/{total_tasks}] {entry['config_name']} "
                f"no6={entry['counters_sig'][1]} "
                f"noup={entry['counters_sig'][3]} "
                f"guar={entry['counters_sig'][4]} "
                f"— {elapsed:.0f}s elapsed, ETA {eta:.0f}s"
            )

    db.close()

    total_time = time.time() - start_time
    print()
    print(f"完成！总耗时: {total_time:.1f}s")
    print(f"数据库: {db_path}")
    print(f"缓存总条目: {BaselineCacheDB(db_path).estimate_count}")


if __name__ == "__main__":
    main()
