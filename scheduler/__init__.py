# -*- coding: utf-8 -*-
"""策略调度包：魔数编码策略、评分系统、多进程评估。"""
from core import Counters
from .engine import Scheduler, main
from .scoring import Resource, ScoringSystem
from .strategy import (
    GachaStrategy,
    URGENT,
    DOSSIER,
    SOFT_PITY,
    UP_OPRT,
    HARD_PITY,
    POTENTIAL,
    OPRT,
    GT,
    LT,
    GE,
    LE,
)
from .workers import (
    get_token,
    consume_resource,
    process_gacha_result,
    handle_urgent_gacha,
    initialize_banner_state,
    _worker_wrapper,
)

__all__ = [
    "Counters",
    "GachaStrategy",
    "Resource",
    "Scheduler",
    "URGENT",
    "DOSSIER",
    "SOFT_PITY",
    "UP_OPRT",
    "OPRT",
    "HARD_PITY",
    "POTENTIAL",
    "GT",
    "LT",
    "GE",
    "LE",
    "ScoringSystem",
    "get_token",
    "consume_resource",
    "process_gacha_result",
    "handle_urgent_gacha",
    "initialize_banner_state",
    "_worker_wrapper",
    "main",
]
