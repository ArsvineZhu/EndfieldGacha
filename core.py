#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心抽卡逻辑模块
====================================================================
实现角色/武器卡池的抽卡、保底、累计奖励机制
 - 模块名称: core
 - 版本: 1.2.0
 - 作者: Arsvine
 - 最后修改时间: 2026-03-10
 - 编码: utf-8
 - 适用Python版本: 3.10+

核心功能
--------
1. 提供单例全局配置加载器，统一加载/管理卡池、抽卡规则、全局常量配置
2. 定义抽卡结果数据类GachaResult，标准化抽卡返回结果
3. 实现角色卡池类CharGacha：支持6星/5星/UP保底、概率递增、累计抽卡奖励
4. 实现武器卡池类WeaponGacha：支持申领式抽卡、保底替换、累计申领奖励
5. 封装高精度概率计算、卡池数据预处理、计数器管理等底层逻辑

模块导出
--------
 - GachaResult
 - GlobalConfigLoader
 - WeaponGacha
 - CharGacha

核心依赖
--------
- json: 配置文件解析
- random.choice: 随机抽卡选择
- time: 随机种子生成
- collections.deque: 高效随机数序列管理
- numpy.random: 批量随机数生成，提升性能
- os: 配置文件路径处理
- dataclasses.dataclass: 抽卡结果数据建模
- decimal.Decimal: 高精度概率计算
- typing: 类型注解（Dict/List/Tuple/Any）

卡池机制说明
------------
1. 角色卡池：单次抽卡，支持6星概率递增、80抽6星保底、10抽5星保底、120抽UP保底
2. 武器卡池：申领式抽卡（默认多抽），支持最后1抽保底替换、UP/6星/5星保底优先级机制
3. 累计奖励：根据抽卡/申领次数，触发一次性/循环性累计奖励发放
4. 保底标记：抽卡结果携带UP/6星/5星保底触发标记，支持结果溯源

异常处理
--------
1. 配置文件不存在：抛出FileNotFoundError
2. 配置文件格式错误：抛出ValueError
3. 概率计算基于Decimal高精度，避免浮点误差
"""

import json
import os
from time import time
from collections import deque
from numpy import random as np_rand
from random import choice
from random import seed as rnd_seed
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Dict, List, Tuple, Any

__all__ = ["GachaResult", "Counters", "GlobalConfigLoader", "WeaponGacha", "CharGacha"]
__version__ = "1.2.0"
__author__ = "Arsvine"


class BatchRandom:
    """批量随机数生成器

    核心能力：
    1. 预生成高精度随机数序列（Decimal类型），按需弹出
    2. 统一随机状态，支持种子复现
    """

    def __init__(self, seed: int = -1, size: int = 1024):
        """初始化批量随机生成器

        Parameters
        ----------
        seed : int, optional
            随机数种子，默认-1（自动基于时间戳+微秒生成）
        size : int, optional
            预生成序列的大小，默认1024
        """
        # 优化种子生成
        if seed < 0:
            seed = int(time() * 1_000_000) % (2**32)
        self.seed = seed
        self.np_rand = np_rand.RandomState(seed)  # 独立随机状态

        # 原有随机数队列
        self.__sequence = deque()
        self.size = size
        self._randomize()

    def _randomize(self) -> List[Decimal]:
        """生成指定数量的随机数，覆盖内部序列"""
        np_rands = self.np_rand.random(self.size)
        rand_list = [Decimal(str(num)) for num in np_rands.tolist()]
        self.__sequence.clear()
        self.__sequence.extend(rand_list)
        return rand_list

    @staticmethod
    def batch(size: int = 1024) -> List[Decimal]:
        """静态方法，直接生成指定数量的随机数"""
        if not isinstance(size, int) or size <= 0:
            raise ValueError(f"随机数数量必须是正整数，当前传入: {size}")
        np_rands = np_rand.random(size)
        return [Decimal(str(num)) for num in np_rands.tolist()]

    def pop(self) -> Decimal:
        """从内部随机数序列中弹出一个随机数"""
        if not self.__sequence:
            self._randomize()  # 自动补充随机数
        return self.__sequence.popleft()

    @property
    def sequence(self) -> List[Decimal]:
        """返回内部随机数序列的副本"""
        return list(self.__sequence).copy()


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
    >>> from core import GachaResult
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
    >>> from core import Counters
    >>> # 创建卡池计数器
    >>> weapon_counters = Counters(total=0, no_6star=0, no_up=0)
    """

    total: int = 0  # 累计抽卡次数
    no_6star: int = 0  # 连续未出 6 星的抽卡次数
    no_5star_plus: int = 0  # 连续未出 5 星/6 星的抽卡次数
    no_up: int = 0  # 连续未出 UP 的抽卡次数
    guarantee_used: bool = False  # 是否已使用 UP 保底
    urgent_used: bool = False  # 是否已使用加急招募


