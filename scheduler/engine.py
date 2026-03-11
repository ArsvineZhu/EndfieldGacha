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
import sys

# 添加项目根目录到路径，确保可以直接运行
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from multiprocessing import Pool, cpu_count
from typing import Any, Dict, List, Tuple, Optional
import time

from scheduler.display import SchedulerDisplay

from core import CharGacha, Counters, GlobalConfigLoader

# Use absolute imports for consistency
from scheduler.scoring import Resource, ScoringSystem
from scheduler.strategy import (
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
from scheduler.workers import (
    get_token,
    consume_resource,
    process_gacha_result,
    handle_urgent_gacha,
    initialize_banner_state,
    _worker_wrapper,
)


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
            - 武库配额: 800
            - 衍质源石: 25
        """
        self.config_dir = config_dir
        self.increment = (
            increment
            if increment
            else Resource(
                chartered_permits=5,
                oroberyl=45 * 500,
                arsenal_tickets=800,
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
        self.__schedules: List[
            Tuple[List[Any], Counters, bool, bool, Resource, bool]
        ] = []

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
        is_core: bool = True,
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
                is_core,
            )
        )

    def add_cycle(
        self,
        rules: List[int],
        init_counters: Optional[Counters] = None,
        check_in: bool = True,
        resource_increment: Resource = Resource(),
        use_origeometry: bool = False,
        is_core: bool = True,
    ) -> None:
        """添加单个周期的策略配置。

        本方法是对 schedule() 方法的别名，提供更符合直觉的命名。

        Parameters
        ----------
        rules : List[int]
            策略描述列表，直接传入 GachaStrategy 构造函数。
        init_counters : Counters, optional
            初始计数器。第一个周期可承接已有进度，后续周期为 None 时
            自动继承上一周期的部分计数。
        check_in : bool, optional
            是否视为完成签到任务，影响增加的特许凭证数量，默认 True。
        resource_increment : Resource, optional
            在本周期开始前额外增加的资源。默认使用空资源对象。
        use_origeometry : bool, optional
            是否允许在券与特许凭证不足时继续消耗源石进行换算抽卡，默认 False.

        See Also
        --------
        schedule : 功能相同的原始方法
        schedule_group : 批量添加多个周期
        """
        self.schedule(
            rules=rules,
            init_counters=init_counters,
            check_in=check_in,
            resource_increment=resource_increment,
            use_origeometry=use_origeometry,
            is_core=is_core,
        )

    def schedule_group(
        self,
        cycles: List[Dict],
    ) -> None:
        """批量添加多个周期的策略配置。

        使用单个调用添加多个抽卡周期，提高代码简洁性。

        Parameters
        ----------
        cycles : List[Dict]
            周期配置列表，每个字典包含以下可选键：
            - rules: List[int] - 策略规则列表
            - init_counters: Optional[Counters] - 初始计数器
            - check_in: bool - 是否签到，默认 True
            - resource_increment: Resource - 资源增量，默认空资源
            - use_origeometry: bool - 是否使用源石，默认 False

        Raises
        ------
        ValueError
            如果 cycles 参数不是列表或包含无效配置时抛出。

        Examples
        --------
        >>> scheduler = Scheduler()
        >>> cycles = [
        ...     {"rules": [DOSSIER, OPRT]},
        ...     {"rules": [UP_OPRT], "use_origeometry": True},
        ...     {"rules": [DOSSIER, OPRT], "check_in": False},
        ... ]
        >>> scheduler.schedule_group(cycles)

        See Also
        --------
        schedule : 添加单个计划的原始方法
        add_cycle : 添加单个周期的别名方法
        """
        if not isinstance(cycles, list):
            raise ValueError("cycles must be a list")

        for cycle_config in cycles:
            if not isinstance(cycle_config, dict):
                raise ValueError(f"Invalid cycle config: {cycle_config}")

            rules = cycle_config.get("rules")
            if rules is None:
                raise ValueError(f"Missing 'rules' key in cycle config: {cycle_config}")

            init_counters = cycle_config.get("init_counters")
            check_in = cycle_config.get("check_in", True)
            resource_increment = cycle_config.get("resource_increment", Resource())
            use_origeometry = cycle_config.get("use_origeometry", False)
            is_core = cycle_config.get("is_core", True)

            self.add_cycle(
                rules=rules,
                init_counters=init_counters,
                check_in=check_in,
                resource_increment=resource_increment,
                use_origeometry=use_origeometry,
                is_core=is_core,
            )

    def _build_schedules_data(self) -> List[Dict[str, Any]]:
        """构造调度计划的序列化数据，用于多进程worker传递。

        Returns
        -------
        List[Dict[str, Any]]
            序列化后的调度计划列表，每个元素包含一个计划的所有配置信息
        """
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
        return schedules_data

    def _build_tasks(
        self, schedules_data: List[Dict[str, Any]], change: bool, scale: int
    ) -> List[Tuple]:
        """构造多进程任务列表。

        Parameters
        ----------
        schedules_data : List[Dict[str, Any]]
            从_build_schedules_data返回的序列化调度计划
        change : bool
            是否在计划间切换卡池配置
        scale : int
            模拟次数

        Returns
        -------
        List[Tuple]
            多进程任务列表，每个元素是传递给worker的参数元组
        """
        resource_data = {
            "chartered_permits": self.resource.chartered_permits,
            "oroberyl": self.resource.oroberyl,
            "arsenal_tickets": self.resource.arsenal_tickets,
            "origeometry": self.resource.origeometry,
        }

        return [
            (
                self.config_dir,
                self.arrangement,
                schedules_data,
                change,
                i,
                resource_data,
            )
            for i in range(scale)
        ]

    @staticmethod
    def _adapt_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """把worker返回的原始结果转换为评分系统需要的格式。

        Parameters
        ----------
        results : List[Dict[str, Any]]
            worker返回的原始模拟结果列表

        Returns
        -------
        List[Dict[str, Any]]
            适配后的结果列表，符合ScoringSystem.calculate_raw_statistics的输入要求
        """
        adapted_results = []
        for res in results:
            adapted_results.append(
                {
                    "draws": res["total_draws"],
                    "six_stars": res["six_stars"],
                    "up_chars": res["up_chars"],
                    "current_up": res["up_chars"],
                    "past_up": 0,
                    "permanent": res["six_stars"] - res["up_chars"],
                    "resource_left": res["resource_left"],
                    "flex_resource": res["resource_left"],
                    "goals_achieved": [
                        res["complete"],
                        res["complete"],
                        res["complete"],
                    ],
                }
            )
        return adapted_results

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
                    gacha.config.get_pool_info("char")["name"],
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

                state, potential = process_gacha_result(result, gacha, state, potential)

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
        self,
        scale: int = 20000,
        change: bool = True,
        workers: int | None = None,
        strategies: List[List[int]] | None = None,
        scoring_mode: str = "relative",
        weights: Optional[Dict[str, Dict[str, float]]] = None,
        show_progress: bool = True,
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
        strategies : List[List[int]] or None, optional
            多策略列表，每个元素为一个策略规则列表。如果提供此参数，将对每个策略
            独立进行模拟评估并输出对比报告。为None时使用当前已调度的策略。
        scoring_mode : str, optional
            评分模式，可选"relative"（相对评分，默认）或"absolute"（绝对评分），
            仅在多策略评估时生效。
        custom_weights : Dict[str, Dict[str, float]] or None, optional
             自定义权重配置，用于覆盖默认评分权重，仅在多策略评估时生效。
             注：此参数已过时，建议使用 weights 参数。
        weights : Dict[str, Dict[str, float]] or None, optional
             评分权重配置，用于覆盖默认评分权重，仅在多策略评估时生效。
             结构：
             {
                 "dimension_weights": {"u": 0.4, "e": 0.2, "r": 0.25, "f": 0.15},
                 "star_weights": {"current_up": 3, "past_up": 2, "permanent": 1}
             }
             如果为 None，则使用默认权重。

        Returns
        -------
        None or List[Dict[str, Any]]
            单策略模式下返回None，结果直接输出到终端；多策略模式下返回各策略的
            评分结果列表。

        Notes
        -----
        - 使用multiprocessing.Pool与imap进行流式处理，在较大样本规模下
          仍保持较低内存占用。
        - 统计汇总与评分计算由_print_statistics完成。
        - 输出包含：总抽数、6星数、UP角色数、资源使用、评分等级等。
        - 多策略模式下会输出策略对比报告，包含各策略的综合评分和排名。

        Examples
        --------
        >>> # 单策略模式（原有方式，兼容）
        >>> scheduler = Scheduler()
        >>> scheduler.schedule([DOSSIER, OPRT])
        >>> scheduler.evaluate(scale=10000, workers=4)

        >>> # 多策略模式
        >>> scheduler = Scheduler()
        >>> strategies = [
        ...     [DOSSIER, OPRT],
        ...     [DOSSIER, UP_OPRT],
        ...     [UP_OPRT, OPRT]
        ... ]
        >>> results = scheduler.evaluate(scale=5000, workers=4, strategies=strategies)

        See Also
        --------
        simulate : 单次可视化模拟
        """
        # 参数校验
        if scale <= 0:
            raise ValueError("scale must be greater than 0")
        if workers is not None and workers < 0:
            raise ValueError("workers must be a non-negative integer")
        if len(self.schedules) == 0 and strategies is None:
            SchedulerDisplay.print(
                "[yellow]警告：未添加任何调度计划，评估结果可能无意义[/yellow]"
            )

        if workers is None:
            workers = max(1, min(int(cpu_count() * 0.75), 4))
        elif workers > cpu_count():
            workers = cpu_count()

        # 多策略评估逻辑
        if strategies is not None:
            if not isinstance(strategies, list) or len(strategies) == 0:
                SchedulerDisplay.print("[red]  策略列表不能为空[/red]")
                return

            all_raw_stats = []
            all_strategy_results = []

            SchedulerDisplay.clear()
            SchedulerDisplay.print(
                f"[bold blue]=== 多策略对比评估报告 ===[/bold blue] {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            SchedulerDisplay.print("")
            SchedulerDisplay.print(
                f"[bold]  共 {len(strategies)} 个策略，每个策略模拟 {scale} 次[/bold]"
            )
            SchedulerDisplay.print(f"[bold]  评分模式: {scoring_mode}[/bold]")
            SchedulerDisplay.print("")

            for idx, strategy_rules in enumerate(strategies):
                SchedulerDisplay.print(
                    f"[cyan]  正在评估策略 {idx + 1}/{len(strategies)}...[/cyan]"
                )

                # 临时保存原始计划，设置当前策略
                original_schedules = self.schedules.copy()
                self.schedules = []
                self.schedule(strategy_rules)

                # 准备调度数据和任务列表
                schedules_data = self._build_schedules_data()
                tasks = self._build_tasks(schedules_data, change, scale)

                # 执行模拟
                start_time = time.time()
                results = []

                with Pool(processes=workers) as pool:
                    batch_size = max(1, scale // 100)
                    batch_results = []
                    for result in pool.imap(_worker_wrapper, tasks):
                        batch_results.append(result)
                        if len(batch_results) >= batch_size:
                            results.extend(batch_results)
                            batch_results = []
                    if batch_results:
                        results.extend(batch_results)

                elapsed_time = time.time() - start_time

                # 转换结果为评分系统所需格式
                adapted_results = self._adapt_results(results)

                # 计算原生统计量
                raw_stats = ScoringSystem.calculate_raw_statistics(adapted_results)
                all_raw_stats.append(raw_stats)

                # 保存策略结果
                all_strategy_results.append(
                    {
                        "strategy_id": f"S{idx + 1}",
                        "strategy_rules": strategy_rules,
                        "simulation_results": results,
                        "raw_stats": raw_stats,
                        "elapsed_time": elapsed_time,
                    }
                )

                # 恢复原始计划
                self.schedules = original_schedules
                SchedulerDisplay.print(
                    f"[green]  策略 {idx + 1} 评估完成，耗时 {elapsed_time:.1f}s[/green]"
                )

            SchedulerDisplay.print("")
            SchedulerDisplay.print(f"[cyan]  正在计算综合评分...[/cyan]")

            # 计算综合评分
            comprehensive_scores = ScoringSystem.calculate_comprehensive_score(
                all_raw_stats, mode=scoring_mode, weights=weights
            )

            # 打印多策略对比报告
            SchedulerDisplay.print_multi_strategy_report(
                all_strategy_results, comprehensive_scores, scoring_mode
            )

            return comprehensive_scores

        # 原有单策略评估逻辑
        schedules_data = self._build_schedules_data()
        tasks = self._build_tasks(schedules_data, change, scale)

        if not tasks:
            SchedulerDisplay.print("[red]  无模拟任务需要执行[/red]")
            return

        start_time = time.time()
        results = []

        with Pool(processes=workers) as pool:
            if show_progress:
                with SchedulerDisplay.create_progress() as progress:
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
                        SchedulerDisplay.print(f"[red]模拟过程中发生错误: {e}[/red]")
                        raise
            else:
                try:
                    batch_size = max(1, scale // 100)
                    batch_results = []
                    for result in pool.imap(_worker_wrapper, tasks):
                        batch_results.append(result)
                        if len(batch_results) >= batch_size:
                            results.extend(batch_results)
                            batch_results = []
                    if batch_results:
                        results.extend(batch_results)
                except Exception as e:
                    SchedulerDisplay.print(f"[red]模拟过程中发生错误: {e}[/red]")
                    raise

        elapsed_time = time.time() - start_time

        # 转换结果为评分系统所需格式
        adapted_results = self._adapt_results(results)
        raw_stats = ScoringSystem.calculate_raw_statistics(adapted_results)

        # 打印统计报告
        if show_progress:
            comprehensive_scores = ScoringSystem.calculate_comprehensive_score(
                [raw_stats], mode="absolute"
            )[0]
            SchedulerDisplay.print_header(scale, workers, change, self.schedules)
            SchedulerDisplay.print_statistics(
                results,
                elapsed_time,
                workers,
                raw_stats,
                comprehensive_scores,
                len(self.schedules),
            )

        return raw_stats

    def print_report(self, raw_stats, mode: str = "relative") -> None:
        """打印简洁的评估报告
        Args:
            raw_stats: 从evaluate方法返回的原始统计数据
            mode: 评分模式，"relative"或"absolute"
        """
        SchedulerDisplay.print_report(raw_stats, mode)


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
