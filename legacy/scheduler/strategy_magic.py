# -*- coding: utf-8 -*-
"""旧魔数策略系统的存档入口。

该模块仅保留历史实现，便于查阅旧版魔数编码策略；当前运行时与协议层均不再
支持导入、序列化或执行这些 legacy 规则。
"""

from .strategy import (
    DOSSIER,
    GE,
    GT,
    HARD_PITY,
    LE,
    LT,
    OPRT,
    POTENTIAL,
    SOFT_PITY,
    UP_OPRT,
    URGENT,
)
from .strategy import (
    GachaStrategy as LegacyMagicStrategy,
)

LEGACY_STRATEGY_VERSION = "magic-v1"

__all__ = [
    "DOSSIER",
    "GE",
    "GT",
    "HARD_PITY",
    "LEGACY_STRATEGY_VERSION",
    "LE",
    "LT",
    "LegacyMagicStrategy",
    "OPRT",
    "POTENTIAL",
    "SOFT_PITY",
    "UP_OPRT",
    "URGENT",
]
