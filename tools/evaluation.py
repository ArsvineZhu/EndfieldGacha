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


if __name__ == "__main__":
    # edge_min()
    # strategy0(5000)  # 100.0 / 70.5 / 126.0 / 2.4
    # strategy1(5000)  # 100 / 72.1 / 167.0 / 2.3
    # strategy2(5000)  # 100 / 72.8 / 119.5 / 2.6
    strategy3(5000)  # 96.6 / 75.8 / 123.2 / 3.1
    # strategy4()
    # edge_max()
