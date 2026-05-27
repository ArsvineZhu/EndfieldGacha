# -*- coding: utf-8 -*-
"""SQLite 缓存模块，支持 WAL 模式并发读写。"""

from __future__ import annotations

import atexit
import json
import sqlite3
from hashlib import md5
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def preferences_hash(theta_signature: Tuple[Any, ...]) -> str:
    """为偏好签名生成稳定哈希，用于 SQLite 索引。"""
    return md5(repr(theta_signature).encode("utf-8")).hexdigest()


# 插值查询时用于 SQL 过滤的安全范围（对应 state_distance 阈值 max(1.5, nearest+0.75) 约 2.25）
_NO6_RANGE = 25
_NOUP_RANGE = 45


class BaselineCacheDB:
    """SQLite 缓存，取代 JSON 文件缓存。

    WAL 模式确保并发读写的安全性。
    精确查询通过 MD5 cache_key（PRIMARY KEY, O(log n)）。
    插值查询通过结构化列 + 复合索引 + SQL 级范围过滤。
    """

    def __init__(self, cache_path: str = "data/baseline_cache.db"):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_hits = 0
        self.cache_misses = 0
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()
        atexit.register(self.close)

    # ------------------------------------------------------------------
    # 连接与初始化
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.cache_path), check_same_thread=False
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS baseline_estimates (
                cache_key TEXT PRIMARY KEY,
                config_name TEXT NOT NULL,
                counters_total INTEGER NOT NULL,
                counters_no_6star INTEGER NOT NULL,
                counters_no_5star_plus INTEGER NOT NULL,
                counters_no_up INTEGER NOT NULL,
                counters_guarantee_used INTEGER NOT NULL,
                counters_urgent_used INTEGER NOT NULL,
                paid_draws INTEGER NOT NULL,
                preferences_sig_hash TEXT NOT NULL DEFAULT '',
                samples INTEGER NOT NULL,
                seed INTEGER NOT NULL,
                estimate REAL NOT NULL,
                source TEXT NOT NULL DEFAULT 'simulation',
                version TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_baseline_interp
            ON baseline_estimates(config_name, samples, seed, preferences_sig_hash, paid_draws)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS distribution_estimates (
                cache_key TEXT PRIMARY KEY,
                config_name TEXT NOT NULL,
                counters_total INTEGER NOT NULL,
                counters_no_6star INTEGER NOT NULL,
                counters_no_5star_plus INTEGER NOT NULL,
                counters_no_up INTEGER NOT NULL,
                counters_guarantee_used INTEGER NOT NULL,
                counters_urgent_used INTEGER NOT NULL,
                paid_draws INTEGER NOT NULL,
                samples INTEGER NOT NULL,
                seed INTEGER NOT NULL,
                expected_six_star_count REAL NOT NULL,
                probabilities_json TEXT NOT NULL DEFAULT '{}',
                tail_probabilities_json TEXT NOT NULL DEFAULT '{}',
                stderr REAL NOT NULL DEFAULT 0.0,
                version TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_distribution_interp
            ON distribution_estimates(config_name, samples, seed, paid_draws)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()

    # ------------------------------------------------------------------
    # 基线估计（baseline_estimates）
    # ------------------------------------------------------------------

    def get_exact(self, cache_key: str) -> Optional[float]:
        """精确查找：通过 cache_key 直接返回估计值。"""
        conn = self._get_conn()
        cursor = conn.execute(
            "SELECT estimate FROM baseline_estimates WHERE cache_key = ?",
            (cache_key,),
        )
        row = cursor.fetchone()
        if row is not None:
            self.cache_hits += 1
            return float(row["estimate"])
        self.cache_misses += 1
        return None

    def get_interp_candidates(
        self,
        config_name: str,
        samples: int,
        seed: int,
        preferences_sig_hash: str,
        target_no_6star: Optional[int] = None,
        target_no_up: Optional[int] = None,
        target_guarantee_used: Optional[bool] = None,
    ) -> List[Tuple]:
        """返回用于样条插值的候选条目。

        SQL 级计数器范围过滤 + 元组输出（避免 dict 开销）。
        结果按 paid_draws 排序。
        列顺序: paid_draws, estimate, counters_total, counters_no_6star,
                counters_no_5star_plus, counters_no_up,
                counters_guarantee_used, counters_urgent_used
        """
        conn = self._get_conn()
        where = (
            "config_name = ? AND samples = ? AND seed = ? AND preferences_sig_hash = ?"
        )
        params: List[Any] = [config_name, samples, seed, preferences_sig_hash]

        if target_no_6star is not None:
            where += " AND ABS(counters_no_6star - ?) <= ?"
            params.extend([target_no_6star, _NO6_RANGE])
        if target_no_up is not None:
            where += " AND ABS(counters_no_up - ?) <= ?"
            params.extend([target_no_up, _NOUP_RANGE])
        if target_guarantee_used is not None:
            where += " AND counters_guarantee_used = ?"
            params.append(int(target_guarantee_used))

        cursor = conn.execute(
            f"""SELECT paid_draws, estimate,
                      counters_total, counters_no_6star,
                      counters_no_5star_plus, counters_no_up,
                      counters_guarantee_used, counters_urgent_used
               FROM baseline_estimates
               WHERE {where}
               ORDER BY paid_draws""",
            params,
        )
        return list(cursor.fetchall())

    def set_baseline(
        self,
        cache_key: str,
        config_name: str,
        counters_signature: Tuple[int, ...],
        paid_draws: int,
        preferences_sig_hash: str,
        samples: int,
        seed: int,
        estimate: float,
        source: str,
        version: str,
        commit: bool = True,
    ) -> None:
        """写入一条基线估计缓存。

        Parameters
        ----------
        commit : bool
            是否立即提交。批量写入时可设为 False 并通过 commit() 统一提交。
        """
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO baseline_estimates
               (cache_key, config_name,
                counters_total, counters_no_6star, counters_no_5star_plus,
                counters_no_up, counters_guarantee_used, counters_urgent_used,
                paid_draws, preferences_sig_hash, samples, seed,
                estimate, source, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cache_key,
                config_name,
                int(counters_signature[0]),
                int(counters_signature[1]),
                int(counters_signature[2]),
                int(counters_signature[3]),
                bool(counters_signature[4]),
                bool(counters_signature[5]),
                paid_draws,
                preferences_sig_hash,
                samples,
                seed,
                round(estimate, 6),
                source,
                version,
            ),
        )
        if commit:
            conn.commit()

    # ------------------------------------------------------------------
    # 6 星分布（distribution_estimates）
    # ------------------------------------------------------------------

    def get_distribution_exact(
        self, cache_key: str
    ) -> Optional[Dict[str, Any]]:
        """精确查找 6 星分布缓存。"""
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT expected_six_star_count, probabilities_json,
                      tail_probabilities_json, stderr, samples, seed
               FROM distribution_estimates WHERE cache_key = ?""",
            (cache_key,),
        )
        row = cursor.fetchone()
        if row is not None:
            self.cache_hits += 1
            return dict(row)
        self.cache_misses += 1
        return None

    def set_distribution(
        self,
        cache_key: str,
        config_name: str,
        counters_signature: Tuple[int, ...],
        paid_draws: int,
        samples: int,
        seed: int,
        expected_six_star_count: float,
        probabilities: Dict[str, float],
        tail_probabilities: Dict[str, float],
        stderr: float,
        version: str,
        commit: bool = True,
    ) -> None:
        """写入一条 6 星分布缓存。"""
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO distribution_estimates
               (cache_key, config_name,
                counters_total, counters_no_6star, counters_no_5star_plus,
                counters_no_up, counters_guarantee_used, counters_urgent_used,
                paid_draws, samples, seed,
                expected_six_star_count, probabilities_json,
                tail_probabilities_json, stderr, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cache_key,
                config_name,
                int(counters_signature[0]),
                int(counters_signature[1]),
                int(counters_signature[2]),
                int(counters_signature[3]),
                bool(counters_signature[4]),
                bool(counters_signature[5]),
                paid_draws,
                samples,
                seed,
                round(expected_six_star_count, 6),
                json.dumps(probabilities, ensure_ascii=False),
                json.dumps(tail_probabilities, ensure_ascii=False),
                round(stderr, 8),
                version,
            ),
        )
        if commit:
            conn.commit()

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def commit(self) -> None:
        """显式提交事务。批量写入后可调用此方法统一提交。"""
        if self._conn is not None:
            self._conn.commit()

    def flush(self) -> None:
        if self._conn is not None:
            try:
                self._conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            except sqlite3.OperationalError:
                pass
            self._conn.commit()

    def close(self) -> None:
        self.flush()
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def estimate_count(self) -> int:
        conn = self._get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM baseline_estimates")
        return int(cursor.fetchone()[0])

    @property
    def distribution_count(self) -> int:
        conn = self._get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM distribution_estimates")
        return int(cursor.fetchone()[0])


__all__ = ["BaselineCacheDB", "preferences_hash"]
