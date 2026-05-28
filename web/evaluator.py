# -*- coding: utf-8 -*-
"""Web evaluation helpers for cross-banner strategy scoring."""

from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Dict, List

from gacha_core import Counters, GlobalConfigLoader
from scheduler import Resource, Scheduler
from scheduler.models import ScoringPreferences, StrategyGoal, StrategyScoreReport
from scheduler.scoring import ScoringSystem
from scheduler.strategy_protocol import StrategyProtocolAdapter

VALID_CONFIG_PREFIX = "config_"
DEFAULT_EVAL_SCALE = 2000
MAX_EVAL_SCALE = 20000
QUESTIONNAIRE_CR_THRESHOLD = 0.1
COMPARE_BASELINE_STRATEGY_IDS = {
    "no_draw",
    "fixed_draw_cap",
    "up_or_cap",
    "all_in",
    "resource_safe",
}


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

    preferences = _normalize_preferences_payload(payload.get("preferences"))
    _validate_questionnaire_gate(preferences)
    goals = _parse_goals(payload.get("goals"))
    normalized_plans = _validate_banner_plans(payload.get("banner_plans"))

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


def validate_compare_payload(payload: Dict[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("请求体必须是 JSON 对象")

    preferences = _normalize_preferences_payload(payload.get("preferences"))
    _validate_questionnaire_gate(preferences)
    goals = _parse_goals(payload.get("goals"))

    scale = int(payload.get("scale", DEFAULT_EVAL_SCALE))
    if scale < 1 or scale > MAX_EVAL_SCALE:
        raise ValueError(f"scale 必须位于 1 到 {MAX_EVAL_SCALE} 之间")

    workers = payload.get("workers")
    if workers is not None:
        workers = int(workers)
        if workers < 1:
            raise ValueError("workers 必须大于 0")

    strategies_payload = payload.get("strategies")
    if not isinstance(strategies_payload, list) or not strategies_payload:
        raise ValueError("strategies 必须是非空数组")

    strategies: List[Dict[str, Any]] = []
    for index, strategy_item in enumerate(strategies_payload, start=1):
        if not isinstance(strategy_item, dict):
            raise ValueError("strategies 中存在非法条目")
        strategy_id = str(strategy_item.get("id", f"strategy_{index}")).strip()
        if not strategy_id:
            raise ValueError("strategy id 不能为空")
        banner_plans = _validate_banner_plans(strategy_item.get("banner_plans"))
        strategies.append(
            {
                "id": strategy_id,
                "label": str(strategy_item.get("label", strategy_id)),
                "banner_plans": banner_plans,
            }
        )

    baseline_strategy_id = payload.get("baseline_strategy_id")
    if baseline_strategy_id is not None:
        baseline_strategy_id = str(baseline_strategy_id).strip()
        if baseline_strategy_id not in COMPARE_BASELINE_STRATEGY_IDS:
            raise ValueError(
                f"不支持的 baseline_strategy_id: {baseline_strategy_id}"
            )

    return {
        "resource": _resource_dict(payload.get("resource")),
        "initial_counters": _counters_dict(payload.get("initial_counters")),
        "preferences": asdict(preferences),
        "goals": [asdict(goal) for goal in goals],
        "scale": scale,
        "workers": workers,
        "strategies": strategies,
        "baseline_strategy_id": baseline_strategy_id,
    }


def evaluate_payload(
    payload: Dict[str, Any], default_workers: int | None = None
) -> Dict[str, Any]:
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


def evaluate_compare_payload(
    payload: Dict[str, Any], default_workers: int | None = None
) -> Dict[str, Any]:
    reports: List[StrategyScoreReport] = []
    strategy_items = list(payload["strategies"])
    baseline_label = None

    if payload.get("baseline_strategy_id"):
        baseline_id = payload["baseline_strategy_id"]
        baseline_label = f"baseline::{baseline_id}"
        baseline_plan = _build_baseline_strategy(
            baseline_id=baseline_id,
            config_name=_resolve_baseline_config_name(strategy_items),
        )
        strategy_items.append(
            {
                "id": baseline_label,
                "label": baseline_label,
                "banner_plans": [baseline_plan],
            }
        )

    workers = payload["workers"] if payload["workers"] is not None else default_workers
    for item in strategy_items:
        report = _evaluate_single_strategy(
            resource=payload["resource"],
            initial_counters=payload["initial_counters"],
            strategy_plans=item["banner_plans"],
            scale=payload["scale"],
            workers=workers,
            preferences=payload["preferences"],
            goals=payload["goals"],
        )
        reports.append(report)

    ScoringSystem.rank_reports(reports)
    if baseline_label is not None:
        baseline_index = next(
            index
            for index, strategy in enumerate(strategy_items)
            if strategy["id"] == baseline_label
        )
        ScoringSystem.attach_baseline_deltas(reports, baseline_index)

    results: List[Dict[str, Any]] = []
    for strategy, report in zip(strategy_items, reports):
        entry = asdict(report)
        entry.pop("traces", None)
        entry["strategy_id"] = strategy["id"]
        entry["strategy_label"] = strategy["label"]
        results.append(entry)

    return {
        "strategies": results,
        "baseline_strategy_id": payload.get("baseline_strategy_id"),
    }


def _evaluate_single_strategy(
    *,
    resource: Dict[str, int],
    initial_counters: Dict[str, Any],
    strategy_plans: List[Dict[str, Any]],
    scale: int,
    workers: int | None,
    preferences: Dict[str, Any],
    goals: List[Dict[str, Any]],
) -> StrategyScoreReport:
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrangement",
        resource=Resource(**resource),
    )
    shared_counters = Counters(**initial_counters)
    for index, plan in enumerate(strategy_plans):
        scheduler.banner(
            rules=plan["strategy"],
            name=plan["config_name"],
            resource_increment=Resource(**plan["resource_increment"]),
            init_counters=shared_counters if index == 0 else Counters(),
            check_in=plan["check_in"],
            use_origeometry=plan["use_origeometry"],
            is_core=plan["is_core"],
        )
    return scheduler.evaluate(
        scale=scale,
        workers=workers,
        show_progress=False,
        preferences=preferences,
        goals=goals,
    )


def _validate_banner_plans(banner_plans: Any) -> List[Dict[str, Any]]:
    if not isinstance(banner_plans, list) or not banner_plans:
        raise ValueError("banner_plans 必须是非空数组")

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
    return normalized_plans


def _parse_goals(goals_payload: Any) -> List[StrategyGoal]:
    if not isinstance(goals_payload, list) or not goals_payload:
        raise ValueError("goals 必须是非空数组")
    return [StrategyGoal.from_dict(item) for item in goals_payload]


def _validate_questionnaire_gate(preferences: ScoringPreferences) -> None:
    if (
        preferences.questionnaire_status == "inconsistent"
        and preferences.questionnaire_consistency_ratio > QUESTIONNAIRE_CR_THRESHOLD
    ):
        raise ValueError("EVAL_QUESTIONNAIRE_INCONSISTENT: 问卷存在冲突，请先复核后再提交")


def _normalize_preferences_payload(raw_preferences: Any) -> ScoringPreferences:
    payload = dict(raw_preferences or {})
    try:
        return ScoringPreferences.from_dict(payload)
    except TypeError as exc:
        message = str(exc)
        if "questionnaire_consistency_ratio" not in message:
            raise
        # Backward compatibility: allow newer frontend payload to reach older models.
        payload.pop("questionnaire_consistency_ratio", None)
        return ScoringPreferences.from_dict(payload)


def _resolve_baseline_config_name(strategies: List[Dict[str, Any]]) -> str:
    first_strategy = strategies[0]
    first_plan = first_strategy["banner_plans"][0]
    return first_plan["config_name"]


def _build_baseline_strategy(baseline_id: str, config_name: str) -> Dict[str, Any]:
    rule = _build_baseline_rule(baseline_id)
    return {
        "config_name": config_name,
        "strategy": {
            "protocol_version": "strategy-protocol-v1",
            "kind": "structured",
            "rule": rule,
        },
        "resource_increment": _resource_dict(None),
        "check_in": False,
        "use_origeometry": False,
        "is_core": True,
    }


def _build_baseline_rule(baseline_id: str) -> Dict[str, Any]:
    if baseline_id == "no_draw":
        return _single_condition_rule("draws", ">=", 0)
    if baseline_id == "fixed_draw_cap":
        return _single_condition_rule("draws", ">=", 30)
    if baseline_id == "up_or_cap":
        return {
            "node_type": "group",
            "match": "any",
            "children": [
                {"node_type": "condition", "kind": "current_up", "operator": ">=", "value": 1},
                {"node_type": "condition", "kind": "draws", "operator": ">=", "value": 120},
            ],
        }
    if baseline_id == "all_in":
        return _single_condition_rule("draws", ">=", 999999)
    if baseline_id == "resource_safe":
        return {
            "node_type": "group",
            "match": "any",
            "children": [
                {"node_type": "condition", "kind": "resource_left", "operator": ">=", "value": 80},
                {"node_type": "condition", "kind": "draws", "operator": ">=", "value": 60},
            ],
        }
    raise ValueError(f"不支持的 baseline_strategy_id: {baseline_id}")


def _single_condition_rule(kind: str, operator: str, value: int) -> Dict[str, Any]:
    return {
        "node_type": "group",
        "match": "all",
        "children": [
            {
                "node_type": "condition",
                "kind": kind,
                "operator": operator,
                "value": value,
            }
        ],
    }


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
