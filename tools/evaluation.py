# -*- coding: utf-8 -*-
"""策略评估脚本。

默认读取 tools/evaluation_examples.json，支持外置：
1) 资源与初始计数器
2) 结构化策略
3) 评分偏好参数（preferences）
4) 评分目标（goals）
"""


# 添加项目根目录到路径，确保可以直接运行
if __name__ == "__main__":
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

import json
from pathlib import Path
from typing import Any, Dict

from core import Counters
from scheduler import (
    Resource,
    Scheduler,
)

DEFAULT_CONFIG_PATH = Path(__file__).with_name("evaluation_examples.json")


def _load_config(path: str | None = None) -> Dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise TypeError("evaluation config must be a JSON object")
    return payload


def _resource_from_dict(payload: Dict[str, Any] | None) -> Resource:
    if payload is None:
        return Resource()
    return Resource(
        chartered_permits=int(payload.get("chartered_permits", 0)),
        oroberyl=int(payload.get("oroberyl", 0)),
        arsenal_tickets=int(payload.get("arsenal_tickets", 0)),
        origeometry=int(payload.get("origeometry", 0)),
    )


def _counters_from_dict(payload: Dict[str, Any]) -> Counters:
    return Counters(
        total=int(payload.get("total", 0)),
        no_6star=int(payload.get("no_6star", 0)),
        no_5star_plus=int(payload.get("no_5star_plus", 0)),
        no_up=int(payload.get("no_up", 0)),
        guarantee_used=bool(payload.get("guarantee_used", False)),
        urgent_used=bool(payload.get("urgent_used", False)),
    )


def run_scenario(name: str, scale: int = 5000, config_path: str | None = None):
    payload = _load_config(config_path)
    shared = payload.get("shared", {})
    scenarios = payload.get("scenarios", {})
    if name not in scenarios:
        raise KeyError(f"scenario not found: {name}")
    scenario = scenarios[name]

    scheduler = Scheduler(
        config_dir=shared.get("config_dir", "configs"),
        arrange=shared.get("arrange", "arrange1"),
        resource=_resource_from_dict(shared.get("resource")),
    )
    base_counters = _counters_from_dict(shared.get("initial_counters", {}))
    default_workers = int(shared.get("workers", 16))

    for banner in scenario.get("banners", []):
        scheduler.banner(
            banner["rules"],
            name=banner.get("name"),
            resource_increment=_resource_from_dict(banner.get("resource_increment")),
            init_counters=(
                base_counters
                if banner.get("use_shared_counters", False)
                else _counters_from_dict(banner.get("init_counters", {}))
            ),
            check_in=bool(banner.get("check_in", True)),
            use_origeometry=bool(banner.get("use_origeometry", False)),
            is_core=bool(banner.get("is_core", True)),
        )

    scenario_scale = int(scenario.get("scale", scale))
    workers = int(scenario.get("workers", default_workers))
    preferences = scenario.get("preferences", shared.get("preferences"))
    goals = scenario.get("goals", shared.get("goals"))
    return scheduler.evaluate(
        scenario_scale,
        workers=workers,
        preferences=preferences,
        goals=goals,
    )


def run_all(config_path: str | None = None):
    payload = _load_config(config_path)
    run_order = payload.get("run_order")
    if run_order is None:
        run_order = list(payload.get("scenarios", {}).keys())
    if not isinstance(run_order, list):
        raise TypeError("run_order must be a list")
    default_scale = int(payload.get("default_scale", 2000))
    for scenario_name in run_order:
        if not isinstance(scenario_name, str):
            raise TypeError("run_order items must be strings")
        run_scenario(scenario_name, scale=default_scale, config_path=config_path)


def str0(scale: int = 5000, config_path: str | None = None):
    return run_scenario("str0", scale=scale, config_path=config_path)


def str1(scale: int = 5000, config_path: str | None = None):
    return run_scenario("str1", scale=scale, config_path=config_path)


def str_bad(scale: int = 5000, config_path: str | None = None):
    return run_scenario("str_bad", scale=scale, config_path=config_path)


if __name__ == "__main__":
    run_all()
