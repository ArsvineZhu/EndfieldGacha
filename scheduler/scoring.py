# -*- coding: utf-8 -*-
"""资源与科学评分系统。

提供抽卡资源管理和综合评分功能，支持三维评分体系：
- 运气评分 (0-45分)：基于抽卡结果的概率偏离度
- 保有评分 (0-35分)：基于资源保有率
- 目标评分 (0-20分)：基于目标完成情况

评分等级：S(90-100)、A(80-89)、B(70-79)、C(60-69)、D(50-59)、E(0-49)
"""
from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class Resource:
    """抽卡所需资源的归一化描述。

    Attributes
    ----------
    chartered_permits : int
        特许寻访凭证数量，角色池单抽消耗1，默认0。
    oroberyl : int
        嵌晶玉数量，角色池单抽消耗75，默认0。
    arsenal_tickets : int
        武库配额数量，武器池申领消耗1980，默认0。
    origeometry : int
        衍质源石数量，可兑换为嵌晶玉(1:75)或武库配额(1:25)，默认0。

    Notes
    -----
    - 资源兑换比例：1源石 = 75嵌晶玉 = 25武库配额
    - 角色池单抽：1特许寻访凭证 或 75嵌晶玉
    - 武器池申领：1980武库配额
    """

    chartered_permits: int = 0
    oroberyl: int = 0
    arsenal_tickets: int = 0
    origeometry: int = 0


