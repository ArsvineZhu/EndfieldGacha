# -*- coding: utf-8 -*-
"""核心数据模型。"""

from dataclasses import dataclass


@dataclass
class GachaResult:
    """抽卡结果数据类，包含干员/武器名称、星级、配额以及保底标记

    Parameters
    ----------
    name : str
        干员或武器的名称
    star : int
        星级，通常为4、5或6星
    quota : int
        配额数量，用于后续奖励计算
    is_up_g : bool, optional
        UP保底标记，默认为False
    is_6_g : bool, optional
        6星保底标记，默认为False
    is_5_g : bool, optional
        5星保底标记，默认为False

    Examples
    --------
    >>> from gacha_core import GachaResult
    >>> # 创建一个普通5星干员的抽卡结果
    >>> result1 = GachaResult(name="德克萨斯", star=5, quota=200)
    >>> # 创建一个UP保底6星干员的抽卡结果
    >>> result2 = GachaResult(name="缄默德克萨斯", star=6, quota=2000, is_up_g=True)
    """

    name: str  # 干员或武器名称
    star: int  # 星级
    quota: int  # 配额数量
    is_up_g: bool = False  # UP保底标记，默认为False
    is_6_g: bool = False  # 6星保底标记，默认为False
    is_5_g: bool = False  # 5星保底标记，默认为False



@dataclass
class Counters:
    """抽卡计数器数据类，管理卡池的各种计数器

    Parameters
    ----------
    total : int
        累计抽卡次数
    no_6star : int
        连续未出 6 星的抽卡次数
    no_5star_plus : int
        连续未出 5 星/6 星的抽卡次数
    no_up : int
        连续未出 UP 的抽卡次数
    guarantee_used : bool
        是否已使用 UP 保底
    urgent_used: bool
        是否已使用加急招募

    Examples
    --------
    >>> from gacha_core import Counters
    >>> # 创建卡池计数器
    >>> weapon_counters = Counters(total=0, no_6star=0, no_up=0)
    """

    total: int = 0  # 累计抽卡次数
    no_6star: int = 0  # 连续未出 6 星的抽卡次数
    no_5star_plus: int = 0  # 连续未出 5 星/6 星的抽卡次数
    no_up: int = 0  # 连续未出 UP 的抽卡次数
    guarantee_used: bool = False  # 是否已使用 UP 保底
    urgent_used: bool = False  # 是否已使用加急招募

