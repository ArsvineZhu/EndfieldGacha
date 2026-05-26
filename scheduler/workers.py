# -*- coding: utf-8 -*-
"""调度用 worker 与辅助方法。"""

from __future__ import annotations

import os
import random
from copy import deepcopy
from math import ceil
from typing import Any, Dict, List, Tuple

from gacha_core import CharGacha, Counters, GlobalConfigLoader
from scheduler.scoring import (
    Resource,
    StageTrace,
    StrategyTrace,
    resource_to_standard_draws,
)
from scheduler.strategy_rules import (
    StrategyRuleEngine,
    StrategyRuleSet,
)


class StrategyRuntime:
    """结构化策略运行时。"""

    def __init__(self, rules: StrategyRuleSet | Dict[str, Any]):
        self.rules = StrategyRuleEngine._coerce(rules)

    def terminate(self, draw_count: int, state: Dict[str, Any]) -> bool:
        return StrategyRuleEngine.should_stop(self.rules, draw_count=draw_count, state=state)


def get_token(gacha: CharGacha) -> int:
    rewards = gacha.get_accumulated_reward()
    count = 0
    for reward in rewards:
        if reward[0].endswith("的信物"):
            count += 1
    return count


def consume_resource(resource: Resource, use_origeometry: bool) -> bool:
    if resource.chartered_permits >= 1:
        resource.chartered_permits -= 1
        return True
    if resource.oroberyl + resource.origeometry * 75 * int(use_origeometry) >= 500:
        if resource.oroberyl < 500 and use_origeometry:
            diff = 500 - resource.oroberyl
            cost = ceil(diff / 75)
            resource.origeometry -= cost
            resource.oroberyl = cost * 75 - diff
        else:
            resource.oroberyl -= 500
        return True
    return False


def process_gacha_result(
    result: Any, gacha: CharGacha, state: Dict[str, Any], potential: int
) -> Tuple[Dict[str, Any], int]:
    """处理单次抽卡结果，更新策略状态。"""

    up_names = gacha.star_up_prob.get(6, ([], []))[0]
    is_up = result.name in up_names if up_names else False

    state["oprt"] = state.get("oprt", False) or (result.star == 6)
    state["up_oprt"] = state.get("up_oprt", False) or is_up
    state["current_up"] = state.get("current_up", 0) + int(is_up)
    state["six_star_count"] = state.get("six_star_count", 0) + int(result.star == 6)
    potential += int(is_up)
    state["potential"] = potential + get_token(gacha)
    state["soft_pity"] = state.get("soft_pity", False) or (
        80 >= gacha.counters.no_6star > 65 and result.star == 6
    )
    state["dossier"] = gacha.counters.total >= 60

    return state, potential


def handle_urgent_gacha(
    config: Any,
    gacha: CharGacha,
    cnts: Counters,
    state: Dict[str, Any],
    potential: int,
    seed: int,
) -> Tuple[Dict[str, Any], int, List[Any]]:
    """处理加急招募赠送的 10 抽。"""

    cnts.urgent_used = True
    urgent = CharGacha(config, seed=seed)
    results: List[Any] = []

    for _ in range(10):
        result = urgent.attempt()
        results.append(result)
        state, potential = process_gacha_result(result, gacha, state, potential)
        state["urgent"] = True

    return state, potential, results


def initialize_banner_state(cnts: Counters) -> Dict[str, Any]:
    return {
        "urgent": cnts.urgent_used,
        "up_oprt": False,
        "oprt": False,
        "soft_pity": False,
        "potential": 0,
        "current_up": 0,
        "six_star_count": 0,
        "resource_left": 0.0,
        "dossier": cnts.total >= 60,
    }


def _worker_wrapper(args: Any) -> StrategyTrace:
    return _simulator(*args)


