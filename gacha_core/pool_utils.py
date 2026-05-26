# -*- coding: utf-8 -*-
"""卡池归一化辅助函数。"""

from typing import Any, Dict, List, Tuple


def _normalize_star_pool(
    pool_data: Dict[str, List[Dict[str, Any]]], star: int, pool_name: str
) -> Tuple[List[str], List[float], List[str]]:
    star_key = str(star)
    items = pool_data.get(star_key)
    if not items:
        raise ValueError(f"{pool_name}{star}星池不能为空")

    up_names: List[str] = []
    up_probs: List[float] = []
    normal_names: List[str] = []
    prob_acc = 0.0

    for item in items:
        name = item.get("name")
        if not name:
            raise ValueError(f"{pool_name}{star}星池存在缺少名称的条目")
        try:
            prob = float(item.get("up_prob", 0.0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{pool_name}{star}星池的 UP 概率格式错误") from exc
        if prob < 0:
            raise ValueError(f"{pool_name}{star}星池的 UP 概率不能为负数")
        if prob > 0:
            prob_acc += prob
            up_names.append(name)
            up_probs.append(prob_acc)
        else:
            normal_names.append(name)

    if prob_acc > 1.0 + 1e-6:
        raise ValueError(f"{pool_name}{star}星 UP 概率累计不能超过 1")
    if prob_acc < 1.0 - 1e-6 and not normal_names:
        raise ValueError(f"{pool_name}{star}星普通池不能为空")
    if up_probs:
        up_probs[-1] = min(up_probs[-1], 1.0)

    return up_names, up_probs, normal_names
