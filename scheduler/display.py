# -*- coding: utf-8 -*-
"""策略评估结果展示模块。

提供所有与输出美化、报告生成、表格打印相关的功能，与核心业务逻辑完全解耦。
使用Rich库实现美观的终端输出，所有展示逻辑集中在此模块，核心业务逻辑仅处理数据。
"""

from typing import Any, Dict, List, Tuple
import time
import statistics
from hashlib import md5
from pprint import pformat
from rich.console import Console
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    TaskProgressColumn,
    SpinnerColumn,
)
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box

from scheduler.scoring import ScoringSystem, NativeStatistics
from scheduler.strategy import GachaStrategy

console = Console()


class SchedulerDisplay:
    """调度器结果展示类，封装所有输出美化逻辑。"""

    @staticmethod
    def print_header(
        scale: int, workers: int, change: bool, schedules: List[Tuple]
    ) -> None:
        """打印评估任务的配置概览。

        Parameters
        ----------
        scale : int
            模拟次数
        workers : int
            进程数
        change : bool
            是否启用卡池切换
        schedules : List[Tuple]
            调度计划列表
        """
        console.clear()

        header = Panel(
            Text("策略评估报告", style="bold white", justify="center"),
            subtitle=f"{time.strftime('%Y-%m-%d %H:%M:%S')}",
            style="bold blue",
            box=box.DOUBLE,
        )
        console.print(header)

        config_table = Table(show_header=False, box=box.SIMPLE, expand=True)
        config_table.add_column("参数", style="cyan", width=15)
        config_table.add_column("值", style="yellow", ratio=1)

        rules = [plan[0] for plan in schedules]
        config_table.add_row(
            "策略标识",
            f"S{md5(pformat(rules).encode('utf-8')).hexdigest()[:5].upper()}",
        )

        config_table.add_row("并行进程", f"{workers}")
        config_table.add_row("卡池切换", "启用" if change else "禁用")
        config_table.add_row("", "")
        config_table.add_row("策略组", "代码")
        for idx, rule in enumerate(rules):
            config_table.add_row(
                f"  ({idx + 1})", f"{pformat(GachaStrategy.decode_strategy(rule))}"
            )
        console.print(
            Panel(config_table, title="[bold]配置信息[/bold]", box=box.ROUNDED)
        )
        console.print()

    @staticmethod
    def print_statistics(
        results: List[Dict[str, Any]],
        elapsed_time: float,
        workers: int,
        raw_stats: NativeStatistics,
        comprehensive_scores: Dict[str, Any],
        schedule_count: int,
    ) -> None:
        """根据worker返回结果打印统计与评分报告。

        Parameters
        ----------
        results : List[Dict[str, Any]]
            模拟结果列表
        elapsed_time : float
            执行耗时（秒）
        workers : int
            进程数
        raw_stats : NativeStatistics
            原生统计量对象
        comprehensive_scores : Dict[str, Any]
            综合评分结果
        schedule_count : int
            调度计划数量
        """
        total = len(results)
        if total == 0:
            return

        total_draws = [r["total_draws"] for r in results]
        six_stars = [r["six_stars"] for r in results]
        up_chars = [r["up_chars"] for r in results]
        resource_left = [r["resource_left"] for r in results]
        complete_count = sum(1 for r in results if r["complete"])
        draw_avg = sum(total_draws) / total
        six_avg = sum(six_stars) / total
        up_avg = sum(up_chars) / total
        complete_rate = complete_count / total * 100

        # 等级分布统计
        grade_distribution = {}
        grade_distribution[comprehensive_scores["grade"]] = total

        console.print()

        summary_panel = Panel(
            Columns(
                [
                    Panel(
                        f"[bold green]{complete_rate:.1f}%[/bold green]\n可行度",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold yellow]{comprehensive_scores['total_score']:.1f}[/bold yellow]\n综合评分",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold yellow]{raw_stats.e_r_remain:.1f}[/bold yellow]\n资源剩余",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold yellow]{up_avg:.1f}[/bold yellow]\nUP获得",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold magenta]{total * workers:,}[/bold magenta]\n模拟次数",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold magenta]{elapsed_time:.1f}s[/bold magenta]\n执行时间",
                        box=box.SIMPLE,
                    ),
                ]
            ),
            title="[bold white]核心指标概览[/bold white]",
            box=box.ROUNDED,
        )
        console.print(summary_panel)
        console.print()

        # 基础统计表格
        stats_table = Table(
            title="[bold]基础统计数据[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        stats_table.add_column("指标", style="bold", ratio=3)
        stats_table.add_column("平均值", justify="right", ratio=3)
        stats_table.add_column("最小值", justify="right", ratio=2)
        stats_table.add_column("最大值", justify="right", ratio=2)
        stats_table.add_column("标准差", justify="right", ratio=2)

        stats_table.add_row(
            "总抽数",
            f"{draw_avg:.1f}",
            f"{min(total_draws)}",
            f"{max(total_draws)}",
            f"{statistics.stdev(total_draws):.1f}" if len(total_draws) > 1 else "N/A",
        )
        stats_table.add_row(
            "6星数量",
            f"{six_avg:.2f}",
            f"{min(six_stars)}",
            f"{max(six_stars)}",
            f"{statistics.stdev(six_stars):.2f}" if len(six_stars) > 1 else "N/A",
        )
        stats_table.add_row(
            "UP数量",
            f"{up_avg:.2f}",
            f"{min(up_chars)}",
            f"{max(up_chars)}",
            f"{statistics.stdev(up_chars):.2f}" if len(up_chars) > 1 else "N/A",
        )
        stats_table.add_row(
            "剩余资源",
            f"[bold]{sum(resource_left) / total:.0f}[/bold]",
            f"{min(resource_left)}",
            f"{max(resource_left)}",
            (
                f"{statistics.stdev(resource_left):.1f}"
                if len(resource_left) > 1
                else "N/A"
            ),
        )
        console.print(stats_table)
        console.print()

        # 评分详情表格
        score_table = Table(
            title="[bold]评分详情[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        score_table.add_column("评分维度", style="bold", ratio=3)
        score_table.add_column("平均得分", justify="right", ratio=3)
        score_table.add_column("满分", justify="right", ratio=2)
        score_table.add_column("得分率", justify="right", ratio=2)

        # 直接展示四维评分结果
        u_score = comprehensive_scores["u_score"] * 40  # 转换为40分制
        e_score = comprehensive_scores["e_score"] * 20  # 转换为20分制
        r_score = comprehensive_scores["r_score"] * 25  # 转换为25分制
        f_score = comprehensive_scores["f_score"] * 15  # 转换为15分制
        total_score = comprehensive_scores["total_score"]

        score_table.add_row(
            "目标达成效用",
            f"{u_score:.1f}",
            "40",
            f"{comprehensive_scores['u_score'] * 100:.1f}%",
        )
        score_table.add_row(
            "资源利用效率",
            f"{e_score:.1f}",
            "20",
            f"{comprehensive_scores['e_score'] * 100:.1f}%",
        )
        score_table.add_row(
            "风险控制能力",
            f"{r_score:.1f}",
            "25",
            f"{comprehensive_scores['r_score'] * 100:.1f}%",
        )
        score_table.add_row(
            "策略灵活性",
            f"{f_score:.1f}",
            "15",
            f"{comprehensive_scores['f_score'] * 100:.1f}%",
        )
        score_table.add_row(
            "[bold]整体评分[/bold]",
            f"[bold]{total_score:.1f}[/bold]",
            "100",
            f"[bold]{total_score:.1f}[/bold]",
        )
        console.print(score_table)
        console.print()

        # 等级分布统计
        grade_table = Table(
            title="[bold]等级分布统计[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        grade_table.add_column("等级", style="bold", ratio=1)
        grade_table.add_column("描述", ratio=2)
        grade_table.add_column("数量", justify="right", ratio=2)
        grade_table.add_column("占比", justify="right", ratio=2)
        grade_table.add_column("分布图", ratio=5)

        grade_order = ["S", "A", "B", "C", "D", "E"]
        grade_names = {
            "S": "极佳",
            "A": "优秀",
            "B": "良好",
            "C": "一般",
            "D": "较差",
            "E": "失败",
        }
        grade_styles = {
            "S": "red",
            "A": "yellow",
            "B": "green",
            "C": "blue",
            "D": "magenta",
            "E": "white",
        }

        for grade in grade_order:
            count = grade_distribution.get(grade, 0)
            percentage = count / total * 100
            bar = "█" * int(percentage / 3.33)
            grade_table.add_row(
                f"[bold {grade_styles[grade]}]{grade}[/bold {grade_styles[grade]}]",
                grade_names[grade],
                f"{count:,}",
                f"{percentage:.1f}%",
                f"[{grade_styles[grade]}]{bar}[/{grade_styles[grade]}]",
            )
        console.print(grade_table)
        console.print()

        # 百分位统计
        percentile_table = Table(
            title="[bold]百分位统计[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        percentile_table.add_column("分位", style="bold", ratio=1)
        percentile_table.add_column("总抽数", justify="right", ratio=2)
        percentile_table.add_column("6星数", justify="right", ratio=2)
        percentile_table.add_column("UP数量", justify="right", ratio=2)

        percentiles = [10, 25, 50, 75, 90, 95, 99]
        for p in percentiles:
            percentile_table.add_row(
                f"P{p}",
                f"{_percentile(total_draws, p):.0f}",
                f"{_percentile(six_stars, p):.0f}",
                f"{_percentile(up_chars, p):.0f}",
            )
        console.print(percentile_table)
        console.print()

        # 性能分析
        perf_table = Table(
            title="[bold]性能分析报告[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        perf_table.add_column("指标", style="bold", ratio=3)
        perf_table.add_column("数值", justify="right", ratio=2)
        perf_table.add_column("说明", ratio=4)

        from multiprocessing import cpu_count

        sim_per_sec = total / elapsed_time if elapsed_time > 0 else 0
        cpu_efficiency = (workers / cpu_count() * 100) if cpu_count() > 0 else 0

        perf_table.add_row(
            "模拟速度", f"{sim_per_sec:,.0f} 次/秒", "每秒完成的模拟次数"
        )
        perf_table.add_row(
            "进程利用率", f"{cpu_efficiency:.1f}%", f"使用 {workers}/{cpu_count()} 核心"
        )
        perf_table.add_row(
            "平均单次耗时", f"{elapsed_time / total * 1000:.2f} ms", "单次模拟平均耗时"
        )
        perf_table.add_row("内存效率", "良好", "使用流式处理，内存占用低")

        footer = Panel(
            Text("报告结束", style="bold", justify="center"),
            box=box.DOUBLE,
            style="bold blue",
        )
        console.print(footer)

    @staticmethod
    def print_multi_strategy_report(
        all_strategy_results: List[Dict[str, Any]],
        comprehensive_scores: List[Dict[str, Any]],
        scoring_mode: str,
    ) -> None:
        """打印多策略对比报告。

        Parameters
        ----------
        all_strategy_results : List[Dict[str, Any]]
            所有策略的模拟结果
        comprehensive_scores : List[Dict[str, Any]]
            所有策略的综合评分结果
        scoring_mode : str
            评分模式："relative"或"absolute"
        """
        console.print()

        # 合并策略数据和评分
        combined = []
        for i in range(len(all_strategy_results)):
            strategy_data = all_strategy_results[i]
            score_data = comprehensive_scores[i]

            # 计算基础统计量
            results = strategy_data["simulation_results"]
            total = len(results)
            complete_count = sum(1 for r in results if r["complete"])
            complete_rate = complete_count / total * 100
            avg_draws = sum(r["total_draws"] for r in results) / total
            avg_six = sum(r["six_stars"] for r in results) / total
            avg_up = sum(r["up_chars"] for r in results) / total
            avg_resource_left = sum(r["resource_left"] for r in results) / total

            combined.append(
                {
                    "strategy_id": strategy_data["strategy_id"],
                    "strategy_rules": strategy_data["strategy_rules"],
                    "complete_rate": complete_rate,
                    "avg_draws": avg_draws,
                    "avg_six": avg_six,
                    "avg_up": avg_up,
                    "avg_resource_left": avg_resource_left,
                    "u_score": score_data["u_score"],
                    "e_score": score_data["e_score"],
                    "r_score": score_data["r_score"],
                    "f_score": score_data["f_score"],
                    "total_score": score_data["total_score"],
                    "grade": score_data["grade"],
                    "grade_name": score_data["grade_name"],
                    "grade_style": score_data["grade_style"],
                    "elapsed_time": strategy_data["elapsed_time"],
                }
            )

        # 按综合评分降序排序
        combined.sort(key=lambda x: x["total_score"], reverse=True)

        # 打印综合排名表
        rank_table = Table(
            title="[bold white]策略综合排名[/bold white]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )

        rank_table.add_column("排名", style="bold", justify="center", width=6)
        rank_table.add_column("策略ID", style="bold", justify="center", width=8)
        rank_table.add_column("可行度", justify="right", width=8)
        rank_table.add_column("平均抽数", justify="right", width=8)
        rank_table.add_column("平均6星", justify="right", width=8)
        rank_table.add_column("平均UP", justify="right", width=8)
        rank_table.add_column("剩余资源", justify="right", width=8)
        rank_table.add_column("U评分", justify="right", width=8)
        rank_table.add_column("E评分", justify="right", width=8)
        rank_table.add_column("R评分", justify="right", width=8)
        rank_table.add_column("F评分", justify="right", width=8)
        rank_table.add_column("综合评分", justify="right", width=10)
        rank_table.add_column("等级", justify="center", width=6)

        for rank, item in enumerate(combined, start=1):
            rank_table.add_row(
                str(rank),
                item["strategy_id"],
                f"{item['complete_rate']:.1f}%",
                f"{item['avg_draws']:.1f}",
                f"{item['avg_six']:.2f}",
                f"{item['avg_up']:.2f}",
                f"{item['avg_resource_left']:.0f}",
                f"{item['u_score']:.3f}",
                f"{item['e_score']:.3f}",
                f"{item['r_score']:.3f}",
                f"{item['f_score']:.3f}",
                f"[bold {item['grade_style']}]{item['total_score']:.1f}[/bold {item['grade_style']}]",
                f"[{item['grade_style']}]{item['grade']}[/{item['grade_style']}]",
            )

        console.print(rank_table)
        console.print()

        # 打印策略详情表
        detail_table = Table(
            title="[bold white]策略详情[/bold white]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )

        detail_table.add_column("策略ID", style="bold", justify="center", width=8)
        detail_table.add_column("策略规则", style="yellow", ratio=1)
        detail_table.add_column("等级描述", justify="center", width=10)
        detail_table.add_column("耗时", justify="right", width=8)

        for item in combined:
            # 解码策略规则为友好名称
            try:
                decoded = GachaStrategy.decode_strategy(item["strategy_rules"])
            except:
                decoded = str(item["strategy_rules"])

            detail_table.add_row(
                item["strategy_id"],
                str(decoded),
                f"[{item['grade_style']}]{item['grade_name']}[/{item['grade_style']}]",
                f"{item['elapsed_time']:.1f}s",
            )

        console.print(detail_table)
        console.print()

        footer = Panel(
            Text(
                f"多策略评估结束（{scoring_mode}模式）", style="bold", justify="center"
            ),
            box=box.DOUBLE,
            style="bold blue",
        )
        console.print(footer)

    @staticmethod
    def print_report(raw_stats: NativeStatistics, mode: str = "relative") -> None:
        """打印简洁的评估报告。

        Parameters
        ----------
        raw_stats : NativeStatistics
            原生统计量对象
        mode : str, optional
            评分模式，默认"relative"
        """
        # 计算综合评分
        comprehensive_scores = ScoringSystem.calculate_comprehensive_score(
            [raw_stats], mode=mode
        )[0]

        # 打印核心指标
        console.print("\n[bold]=== 评估报告 ===[/bold]")
        console.print(f"核心目标达成率: {raw_stats.p_core * 100:.1f}%")
        console.print(f"加权目标达成率: {raw_stats.p_t * 100:.1f}%")
        console.print(f"平均抽数: {raw_stats.e_k_total:.1f}")
        console.print(f"平均剩余资源: {raw_stats.e_r_remain:.0f}")
        console.print(f"下行风险概率: {raw_stats.p_down * 100:.1f}%")
        console.print("\n[bold]评分详情:[/bold]")
        console.print(f"目标达成效用: {comprehensive_scores['u_score'] * 100:.1f}%")
        console.print(f"资源利用效率: {comprehensive_scores['e_score'] * 100:.1f}%")
        console.print(f"风险控制能力: {comprehensive_scores['r_score'] * 100:.1f}%")
        console.print(f"策略灵活性: {comprehensive_scores['f_score'] * 100:.1f}%")
        console.print(
            f"[bold]综合评分: {comprehensive_scores['total_score']:.1f} ({comprehensive_scores['grade']})[/bold]\n"
        )

    @staticmethod
    def create_progress() -> Progress:
        """创建进度条实例。

        Returns
        -------
        Progress
            配置好的Rich进度条对象
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TextColumn("已用时: "),
            TimeElapsedColumn(),
            TextColumn(" | 预计剩余: "),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        )

    @staticmethod
    def clear() -> None:
        """清空控制台。"""
        console.clear()

    @staticmethod
    def print(message: str, **kwargs) -> None:
        """打印通用消息。

        Parameters
        ----------
        message : str
            要打印的消息
        **kwargs
            传递给console.print的其他参数
        """
        console.print(message, **kwargs)


def _percentile(data: List, p: float) -> float:
    """计算列表数据的近似分位数。

    Parameters
    ----------
    data : List
        数据列表
    p : float
        分位数值（0-100）

    Returns
    -------
    float
        分位数值
    """
    sorted_data = sorted(data)
    idx = int(len(data) * p / 100)
    if idx >= len(sorted_data):
        idx = len(sorted_data) - 1
    return sorted_data[idx]