# ===================== 全局配置加载器=====================
class GlobalConfigLoader:
    """全局配置加载器，负责加载全局常量和各类配置文件，并提供统一接口访问

    用于加载和管理所有配置文件，包括全局常量、卡池数据、抽卡规则等。

    Examples
    --------
    >>> from core import GlobalConfigLoader
    >>> # 获取配置加载器实例
    >>> config = GlobalConfigLoader()
    >>> # 加载角色卡池数据
    >>> config = GlobalConfigLoader("configs/config_1")
    >>> char_pool_data = config.get_pool_data("char")
    >>> # 获取角色卡池规则配置
    >>> char_rules = config.get_rule_config("char")
    """

    @staticmethod
    def _get_default_config_path() -> str:
        """从 arrangement 文件获取默认配置路径"""
        arrangement_path = os.path.join(
            os.path.dirname(__file__), "configs", "arrangement"
        )
        try:
            with open(arrangement_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line:
                    return os.path.join("configs", first_line)
        except FileNotFoundError:
            pass
        return "configs/config_1"

    def __init__(self, path: str | None = None):
        """初始化配置加载器

        Parameters
        ----------
        path : str, optional
            配置文件路径，默认从 arrangement 文件第一行获取
        """
        if path is None:
            path = self._get_default_config_path()
        self._current_path = path
        self._cache: Dict[str, Any] = {}
        self.constants = self._load_constants(path)
        getcontext().prec = self.constants.get("default_precision", 6)

    def _load_constants(self, path: str) -> Dict[str, Any]:
        """加载全局常量配置（从gacha_rules.json读取）

        Returns
        -------
        Dict[str, Any]
            包含全局常量的字典

        Raises
        ------
        FileNotFoundError
            当gacha_rules.json配置文件不存在时
        ValueError
            当gacha_rules.json配置文件格式错误时
        """
        # 从gacha_rules.json加载配置
        rules_path = os.path.join(os.path.dirname(__file__), path, "gacha_rules.json")
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件 `{rules_path}` 不存在")
        except json.JSONDecodeError:
            raise ValueError("配置文件 gacha_rules.json 格式错误")

    def _get_config_path(self, file_name: str) -> str:
        """获取配置文件路径

        Parameters
        ----------
        file_name : str
            配置文件名称

        Returns
        -------
        str
            配置文件的完整路径
        """
        return os.path.join(os.path.dirname(__file__), self._current_path, file_name)

    def load_config(self, file_name: str) -> Dict[str, Any]:
        """加载指定配置文件

        Parameters
        ----------
        file_name : str
            配置文件名称

        Returns
        -------
        Dict[str, Any]
            配置文件内容

        Raises
        ------
        FileNotFoundError
            当配置文件不存在时
        ValueError
            当配置文件格式错误时
        """
        if file_name in self._cache:
            return self._cache[file_name]
        config_path = self._get_config_path(file_name)
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache[file_name] = data
                return data
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件 {config_path} 不存在")
        except json.JSONDecodeError:
            raise ValueError(f"配置文件 {file_name} 格式错误")

    def get_pool_data(self, pool_type: str) -> Dict[str, List[Dict]]:
        """获取卡池数据

        Parameters
        ----------
        pool_type : str
            卡池类型，如 "char"或 "weapon"（武器卡池）

        Returns
        -------
        Dict[str, List[Dict]]
            卡池数据，包含不同星级的干员或武器列表
        """
        file_name = f"{pool_type}_pool.json"
        return self.load_config(file_name)

    def get_rule_config(self, pool_type: str) -> Dict[str, Any]:
        """获取抽卡规则配置，统一类型转换

        Parameters
        ----------
        pool_type : str
            卡池类型，如 "char"或 "weapon"（武器卡池）

        Returns
        -------
        Dict[str, Any]
            抽卡规则配置，包含概率、保底规则等
        """
        rules = self.load_config("gacha_rules.json")[pool_type]
        # 类型转换：str键→int键，概率→Decimal
        rules["quota_rule"] = {int(k): int(v) for k, v in rules["quota_rule"].items()}
        rules["base_prob"] = {
            int(k): Decimal(str(v)) for k, v in rules["base_prob"].items()
        }
        return rules

    def get_text(self, key: str) -> str:
        """获取文本常量(基本废弃)

        注意：text_constants字段已从配置文件中移除，现在返回硬编码值

        Parameters
        ----------
        key : str
            文本常量的键名

        Returns
        -------
        str
            对应的文本常量值
        """
        # 硬编码的文本常量值（原text_constants字段内容）
        text_constants = {
            "char_quota_name": "武库配额",
            "weapon_quota_name": "集成配额",
            "draw_text": "寻访",
            "apply_text": "申领",
            "weapon_draw_text": "抽",
            "star_text": "星",
            "up_text": "概率提升",
            "rate_text": "出率",
            "time_text": "秒",
            "total_time_text": "总耗时",
            "per_second_text": "每秒",
        }

        # 特殊处理：卡池名称从pool_info获取
        if key == "char_pool_name":
            pool_info = self.constants.get("pool_info", {})
            return pool_info.get("char_pool_name", "「熔火灼痕」")
        elif key == "weapon_pool_name":
            pool_info = self.constants.get("pool_info", {})
            return pool_info.get("weapon_pool_name", "「熔铸申领」")

        # 返回硬编码的文本常量
        if key in text_constants:
            return text_constants[key]

        # 如果键不存在，返回空字符串
        return ""

    def get_default(self, key: str) -> Any:
        """获取默认值（已弃用，使用get_default_precision代替）

        Parameters
        ----------
        key : str
            默认值的键名

        Returns
        -------
        Any
            对应的默认值
        """
        # 兼容旧代码，default_precision现在直接在根层级
        if key == "default_precision":
            return self.constants.get("default_precision", 6)
        return None

    def get_default_precision(self) -> int:
        """获取默认精度

        Returns
        -------
        int
            默认精度值
        """
        return self.constants.get("default_precision", 6)

    def get_pool_info(self, pool_type: str) -> Dict[str, Any]:
        """获取卡池信息（开放时间、结束时间等）

        Parameters
        ----------
        pool_type : str
            卡池类型，如 "char"或 "weapon"

        Returns
        -------
        Dict[str, Any]
            卡池信息，包含开放时间、结束时间等
        """
        pool_info = self.constants.get("pool_info", {})
        if pool_type == "char":
            return {
                "name": pool_info.get("char_pool_name", ""),
                "open_time": pool_info.get("open_time", ""),
                "close_time": pool_info.get("close_time", ""),
            }
        else:  # weapon
            return {
                "name": pool_info.get("weapon_pool_name", ""),
                "open_time": pool_info.get("open_time", ""),
                "close_time": pool_info.get("close_time", ""),
            }


# ===================== 角色卡池类（CharGacha）=====================
class CharGacha:
    """角色卡池类，负责角色卡池的抽卡逻辑和累计奖励逻辑，包含UP保底、6星保底、5星保底等机制

    该类实现了角色卡池的完整抽卡流程，包括概率计算、保底机制触发、
    累计奖励计算等功能。支持UP角色保底、6星保底和5星保底等多种机制。

    Examples
    --------
    >>> from core import CharGacha
    >>> # 创建角色卡池实例
    >>> char_gacha = CharGacha()
    >>> # 进行单次抽卡
    >>> result = char_gacha.attempt()
    >>> print(f"抽卡结果：{result.name}，{result.star}星")
    >>> # 获取累计奖励
    >>> rewards = char_gacha.get_accumulated_reward()
    >>> print(f"累计奖励：{rewards}")
    """

    def __init__(
        self, config: GlobalConfigLoader | None = None, seed: int = -1, size: int = 1024
    ):
        """初始化角色卡池

        加载配置文件，预缓存数据，并初始化计数器。

        Parameters
        ----------
        config : GlobalConfigLoader, optional
            配置加载器实例，默认使用 configs/config_1
        seed : int, optional
            随机数种子，默认-1（自动基于时间戳+微秒生成随机种子）
        size : int, optional
            预生成随机数序列的大小，默认1024
        """
        self.config = config if config else GlobalConfigLoader()
        self.rand = BatchRandom(
            seed, size=size
        )  # 用于生成随机数序列，支持性能优化和可复现性
        if seed >= 0:
            rnd_seed(seed)
        # 加载配置
        self.pool_data = self.config.get_pool_data("char")
        self.rule_config = self.config.get_rule_config("char")
        # 预缓存数据
        self._precache_data()
        # 初始化计数器
        self.counters = Counters()

    def _precache_data(self):
        """预缓存UP/普通干员数据

        从配置文件中加载并预处理干员数据，包括UP干员和普通干员的概率分布。
        """
        # noinspection DuplicatedCode
        self.star_up_prob: Dict[int, Tuple[List[str], List[Decimal]]] = {}
        self.star_normal: Dict[int, List[str]] = {}

        for star_str in ["6", "5", "4"]:
            star = int(star_str)
            items = self.pool_data[star_str]
            up_names, up_probs, normal_names = [], [], []
            prob_acc = Decimal("0.0")

            for item in items:
                prob = Decimal(str(item["up_prob"]))
                if prob > 0:
                    up_names.append(item["name"])
                    prob_acc += prob
                    up_probs.append(prob_acc)
                else:
                    normal_names.append(item["name"])

            self.star_up_prob[star] = (up_names, up_probs)
            self.star_normal[star] = normal_names

        # 读取概率递增参数
        self.prob_increase = Decimal(str(self.rule_config["prob_increase"]))
        self.prob_upper = Decimal(str(self.rule_config["prob_upper_limit"]))
        # 读取UP角色名称
        self.up_char_name = self.rule_config["up_char_name"]
        # 从配置读取6星概率递增起始次数（6星保底起始次数）
        self.six_star_increase_start = self.rule_config["6star_prob_increase_start"]

    def init_counters(self):
        """初始化计数器

        初始化抽卡相关的计数器，包括累计抽卡次数、保底计数器等。
        """
        self.counters = Counters()  # 使用Counters数据类管理计数器

    def _get_char_by_star(self, star: int) -> Tuple[str, int, bool]:
        """按星级随机获取干员

        Parameters
        ----------
        star : int
            干员星级，通常为4、5或6星

        Returns
        -------
        Tuple[str, int, bool]
            返回一个元组，包含干员名称、星级和是否为UP干员的标记
        """
        up_names, up_probs = self.star_up_prob[star]
        normal_names = self.star_normal[star]

        if up_names:
            rand = self.rand.pop()
            for idx, prob_acc in enumerate(up_probs):
                if rand < prob_acc:
                    return up_names[idx], star, True
            return choice(normal_names), star, False
        else:
            return choice(normal_names), star, False

    def _get_up_char(self, star: int = 6) -> Tuple[str, int]:
        """获取UP干员（默认6星），等概率返回

        Parameters
        ----------
        star : int, optional
            干员星级，默认为6星

        Returns
        -------
        Tuple[str, int]
            返回一个元组，包含UP干员名称和星级
        """
        if not hasattr(self, "_up_chars"):
            self._up_chars = []
            up_names, _ = self.star_up_prob[star]
            self._up_chars.extend([(n, star) for n in up_names])
        return choice(self._up_chars)

    def attempt(self, disable_guarantee: bool = False) -> GachaResult:
        """
        角色卡池单次抽卡，包含UP保底、6星保底、5星保底等机制

        Parameters
        ----------
        disable_guarantee : bool, optional
            参数用于禁用保底机制，主要用于模拟抽卡分布时使用，默认False（即启用保底）

        Returns
        -------
        GachaResult
            GachaResult 对象，包含抽卡结果和保底触发标记

        Examples
        --------
        >>> from core import CharGacha
        >>> char_gacha = CharGacha()
        >>> # 正常抽卡（启用保底）
        >>> result1 = char_gacha.attempt()
        >>> print(f"抽卡结果：{result1.name}，{result1.star}星")
        >>> # 禁用保底抽卡（用于模拟）
        >>> result2 = char_gacha.attempt(disable_guarantee=True)
        """
        self.counters.total += 1
        if disable_guarantee:
            self.counters.no_6star = 0
            self.counters.no_5star_plus = 0
            self.counters.no_up = 0
        else:
            self.counters.no_6star += 1
            self.counters.no_5star_plus += 1
            self.counters.no_up += 1

        # 步骤1：计算当前6星概率（含递增）
        base_6star_prob = self.rule_config["base_prob"][6]  # 基础0.8%
        current_6star_prob = base_6star_prob
        # 核心：从配置读取递增起始次数
        if self.counters.no_6star > self.six_star_increase_start:
            current_6star_prob += (
                self.counters.no_6star - self.six_star_increase_start
            ) * self.prob_increase
            if current_6star_prob > self.prob_upper:
                current_6star_prob = self.prob_upper

        # 步骤2：UP角色保底（连续120抽未出）- 最高优先级
        if (
            not self.counters.guarantee_used
            and self.counters.no_up >= self.rule_config["up_guarantee_draw"]
            and not disable_guarantee
        ):
            result, star_int = self._get_up_char()
            # 重置所有相关计数器
            self.counters.no_up = 0
            self.counters.no_6star = 0
            self.counters.no_5star_plus = 0
            self.counters.guarantee_used = True
            quota = self.rule_config["quota_rule"][star_int]
            return GachaResult(
                name=result, star=star_int, quota=quota, is_up_g=True
            )  # UP保底触发，标记为True

        # 步骤3：判定是否触发6星保底（连续80抽未出6星，这也太非了）
        if (
            self.counters.no_6star >= self.rule_config["guarantee_6star_draw"]
            and not disable_guarantee
        ):
            # 6星保底：6星100%，5/4星0%
            result, star_int, is_up = self._get_char_by_star(6)
            # 重置所有计数器
            self.counters.no_6star = 0
            self.counters.no_5star_plus = 0
            if is_up:
                self.counters.no_up = 0
            quota = self.rule_config["quota_rule"][6]
            return GachaResult(
                name=result, star=star_int, quota=quota, is_6_g=True
            )  # 6星保底触发，标记为True

        # 步骤4：判定是否触发5星保底（连续10抽未出5/6星）
        is_5star_guarantee = (
            self.counters.no_5star_plus >= self.rule_config["guarantee_5star_plus_draw"]
            and not disable_guarantee
        )
        rand = self.rand.pop()

        if is_5star_guarantee:
            # 5星保底：6星概率=当前6星概率（0.8%/递增后），5星=1-6星概率，4星0%
            if rand < current_6star_prob:
                # 出6星：重置所有计数器
                result, star_int, is_up = self._get_char_by_star(6)
                self.counters.no_6star = 0
                self.counters.no_5star_plus = 0
                if is_up:
                    self.counters.no_up = 0
            else:
                # 出5星：仅重置5星保底计数器
                result, star_int, is_up = self._get_char_by_star(5)
                self.counters.no_5star_plus = 0
            quota = self.rule_config["quota_rule"][star_int]
            return GachaResult(
                name=result, star=star_int, quota=quota, is_5_g=True
            )  # 5星保底触发，标记为True

        # 步骤5：无保底阶段（正常抽卡）：6星概率提升后，五星与四星按比例重新映射
        base_5star_prob = self.rule_config["base_prob"][5]  # 基础8%
        base_4star_prob = self.rule_config["base_prob"][4]  # 基础91.2%

        # 计算剩余概率并按比例重新映射五星和四星概率
        remaining_prob = Decimal("1.0") - current_6star_prob
        if remaining_prob > 0:
            # 计算五星和四星的基础概率比例
            total_base_prob = base_5star_prob + base_4star_prob
            base_5star_ratio = base_5star_prob / total_base_prob

            # 重新计算五星和四星概率
            adjusted_5star_prob = remaining_prob * base_5star_ratio
            # adjusted_4star_prob = remaining_prob * (Decimal("1.0") - base_5star_ratio)
        else:
            # 剩余概率为0，所有概率都被六星挤占
            adjusted_5star_prob = Decimal("0.0")
            # adjusted_4star_prob = Decimal("0.0")

        if rand < current_6star_prob:
            # 出6星：重置所有计数器
            result, star_int, is_up = self._get_char_by_star(6)
            self.counters.no_6star = 0
            self.counters.no_5star_plus = 0
            if is_up:
                self.counters.no_up = 0
                self.counters.guarantee_used = True  # 出6星UP时视同触发UP保底，永久失效
        elif rand < current_6star_prob + adjusted_5star_prob:
            # 出5星：重置5星保底计数器
            result, star_int, is_up = self._get_char_by_star(5)
            self.counters.no_5star_plus = 0
        else:
            # 出4星：计数器继续累积
            result, star_int, is_up = self._get_char_by_star(4)
        quota = self.rule_config["quota_rule"][star_int]

        # 改造返回值：新增保底标记
        return GachaResult(
            name=result, star=star_int, quota=quota
        )  # 无保底，标记均为False

    def get_accumulated_reward(self) -> List[Tuple[str, int]]:
        """获取累计奖励

        根据累计抽卡次数，计算并返回可获得的累计奖励列表。

        Returns
        -------
        List[Tuple[str, int]]
            返回奖励列表，每个元素为(奖励名称, 数量)的元组

        Examples
        --------
        >>> from core import CharGacha
        >>> char_gacha = CharGacha()
        >>> # 进行多次抽卡
        >>> for _ in range(30):
        ...     char_gacha.attempt_once()
        >>> # 获取累计奖励
        >>> rewards = char_gacha.get_accumulated_reward()
        >>> print(f"累计奖励：{rewards}")
        """
        # 统计奖励出现次数
        reward_counts = {}
        reward_config = self.rule_config["rewards"]

        # 30抽奖励（一次性）
        if self.counters.total >= 30:
            reward = reward_config.get("Type_A", "加急招募")
            reward_counts[reward] = reward_counts.get(reward, 0) + 1

        # 60抽奖励（一次性）
        if self.counters.total >= 60:
            reward = reward_config.get("Type_B", "寻访情报书")
            reward_counts[reward] = reward_counts.get(reward, 0) + 1

        # 240抽奖励（可重复获取，每240次）
        repeat_count = self.counters.total // 240
        if repeat_count > 0:
            reward = reward_config.get("Type_C", "概率提升干员的信物")
            reward_counts[reward] = reward_counts.get(reward, 0) + repeat_count

        # 格式化奖励列表
        return [(reward, count) for reward, count in reward_counts.items()]


# ===================== 武器卡池类（WeaponGacha）=====================
class WeaponGacha:
    """武器卡池类，负责武器卡池的抽卡逻辑和累计奖励逻辑，包含UP保底、6星保底、5星保底等机制

    该类实现了武器卡池的完整抽卡流程，包括单次申领（多次抽卡）、
    保底机制触发、累计奖励计算等功能。支持UP武器保底、6星保底和5星保底等多种机制。

    Examples
    --------
    >>> from core import WeaponGacha
    >>> # 创建武器卡池实例
    >>> weapon_gacha = WeaponGacha()
    >>> # 进行单次申领（通常为10连抽）
    >>> results = weapon_gacha.apply_once()
    >>> for result in results:
    ...     print(f"抽卡结果：{result.name}，{result.star}星")
    >>> # 获取累计奖励
    >>> rewards = weapon_gacha.get_accumulated_reward()
    >>> print(f"累计奖励：{rewards}")
    """

    def __init__(
        self, config: GlobalConfigLoader | None = None, seed: int = -1, size: int = 1024
    ):
        """初始化武器卡池

        加载配置文件，预缓存数据，并初始化计数器。

        Parameters
        ----------
        config : GlobalConfigLoader, optional
            配置加载器实例，默认使用 configs/config_1
        seed : int, optional
            随机数种子，默认-1（自动基于时间戳+微秒生成随机种子）
        size : int, optional
            预生成随机数序列的大小，默认1024
        """
        self.config = config if config else GlobalConfigLoader()
        self.rand = BatchRandom(seed, size=size)  # 武器卡池使用独立的随机数生成器实例
        if seed >= 0:
            rnd_seed(seed)
        self.pool_data = self.config.get_pool_data("weapon")
        self.rule_config = self.config.get_rule_config("weapon")
        self._precache_data()
        self.counters = Counters()  # 使用Counters数据类管理计数器

    def _precache_data(self):
        """预缓存UP/普通武器数据

        从配置文件中加载并预处理武器数据，包括UP武器和普通武器的概率分布。
        """
        # noinspection DuplicatedCode
        self.star_up_prob: Dict[int, Tuple[List[str], List[Decimal]]] = {}
        self.star_normal: Dict[int, List[str]] = {}

        for star_str in ["6", "5", "4"]:
            star = int(star_str)
            items = self.pool_data[star_str]
            up_names, up_probs, normal_names = [], [], []
            prob_acc = Decimal("0.0")

            for item in items:
                prob = Decimal(str(item["up_prob"]))
                if prob > 0:
                    up_names.append(item["name"])
                    prob_acc += prob
                    up_probs.append(prob_acc)
                else:
                    normal_names.append(item["name"])

            self.star_up_prob[star] = (up_names, up_probs)
            self.star_normal[star] = normal_names

        self.up_weapon_name = self.rule_config["up_weapon_name"]

    def init_counters(self):
        """初始化计数器

        初始化申领相关的计数器，包括累计申领次数、保底计数器等。
        """
        self.counters = Counters()  # 使用Counters数据类管理计数器

    def _get_weapon_by_star(self, star: int) -> Tuple[str, int]:
        """按星级获取武器（优先UP，无UP则普通）

        Parameters
        ----------
        star : int
            武器星级，通常为4、5或6星

        Returns
        -------
        Tuple[str, int]
            返回一个元组，包含武器名称和星级
        """
        up_names, up_probs = self.star_up_prob[star]
        normal_names = self.star_normal[star]

        if up_names:
            rand = self.rand.pop()
            for idx, prob_acc in enumerate(up_probs):
                if rand < prob_acc:
                    return up_names[idx], star
            return choice(normal_names), star
        else:
            return choice(normal_names), star

    def _get_only_up_weapon(self) -> Tuple[str, int]:
        """获取纯UP武器（6星，最高优先级）

        Returns
        -------
        Tuple[str, int]
            返回一个元组，包含UP武器名称和星级（固定为6星）
        """
        return self.up_weapon_name, 6

    def _get_only_6star_weapon(self) -> Tuple[str, int, bool]:
        """6星保底：从所有6星武器（含UP+通用）中随机抽取，UP概率=卡池设定值

        Returns
        -------
        Tuple[str, int, bool]
            返回一个元组，包含武器名称、星级（固定为6星）和是否为UP武器的标记
        """
        # 1. 读取6星UP武器的概率配置（通常UP占25%）
        up_names, up_probs = self.star_up_prob[6]
        normal_names = self.star_normal[6]

        # 2. 按概率判定是否出UP
        rand = self.rand.pop()
        if up_names:  # 有UP武器时
            for idx, prob_acc in enumerate(up_probs):
                if rand < prob_acc:
                    return up_names[idx], 6, True  # 出UP武器，标记为True

        # 3. 未出UP则出6星通用武器
        return choice(normal_names), 6, False

    def _get_only_5star_weapon(self) -> Tuple[str, int]:
        """获取5星通用武器（最低优先级）

        Returns
        -------
        Tuple[str, int]
            返回一个元组，包含5星通用武器名称和星级（固定为5星）
        """
        return choice(self.star_normal[5]), 5

    def attempt(self, disable_guarantee: bool = False) -> List[GachaResult]:
        """武器卡池单次申领：8次UP保底仅生效一次 + 固定最后1抽替换 + 优先级UP>6星>5星

        Parameters
        ----------
        disable_guarantee : bool, optional
            参数用于禁用保底机制，主要用于模拟抽卡分布时使用，默认False（即启用保底）

        Returns
        -------
        List[GachaResult]
            返回抽卡结果列表，每个元素为一个GachaResult对象

        Examples
        --------
        >>> from core import WeaponGacha
        >>> weapon_gacha = WeaponGacha()
        >>> # 进行单次申领
        >>> results = weapon_gacha.attempt_once()
        >>> for i, result in enumerate(results):
        ...     print(f"第{i+1}抽：{result.name}，{result.star}星")
        """
        self.counters.total += 1
        results = []
        has_5star_plus = False  # 是否出 5 星及以上
        has_6star = False  # 是否出 6 星
        has_up = False  # 是否出 UP 武器
        is_6_guarantee = False  # 是否触发 6 星保底
        is_5_guarantee = False  # 是否触发 5 星保底
        # noinspection PyUnusedLocal
        is_up_guarantee = False  # 是否触发 UP 保底

        # 步骤 1：基础抽卡（按配置次数抽卡，记录抽卡结果）
        for _ in range(self.rule_config["apply_draws"]):
            rand = self.rand.pop()
            if rand < self.rule_config["base_prob"][6]:
                res, star = self._get_weapon_by_star(6)
                has_5star_plus = True
                has_6star = True
                self.counters.no_6star = 0  # 出6星重置6星保底计数
                if res == self.up_weapon_name:
                    self.counters.no_up = 0  # 出UP武器重置UP保底计数
                    has_up = True
                    self.counters.guarantee_used = (
                        True  # 出6星UP视同触发UP保底，永久失效
                    )
            elif (
                rand
                < self.rule_config["base_prob"][6] + self.rule_config["base_prob"][5]
            ):
                res, star = self._get_weapon_by_star(5)
                has_5star_plus = True
            else:
                res, star = self._get_weapon_by_star(4)
            quota = self.rule_config["quota_rule"][star]
            results.append(GachaResult(name=res, star=star, quota=quota))

        # 步骤2：保底判定 + 固定替换最后1抽（优先级UP>6星>5星，UP保底仅生效一次）
        replace_weapon = None
        replace_quota = 0
        # 优先级1：UP武器保底（最高）- 仅未使用过且触发条件满足时生效
        is_up_guarantee = (
            not self.counters.guarantee_used
            and not has_up
            and self.counters.no_up >= self.rule_config["up_guarantee_apply"] - 1
            and not disable_guarantee
        )
        if is_up_guarantee:
            replace_weapon, star = self._get_only_up_weapon()
            replace_quota = self.rule_config["quota_rule"][star]
            self.counters.guarantee_used = True  # 标记UP保底已使用，永久失效
            self.counters.no_up = 0
            self.counters.no_6star = 0  # 出UP必出6星，同步重置6星计数器
            has_6star = True
            has_up = True

        # 优先级2：6星武器保底（中）- 未触发UP保底时生效
        elif (
            not has_6star
            and self.counters.no_6star >= self.rule_config["guarantee_6star_apply"] - 1
            and not disable_guarantee
        ):
            replace_weapon, star, is_up = self._get_only_6star_weapon()
            replace_quota = self.rule_config["quota_rule"][star]
            self.counters.no_6star = 0
            has_6star = True
            is_6_guarantee = True
            if is_up:
                self.counters.no_up = 0  # 出6星UP武器时同步重置UP计数器
                has_up = True

        # 优先级3：5星武器保底（最低）- 未触发前两级保底时生效
        elif (
            not has_5star_plus
            and self.rule_config["per_apply_must_have"]
            and not disable_guarantee
        ):
            replace_weapon, star = self._get_only_5star_weapon()
            replace_quota = self.rule_config["quota_rule"][star]
            is_5_guarantee = True

        # 执行替换：固定替换最后1抽（有替换内容时）
        if replace_weapon:
            # noinspection PyUnboundLocalVariable
            results[-1] = GachaResult(
                name=replace_weapon,
                star=star,  # type: ignore
                quota=replace_quota,
                is_up_g=is_up_guarantee,
                is_6_g=is_6_guarantee,
                is_5_g=is_5_guarantee,
            )

        # 步骤3：更新计数器（未出对应武器则计数+1；UP保底已使用则不再累计UP计数）
        if not has_up and not self.counters.guarantee_used and not disable_guarantee:
            self.counters.no_up += 1
        if not has_6star and not disable_guarantee:
            self.counters.no_6star += 1

        return results

    def get_accumulated_reward(self) -> List[Tuple[str, int]]:
        """获取累计奖励

        根据累计申领次数，计算并返回可获得的累计奖励列表。

        Returns
        -------
        List[Tuple[str, int]]
            返回奖励列表，每个元素为(奖励名称, 数量)的元组

        Examples
        --------
        >>> from core import WeaponGacha
        >>> weapon_gacha = WeaponGacha()
        >>> # 进行多次申领
        >>> for _ in range(10):
        ...     weapon_gacha.attempt_once()
        >>> # 获取累计奖励
        >>> rewards = weapon_gacha.get_accumulated_reward()
        >>> print(f"累计奖励：{rewards}")
        """
        reward_counts = {}  # 统计各奖励的次数
        reward_config = self.rule_config["rewards"]
        cycle_step = reward_config.get("cycle", 8)
        start_count = reward_config.get("start", 10)

        if self.counters.total >= start_count:
            total_cycles = (self.counters.total - start_count) // cycle_step + 1
            for round_num in range(total_cycles):
                reward = (
                    reward_config["Type_A"]
                    if round_num % 2 == 0
                    else reward_config["Type_B"]
                )
                reward_counts[reward] = reward_counts.get(reward, 0) + 1

        # 转换为 (奖励, 次数) 的格式
        return [(reward, count) for reward, count in reward_counts.items()]
