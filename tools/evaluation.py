# -*- coding: utf-8 -*-
"""策略评估脚本"""

import os
import sys

# 添加项目根目录到路径，确保可以直接运行
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from scheduler import *


def edge_min():
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([0])
    scheduler.schedule([0])
    scheduler.schedule([0])
    scheduler.schedule([0])

    # scheduler.simulate()
    scheduler.evaluate(scale=5000, workers=16)


def edge_max():
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [UP_OPRT], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([UP_OPRT])
    scheduler.schedule([UP_OPRT])
    scheduler.schedule([UP_OPRT])
    scheduler.schedule([UP_OPRT])

    # scheduler.simulate()
    scheduler.evaluate(scale=5000, workers=16)


def strategy0(scale=5000):
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([DOSSIER, OPRT])
    scheduler.schedule([DOSSIER])
    scheduler.schedule([DOSSIER, UP_OPRT], use_origeometry=True)
    scheduler.schedule([DOSSIER, OPRT])

    # scheduler.simulate()
    scheduler.evaluate(scale, workers=16)


def strategy1(scale=5000):
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([[DOSSIER, GT ^ 43, UP_OPRT], [URGENT, LE ^ 43, UP_OPRT]])
    scheduler.schedule([URGENT])
    scheduler.schedule(
        [[DOSSIER, GT ^ 43, UP_OPRT], [URGENT, LE ^ 43, UP_OPRT]], use_origeometry=True
    )
    scheduler.schedule([URGENT])

    # scheduler.simulate()
    scheduler.evaluate(scale, workers=16)


def strategy2(scale=5000):
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([DOSSIER, UP_OPRT])
    scheduler.schedule([DOSSIER, [URGENT, LE ^ 43, UP_OPRT]])
    scheduler.schedule([DOSSIER, UP_OPRT], use_origeometry=True)
    scheduler.schedule([DOSSIER, [URGENT, LE ^ 43, UP_OPRT]])

    # scheduler.simulate()
    scheduler.evaluate(scale, workers=16)


def strategy3(scale=5000):
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([[UP_OPRT, GE ^ 50, DOSSIER], [URGENT, LT ^ 50, UP_OPRT]])
    scheduler.schedule([[OPRT, GE ^ 50, DOSSIER], [URGENT, LT ^ 50, OPRT]])
    scheduler.schedule(
        [[UP_OPRT, GE ^ 50, DOSSIER], [URGENT, LT ^ 50, UP_OPRT]], use_origeometry=True
    )
    scheduler.schedule([[OPRT, GE ^ 50, DOSSIER], [URGENT, LT ^ 50, OPRT]])

    # scheduler.simulate()
    scheduler.evaluate(scale, workers=16)


def strategy4(scale=5000):
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([0])
    scheduler.schedule([0])
    scheduler.schedule([POTENTIAL ^ 3], use_origeometry=True)
    scheduler.schedule([0])

    # scheduler.simulate()
    scheduler.evaluate(scale, workers=16)


def strategy_new_scoring(scale=2000):
    """新版评分系统示例 - 多策略批量评估与四维评分

    展示新版评分系统的核心功能：
    1. 四维评分（目标达成效用、资源利用效率、风险控制能力、策略灵活性）
    2. 双模式支持（相对模式、绝对模式）
    3. 多策略对比分析
    """
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    # 定义多种抽卡策略进行对比分析
    strategies = [
        [DOSSIER, OPRT],  # 策略1：情报书+6星角色（保守型）
        [UP_OPRT],  # 策略2：专注UP角色（目标型）
        [URGENT, DOSSIER, UP_OPRT],  # 策略3：综合策略（平衡型）
    ]

    # 使用新版评分系统进行多策略评估
    # Scheduler.evaluate()方法已支持多策略评估
    results = scheduler.evaluate(
        scale=scale,
        workers=8,  # 使用8个worker提升评估效率
        strategies=strategies,  # 传递多策略列表
        scoring_mode="relative",  # 相对模式：基于组内相对表现评分
    )


def example_multi_cycle():
    """多周期策略组示例"""
    # 1. 创建规划器
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )
    # 2. 添加周期
    scheduler.add_cycle(
        [DOSSIER, OPRT], check_in=True, resource_increment=Resource(1, 5000, 0, 0)
    )
    scheduler.add_cycle(
        [UP_OPRT], use_origeometry=True, resource_increment=Resource(0, 10000, 1000, 0)
    )
    scheduler.add_cycle(
        [URGENT, DOSSIER, UP_OPRT],
        check_in=False,
        resource_increment=Resource(2, 15000, 2000, 50),
    )
    # 3. 执行模拟
    # raw_stats = scheduler.evaluate(scale=1000, workers=2)
    # 4. 输出报告（可选）
    # scheduler.print_report(raw_stats, mode="relative")
    scheduler.add_cycle(
        [URGENT, DOSSIER, UP_OPRT],
        check_in=False,
        resource_increment=Resource(2, 15000, 2000, 50),
    )
    # 3. 执行模拟
    # raw_stats = scheduler.evaluate(scale=1000, workers=2)
    # 4. 输出报告（可选）
    # scheduler.print_report(raw_stats, mode="relative")


if __name__ == "__main__":
    # 默认执行示例策略评估
    strategy1(2000)
    strategy2(2000)
    strategy3(2000)

    # example_multi_cycle()
    # example_custom_weights()
    # example_multi_strategy()

    # 新版评分系统示例
    # strategy_new_scoring(2000)  # 多策略批量评估示例
    # strategy_raw_statistics(1000)  # 原生统计量分析示例
