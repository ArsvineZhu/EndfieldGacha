# -*- coding: utf-8 -*-
"""武器卡池逻辑。"""

from bisect import bisect_right
from random import Random
from typing import Dict, List, Tuple

from .config import GlobalConfigLoader
from .models import Counters, GachaResult
from .pool_utils import _normalize_star_pool
from .randomizer import BatchRandom


class WeaponGacha:
    """武器卡池类，负责武器卡池的抽卡逻辑和累计奖励逻辑，包含UP保底、6星保底、5星保底等机制

    该类实现了武器卡池的完整抽卡流程，包括单次申领（多次抽卡）、
    保底机制触发、累计奖励计算等功能。支持UP武器保底、6星保底和5星保底等多种机制。

    Examples
    --------
    >>> from gacha_core import WeaponGacha
    >>> # 创建武器卡池实例
    >>> weapon_gacha = WeaponGacha()
    >>> # 进行单次申领（通常为10连抽）
    >>> results = weapon_gacha.attempt()
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
        self._picker = Random(self.rand.seed)
        self.pool_data = self.config.get_pool_data("weapon")
        self.rule_config = self.config.get_rule_config("weapon")
        self._precache_data()
        self.counters = Counters()  # 使用Counters数据类管理计数器

    def _precache_data(self):
        """预缓存UP/普通武器数据

        从配置文件中加载并预处理武器数据，包括：
        - UP / 普通武器池拆分
        - UP 概率累积阈值
        - 运行时使用的基础概率与保底参数
        """
        # noinspection DuplicatedCode
        self.star_up_prob: Dict[int, Tuple[List[str], List[float]]] = {}
        self.star_normal: Dict[int, List[str]] = {}

        for star in (6, 5, 4):
            up_names, up_probs, normal_names = _normalize_star_pool(
                self.pool_data, star, "武器池"
            )
            self.star_up_prob[star] = (up_names, up_probs)
            self.star_normal[star] = normal_names

        self.up_weapon_name = self.rule_config["up_weapon_name"]
        self._up_weapon_names = self.star_up_prob[6][0]
        self.base_6star_prob = float(self.rule_config["base_prob"][6])
        self.base_65star_threshold = self.base_6star_prob + float(self.rule_config["base_prob"][5])
        self.apply_draws = self.rule_config["apply_draws"]
        self.quota_rule = self.rule_config["quota_rule"]
        self.guarantee_6star_apply = self.rule_config["guarantee_6star_apply"]
        self.up_guarantee_apply = self.rule_config["up_guarantee_apply"]
        self.per_apply_must_have = self.rule_config["per_apply_must_have"]
        if self._up_weapon_names and self.up_weapon_name not in self._up_weapon_names:
            raise ValueError("武器池6星 UP 目标不存在于卡池配置中")
        if not self._up_weapon_names and self.up_weapon_name not in ("", None):
            raise ValueError("武器池没有 6 星 UP 目标时，up_weapon_name 必须为空")

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
            idx = bisect_right(up_probs, self.rand.pop_float())
            if idx < len(up_names):
                return up_names[idx], star
            if not normal_names:
                return up_names[-1], star
        return self._picker.choice(normal_names), star

    def _get_only_up_weapon(self) -> Tuple[str, int]:
        """获取纯UP武器（6星，最高优先级）

        Returns
        -------
        Tuple[str, int]
            返回一个元组，包含UP武器名称和星级（固定为6星）
        """
        if not self._up_weapon_names:
            raise ValueError("当前武器池不存在可用的 UP 目标")
        return self._picker.choice(self._up_weapon_names), 6

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
        if up_names:  # 有UP武器时
            idx = bisect_right(up_probs, self.rand.pop_float())
            if idx < len(up_names):
                return up_names[idx], 6, True  # 出UP武器，标记为True
            if not normal_names:
                return up_names[-1], 6, True

        # 3. 未出UP则出6星通用武器
        return self._picker.choice(normal_names), 6, False

    def _get_only_5star_weapon(self) -> Tuple[str, int]:
        """获取5星通用武器（最低优先级）

        Returns
        -------
        Tuple[str, int]
            返回一个元组，包含5星通用武器名称和星级（固定为5星）
        """
        return self._picker.choice(self.star_normal[5]), 5

    def attempt(self, disable_guarantee: bool = False) -> List[GachaResult]:
        """武器卡池单次申领：8次UP保底仅生效一次 + 固定最后1抽替换 + 优先级UP>6星>5星

        Parameters
        ----------
        disable_guarantee : bool, optional
            用于禁用保底机制，主要服务于分布模拟。
            启用后本次申领不会修改 no_6star / no_up / guarantee_used，
            仅保留 total 计数的递增行为。

        Returns
        -------
        List[GachaResult]
            返回抽卡结果列表，每个元素为一个GachaResult对象

        Examples
        --------
        >>> from gacha_core import WeaponGacha
        >>> weapon_gacha = WeaponGacha()
        >>> # 进行单次申领
        >>> results = weapon_gacha.attempt()
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

        next_no_6star = self.counters.no_6star
        next_no_up = self.counters.no_up
        next_guarantee_used = self.counters.guarantee_used

        for _ in range(self.apply_draws):
            rand = self.rand.pop_float()
            if rand < self.base_6star_prob:
                res, star = self._get_weapon_by_star(6)
                has_5star_plus = True
                has_6star = True
                if not disable_guarantee:
                    next_no_6star = 0
                if res in self._up_weapon_names:
                    has_up = True
                    if not disable_guarantee:
                        next_no_up = 0
                        next_guarantee_used = True
            elif rand < self.base_65star_threshold:
                res, star = self._get_weapon_by_star(5)
                has_5star_plus = True
            else:
                res, star = self._get_weapon_by_star(4)
            quota = self.quota_rule[star]
            results.append(GachaResult(name=res, star=star, quota=quota))

        replace_weapon = None
        replace_quota = 0
        is_up_guarantee = (
            not disable_guarantee
            and bool(self._up_weapon_names)
            and not self.counters.guarantee_used
            and not has_up
            and self.counters.no_up >= self.up_guarantee_apply - 1
        )
        if is_up_guarantee:
            replace_weapon, star = self._get_only_up_weapon()
            replace_quota = self.quota_rule[star]
            next_guarantee_used = True
            next_no_up = 0
            next_no_6star = 0
            has_6star = True
            has_up = True

        elif (
            not disable_guarantee
            and not has_6star
            and self.counters.no_6star >= self.guarantee_6star_apply - 1
        ):
            replace_weapon, star, is_up = self._get_only_6star_weapon()
            replace_quota = self.quota_rule[star]
            next_no_6star = 0
            has_6star = True
            is_6_guarantee = True
            if is_up:
                next_no_up = 0
                has_up = True

        elif (
            not disable_guarantee
            and not has_5star_plus
            and self.per_apply_must_have
        ):
            replace_weapon, star = self._get_only_5star_weapon()
            replace_quota = self.quota_rule[star]
            is_5_guarantee = True

        if replace_weapon:
            results[-1] = GachaResult(
                name=replace_weapon,
                star=star,  # type: ignore[name-defined]
                quota=replace_quota,
                is_up_g=is_up_guarantee,
                is_6_g=is_6_guarantee,
                is_5_g=is_5_guarantee,
            )

        if not disable_guarantee:
            if not has_up and not next_guarantee_used:
                next_no_up = self.counters.no_up + 1
            if not has_6star:
                next_no_6star = self.counters.no_6star + 1
            self.counters.no_up = next_no_up
            self.counters.no_6star = next_no_6star
            self.counters.guarantee_used = next_guarantee_used

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
        >>> from gacha_core import WeaponGacha
        >>> weapon_gacha = WeaponGacha()
        >>> # 进行多次申领
        >>> for _ in range(10):
        ...     weapon_gacha.attempt()
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

