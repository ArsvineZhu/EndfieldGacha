# -*- coding: utf-8 -*-
"""策略评估结果展示模块。"""

from __future__ import annotations

import statistics
import time
from hashlib import md5
from pprint import pformat
from typing import Any, Dict, List

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

from scheduler.models import StrategyScoreReport, StrategyTrace
from scheduler.strategy_rules import StrategyRuleEngine, is_structured_strategy

console = Console()


class SchedulerDisplay:
    """调度器结果展示类。"""

    @staticmethod
    def print_header(
        scale: int, workers: int, change: bool, schedules: List[Any]
    ) -> None:
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

        rules = [plan.rules for plan in schedules]
        config_table.add_row(
            "策略标识",
            f"S{md5(pformat(rules).encode('utf-8')).hexdigest()[:5].upper()}",
        )
        config_table.add_row("模拟次数", f"{scale}")
        config_table.add_row("并行进程", f"{workers}")
        config_table.add_row("卡池切换", "启用" if change else "禁用")
        config_table.add_row("", "")
        config_table.add_row("策略组", "代码")
        for idx, rule in enumerate(rules):
            config_table.add_row(
                f"  ({idx + 1})", f"{pformat(SchedulerDisplay._format_strategy(rule))}"
            )

        console.print(
            Panel(config_table, title="[bold]配置信息[/bold]", box=box.ROUNDED)
        )
        console.print()

    @staticmethod
    def print_statistics(
        traces: List[StrategyTrace],
        elapsed_time: float,
        workers: int,
        report: StrategyScoreReport,
        schedule_count: int,
    ) -> None:
        del schedule_count
        total = len(traces)
        if total == 0:
            return

        paid_draws = [trace.total_paid_draws for trace in traces]
        bonus_draws = [trace.total_bonus_draws for trace in traces]
        total_draws = [trace.total_draws for trace in traces]
        resource_left = [trace.final_resource_left for trace in traces]
        complete_count = sum(1 for trace in traces if trace.completed)
        six_stars = [
            sum(1 for stage in trace.stages for result in stage.results if result["star"] == 6)
            for trace in traces
        ]
        current_ups = [
            sum(
                1
                for stage in trace.stages
                for result in stage.results
                if result.get("is_current_up")
            )
            for trace in traces
        ]
        complete_rate = complete_count / total * 100.0

        console.print()
        summary_panel = Panel(
            Columns(
                [
                    Panel(
                        f"[bold green]{report.raw_score:.1f}[/bold green]\n原始分",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold yellow]{report.goal_score:.1f}[/bold yellow]\n目标分",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold yellow]{report.utility_score:.1f}[/bold yellow]\n收益分",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold yellow]{report.resource_score:.1f}[/bold yellow]\n资源分",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold magenta]{report.risk_score:.1f}[/bold magenta]\n风险分",
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

        stats_table = Table(
            title="[bold]基础统计数据[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        stats_table.add_column("指标", style="bold", ratio=3)
        stats_table.add_column("平均值", justify="right", ratio=2)
        stats_table.add_column("最小值", justify="right", ratio=2)
        stats_table.add_column("最大值", justify="right", ratio=2)
        stats_table.add_column("标准差", justify="right", ratio=2)

        SchedulerDisplay._add_stat_row(stats_table, "总抽数", total_draws)
        SchedulerDisplay._add_stat_row(stats_table, "付费抽数", paid_draws)
        SchedulerDisplay._add_stat_row(stats_table, "赠送抽数", bonus_draws)
        SchedulerDisplay._add_stat_row(stats_table, "6星数量", six_stars)
        SchedulerDisplay._add_stat_row(stats_table, "当期UP数量", current_ups)
        SchedulerDisplay._add_stat_row(stats_table, "剩余资源", resource_left)
        console.print(stats_table)
        console.print()

        score_table = Table(
            title="[bold]评分详情[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        score_table.add_column("指标", style="bold", ratio=3)
        score_table.add_column("数值", justify="right", ratio=2)
        score_table.add_column("说明", ratio=4)

        score_table.add_row("等级", report.grade, report.grade_name)
        score_table.add_row("目标完成率", f"{report.goal_completion_rate * 100:.1f}%", "AND 目标集合")
        score_table.add_row("平均实际价值", f"{report.mean_utility:.2f}", "策略样本均值")
        score_table.add_row("平均基准价值", f"{report.mean_baseline:.2f}", "固定抽数状态基准")
        score_table.add_row("收益效率倍率", f"{report.utility_ratio:.3f}", "mean_utility / mean_baseline")
        score_table.add_row("平均机会价值", f"{report.mean_opportunity:.2f}", "剩余资源未来机会")
        score_table.add_row("资源机会倍率", f"{report.opportunity_ratio:.3f}", "mean_opportunity / O_ref")
        score_table.add_row("低尾风险均值", f"{report.tail_risk_mean:.2f}", "最低 q% 样本质量均值")
        score_table.add_row("可完成率", f"{complete_rate:.1f}%", "资源足够完成全部计划")
        score_table.add_row(
            "基准估计器",
            f"{report.baseline_samples} samples / seed {report.baseline_seed}",
            "固定样本、固定 seed 的 Monte Carlo 估计",
        )
        console.print(score_table)
        console.print()

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

        sim_per_sec = total / elapsed_time if elapsed_time > 0 else 0.0
        cpu_efficiency = (workers / cpu_count() * 100) if cpu_count() > 0 else 0.0

        perf_table.add_row("模拟速度", f"{sim_per_sec:,.0f} 次/秒", "每秒完成的策略样本数")
        perf_table.add_row("进程利用率", f"{cpu_efficiency:.1f}%", f"使用 {workers}/{cpu_count()} 核心")
        perf_table.add_row(
            "平均单次耗时",
            f"{elapsed_time / total * 1000:.2f} ms",
            "单条策略轨迹平均耗时",
        )
        console.print(perf_table)
        console.print(
            Panel(Text("报告结束", style="bold", justify="center"), box=box.DOUBLE, style="bold blue")
        )

    @staticmethod
    def print_multi_strategy_report(
        all_strategy_results: List[Dict[str, Any]],
        reports: List[StrategyScoreReport],
        scoring_mode: str,
    ) -> None:
        console.print()

        combined: List[Dict[str, Any]] = []
        for idx, strategy_data in enumerate(all_strategy_results):
            traces = strategy_data["traces"]
            report = reports[idx]
            avg_paid = sum(trace.total_paid_draws for trace in traces) / len(traces)
            avg_bonus = sum(trace.total_bonus_draws for trace in traces) / len(traces)
            avg_resource_left = sum(trace.final_resource_left for trace in traces) / len(traces)

            combined.append(
                {
                    "strategy_id": strategy_data["strategy_id"],
                    "strategy_rules": strategy_data["strategy_rules"],
                    "avg_paid": avg_paid,
                    "avg_bonus": avg_bonus,
                    "avg_resource_left": avg_resource_left,
                    "elapsed_time": strategy_data["elapsed_time"],
                    "report": report,
                }
            )

        combined.sort(key=lambda item: item["report"].rank or 9999)

        rank_table = Table(
            title="[bold white]策略综合排名[/bold white]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        rank_table.add_column("排名", justify="center", width=6)
        rank_table.add_column("策略ID", justify="center", width=8)
        rank_table.add_column("原始分", justify="right", width=8)
        rank_table.add_column("目标分", justify="right", width=8)
        rank_table.add_column("收益分", justify="right", width=8)
        rank_table.add_column("资源分", justify="right", width=8)
        rank_table.add_column("风险分", justify="right", width=8)
        rank_table.add_column("目标完成率", justify="right", width=10)
        rank_table.add_column("均付费抽", justify="right", width=10)
        rank_table.add_column("均赠送抽", justify="right", width=10)
        rank_table.add_column("均剩余资源", justify="right", width=12)
        rank_table.add_column("百分位", justify="right", width=8)

        for item in combined:
            report = item["report"]
            rank_table.add_row(
                str(report.rank),
                item["strategy_id"],
                f"{report.raw_score:.1f}",
                f"{report.goal_score:.1f}",
                f"{report.utility_score:.1f}",
                f"{report.resource_score:.1f}",
                f"{report.risk_score:.1f}",
                f"{report.goal_completion_rate * 100:.1f}%",
                f"{item['avg_paid']:.1f}",
                f"{item['avg_bonus']:.1f}",
                f"{item['avg_resource_left']:.1f}",
                f"{report.percentile:.1f}",
            )

        console.print(rank_table)
        console.print()

        detail_table = Table(
            title="[bold white]策略详情[/bold white]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        detail_table.add_column("策略ID", justify="center", width=8)
        detail_table.add_column("策略规则", style="yellow", ratio=1)
        detail_table.add_column("分差", justify="right", width=8)
        detail_table.add_column("目标差", justify="right", width=8)
        detail_table.add_column("机会差", justify="right", width=8)
        detail_table.add_column("耗时", justify="right", width=8)

        for item in combined:
            report = item["report"]
            detail_table.add_row(
                item["strategy_id"],
                str(SchedulerDisplay._format_strategy(item["strategy_rules"])),
                f"{report.score_delta_from_best:.1f}",
                f"{report.goal_delta_from_best * 100:.1f}%",
                f"{report.opportunity_delta_from_best:.1f}",
                f"{item['elapsed_time']:.1f}s",
            )

        console.print(detail_table)
        console.print(
            Panel(
                Text(f"多策略评估结束（{scoring_mode}模式）", style="bold", justify="center"),
                box=box.DOUBLE,
                style="bold blue",
            )
        )

    @staticmethod
    def print_report(report: StrategyScoreReport) -> None:
        console.print("\n[bold]=== 评估报告 ===[/bold]")
        console.print(f"原始分: {report.raw_score:.1f} ({report.grade})")
        console.print(f"目标完成率: {report.goal_completion_rate * 100:.1f}%")
        console.print(f"平均实际价值: {report.mean_utility:.2f}")
        console.print(f"平均基准价值: {report.mean_baseline:.2f}")
        console.print(f"平均机会价值: {report.mean_opportunity:.2f}")

    @staticmethod
    def create_progress() -> Progress:
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
        console.clear()

    @staticmethod
    def print(message: str, **kwargs: Any) -> None:
        console.print(message, **kwargs)

    @staticmethod
    def _add_stat_row(table: Table, name: str, values: List[int]) -> None:
        table.add_row(
            name,
            f"{sum(values) / len(values):.2f}",
            f"{min(values)}",
            f"{max(values)}",
            f"{statistics.stdev(values):.2f}" if len(values) > 1 else "N/A",
        )

    @staticmethod
    def _format_strategy(rule: Any) -> Any:
        if is_structured_strategy(rule):
            return StrategyRuleEngine.describe(rule)
        raise TypeError(f"仅支持结构化策略规则，收到: {type(rule)}")


__all__ = ["SchedulerDisplay"]

