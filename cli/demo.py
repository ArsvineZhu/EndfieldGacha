# -*- coding: utf-8 -*-
"""抽卡演示与统计工具。"""

import os
import sys

from gacha_core import GlobalConfigLoader

from ._demo_char import (
    demo_char_draw,
    stats_char_draw,
    stats_char_potential,
    stats_char_quota,
    stats_char_up_prob,
)
from ._demo_weapon import (
    demo_weapon_apply,
    stats_urgent_quota,
    stats_weapon_draw,
    stats_weapon_quota,
    stats_weapon_up_prob,
)


class GachaTestTool:
    """卡池测试与统计工具。"""

    def __init__(self):
        self.config = GlobalConfigLoader()
        self.width = {
            "draw_num": 10,
            "star": 2,
            "quota": 9,
            "stat_num": 10,
            "stat_rate": 8,
        }

    def demo_char_draw(self, draw_times: int = 5):
        demo_char_draw(self.config, self.width, draw_times)

    def demo_weapon_apply(self, apply_times: int = 1):
        demo_weapon_apply(self.config, self.width, apply_times)

    def stats_char_quota(self, draw_times: int = 50000, gragh: bool = False):
        stats_char_quota(self.config, self.width, draw_times, gragh=gragh)

    def stats_weapon_quota(self, draw_times: int = 50000, gragh: bool = False):
        stats_weapon_quota(self.config, draw_times, gragh=gragh)

    def stats_char_draw(self, draw_times: int = 50000, gragh: bool = False):
        stats_char_draw(self.config, draw_times, gragh=gragh)

    def stats_weapon_draw(self, draw_times: int = 50000, gragh: bool = False):
        stats_weapon_draw(self.config, draw_times, gragh=gragh)

    def stats_char_up_prob(self, test_times: int = 50000, gragh: bool = False, limit: int = 0):
        stats_char_up_prob(self.config, test_times, gragh=gragh, limit=limit)

    def stats_weapon_up_prob(self, test_times: int = 50000, gragh: bool = False, limit: int = 0):
        stats_weapon_up_prob(self.config, test_times, gragh=gragh, limit=limit)

    def stats_urgent_quota(self, draw_times: int = 50000, gragh: bool = False):
        stats_urgent_quota(self.config, draw_times, gragh=gragh)

    def stats_char_potential(self, draw_times: int = 50000, gragh: bool = False):
        stats_char_potential(self.config, draw_times, gragh=gragh)


# ===================== 主函数 =====================
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    tool = GachaTestTool()
    tool.demo_char_draw(120)
    tool.demo_weapon_apply(8)

    # 统计 UP 角色所需抽数（样本量 100000）
    # tool.stats_char_up_prob(20000, gragh=True)

    # 统计 UP 武器所需抽数（样本量 100000）
    # tool.stats_weapon_up_prob(20000, gragh=True)

    # 截断大保底，最多 80 抽查看期望
    # tool.stats_char_up_prob(20000, gragh=True, limit=80)

    # 截断大保底，最多 119 抽查看期望
    # tool.stats_char_up_prob(20000, gragh=True, limit=119)

    # 120 次角色池配额（样本量 100000）
    # tool.stats_char_quota(20000, gragh=True)

    # 8 次武器池配额（样本量 100000）
    # tool.stats_weapon_quota(20000, gragh=True)

    # 120 抽角色池 6 星数量分布（样本量 100000）
    # tool.stats_char_draw(20000, gragh=True)

    # 8 次武器池 6 星数量分布（样本量 100000）
    # tool.stats_weapon_draw(20000, gragh=True)

    # 加急招募 10 连配额分布（样本量 100000）
    # tool.stats_urgent_quota(20000, gragh=True)

    # 当期 UP 满潜所需抽数（样本量 100000）
    # tool.stats_char_potential(20000, gragh=True)