class ScoringSystem:
    """抽卡结果综合评分系统（0–100 分百分制）。

    采用三维评分体系，综合评估抽卡结果的质量：
    - 运气评分 (0-45分)：评估抽卡结果的概率偏离度
    - 效率评分 (0-35分)：评估资源使用效率
    - 目标评分 (0-20分)：评估目标完成情况

    Attributes
    ----------
    UP_SIX_STAR_RATIO : float
        UP角色与6星角色的权重比，默认2.0。
    LUCK_MAX : float
        运气评分最大值，默认45.0。
    RESOURCE_MAX : float
        效率评分最大值，默认35.0。
    ACHIEVEMENT_MAX : float
        目标评分最大值，默认20.0。
    GRADE_THRESHOLDS : dict
        评分等级阈值，包含等级、名称和显示样式。

    Examples
    --------
    >>> from scheduler import ScoringSystem
    >>> score = ScoringSystem.calculate_score(
    ...     total_draws=120,
    ...     six_stars=2,
    ...     up_chars=1,
    ...     resource_left=5000,
    ...     complete=True,
    ...     banners_count=5
    ... )
    >>> score['total_score']
    85.3
    >>> score['grade']
    'A'

    Notes
    -----
    - 运气评分：基于UP角色和6星角色的实际获得率与期望率的比值
    - 保有评分：基于实际抽数与总资源（抽数+剩余资源）的比值
    - 目标评分：基于任务完成度、UP角色数和6星角色数
    """

    GRADE_THRESHOLDS: Dict[Tuple[float, float], Tuple[str, str, str]] = {
        (100 / 6 * 5, 100): ("S", "极佳", "bold red"),
        (100 / 6 * 4, 100 / 6 * 5): ("A", "优秀", "bold yellow"),
        (100 / 6 * 3, 100 / 6 * 4): ("B", "良好", "bold green"),
        (100 / 6 * 2, 100 / 6 * 3): ("C", "一般", "bold blue"),
        (100 / 6, 100 / 6 * 2): ("D", "较差", "bold magenta"),
        (0, 100 / 6): ("E", "失败", "bold white"),
    }

    UP_SIX_STAR_RATIO = 2.0
    LUCK_MAX = 45.0
    RESOURCE_MAX = 35.0
    ACHIEVEMENT_MAX = 20.0

    @staticmethod
    def calculate_score(
        total_draws: int,
        six_stars: int,
        up_chars: int,
        resource_left: int,
        complete: bool,
        banners_count: int = 5,
    ) -> Dict[str, Any]:
        """计算抽卡结果的综合评分。

        Parameters
        ----------
        total_draws : int
            总抽数（实际消耗的资源换算的抽数）。
        six_stars : int
            获得的6星角色数量。
        up_chars : int
            获得的UP角色数量。
        resource_left : int
            剩余资源（换算为抽数）。
        complete : bool
            是否完成所有计划任务。
        banners_count : int, optional
            卡池数量，用于目标评分计算，默认5。

        Returns
        -------
        dict
            包含各项评分和等级的字典：
            - total_score: float - 总评分 (0-100)
            - luck_score: float - 运气评分 (0-60)
            - storage_score: float - 效率评分 (0-20)
            - achievement_score: float - 目标评分 (0-20)
            - grade: str - 等级字母 (S/A/B/C/D/E)
            - grade_name: str - 等级中文名称
            - grade_style: str - Rich库显示样式

        Notes
        -----
        - 资源换算：所有资源统一换算为等效抽数
        - 期望概率：UP角色0.87%，6星角色1.74%
        - 评分算法：分段函数，不同概率区间有不同的得分系数
        """
        luck_score = ScoringSystem._calculate_luck_score(
            total_draws + resource_left, six_stars, up_chars
        )
        storage_score = ScoringSystem._calculate_storage_score(
            total_draws, resource_left, complete
        )
        achievement_score = ScoringSystem._calculate_achievement_score(
            six_stars, up_chars, complete, banners_count
        )

        total_score = luck_score + storage_score + achievement_score
        total_score = max(0, min(100, total_score))

        grade, grade_name, grade_style = ScoringSystem.get_grade(total_score)

        return {
            "total_score": round(total_score, 1),
            "luck_score": round(luck_score, 1),
            "storage_score": round(storage_score, 1),
            "achievement_score": round(achievement_score, 1),
            "grade": grade,
            "grade_name": grade_name,
            "grade_style": grade_style,
        }

    @staticmethod
    def _calculate_luck_score(total_draws: int, six_stars: int, up_chars: int) -> float:
        MAX = ScoringSystem.LUCK_MAX
        if total_draws == 0:
            return MAX * 0.6

        up_ratio = up_chars / (total_draws * 0.0087)
        six_ratio = six_stars / (total_draws * 0.0174)

        total_weight = ScoringSystem.UP_SIX_STAR_RATIO + 1.0

        def calc_score(ratio: float, weight: float) -> float:
            w = weight / total_weight
            if ratio <= 0.6:
                return ratio * MAX * w
            elif ratio <= 1.0:
                return (0.6 + (ratio - 0.6) / 0.4 * 0.3) * MAX * w
            else:
                return min(MAX, (0.9 + (ratio - 1.0) * 0.1) * MAX) * w

        score = calc_score(up_ratio, ScoringSystem.UP_SIX_STAR_RATIO) + calc_score(
            six_ratio, 1.0
        )
        return max(0, min(MAX, score))

    @staticmethod
    def _calculate_storage_score(
        total_draws: int, resource_left: int, complete: bool
    ) -> float:
        base_score = 35 if complete else 20

        if total_draws > 0:
            storage_ratio = min(1.0, total_draws / (total_draws + resource_left))
            storage_bonus = -storage_ratio * 20
        else:
            storage_bonus = -20

        return max(0, min(ScoringSystem.RESOURCE_MAX, base_score + storage_bonus))

    @staticmethod
    def _calculate_achievement_score(
        six_stars: int, up_chars: int, complete: bool, banners_count: int
    ) -> float:
        score = 0.0

        if complete:
            score += 8.0

        up_score = min(8.0, up_chars * 4.0)
        score += up_score

        six_star_score = min(4.0, six_stars * 2.0)
        score += six_star_score

        return min(ScoringSystem.ACHIEVEMENT_MAX, score)

    @staticmethod
    def get_grade(score: float) -> Tuple[str, str, str]:
        """根据评分获取等级信息。

        Parameters
        ----------
        score : float
            总评分 (0-100)。

        Returns
        -------
        tuple
            (等级字母, 等级中文名称, Rich库显示样式)

        Notes
        -----
        等级划分：
        - S级 (90-100): 极佳
        - A级 (80-89): 优秀
        - B级 (70-79): 良好
        - C级 (60-69): 一般
        - D级 (50-59): 较差
        - E级 (0-49): 失败
        """
        for (low, high), (grade, name, style) in ScoringSystem.GRADE_THRESHOLDS.items():
            if low <= score <= high:
                return grade, name, style
        return "E", "失败", "bold white"


__all__ = ["Resource", "ScoringSystem"]
