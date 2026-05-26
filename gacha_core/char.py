# -*- coding: utf-8 -*-
"""角色卡池逻辑。"""

from bisect import bisect_right
from random import Random
from typing import Dict, List, Tuple

from .config import GlobalConfigLoader
from .models import Counters, GachaResult
from .pool_utils import _normalize_star_pool
from .randomizer import BatchRandom


class CharGacha:
    """角色卡池类，负责角色卡池的抽卡逻辑和累计奖励逻辑，包含UP保底、6星保底、5星保底等机制

    该类实现了角色卡池的完整抽卡流程，包括概率计算、保底机制触发、
    累计奖励计算等功能。支持UP角色保底、6星保底和5星保底等多种机制。

    Examples
    --------
    >>> from gacha_core import CharGacha
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
        self.rand = BatchRandom(seed, size=size)
        self._picker = Random(self.rand.seed)
        # 加载配置
        self.pool_data = self.config.get_pool_data("char")
        self.rule_config = self.config.get_rule_config("char")
        # 预缓存数据
        self._precache_data()
        # 初始化计数器
        self.counters = Counters()

    def _precache_data(self):
        """预缓存UP/普通干员数据

        从配置文件中加载并预处理干员数据，包括：
        - UP / 普通干员池拆分
        - UP 概率累积阈值
        - 运行时使用的基础概率与软保底参数
        """
        # noinspection DuplicatedCode
        self.star_up_prob: Dict[int, Tuple[List[str], List[float]]] = {}
        self.star_normal: Dict[int, List[str]] = {}

        for star in (6, 5, 4):
            up_names, up_probs, normal_names = _normalize_star_pool(
                self.pool_data, star, "角色池"
            )
            self.star_up_prob[star] = (up_names, up_probs)
            self.star_normal[star] = normal_names

        self.base_6star_prob = float(self.rule_config["base_prob"][6])
        self.base_5star_prob = float(self.rule_config["base_prob"][5])
        self.base_4star_prob = float(self.rule_config["base_prob"][4])
        total_base_prob = self.base_5star_prob + self.base_4star_prob
        self.base_5star_ratio = self.base_5star_prob / total_base_prob
        self.prob_increase = float(self.rule_config["prob_increase"])
        self.prob_upper = float(self.rule_config["prob_upper_limit"])
        self.up_char_name = self.rule_config["up_char_name"]
        self.six_star_increase_start = self.rule_config["6star_prob_increase_start"]
        self.guarantee_5star_plus_draw = self.rule_config["guarantee_5star_plus_draw"]
        self.guarantee_6star_draw = self.rule_config["guarantee_6star_draw"]
        self.up_guarantee_draw = self.rule_config["up_guarantee_draw"]
        self.quota_rule = self.rule_config["quota_rule"]
        self._up_char_names = self.star_up_prob[6][0]
        if self._up_char_names and self.up_char_name not in self._up_char_names:
            raise ValueError("角色池6星 UP 目标不存在于卡池配置中")
        if not self._up_char_names and self.up_char_name not in ("", None):
            raise ValueError("角色池没有 6 星 UP 目标时，up_char_name 必须为空")

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
            idx = bisect_right(up_probs, self.rand.pop_float())
            if idx < len(up_names):
                return up_names[idx], star, True
            if not normal_names:
                return up_names[-1], star, True
        return self._picker.choice(normal_names), star, False

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
        if not self.star_up_prob[star][0]:
            raise ValueError("当前角色池不存在可用的 UP 目标")
        return self._picker.choice(self.star_up_prob[star][0]), star

    def attempt(self, disable_guarantee: bool = False) -> GachaResult:
        """
        角色卡池单次抽卡，包含UP保底、6星保底、5星保底等机制

        Parameters
        ----------
        disable_guarantee : bool, optional
            用于禁用保底机制，主要服务于分布模拟。
            启用后本次抽样不会修改 no_6star / no_5star_plus / no_up /
            guarantee_used，仅保留 total 计数的递增行为。

        Returns
        -------
        GachaResult
            GachaResult 对象，包含抽卡结果和保底触发标记

        Examples
        --------
        >>> from gacha_core import CharGacha
        >>> char_gacha = CharGacha()
        >>> # 正常抽卡（启用保底）
        >>> result1 = char_gacha.attempt()
        >>> print(f"抽卡结果：{result1.name}，{result1.star}星")
        >>> # 禁用保底抽卡（用于模拟）
        >>> result2 = char_gacha.attempt(disable_guarantee=True)
        """
        self.counters.total += 1
        effective_no_6star = 0 if disable_guarantee else self.counters.no_6star + 1
        effective_no_5star_plus = 0 if disable_guarantee else self.counters.no_5star_plus + 1
        effective_no_up = 0 if disable_guarantee else self.counters.no_up + 1
        next_no_6star = self.counters.no_6star
        next_no_5star_plus = self.counters.no_5star_plus
        next_no_up = self.counters.no_up
        next_guarantee_used = self.counters.guarantee_used

        current_6star_prob = self.base_6star_prob
        if effective_no_6star > self.six_star_increase_start:
            current_6star_prob += (
                effective_no_6star - self.six_star_increase_start
            ) * self.prob_increase
            current_6star_prob = min(current_6star_prob, self.prob_upper)

        if (
            not disable_guarantee
            and self._up_char_names
            and not self.counters.guarantee_used
            and effective_no_up >= self.up_guarantee_draw
        ):
            result, star_int = self._get_up_char()
            self.counters.no_up = 0
            self.counters.no_6star = 0
            self.counters.no_5star_plus = 0
            self.counters.guarantee_used = True
            quota = self.quota_rule[star_int]
            return GachaResult(
                name=result, star=star_int, quota=quota, is_up_g=True
            )

        if (
            not disable_guarantee
            and effective_no_6star >= self.guarantee_6star_draw
        ):
            result, star_int, is_up = self._get_char_by_star(6)
            self.counters.no_6star = 0
            self.counters.no_5star_plus = 0
            self.counters.no_up = 0 if is_up else effective_no_up
            quota = self.quota_rule[6]
            return GachaResult(
                name=result, star=star_int, quota=quota, is_6_g=True
            )

        is_5star_guarantee = (
            not disable_guarantee
            and effective_no_5star_plus >= self.guarantee_5star_plus_draw
        )
        rand = self.rand.pop_float()

        if is_5star_guarantee:
            if rand < current_6star_prob:
                result, star_int, is_up = self._get_char_by_star(6)
                if not disable_guarantee:
                    next_no_6star = 0
                    next_no_5star_plus = 0
                    next_no_up = effective_no_up
                    if is_up:
                        next_no_up = 0
            else:
                result, star_int, is_up = self._get_char_by_star(5)
                if not disable_guarantee:
                    next_no_6star = effective_no_6star
                    next_no_5star_plus = 0
                    next_no_up = effective_no_up
            if not disable_guarantee:
                self.counters.no_6star = next_no_6star
                self.counters.no_5star_plus = next_no_5star_plus
                self.counters.no_up = next_no_up
                self.counters.guarantee_used = next_guarantee_used
            quota = self.quota_rule[star_int]
            return GachaResult(
                name=result, star=star_int, quota=quota, is_5_g=True
            )

        remaining_prob = max(0.0, 1.0 - current_6star_prob)
        adjusted_5star_prob = remaining_prob * self.base_5star_ratio if remaining_prob > 0 else 0.0

        if rand < current_6star_prob:
            result, star_int, is_up = self._get_char_by_star(6)
            if not disable_guarantee:
                next_no_6star = 0
                next_no_5star_plus = 0
                next_no_up = effective_no_up
                if is_up:
                    next_no_up = 0
                    next_guarantee_used = True
        elif rand < current_6star_prob + adjusted_5star_prob:
            result, star_int, is_up = self._get_char_by_star(5)
            if not disable_guarantee:
                next_no_6star = effective_no_6star
                next_no_5star_plus = 0
                next_no_up = effective_no_up
        else:
            result, star_int, is_up = self._get_char_by_star(4)
            if not disable_guarantee:
                next_no_6star = effective_no_6star
                next_no_5star_plus = effective_no_5star_plus
                next_no_up = effective_no_up

        if not disable_guarantee:
            self.counters.no_6star = next_no_6star
            self.counters.no_5star_plus = next_no_5star_plus
            self.counters.no_up = next_no_up
            self.counters.guarantee_used = next_guarantee_used
        quota = self.quota_rule[star_int]
        return GachaResult(name=result, star=star_int, quota=quota)

    def get_accumulated_reward(self) -> List[Tuple[str, int]]:
        """获取累计奖励

        根据累计抽卡次数，计算并返回可获得的累计奖励列表。

        Returns
        -------
        List[Tuple[str, int]]
            返回奖励列表，每个元素为(奖励名称, 数量)的元组

        Examples
        --------
        >>> from gacha_core import CharGacha
        >>> char_gacha = CharGacha()
        >>> # 进行多次抽卡
        >>> for _ in range(30):
        ...     char_gacha.attempt()
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

