# -*- coding: utf-8 -*-
"""策略调度器核心逻辑。

提供多卡池策略调度、大规模并行评估和可视化统计功能。

主要功能：
- 多卡池连续模拟（支持配置切换）
- 大规模并行评估（多进程优化）
- 详细的统计报告输出（使用Rich库美化）
- 策略性能评分系统
"""
import os
from hashlib import md5
from multiprocessing import Pool, cpu_count
from pprint import pformat
from typing import Any, Dict, List, Tuple
import time
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

from core import CharGacha, Counters, GlobalConfigLoader
from .scoring import Resource, ScoringSystem
from .strategy import (
    GachaStrategy,
    URGENT,
    DOSSIER,
    SOFT_PITY,
    UP_OPRT,
    HARD_PITY,
    POTENTIAL,
    OPRT,
    GT,
    LT,
    GE,
    LE,
)
from .workers import (
    get_token,
    consume_resource,
    process_gacha_result,
    handle_urgent_gacha,
    initialize_banner_state,
    _worker_wrapper,
)

console = Console()


class Scheduler:
    """策略调度器：多卡池策略评估总控类。
    
    负责从配置目录加载卡池配置，组织多段抽卡计划，提供单次可视化模拟
    和大规模并行评估两种模式。支持配置切换、资源管理和详细的统计报告。
    
    Attributes
    ----------
    config_dir : str
        配置文件目录路径，默认"configs"。
    arrangement : list of str
        卡池配置顺序列表，从arrange文件中读取。
    resource : Resource
        当前可用的抽卡资源。
    increment : Resource
        每日/每阶段资源增量。
    __schedules : list of tuple
        已登记的抽卡计划列表，格式为:
        (rules, counters, check_in, use_origeometry, resource_inc)
    
    Examples
    --------
    >>> from scheduler import Scheduler, Resource, Counters, DOSSIER, UP_OPRT
    >>> scheduler = Scheduler(
    ...     config_dir="configs",
    ...     arrange="arrange1",
    ...     resource=Resource(2, 61000, 6000, 100)
    ... )
    >>> scheduler.schedule([DOSSIER, OPRT])
    >>> scheduler.schedule([UP_OPRT], use_origeometry=True)
    >>> scheduler.evaluate(scale=5000, workers=8)
    
    Notes
    -----
    - 多进程评估使用``multiprocessing.Pool``，支持流式处理，内存占用较低
    - 统计报告使用Rich库美化输出，支持颜色和表格格式
    - 支持配置切换：每个计划可以对应不同的卡池配置
    """
    
    def __init__(
        self,
        config_dir: str = "configs",
        arrange: str = "arrangement",
        resource: Resource | None = None,
        increment: Resource | None = None,
    ):
        """初始化策略调度器。
        
        Parameters
        ----------
        config_dir : str, optional
            抽卡配置文件所在目录路径，默认"configs"。
        arrange : str, optional
            卡池顺序文件名，文件按行存放配置名，默认"arrangement"。
        resource : Resource or None, optional
            初始资源对象；为None时使用零资源初始化。
        increment : Resource or None, optional
            每日/每阶段资源增量；为None时使用默认值：
            - 特许寻访凭证: 5
            - 嵌晶玉: 22500 (500*45)
            - 武库配额: 600
            - 衍质源石: 25
        """
        self.config_dir = config_dir
        self.increment = (
            increment
            if increment
            else Resource(
                chartered_permits=5,
                oroberyl=45 * 500,
                arsenal_tickets=600,
                origeometry=25,
            )
        )

        self.arrangement = []
        with open(os.path.join(config_dir, arrange), "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                if line:
                    self.arrangement.append(line.strip())

        self.resource = Resource() if not resource else resource
        self.__schedules: List[Tuple[List[Any], Counters, bool, bool, Resource]] = []

    @property
    def schedules(self):
        """已登记的抽卡计划列表（只读属性）。
        
        Returns
        -------
        list of tuple
            每个元素为五元组(rules, counters, check_in, use_origeometry, resource_inc)：
            
            rules : list
                策略描述列表，传入GachaStrategy构造函数。
            counters : Counters
                起始计数器。
            check_in : bool
                是否视为已签到（影响特许凭证获取）。
            use_origeometry : bool
                是否允许消耗源石换算为抽卡。
            resource_inc : Resource
                在本计划开始前额外发放的资源。
        """
        return self.__schedules

    @schedules.setter
    def schedules(self, value):
        """设置抽卡计划集合。
        
        Parameters
        ----------
        value : list
            由若干五元组组成的列表，结构同只读属性schedules。
            
        Raises
        ------
        ValueError
            当传入的值不是列表时抛出。
        """
        if not isinstance(value, list):
            raise ValueError("Schedules must be a list")
        else:
            self.__schedules = value

    def schedule(
        self,
        rules: List[Any],
        resource_increment: Resource | None = None,
        init_counters: Counters | None = None,
        check_in: bool = True,
        use_origeometry: bool = False,
    ):
        """追加一段抽卡计划。
        
        每次调用会在内部schedules列表末尾添加一个计划。在evaluate调用中，
        这些计划会按顺序依次执行。
        
        Parameters
        ----------
        rules : list
            策略描述列表，直接传入GachaStrategy构造函数。
        resource_increment : Resource, optional
            在本计划开始前额外增加的资源。为None时使用默认增量。
        init_counters : Counters, optional
            初始计数器。第一个计划可承接已有进度，后续计划为None时
            自动继承上一计划的部分计数。
        check_in : bool, optional
            是否视为完成签到任务，影响增加的特许凭证数量，默认True。
        use_origeometry : bool, optional
            是否允许在券与特许凭证不足时继续消耗源石进行换算抽卡，默认False。
            
        Notes
        -----
        - 建议在调用evaluate之前先连续调用本方法，构造完整抽卡流程。
        - 本方法不进行任何模拟，仅记录配置。
        
        See Also
        --------
        evaluate : 执行大规模评估
        simulate : 单次可视化模拟
        """
        self.schedules.append(
            (
                rules,
                init_counters if init_counters else Counters(),
                check_in,
                use_origeometry,
                (resource_increment if resource_increment else self.increment),
            )
        )

    def simulate(self, change: bool = True, display: bool = True):
        """按当前计划执行一次顺序模拟，并可选地打印详细过程。
        
        Parameters
        ----------
        change : bool, optional
            是否在不同计划之间切换至对应的卡池配置，默认True。
            为False时所有计划都使用第一个配置文件。
        display : bool, optional
            是否在标准输出中打印每步抽卡过程与结果，默认True。
            
        Returns
        -------
        None
            本方法主要用于调试与验证策略，不返回统计结果。
            
        Notes
        -----
        - 输出包含每个banner的卡池名称、UP角色、计数器和资源状态。
        - 6星角色用星号(*)标记，加急招募结果用井号(#)标记。
        - 适合小规模测试和策略逻辑验证。
        """
        counters: Counters = Counters()
        outputs: List[List[Tuple[str, int, bool]]] = []

        dossier = False

        for idx, plan in enumerate(self.schedules):
            rules: list = plan[0]
            cnts: Counters = plan[1] if idx == 0 else counters
            check: bool = plan[2]
            use_ori: bool = plan[3]
            addition: Resource = plan[4]

            output: List[Tuple[str, int, bool]] = []

            config = GlobalConfigLoader(
                os.path.join(
                    self.config_dir,
                    self.arrangement[idx] if change else self.arrangement[0],
                )
            )
            gacha = CharGacha(config)
            gacha.counters = cnts
            self.resource.chartered_permits += (
                5 * int(check) + 10 * int(dossier) + addition.chartered_permits
            )
            self.resource.oroberyl += addition.oroberyl
            self.resource.arsenal_tickets += addition.arsenal_tickets
            self.resource.origeometry += addition.origeometry
            strategy = GachaStrategy(rules)
            state = initialize_banner_state(cnts)

            if display:
                print(
                    idx + 1,
                    gacha.config.get_text("char_pool_name"),
                    gacha._get_up_char()[0],
                )
                print(gacha.counters)
                print(self.resource)
                print()

            potential = 0

            while not (strategy.terminate(gacha.counters.total, state)):
                if not consume_resource(self.resource, use_ori):
                    break

                result = gacha.attempt()
                output.append((result.name, result.star, False))

                state, potential = process_gacha_result(
                    result, gacha, state, potential
                )

                if gacha.counters.total == 30 and not cnts.urgent_used:
                    state, potential, urgent_results = handle_urgent_gacha(
                        config, gacha, cnts, state, potential
                    )
                    for result in urgent_results:
                        output.append((result.name, result.star, True))
                    continue

            outputs.append(output)
            dossier = gacha.counters.total >= 60
            counters = Counters(
                0,
                gacha.counters.no_6star,
                gacha.counters.no_5star_plus,
                0,
                False,
                False,
            )

        if display:
            for index, item in enumerate(outputs):
                print(f"Banner {index + 1}")
                cnt = 0
                for i in range(len(item)):
                    cnt += int(not item[i][2])
                    if item[i][1] == 6:
                        print("* ", end="")
                    print(cnt if not item[i][2] else "#", item[i][0])

    def evaluate(
        self, scale: int = 20000, change: bool = True, workers: int | None = None
    ):
        """进行大规模多进程模拟并输出详细统计报告。
        
        Parameters
        ----------
        scale : int, optional
            模拟次数（样本数量），即worker被调用的总次数，默认20000。
        change : bool, optional
            是否在各计划间切换卡池配置，与simulate中参数含义一致，默认True。
        workers : int or None, optional
            进程数。为None时自动设为max(1, min(int(cpu_count() * 0.75), 4))；
            若指定值大于cpu_count()，则会被裁剪到CPU核心数。
            
        Returns
        -------
        None
            计算结果通过Rich表格与面板直接输出到终端，不以返回值形式提供。
            
        Notes
        -----
        - 使用multiprocessing.Pool与imap进行流式处理，在较大样本规模下
          仍保持较低内存占用。
        - 统计汇总与评分计算由_print_statistics完成。
        - 输出包含：总抽数、6星数、UP角色数、资源使用、评分等级等。
        
        Examples
        --------
        >>> scheduler = Scheduler()
        >>> scheduler.schedule([DOSSIER, OPRT])
        >>> scheduler.evaluate(scale=10000, workers=4)
        
        See Also
        --------
        simulate : 单次可视化模拟
        """
        if workers is None:
            workers = max(1, min(int(cpu_count() * 0.75), 4))
        elif workers > cpu_count():
            workers = cpu_count()

        schedules_data = []
        for plan in self.schedules:
            schedules_data.append(
                {
                    "rules": plan[0],
                    "init_counters": {
                        "total": plan[1].total,
                        "no_6star": plan[1].no_6star,
                        "no_5star_plus": plan[1].no_5star_plus,
                        "no_up": plan[1].no_up,
                        "guarantee_used": plan[1].guarantee_used,
                        "urgent_used": plan[1].urgent_used,
                    },
                    "check_in": plan[2],
                    "use_origeometry": plan[3],
                    "resource_increment": {
                        "chartered_permits": plan[4].chartered_permits,
                        "oroberyl": plan[4].oroberyl,
                        "arsenal_tickets": plan[4].arsenal_tickets,
                        "origeometry": plan[4].origeometry,
                    },
                }
            )

        self._print_header(scale, workers, change, schedules_data)

        tasks = [
            (
                self.config_dir,
                self.arrangement,
                schedules_data,
                change,
                i,
                {
                    "chartered_permits": self.resource.chartered_permits,
                    "oroberyl": self.resource.oroberyl,
                    "arsenal_tickets": self.resource.arsenal_tickets,
                    "origeometry": self.resource.origeometry,
                },
            )
            for i in range(scale)
        ]

        if not tasks:
            console.print("[red]  无模拟任务需要执行[/red]")
            return

        start_time = time.time()
        results = []

        with Pool(processes=workers) as pool:
            with Progress(
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
            ) as progress:
                task = progress.add_task("模拟进度", total=scale)
                try:
                    batch_size = max(1, scale // 100)
                    batch_results = []
                    for result in pool.imap(_worker_wrapper, tasks):
                        batch_results.append(result)
                        if len(batch_results) >= batch_size:
                            results.extend(batch_results)
                            progress.update(task, advance=len(batch_results))
                            batch_results = []
                    if batch_results:
                        results.extend(batch_results)
                        progress.update(task, advance=len(batch_results))
                except Exception as e:
                    console.print(f"[red]  模拟过程中发生错误: {e}[/red]")
                    raise

        elapsed_time = time.time() - start_time
        self._print_statistics(results, elapsed_time, workers)

    def _print_header(
        self, scale: int, workers: int, change: bool, schedules_data: list
    ):
        """打印评估任务的配置概览。"""
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

        rules = [plan["rules"] for plan in schedules_data]
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

    def _print_statistics(
        self, results: List[Dict[str, Any]], elapsed_time: float, workers: int
    ):
        """根据 worker 返回结果打印统计与评分报告。"""
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

        new_scores = [
            ScoringSystem.calculate_score(
                r["total_draws"],
                r["six_stars"],
                r["up_chars"],
                r["resource_left"],
                r["complete"],
                len(self.schedules),
            )
            for r in results
        ]

        new_score_values = [s["total_score"] for s in new_scores]
        new_score_avg = sum(new_score_values) / total
        grade_distribution = {}
        for s in new_scores:
            grade = s["grade"]
            grade_distribution[grade] = grade_distribution.get(grade, 0) + 1

        console.print()

        summary_panel = Panel(
            Columns(
                [
                    Panel(
                        f"[bold green]{complete_rate:.1f}%[/bold green]\n可行度",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold yellow]{new_score_avg * complete_rate / 100:.1f}[/bold yellow]\n综合评分",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        f"[bold yellow]{sum(resource_left)/total:.1f}[/bold yellow]\n资源剩余",
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

        import statistics

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
            f"[bold]{sum(resource_left)/total:.0f}[/bold]",
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

        luck_avg = sum(s["luck_score"] for s in new_scores) / total
        storage_avg = sum(s["storage_score"] for s in new_scores) / total
        ach_avg = sum(s["achievement_score"] for s in new_scores) / total

        score_table.add_row(
            "获取评估", f"{luck_avg:.1f}", "45", f"{luck_avg/45*100:.1f}%"
        )
        score_table.add_row(
            "资源保有", f"{storage_avg:.1f}", "35", f"{storage_avg/35*100:.1f}%"
        )
        score_table.add_row(
            "目标达成", f"{ach_avg:.1f}", "20", f"{ach_avg/20*100:.1f}%"
        )
        score_table.add_row(
            "[bold]整体评分[/bold]",
            f"[bold]{new_score_avg:.1f}[/bold]",
            "100",
            f"[bold]{new_score_avg:.1f}%[/bold]",
        )
        console.print(score_table)
        console.print()

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

        percentile_table = Table(
            title="[bold]百分位统计[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        percentile_table.add_column("分位", style="bold", ratio=1)
        percentile_table.add_column("综合评分", justify="right", ratio=2)
        percentile_table.add_column("总抽数", justify="right", ratio=2)
        percentile_table.add_column("6星数", justify="right", ratio=2)

        percentiles = [10, 25, 50, 75, 90, 95, 99]
        for p in percentiles:
            percentile_table.add_row(
                f"P{p}",
                f"{self._percentile(new_score_values, p):.1f}",
                f"{self._percentile(total_draws, p):.0f}",
                f"{self._percentile(six_stars, p):.0f}",
            )
        console.print(percentile_table)
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

        sim_per_sec = total / elapsed_time if elapsed_time > 0 else 0
        cpu_efficiency = (workers / cpu_count() * 100) if cpu_count() > 0 else 0

        perf_table.add_row(
            "模拟速度", f"{sim_per_sec:,.0f} 次/秒", "每秒完成的模拟次数"
        )
        perf_table.add_row(
            "进程利用率", f"{cpu_efficiency:.1f}%", f"使用 {workers}/{cpu_count()} 核心"
        )
        perf_table.add_row(
            "平均单次耗时", f"{elapsed_time/total*1000:.2f} ms", "单次模拟平均耗时"
        )
        perf_table.add_row("内存效率", "良好", "使用流式处理，内存占用低")

        footer = Panel(
            Text("报告结束", style="bold", justify="center"),
            box=box.DOUBLE,
            style="bold blue",
        )
        console.print(footer)

    def _percentile(self, data: List, p: float) -> float:
        """计算列表数据的近似分位数。"""
        sorted_data = sorted(data)
        idx = int(len(data) * p / 100)
        if idx >= len(sorted_data):
            idx = len(sorted_data) - 1
        return sorted_data[idx]


def main():
    """模块自测与示例入口。"""
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 6975 // 75),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule([[DOSSIER, [URGENT, LE ^ 43, UP_OPRT]]])
    scheduler.schedule([DOSSIER, OPRT])
    scheduler.schedule([DOSSIER, UP_OPRT], use_origeometry=True)
    scheduler.schedule([DOSSIER, OPRT])

    scheduler.evaluate(scale=5000, workers=16)


if __name__ == "__main__":
    main()