def _simulator(
    config_dir: str,
    arrangement: List[str],
    schedules: List[Dict[str, Any]],
    change: bool,
    seed: int,
    init_resource: Dict[str, int],
) -> StrategyTrace:
    """运行单次模拟并返回完整策略轨迹。"""

    random.seed(seed)

    resource = Resource(**init_resource)
    dossier = False
    counters = Counters()
    total_paid_draws = 0
    total_bonus_draws = 0
    stages: List[StageTrace] = []

    for idx, plan in enumerate(schedules):
        rules = plan["rules"]
        cnts_data = (
            plan["init_counters"]
            if idx == 0
            else {
                "total": 0,
                "no_6star": 0,
                "no_5star_plus": counters.no_5star_plus,
                "no_up": counters.no_up,
                "guarantee_used": False,
                "urgent_used": False,
            }
        )
        cnts = Counters(**cnts_data)
        check = plan["check_in"]
        use_ori = plan["use_origeometry"]
        addition = Resource(**plan["resource_increment"])
        config_name = plan.get("name")

        if config_name:
            selected_config = config_name
        else:
            selected_config = arrangement[idx] if change else arrangement[0]

        config = GlobalConfigLoader(os.path.join(config_dir, selected_config))
        gacha = CharGacha(config, seed=seed * 1000 + idx)
        gacha.counters = deepcopy(cnts)
        resource.chartered_permits += (
            5 * int(check) + 10 * int(dossier) + addition.chartered_permits
        )
        resource.oroberyl += addition.oroberyl
        resource.arsenal_tickets += addition.arsenal_tickets
        resource.origeometry += addition.origeometry

        strategy = StrategyRuntime(rules)
        state = initialize_banner_state(cnts)
        potential = 0
        stage_paid_draws = 0
        stage_bonus_draws = 0
        stage_results: List[Dict[str, Any]] = []
        featured_names = config.get_char_featured_names()
        up_names = set(featured_names["current_up"])
        past_up_names = set(featured_names["past_up"])
        start_counters = deepcopy(gacha.counters)
        state["resource_left"] = resource_to_standard_draws(resource)

        while not strategy.terminate(gacha.counters.total, state):
            if not consume_resource(resource, use_ori):
                resource_left = resource_to_standard_draws(resource)
                state["resource_left"] = resource_left
                stages.append(
                    StageTrace(
                        config_name=selected_config,
                        start_counters=start_counters,
                        end_counters=deepcopy(gacha.counters),
                        paid_draws=stage_paid_draws,
                        bonus_draws=stage_bonus_draws,
                        resource_left=resource_left,
                        results=stage_results,
                    )
                )
                return StrategyTrace(
                    completed=False,
                    total_paid_draws=total_paid_draws,
                    total_bonus_draws=total_bonus_draws,
                    final_resource_left=resource_left,
                    stages=stages,
                    failure_reason="resource_exhausted",
                )

            result = gacha.attempt()
            total_paid_draws += 1
            stage_paid_draws += 1
            stage_results.append(
                _result_to_record(result, selected_config, up_names, past_up_names)
            )
            state, potential = process_gacha_result(result, gacha, state, potential)
            state["resource_left"] = resource_to_standard_draws(resource)

            if gacha.counters.total == 30 and not cnts.urgent_used:
                state, potential, urgent_results = handle_urgent_gacha(
                    config,
                    gacha,
                    cnts,
                    state,
                    potential,
                    seed + total_paid_draws,
                )
                for urgent_result in urgent_results:
                    total_bonus_draws += 1
                    stage_bonus_draws += 1
                    stage_results.append(
                        _result_to_record(
                            urgent_result, selected_config, up_names, past_up_names
                        )
                    )
                state["resource_left"] = resource_to_standard_draws(resource)

        dossier = gacha.counters.total >= 60
        counters = Counters(
            0,
            gacha.counters.no_6star,
            gacha.counters.no_5star_plus,
            0,
            False,
            False,
        )
        resource_left = resource_to_standard_draws(resource)
        stages.append(
            StageTrace(
                config_name=selected_config,
                start_counters=start_counters,
                end_counters=deepcopy(gacha.counters),
                paid_draws=stage_paid_draws,
                bonus_draws=stage_bonus_draws,
                resource_left=resource_left,
                results=stage_results,
            )
        )

    return StrategyTrace(
        completed=True,
        total_paid_draws=total_paid_draws,
        total_bonus_draws=total_bonus_draws,
        final_resource_left=resource_to_standard_draws(resource),
        stages=stages,
    )


def _result_to_record(
    result: Any,
    config_name: str,
    up_names: set[str],
    past_up_names: set[str],
) -> Dict[str, Any]:
    return {
        "name": result.name,
        "star": result.star,
        "quota": result.quota,
        "is_up_g": result.is_up_g,
        "is_6_g": result.is_6_g,
        "is_5_g": result.is_5_g,
        "is_current_up": result.name in up_names,
        "is_past_up": result.name in past_up_names,
        "config_name": config_name,
    }


__all__ = [
    "consume_resource",
    "get_token",
    "handle_urgent_gacha",
    "initialize_banner_state",
    "process_gacha_result",
    "_worker_wrapper",
]


