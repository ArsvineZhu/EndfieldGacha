# -*- coding: utf-8 -*-
"""调度用 worker 与辅助方法。"""

from math import ceil
from copy import deepcopy
from typing import Any, Dict, List, Tuple
import os
import random

from core import CharGacha, Counters, GlobalConfigLoader

from scheduler.scoring import Resource
from scheduler.strategy import GachaStrategy


def get_token(gacha: CharGacha) -> int:
    rewards = gacha.get_accumulated_reward()
    count = 0
    for i in rewards:
        if i[0].endswith("的信物"):
            count += 1
    return count


def consume_resource(resource: Resource, use_origeometry: bool) -> bool:
    if resource.chartered_permits >= 1:
        resource.chartered_permits -= 1
        return True
    elif resource.oroberyl + resource.origeometry * 75 * int(use_origeometry) >= 500:
        if resource.oroberyl < 500 and use_origeometry:
            diff = 500 - resource.oroberyl
            cost = ceil(diff / 75)
            resource.origeometry -= cost
            resource.oroberyl = cost * 75 - diff
        else:
            resource.oroberyl -= 500
        return True
    else:
        return False


def process_gacha_result(
    result: Any, gacha: CharGacha, state: Dict[str, Any], potential: int
) -> Tuple[Dict[str, Any], int]:
    """处理单次抽卡结果，更新状态和潜能计数。

    Parameters
    ----------
    result : Any
        抽卡结果对象。
    gacha : CharGacha
        角色卡池实例。
    state : dict
        当前状态字典。
    potential : int
        当前潜能计数。

    Returns
    -------
    tuple
        (更新后的状态字典, 更新后的潜能计数)
    """
    up_names = gacha.star_up_prob.get(6, ([], []))[0]
    is_up = result.name in up_names if up_names else False

    state["oprt"] = state.get("oprt", False) or (result.star == 6)
    state["up_oprt"] = state.get("up_oprt", False) or is_up
    potential += int(is_up)
    state["potential"] = potential + get_token(gacha)
    state["soft_pity"] = state.get("soft_pity", False) or (
        85 >= gacha.counters.no_6star > 65 and result.star == 6
    )

    return state, potential


def handle_urgent_gacha(
    config: Any,
    gacha: CharGacha,
    cnts: Counters,
    state: Dict[str, Any],
    potential: int,
) -> Tuple[Dict[str, Any], int, List[Any]]:
    """处理加急招募（10连抽）。

    Parameters
    ----------
    config : Any
        配置对象。
    gacha : CharGacha
        角色卡池实例。
    cnts : Counters
        计数器对象。
    state : dict
        当前状态字典。
    potential : int
        当前潜能计数。

    Returns
    -------
    tuple
        (更新后的状态字典, 更新后的潜能计数, 加急招募结果列表)
    """
    cnts.urgent_used = True
    urgent = CharGacha(config)
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
    }


def _worker_wrapper(args: Any) -> Dict[str, Any]:
    return _simulator(*args)


def _simulator(
    config_dir: str,
    arrangement: List[str],
    schedules: List[Dict[str, Any]],
    change: bool,
    seed: int,
    init_resource: Dict[str, int],
) -> Dict[str, Any]:
    """运行单次模拟的worker函数。

    Parameters
    ----------
    config_dir : str
        配置文件目录。
    arrangement : list of str
        卡池顺序列表。
    schedules : list of dict
        策略计划列表。
    change : bool
        是否切换卡池配置。
    seed : int
        随机种子。
    init_resource : dict
        初始资源。

    Returns
    -------
    dict
        模拟结果，包含：
        - total_draws: 总抽数
        - six_stars: 6星数量
        - up_chars: UP角色数量
        - resource_left: 剩余资源（换算为抽数）
        - complete: 是否完成所有计划
    """
    random.seed(seed)

    resource = Resource(**init_resource)
    dossier = False
    counters = Counters()
    total_draws = 0
    six_stars = 0
    up_chars = 0

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

        # 选择配置：如果有 name 则使用 name，否则使用 arrangement 顺序
        if config_name:
            selected_config = config_name
        else:
            selected_config = arrangement[idx] if change else arrangement[0]

        config = GlobalConfigLoader(
            os.path.join(
                config_dir,
                selected_config,
            )
        )
        gacha = CharGacha(config)
        gacha.counters = deepcopy(cnts)
        resource.chartered_permits += (
            5 * int(check) + 10 * int(dossier) + addition.chartered_permits
        )
        resource.oroberyl += addition.oroberyl
        resource.arsenal_tickets += addition.arsenal_tickets
        resource.origeometry += addition.origeometry

        strategy = GachaStrategy(rules)
        state = initialize_banner_state(cnts)

        potential = 0

        while not (strategy.terminate(gacha.counters.total, state)):
            if not consume_resource(resource, use_ori):
                # 资源不足，模拟失败
                return {
                    "total_draws": total_draws,
                    "six_stars": six_stars,
                    "up_chars": up_chars,
                    "resource_left": resource.chartered_permits
                    + (resource.oroberyl + resource.origeometry * 75) // 500,
                    "complete": False,
                }

            result = gacha.attempt()
            total_draws += 1

            if result.star == 6:
                six_stars += 1
            up_names = gacha.star_up_prob.get(6, ([], []))[0]
            if up_names and result.name in up_names:
                up_chars += 1

            state, potential = process_gacha_result(result, gacha, state, potential)

            if gacha.counters.total == 30 and not cnts.urgent_used:
                state, potential, urgent_results = handle_urgent_gacha(
                    config, gacha, cnts, state, potential
                )
                for urgent_result in urgent_results:
                    if urgent_result.star == 6:
                        six_stars += 1
                    up_names = gacha.star_up_prob.get(6, ([], []))[0]
                    if up_names and urgent_result.name in up_names:
                        up_chars += 1
                continue

        dossier = gacha.counters.total >= 60
        counters = Counters(
            0,
            gacha.counters.no_6star,
            gacha.counters.no_5star_plus,
            0,
            False,
            False,
        )

    return {
        "total_draws": total_draws,
        "six_stars": six_stars,
        "up_chars": up_chars,
        "resource_left": resource.chartered_permits
        + (resource.oroberyl + resource.origeometry * 75) // 500,
        "complete": True,
    }


__all__ = [
    "get_token",
    "consume_resource",
    "process_gacha_result",
    "handle_urgent_gacha",
    "initialize_banner_state",
    "_worker_wrapper",
]
