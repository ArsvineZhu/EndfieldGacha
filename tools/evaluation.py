# -*- coding: utf-8 -*-
"""策略评估脚本"""


# 添加项目根目录到路径，确保可以直接运行
if __name__ == "__main__":
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from scheduler import *


def str0(scale: int = 5000):
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.banner(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.banner([[UP_OPRT, GE ^ 50, DOSSIER], [URGENT, LT ^ 50, UP_OPRT]])
    scheduler.banner([[OPRT, GE ^ 50, DOSSIER], [URGENT, LT ^ 50, OPRT]])
    scheduler.banner(
        [[UP_OPRT, GE ^ 50, DOSSIER], [URGENT, LT ^ 50, UP_OPRT]],
        use_origeometry=True,
        is_core=True,
    )
    scheduler.banner([[OPRT, GE ^ 50, DOSSIER], [URGENT, LT ^ 50, OPRT]])

    scheduler.evaluate(scale, workers=16)


def str1(scale: int = 5000):
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 100),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.banner(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.banner([UP_OPRT])
    scheduler.banner([OPRT])
    scheduler.banner(
        [[UP_OPRT, GE ^ 50, DOSSIER], [URGENT, LT ^ 50, UP_OPRT]],
        use_origeometry=True,
        is_core=True,
    )
    scheduler.banner([OPRT])

    scheduler.evaluate(scale, workers=16)


if __name__ == "__main__":
    str0(2000)
    str1(2000)
