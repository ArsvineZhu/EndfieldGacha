# -*- coding: utf-8 -*-
"""资源与科学评分系统。

提供抽卡资源管理和综合评分功能，采用四维评分体系，严格遵循《策略评分系统设计方案》：
- 目标达成效用 (0-40分)：评估策略达成目标的能力，使用3:2:1价值权重
- 资源利用效率 (0-20分)：评估资源使用的经济性
- 风险控制能力 (0-25分)：评估策略的抗风险能力
- 策略灵活性 (0-15分)：评估策略的调整潜力

支持双模式评分：
- 相对模式：基于策略组内相对表现评分，适合同组策略对比
- 绝对模式：基于绝对阈值评分，适合跨组策略评估

评分等级：S级(≥83.33)、A级(66.67-83.32)、B级(50.00-66.66)、C级(33.33-49.99)、D级(16.67-33.32)、E级(<16.67)
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple, List, Optional
import numpy as np


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


@dataclass
class NativeStatistics:
    """原生统计量数据结构。

    包含策略评分系统所需的所有原生统计量，分为四类：
    1. 分级目标达成类
    2. 资源消耗与留存类
    3. 风险控制类
    4. 策略灵活性类

    Attributes
    ----------
    # 分级目标达成类
    p_i_t : List[float]
        分级目标达成概率 P_{i,t}(S)，各星级目标达成概率列表。
    p_t : float
        总目标达成概率 P_t(S)。
    p_core : float
        核心目标达成概率 P_core(S)。
    u_raw : float
        原始效用值 U_raw(S)。

    # 资源消耗与留存类
    e_k_total : float
        期望总抽数 E[K_total(S)]。
    e_w_total : float
        期望总资源消耗 E[W_total(S)]。
    e_r_remain : float
        期望剩余资源 E[R_remain(S)]。

    # 风险控制类
    p_down : float
        向下风险概率 P_down(S)。
    cv : float
        变异系数 CV(S)。
    p_zero : float
        零收益概率 P_zero(S)。

    # 策略灵活性类
    e_r_flex : float
        期望灵活性资源 E[R_flex(S)]。

    Notes
    -----
    所有统计量均为浮点数，表示期望值或概率值。
    """

    # 分级目标达成类
    p_i_t: List[float]
    p_t: float
    p_core: float
    u_raw: float

    # 资源消耗与留存类
    e_k_total: float
    e_w_total: float
    e_r_remain: float

    # 风险控制类
    p_down: float
    cv: float
    p_zero: float

    # 策略灵活性类
    e_r_flex: float


class ScoringSystem:
    """抽卡结果综合评分系统（0–100 分百分制）。

    采用四维评分体系，严格遵循《策略评分系统设计方案》：
    - 目标达成效用 (0-40分)：评估策略达成目标的能力，使用3:2:1价值权重
    - 资源利用效率 (0-20分)：评估资源使用的经济性
    - 风险控制能力 (0-25分)：评估策略的抗风险能力
    - 策略灵活性 (0-15分)：评估策略的调整潜力

    支持双模式评分：
    - 相对模式：基于策略组内相对表现评分，适合同组策略对比
    - 绝对模式：基于绝对阈值评分，适合跨组策略评估

    Attributes
    ----------
    GRADE_THRESHOLDS : dict
        评分等级阈值，包含等级、名称和显示样式。
    DEFAULT_WEIGHTS : dict
        四维评分权重默认配置。

    Notes
    -----
    - 四维评分权重：目标达成效用40%、资源利用效率20%、风险控制能力25%、策略灵活性15%
    - 评分等级：S级(≥83.33)、A级(66.67-83.32)、B级(50.00-66.66)、C级(33.33-49.99)、D级(16.67-33.32)、E级(<16.67)
    - 3:2:1价值权重：当期UP(3)、往期UP(2)、常驻6星(1)
    """

    GRADE_THRESHOLDS: Dict[Tuple[float, float], Tuple[str, str, str]] = {
        (83.33, 100.0): ("S", "极佳", "bold red"),  # ≥83.33分
        (66.67, 83.33): ("A", "优秀", "bold yellow"),  # 66.67-83.32分
        (50.00, 66.67): ("B", "良好", "bold green"),  # 50.00-66.66分
        (33.33, 50.00): ("C", "一般", "bold blue"),  # 33.33-49.99分
        (16.67, 33.33): ("D", "较差", "bold magenta"),  # 16.67-33.32分
        (0.00, 16.67): ("E", "失败", "bold white"),  # <16.67分
    }

    # 评分系统权重配置
    DEFAULT_WEIGHTS = {
        "dimension_weights": {
            "u": 0.4,
            "e": 0.2,
            "r": 0.25,
            "f": 0.15,
        },  # U:40%, E:20%, R:25%, F:15%
        "star_weights": {
            "current_up": 3.0,
            "past_up": 2.0,
            "permanent": 1.0,
        },  # 3:2:1价值权重
    }

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

    @staticmethod
    def calculate_raw_statistics(
        strategy_results: List[Dict[str, Any]],
    ) -> NativeStatistics:
        """计算策略结果的所有原生统计量。

        Parameters
        ----------
        strategy_results : List[Dict[str, Any]]
            策略执行结果列表，包含多次模拟的抽卡结果。每个字典应包含以下字段：
            - draws: int - 本次模拟的总抽数
            - six_stars: int - 本次模拟获得的6星数量
            - up_chars: int - 本次模拟获得的UP角色数量
            - current_up: int - 本次模拟获得的当期UP数量（分级1）
            - past_up: int - 本次模拟获得的往期UP数量（分级2）
            - permanent: int - 本次模拟获得的常驻数量（分级3）
            - resource_left: int - 本次模拟剩余资源
            - flex_resource: int - 本次模拟可灵活调配资源
            - goals_achieved: List[bool] - 本次模拟各目标达成情况

        Returns
        -------
        NativeStatistics
             包含所有原生统计量的数据对象。

        Notes
        -----
        此方法计算四类原生统计量：
        1. 分级目标达成类：P_{i,t}(S), P_t(S), P_core(S), U_raw(S)
        2. 资源消耗与留存类：E[K_total(S)], E[W_total(S)], E[R_remain(S)]
        3. 风险控制类：P_down(S), CV(S), P_zero(S)
        4. 策略灵活性类：E[R_flex(S)]

        公式严格按照《策略评分系统设计方案》第四部分实现。
        """
        # 输入验证
        if not strategy_results:
            raise ValueError("strategy_results列表不能为空")

        if not isinstance(strategy_results, list):
            raise TypeError("strategy_results必须是列表类型")

        for i, result in enumerate(strategy_results):
            if not isinstance(result, dict):
                raise TypeError(f"strategy_results[{i}]必须是字典类型")

        # 提取数据
        N = len(strategy_results)  # 模拟次数

        # 初始化统计量
        p_i_t = []
        p_t = 0.0
        p_core = 0.0
        u_raw = 0.0

        e_k_total = 0.0
        e_w_total = 0.0
        e_r_remain = 0.0

        p_down = 0.0
        cv = 0.0
        p_zero = 0.0

        e_r_flex = 0.0

        # ==================== 1. 分级目标达成类统计量 ====================

        # 提取各分级目标达成数据
        current_up_list = [result.get("current_up", 0) for result in strategy_results]
        past_up_list = [result.get("past_up", 0) for result in strategy_results]
        permanent_list = [result.get("permanent", 0) for result in strategy_results]

        # 计算分级目标达成概率 P_i_t(S)
        # P_1(S)：当期UP达成概率（分级1）
        # 公式：P_1(S) = (当期UP > 0 的模拟次数) / N
        p1 = sum(1 for x in current_up_list if x > 0) / N if N > 0 else 0.0

        # P_2(S)：往期UP达成概率（分级2）
        # 公式：P_2(S) = (往期UP > 0 的模拟次数) / N
        p2 = sum(1 for x in past_up_list if x > 0) / N if N > 0 else 0.0

        # P_3(S)：常驻达成概率（分级3）
        # 公式：P_3(S) = (常驻 > 0 的模拟次数) / N
        p3 = sum(1 for x in permanent_list if x > 0) / N if N > 0 else 0.0

        p_i_t = [p1, p2, p3]

        # 计算总目标达成概率 P_t(S)
        # 公式：P_t(S) = α₁·P₁(S) + α₂·P₂(S) + α₃·P₃(S)
        # 使用3:2:1权重进行归一化：α1=0.5, α2≈0.333, α3≈0.167
        alpha1 = 0.5  # 3/(3+2+1)
        alpha2 = 1.0 / 3.0  # 2/(3+2+1)
        alpha3 = 1.0 / 6.0  # 1/(3+2+1)
        p_t = alpha1 * p1 + alpha2 * p2 + alpha3 * p3

        # 计算核心目标达成概率 P_core(S)
        # 定义：核心目标为当期UP（分级1）
        # 公式：P_core(S) = P_1(S)
        p_core = p1

        # 计算全目标加权达成总分 U_raw(S)
        # 公式：U_raw(S) = α₁·P₁(S) + α₂·P₂(S) + α₃·P₃(S)
        # 使用3:2:1权重进行归一化：α1=0.5, α2≈0.333, α3≈0.167
        alpha1 = 0.5  # 3/(3+2+1)
        alpha2 = 1.0 / 3.0  # 2/(3+2+1)
        alpha3 = 1.0 / 6.0  # 1/(3+2+1)
        u_raw = alpha1 * p1 + alpha2 * p2 + alpha3 * p3

        # ==================== 2. 资源消耗与留存类统计量 ====================

        # 提取资源相关数据
        draws_list = [result.get("draws", 0) for result in strategy_results]
        resource_left_list = [
            result.get("resource_left", 0) for result in strategy_results
        ]

        # 计算期望总抽数 E[K_total(S)]
        # 公式：E[K_total(S)] = (Σ_{j=1}^N K_total,j(S)) / N
        e_k_total = float(np.mean(draws_list)) if draws_list else 0.0

        # 计算期望总资源消耗 E[W_total(S)]
        # 这里简化为总抽数作为资源消耗的度量
        e_w_total = e_k_total

        # 计算期望剩余资源 E[R_remain(S)]
        # 公式：E[R_remain(S)] = (Σ_{j=1}^N R_remain,j(S)) / N
        e_r_remain = float(np.mean(resource_left_list)) if resource_left_list else 0.0

        # ==================== 3. 风险控制类统计量 ====================

        # 计算核心目标下行风险概率 P_down(S)
        # 公式：P_down(S) = 1 - P_core(S)
        p_down = 1.0 - p_core

        # 计算目标达成数变异系数 CV(S)
        # 公式：CV(S) = σ(S) / μ(S)
        # 子公式：
        #   μ(S) = (Σ_{j=1}^N M_j(S)) / N  # 达成目标数期望
        #   σ(S) = sqrt(Σ_{j=1}^N (M_j(S) - μ(S))² / N)  # 达成目标数标准差
        # 其中 M_j(S) = 当期UP>0 + 往期UP>0 + 常驻>0
        achieved_counts = []
        for result in strategy_results:
            current = 1 if result.get("current_up", 0) > 0 else 0
            past = 1 if result.get("past_up", 0) > 0 else 0
            perm = 1 if result.get("permanent", 0) > 0 else 0
            achieved_counts.append(current + past + perm)

        if achieved_counts:
            mu = float(np.mean(achieved_counts))  # μ(S)
            sigma = float(np.std(achieved_counts, ddof=0))  # σ(S)，总体标准差

            # 计算变异系数，处理除以0的情况
            if mu > 0:
                cv = sigma / mu
            else:
                cv = 0.0  # 如果期望为0，变异系数为0

        # 计算全目标未达成概率 P_zero(S)
        # 公式：P_zero(S) = (所有目标均未达成的模拟次数) / N
        # 所有目标均未达成：当期UP=0 且 往期UP=0 且 常驻=0
        zero_count = 0
        for result in strategy_results:
            current = result.get("current_up", 0)
            past = result.get("past_up", 0)
            perm = result.get("permanent", 0)
            if current == 0 and past == 0 and perm == 0:
                zero_count += 1

        p_zero = zero_count / N if N > 0 else 0.0

        # ==================== 4. 策略灵活性类统计量 ====================

        # 提取灵活资源数据
        flex_resource_list = [
            result.get("flex_resource", 0) for result in strategy_results
        ]

        # 计算期望灵活性资源 E[R_flex(S)]
        # 公式：E[R_flex(S)] = (Σ_{j=1}^N R_flex,j(S)) / N
        e_r_flex = float(np.mean(flex_resource_list)) if flex_resource_list else 0.0

        # 创建并返回NativeStatistics对象
        return NativeStatistics(
            p_i_t=p_i_t,
            p_t=p_t,
            p_core=p_core,
            u_raw=u_raw,
            e_k_total=e_k_total,
            e_w_total=e_w_total,
            e_r_remain=e_r_remain,
            p_down=p_down,
            cv=cv,
            p_zero=p_zero,
            e_r_flex=e_r_flex,
        )

    @staticmethod
    def calculate_comprehensive_score(
        raw_stats_list: List[NativeStatistics],
        mode: str = "relative",
        weights: Optional[Dict[str, Dict[str, float]]] = None,
        k_total: float = 1000.0,
    ) -> List[Dict[str, Any]]:
        """基于原生统计量计算综合评分（新评分系统）。

        支持两种模式：
        - 相对模式：基于统计量相对值计算评分（需要组内最大值）
        - 绝对模式：基于统计量绝对值计算评分

        Parameters
        ----------
        raw_stats_list : List[NativeStatistics]
            原生统计量数据对象列表，支持同时处理多个策略。
        mode : str, optional
            评分模式，可选"relative"或"absolute"，默认"relative"。
        weights : Optional[Dict[str, Dict[str, float]]], optional
            自定义权重配置，包含维度权重和星级权重。
        k_total : float, optional
            初始总资源折算标准抽数，用于绝对模式，默认1000.0。

        Returns
        -------
        List[Dict[str, Any]]
            包含每个策略四维评分和综合评分的字典列表，每个字典包含：
            - u_score: float - 目标达成效用评分 (0-1)
            - e_score: float - 资源利用效率评分 (0-1)
            - r_score: float - 风险控制能力评分 (0-1)
            - f_score: float - 策略灵活性评分 (0-1)
            - total_score: float - 综合评分 (0-100)
            - grade: str - 等级字母 (S/A/B/C/D/E)
            - grade_name: str - 等级中文名称
            - grade_style: str - Rich库显示样式

        Raises
        ------
        ValueError
            当mode参数不是"relative"或"absolute"时抛出，或输入列表为空时抛出。
        """
        if mode not in ["relative", "absolute"]:
            raise ValueError(f"无效的评分模式: {mode}，必须为'relative'或'absolute'")

        if not raw_stats_list:
            raise ValueError("raw_stats_list不能为空")

        # 使用默认权重或自定义权重
        if weights is None:
            weights = ScoringSystem.DEFAULT_WEIGHTS

        dim_weights = weights["dimension_weights"]

        # 提取所有统计量用于计算组内最大值（相对模式）
        n = len(raw_stats_list)
        u_raw_list = [stats.u_raw for stats in raw_stats_list]
        e_k_total_list = [stats.e_k_total for stats in raw_stats_list]
        e_r_remain_list = [stats.e_r_remain for stats in raw_stats_list]
        p_down_list = [stats.p_down for stats in raw_stats_list]
        cv_list = [stats.cv for stats in raw_stats_list]
        e_r_flex_list = [stats.e_r_flex for stats in raw_stats_list]

        # 计算组内最大值（相对模式）
        max_u_raw = max(u_raw_list) if n > 0 else 1.0
        max_efficiency = (
            max((u / k) if k > 0 else 0.0 for u, k in zip(u_raw_list, e_k_total_list))
            if n > 0
            else 1.0
        )
        max_e_r_remain = max(e_r_remain_list) if n > 0 else 1.0
        max_cv = max(cv_list) if n > 0 and max(cv_list) > 0 else 1.0
        max_e_r_flex = max(e_r_flex_list) if n > 0 else 1.0

        results = []
        for i in range(n):
            stats = raw_stats_list[i]
            u_raw = stats.u_raw
            e_k_total = stats.e_k_total
            e_r_remain = stats.e_r_remain
            p_down = stats.p_down
            cv = stats.cv
            e_r_flex = stats.e_r_flex

            # ==================== 维度1：目标达成效用 U(S) ====================
            # 公式5.1.1（相对模式）：U(S) = U_raw(S) / max(U_raw(S'))
            # 公式5.1.2（绝对模式）：U(S) = U_raw(S)
            if mode == "relative":
                u_score = u_raw / max_u_raw if max_u_raw > 0 else 0.0
            else:  # absolute
                u_score = u_raw

            # 标准化到 [0, 1] 区间
            u_score = max(0.0, min(1.0, u_score))

            # ==================== 维度2：资源利用效率 E(S) ====================
            # 公式5.2.1（相对模式）：
            # E(S) = 0.5 * (U(S)/E[K_total(S)])/max(...) + 0.5 * E[R_remain(S)]/max(...)
            # 公式5.2.2（绝对模式）：
            # E(S) = 0.5 * (U(S)/E[K_total(S)])/(U_max/K_min) + 0.5 * E[R_remain(S)]/K_total
            efficiency_part1 = 0.0
            if e_k_total > 0:
                efficiency_ratio = u_score / e_k_total
                if mode == "relative":
                    efficiency_part1 = (
                        efficiency_ratio / max_efficiency if max_efficiency > 0 else 0.0
                    )
                else:  # absolute
                    # 绝对模式理论基准：U_max=1, K_min=1（避免除以0）
                    efficiency_part1 = (
                        efficiency_ratio / (1.0 / 1.0) if (1.0 / 1.0) > 0 else 0.0
                    )

            if mode == "relative":
                efficiency_part2 = (
                    e_r_remain / max_e_r_remain if max_e_r_remain > 0 else 0.0
                )
            else:  # absolute
                efficiency_part2 = e_r_remain / k_total if k_total > 0 else 0.0

            e_score = 0.5 * efficiency_part1 + 0.5 * efficiency_part2
            e_score = max(0.0, min(1.0, e_score))

            # ==================== 维度3：风险控制能力 R(S) ====================
            # 公式5.3.1（相对模式）：
            # R(S) = 0.6*(1-P_down(S)) + 0.4*(1 - CV(S)/max(CV(S')))
            # 公式5.3.2（绝对模式）：
            # R(S) = 0.6*(1-P_down(S)) + 0.4*(1-CV(S))
            risk_part1 = 1.0 - p_down

            if mode == "relative":
                risk_part2 = 1.0 - (cv / max_cv if max_cv > 0 else 0.0)
            else:  # absolute
                risk_part2 = 1.0 - cv

            r_score = 0.6 * risk_part1 + 0.4 * risk_part2
            r_score = max(0.0, min(1.0, r_score))

            # ==================== 维度4：策略灵活性 F(S) ====================
            # 公式5.4.1（相对模式）：F(S) = E[R_flex(S)] / max(E[R_flex(S')])
            # 公式5.4.2（绝对模式）：F(S) = E[R_flex(S)] / K_total
            if mode == "relative":
                f_score = e_r_flex / max_e_r_flex if max_e_r_flex > 0 else 0.0
            else:  # absolute
                f_score = e_r_flex / k_total if k_total > 0 else 0.0

            f_score = max(0.0, min(1.0, f_score))

            # ==================== 综合评分合成 ====================
            # 公式6.1：Score(S) = 100 * (ω1·U(S) + ω2·E(S) + ω3·R(S) + ω4·F(S))
            total_score = 100 * (
                dim_weights.get("u", 0.4) * u_score
                + dim_weights.get("e", 0.2) * e_score
                + dim_weights.get("r", 0.25) * r_score
                + dim_weights.get("f", 0.15) * f_score
            )
            total_score = max(0.0, min(100.0, total_score))

            # 获取等级信息
            grade, grade_name, grade_style = ScoringSystem.get_grade(total_score)

            results.append(
                {
                    "u_score": round(u_score, 4),
                    "e_score": round(e_score, 4),
                    "r_score": round(r_score, 4),
                    "f_score": round(f_score, 4),
                    "total_score": round(total_score, 1),
                    "grade": grade,
                    "grade_name": grade_name,
                    "grade_style": grade_style,
                }
            )

        return results

    @staticmethod
    def set_weights(
        dimension_weights: Optional[Dict[str, float]] = None,
        star_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Dict[str, float]]:
        """设置自定义权重配置。

        Parameters
        ----------
        dimension_weights : Optional[Dict[str, float]], optional
            维度权重配置，包含u(目标达成)、e(资源效率)、r(风险控制)、f(策略灵活性)四个维度的权重。
            权重总和应为1.0。
        star_weights : Optional[Dict[str, float]], optional
            6星分级权重配置，包含6、5、4三个星级的权重。

        Returns
        -------
        Dict[str, Dict[str, float]]
            更新后的权重配置字典，包含：
            - dimension_weights: 维度权重
            - star_weights: 星级权重

        Raises
        ------
        ValueError
            当维度权重总和不为1.0时抛出。
        """
        # 创建新的权重配置，基于默认配置
        new_weights = ScoringSystem.DEFAULT_WEIGHTS.copy()

        # 更新维度权重
        if dimension_weights is not None:
            total_weight = sum(dimension_weights.values())
            if abs(total_weight - 1.0) > 1e-10:
                raise ValueError(f"维度权重总和必须为1.0，当前为{total_weight}")
            new_weights["dimension_weights"] = dimension_weights

        # 更新星级权重
        if star_weights is not None:
            new_weights["star_weights"] = star_weights

        # 更新类属性
        ScoringSystem.DEFAULT_WEIGHTS = new_weights

        return new_weights


__all__ = ["Resource", "NativeStatistics", "ScoringSystem"]
