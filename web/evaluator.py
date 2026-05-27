# -*- coding: utf-8 -*-
"""Web evaluation helpers for cross-banner strategy scoring."""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Dict, List

from gacha_core import Counters, GlobalConfigLoader
from scheduler import Resource, Scheduler
from scheduler.models import ScoringPreferences, StrategyGoal
from scheduler.strategy_protocol import StrategyProtocolAdapter

VALID_CONFIG_PREFIX = "config_"
DEFAULT_EVAL_SCALE = 2000
MAX_EVAL_SCALE = 20000


def list_eval_configs(config_root: str = "configs") -> List[Dict[str, Any]]:
    configs: List[Dict[str, Any]] = []
    for entry in sorted(os.listdir(config_root)):
        if not entry.startswith(VALID_CONFIG_PREFIX):
            continue
        config_path = os.path.join(config_root, entry)
        if not os.path.isdir(config_path):
            continue
        try:
            loader = GlobalConfigLoader(config_path)
            featured = loader.get_char_featured_names()
            pool_info = loader.get_pool_info("char")
        except (FileNotFoundError, ValueError):
            continue
        configs.append(
            {
                "id": entry,
                "pool_name": pool_info.get("name", ""),
                "open_time": pool_info.get("open_time", ""),
                "close_time": pool_info.get("close_time", ""),
                "current_up": featured.get("current_up", []),
                "past_up": featured.get("past_up", []),
                "normal": featured.get("normal", []),
            }
        )
    return configs


def validate_eval_payload(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("请求体必须是 JSON 对象")

    banner_plans = payload.get("banner_plans")
    if not isinstance(banner_plans, list) or not banner_plans:
        raise ValueError("banner_plans 必须是非空数组")

    preferences = ScoringPreferences.from_dict(dict(payload.get("preferences", {})))

    goals_payload = payload.get("goals")
    if not isinstance(goals_payload, list) or not goals_payload:
        raise ValueError("goals 必须是非空数组")
    goals = [StrategyGoal.from_dict(item) for item in goals_payload]

    available_configs = {item["id"] for item in list_eval_configs()}
    normalized_plans: List[Dict[str, Any]] = []
    for plan in banner_plans:
        if not isinstance(plan, dict):
            raise ValueError("banner_plans 中存在非法条目")

        config_name = str(plan.get("config_name", "")).strip()
        if config_name not in available_configs:
            raise ValueError(f"未知卡池配置: {config_name}")

        strategy_payload = plan.get("strategy")
        if strategy_payload is None:
            raise ValueError("每个卡池阶段都必须包含 strategy")
        StrategyProtocolAdapter.from_payload(strategy_payload)

        normalized_plans.append(
            {
                "config_name": config_name,
                "strategy": strategy_payload,
                "resource_increment": _resource_dict(plan.get("resource_increment")),
                "check_in": bool(plan.get("check_in", True)),
                "use_origeometry": bool(plan.get("use_origeometry", False)),
                "is_core": bool(plan.get("is_core", True)),
            }
        )

    scale = int(payload.get("scale", DEFAULT_EVAL_SCALE))
    if scale < 1 or scale > MAX_EVAL_SCALE:
        raise ValueError(f"scale 必须位于 1 到 {MAX_EVAL_SCALE} 之间")

    workers = payload.get("workers")
    if workers is not None:
        workers = int(workers)
        if workers < 1:
            raise ValueError("workers 必须大于 0")

    return {
        "resource": _resource_dict(payload.get("resource")),
        "initial_counters": _counters_dict(payload.get("initial_counters")),
        "preferences": asdict(preferences),
        "goals": [asdict(goal) for goal in goals],
        "banner_plans": normalized_plans,
        "scale": scale,
        "workers": workers,
    }


def evaluate_payload(payload: Dict[str, Any], default_workers: int | None = None) -> Dict[str, Any]:
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrangement",
        resource=Resource(**payload["resource"]),
    )
    initial_counters = Counters(**payload["initial_counters"])

    for index, plan in enumerate(payload["banner_plans"]):
        scheduler.banner(
            rules=plan["strategy"],
            name=plan["config_name"],
            resource_increment=Resource(**plan["resource_increment"]),
            init_counters=initial_counters if index == 0 else Counters(),
            check_in=plan["check_in"],
            use_origeometry=plan["use_origeometry"],
            is_core=plan["is_core"],
        )

    workers = payload["workers"] if payload["workers"] is not None else default_workers
    report = scheduler.evaluate(
        scale=payload["scale"],
        workers=workers,
        show_progress=False,
        preferences=payload["preferences"],
        goals=payload["goals"],
    )
    result = asdict(report)
    result.pop("traces", None)
    return result


def _resource_dict(payload: Dict[str, Any] | None) -> Dict[str, int]:
    payload = payload or {}
    return {
        "chartered_permits": int(payload.get("chartered_permits", 0)),
        "oroberyl": int(payload.get("oroberyl", 0)),
        "arsenal_tickets": int(payload.get("arsenal_tickets", 0)),
        "origeometry": int(payload.get("origeometry", 0)),
    }


def _counters_dict(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    payload = payload or {}
    return {
        "total": int(payload.get("total", 0)),
        "no_6star": int(payload.get("no_6star", 0)),
        "no_5star_plus": int(payload.get("no_5star_plus", 0)),
        "no_up": int(payload.get("no_up", 0)),
        "guarantee_used": bool(payload.get("guarantee_used", False)),
        "urgent_used": bool(payload.get("urgent_used", False)),
    }

