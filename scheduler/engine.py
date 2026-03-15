# -*- coding: utf-8 -*-
"""策略规划器核心逻辑。

提供多卡池策略规划、大规模并行评估和可视化统计功能。

主要功能：
- 多卡池连续模拟（支持配置切换）
- 大规模并行评估（多进程优化）
- 详细的统计报告输出（使用Rich库美化）
- 策略性能评分系统
"""

from multiprocessing import Pool, cpu_count
from typing import Any, Dict, List, Tuple, Optional
from dataclasses import dataclass
import time, os

from core import Counters

from scheduler.display import SchedulerDisplay
from scheduler.scoring import Resource, ScoringSystem
from scheduler.workers import _worker_wrapper


@dataclass
class BannerPlan:
    """单个卡池计划的数据类。

    用于存储单个卡池的完整配置信息，包括策略规则、资源配置、卡池名称等。

    Attributes
    ----------
    rules : List[Any]
        策略规则列表，传入 GachaStrategy 构造函数。
    init_counters : Counters
        初始计数器对象。
    check_in : bool
        是否视为完成签到任务，影响特许凭证获取。
    use_origeometry : bool
        是否允许消耗源石换算为抽卡资源。
    resource_increment : Resource
        计划开始前额外发放的资源增量。
    is_core : bool
        是否为核心计划。
    name : Optional[str], optional
        卡池配置名称，对应 configs/ 目录下的配置文件夹名，
        如 "config_1"、"config_3" 等。
    """

    rules: List[Any]
    init_counters: Counters
    check_in: bool
    use_origeometry: bool
    resource_increment: Resource
    is_core: bool
    name: Optional[str] = None


class Scheduler:
    """策略规划器：多卡池策略评估总控类。

    负责从配置目录加载卡池配置，组织多段抽卡计划，提供单次可视化模拟
    和大规模并行评估两种模式。支持配置切换、资源管理和详细的统计报告。

    Attributes
    ----------
    config_dir : str
        配置文件目录路径，默认 "configs"。
    arrangement : List[str]
        卡池配置顺序列表，从 arrange 文件中读取。
    resource : Resource
        当前可用的抽卡资源对象。
    increment : Resource
        每日/每阶段默认资源增量对象。
    __schedules : Dict[str, BannerPlan]
        按名称存储的抽卡计划字典。
    __schedule_order : List[str]
        抽卡计划的执行顺序列表。

    Examples
    --------
    >>> from scheduler import Scheduler, Resource, Counters, DOSSIER, UP_OPRT
    >>> scheduler = Scheduler(
    ...     config_dir="configs",
    ...     arrange="arrange1",
    ...     resource=Resource(2, 61000, 6000, 100)
    ... )
    >>> # 使用名称指定卡池
    >>> scheduler.banner([DOSSIER, OPRT], name="config_3")
    >>> scheduler.banner([UP_OPRT], name="config_5", use_origeometry=True)
    >>> # 或者批量添加
    >>> cycles = [
    ...     {"rules": [DOSSIER, OPRT], "name": "config_3"},
    ...     {"rules": [UP_OPRT], "name": "config_5", "use_ori": True},
    ... ]
    >>> scheduler.banners(cycles)
    >>> # 执行评估（会自动校验计划）
    >>> scheduler.evaluate(scale=5000, workers=8)

    Notes
    -----
    - 多进程评估使用 ``multiprocessing.Pool``，支持流式处理，内存占用较低
    - 统计报告使用 Rich 库美化输出，支持颜色和表格格式
    - 支持配置切换：每个计划可以通过 name 参数指定不同的卡池配置
    - 执行 evaluate() 前会自动调用 _validate_schedules() 进行完整校验
    """

    def __init__(
        self,
        config_dir: str = "configs",
        arrange: str = "arrangement",
        resource: Resource | None = None,
        increment: Resource | None = None,
    ):
        """初始化策略规划器。

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
            - 嵌晶玉: 22500 (45 * 500)
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
        self.__schedules: Dict[str, BannerPlan] = {}  # 按名称存储的计划
        self.__schedule_order: List[str] = []  # 计划的执行顺序

    @property
    def schedules(self):
        """已登记的抽卡计划列表（按执行顺序）。

        Returns
        -------
        list of BannerPlan
            按执行顺序排列的计划列表。
        """
        return [self.__schedules[name] for name in self.__schedule_order]

    @schedules.setter
    def schedules(self, value):
        """设置抽卡计划集合。

        Parameters
        ----------
        value : list
            由 BannerPlan 对象组成的列表。

        Raises
        ------
        ValueError
            当传入的值格式不正确时抛出。
        """
        self.__schedules = {}
        self.__schedule_order = []

        if not isinstance(value, list):
            raise ValueError("Schedules must be a list")

        for idx, item in enumerate(value):
            if not isinstance(item, BannerPlan):
                raise ValueError(
                    f"Invalid schedule type at index {idx}: expected BannerPlan, got {type(item)}"
                )

            plan_name = item.name or f"plan_{idx}"
            self.__schedules[plan_name] = item
            self.__schedule_order.append(plan_name)

    def banner(
        self,
        rules: List[Any],
        name: str | None = None,
        resource_increment: Resource | None = None,
        init_counters: Counters | None = None,
        check_in: bool = True,
        use_origeometry: bool = False,
        is_core: bool = True,
    ):
        """追加一段抽卡计划。

        每次调用会在内部计划列表末尾添加一个计划。在 evaluate 调用中，
        这些计划会按添加顺序依次执行。

        Parameters
        ----------
        rules : List[Any]
            策略规则列表，直接传入 GachaStrategy 构造函数。
        name : Optional[str], optional
            卡池配置名称，对应 configs/ 目录下的配置文件夹名，
            如 "config_1"、"config_3" 等。若不指定则按 arrangement 顺序自动分配。
        resource_increment : Optional[Resource], optional
            在本计划开始前额外发放的资源增量。为 None 时使用默认增量。
        init_counters : Optional[Counters], optional
            初始计数器对象。第一个计划可承接已有进度，后续计划为 None 时
            自动继承上一计划的部分计数。
        check_in : bool, optional
            是否视为完成签到任务，影响特许凭证获取数量，默认为 True。
        use_origeometry : bool, optional
            是否允许在券与特许凭证不足时继续消耗源石进行换算抽卡，默认为 False。
        is_core : bool, optional
            是否为核心计划，默认为 True。

        Notes
        -----
        - 建议在调用 evaluate() 之前先连续调用本方法，构造完整的抽卡流程。
        - 本方法不进行任何模拟，仅记录计划配置。
        - 若指定了 name 参数，则该计划绑定到对应的卡池配置。
        """
        plan = BannerPlan(
            rules=rules,
            init_counters=init_counters if init_counters else Counters(),
            check_in=check_in,
            use_origeometry=use_origeometry,
            resource_increment=(
                resource_increment if resource_increment else self.increment
            ),
            is_core=is_core,
            name=name,
        )

        # 确定计划名称
        if name:
            plan_name = name
        else:
            plan_name = f"plan_{len(self.__schedule_order)}"

        self.__schedules[plan_name] = plan
        self.__schedule_order.append(plan_name)

    def banners(
        self,
        cycles: List[Dict],
    ) -> None:
        """批量添加多个周期的策略配置。

        使用单个调用添加多个抽卡周期，提高代码简洁性和可读性。

        Parameters
        ----------
        cycles : List[Dict]
            周期配置列表，每个字典包含以下可选键：
            - rules: List[int] - 策略规则列表（必需）
            - name: Optional[str] - 卡池配置名称，如 "config_3"
            - counters: Optional[Counters] - 初始计数器对象
            - check_in: bool - 是否签到，默认为 True
            - increment: Resource - 资源增量，默认为空资源
            - use_ori: bool - 是否使用源石，默认为 False
            - is_core: bool - 是否为核心计划，默认为 True

        Raises
        ------
        ValueError
            如果 cycles 参数不是列表或包含无效配置时抛出，
            或缺少必需的 "rules" 键时抛出。

        Examples
        --------
        >>> scheduler = Scheduler()
        >>> # 批量添加计划，部分指定卡池名称
        >>> cycles = [
        ...     {"rules": [DOSSIER, OPRT], "name": "config_3"},
        ...     {"rules": [UP_OPRT], "name": "config_5", "use_ori": True},
        ...     {"rules": [DOSSIER, OPRT], "check_in": False},
        ... ]
        >>> scheduler.banners(cycles)

        See Also
        --------
        banner : 添加单个计划的原始方法
        """
        if not isinstance(cycles, list):
            raise ValueError("cycles must be a list")

        for cycle_config in cycles:
            if not isinstance(cycle_config, dict):
                raise ValueError(f"Invalid cycle config: {cycle_config}")

            rules = cycle_config.get("rules")
            if rules is None:
                raise ValueError(f"Missing 'rules' key in cycle config: {cycle_config}")

            init_counters = cycle_config.get("counters")
            check_in = cycle_config.get("check_in", True)
            resource_increment = cycle_config.get("increment", Resource())
            use_origeometry = cycle_config.get("use_ori", False)
            is_core = cycle_config.get("is_core", True)
            name = cycle_config.get("name")

            self.banner(
                rules=rules,
                name=name,
                init_counters=init_counters,
                check_in=check_in,
                resource_increment=resource_increment,
                use_origeometry=use_origeometry,
                is_core=is_core,
            )

    def _build_schedules_data(self) -> List[Dict[str, Any]]:
        """构造规划计划的序列化数据，用于多进程 worker 传递。

        将 BannerPlan 对象转换为可序列化的字典格式，便于在多进程间传递。

        Returns
        -------
        List[Dict[str, Any]]
            序列化后的规划计划列表，每个元素包含一个计划的所有配置信息，
            包括 rules、init_counters、check_in、use_origeometry、
            resource_increment 和 name。
        """
        schedules_data = []
        for plan in self.schedules:
            schedules_data.append(
                {
                    "rules": plan.rules,
                    "init_counters": {
                        "total": plan.init_counters.total,
                        "no_6star": plan.init_counters.no_6star,
                        "no_5star_plus": plan.init_counters.no_5star_plus,
                        "no_up": plan.init_counters.no_up,
                        "guarantee_used": plan.init_counters.guarantee_used,
                        "urgent_used": plan.init_counters.urgent_used,
                    },
                    "check_in": plan.check_in,
                    "use_origeometry": plan.use_origeometry,
                    "resource_increment": {
                        "chartered_permits": plan.resource_increment.chartered_permits,
                        "oroberyl": plan.resource_increment.oroberyl,
                        "arsenal_tickets": plan.resource_increment.arsenal_tickets,
                        "origeometry": plan.resource_increment.origeometry,
                    },
                    "name": plan.name,
                }
            )
        return schedules_data

    def _validate_schedules(self):
        """校验计划的完整性和一致性。

        在执行 evaluate() 前自动调用，确保所有计划配置正确无误。
        执行以下四项校验：

        1. **名称存在性校验**：检查所有指定的卡池名称是否存在于安排文件中
        2. **数量对应校验**：确保未命名计划数量不超过剩余可用卡池数量
        3. **名称冲突校验**：检查是否有多个计划指定了同一个卡池名称
        4. **完整性校验**：检查安排文件中的卡池是否都有对应的计划（仅警告）

        Raises
        ------
        ValueError
            当校验失败时抛出异常，包含详细的错误信息
        """
        named_plans: Dict[str, int] = {}  # 按名称存储的计划 -> 索引映射
        unnamed_plans: List[int] = []  # 未指定名称的计划索引列表

        # 步骤 1：收集所有计划信息，同时检查名称冲突
        for idx, plan in enumerate(self.schedules):
            plan_name = plan.name
            if plan_name:
                # 检查名称是否重复
                if plan_name in named_plans:
                    raise ValueError(
                        f"计划名称冲突：卡池 '{plan_name}' 被多个计划指定（索引 {named_plans[plan_name]} 和 {idx}）"
                    )
                named_plans[plan_name] = idx
            else:
                unnamed_plans.append(idx)

        # 步骤 2：校验所有指定的名称是否存在于安排文件中
        for plan_name in named_plans:
            if plan_name not in self.arrangement:
                raise ValueError(
                    f"指定的卡池名称 '{plan_name}' 不在安排文件中。可用名称: {self.arrangement}"
                )

        # 步骤 3：计算剩余可用卡池（已被命名计划占用的卡池不可再分配给未命名计划）
        used_pools = set(named_plans.keys())
        remaining_pools = [pool for pool in self.arrangement if pool not in used_pools]

        # 步骤 4：校验未命名计划数量是否超过剩余可用卡池数量
        if len(unnamed_plans) > len(remaining_pools):
            raise ValueError(
                f"计划数量超过可用卡池数量。"
                f"已指定名称的计划: {len(named_plans)} 个 ({list(named_plans.keys())}), "
                f"未指定名称的计划: {len(unnamed_plans)} 个, "
                f"剩余可用卡池: {len(remaining_pools)} 个 ({remaining_pools})"
            )

        # 步骤 5：完整性检查 - 警告用户未被规划的卡池（不抛出异常）
        total_planned = len(named_plans) + len(unnamed_plans)
        if total_planned < len(self.arrangement):
            unplanned_pools = self.arrangement[total_planned:]
            SchedulerDisplay.print(
                f"[yellow]警告: 安排文件中有 {len(unplanned_pools)} 个卡池未被规划: {unplanned_pools}[/yellow]"
            )

    def _build_tasks(
        self, schedules_data: List[Dict[str, Any]], change: bool, scale: int
    ) -> List[Tuple]:
        """构造多进程任务列表。

        为每个模拟生成一个独立的任务元组，包含所有必要的参数，
        便于多进程 worker 并行执行。

        Parameters
        ----------
        schedules_data : List[Dict[str, Any]]
            从 `_build_schedules_data()` 返回的序列化规划计划列表。
        change : bool
            是否在计划间切换卡池配置。
        scale : int
            总模拟次数。

        Returns
        -------
        List[Tuple]
            多进程任务列表，每个元素是传递给 worker 的参数元组，
            包含：config_dir, arrangement, schedules_data, change, seed, resource_data。
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
        """把 worker 返回的原始结果转换为评分系统需要的格式。

        将 worker 输出的简化格式转换为 `ScoringSystem.calculate_raw_statistics()`
        所需的完整格式，包括分级目标达成信息、资源信息等。

        Parameters
        ----------
        results : List[Dict[str, Any]]
            worker 返回的原始模拟结果列表，每个结果包含：
            - total_draws: 总抽数
            - six_stars: 6星数量
            - up_chars: UP角色数量
            - resource_left: 剩余资源
            - complete: 是否完成

        Returns
        -------
        List[Dict[str, Any]]
            适配后的结果列表，符合 `ScoringSystem.calculate_raw_statistics()` 的输入要求，
            包含：draws, six_stars, up_chars, current_up, past_up, permanent,
            resource_left, flex_resource, goals_achieved。
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

    def evaluate(
        self,
        scale: int = 20000,
        change: bool = True,
        workers: int | None = None,
        scoring_mode: str = "relative",
        weights: Optional[Dict[str, Dict[str, float]]] = None,
        show_progress: bool = True,
    ):
        """进行大规模多进程模拟并输出详细统计报告。

        在执行模拟前会自动调用 `_validate_schedules()` 进行完整的计划校验。
        支持多进程并行模拟，使用 Rich 库输出美观的进度条和统计报告。

        Parameters
        ----------
        scale : int, optional
            模拟次数（样本数量），即 worker 被调用的总次数，默认为 20000。
        change : bool, optional
            是否在各计划间切换卡池配置，默认为 True。
            若为 True，则按 arrangement 顺序或 name 参数指定的配置切换；
            若为 False，则所有计划都使用第一个配置。
        workers : Optional[int], optional
            并行进程数。
            若为 None，则自动设为 max(1, int(cpu_count() * 0.75))；
            若指定值大于 cpu_count()，则会被裁剪到 CPU 核心数。
        scoring_mode : str, optional
            评分模式，可选 "relative"（相对评分，默认）或 "absolute"（绝对评分）。
            - 相对模式：基于策略组内相对表现评分，适合同组策略对比
            - 绝对模式：基于绝对阈值评分，适合跨组策略评估
        weights : Optional[Dict[str, Dict[str, float]]], optional
            自定义评分权重配置，用于覆盖默认评分权重。
            结构示例：
            {
                "dim": {"u": 0.4, "e": 0.2, "r": 0.25, "f": 0.15},
                "star": {"current_up": 3, "past_up": 2, "permanent": 1}
            }
            若为 None，则使用默认权重。
        show_progress : bool, optional
            是否显示进度条，默认为 True。
            若为 True，使用 `pool.imap()` 流式处理并显示进度；
            若为 False，使用 `pool.map()` 批量处理，效率更高。

        Returns
        -------
        Optional[NativeStatistics]
            单策略模式下返回计算得到的原生统计量对象，
            结果同时直接输出到终端。

        Notes
        -----
        - 执行前自动调用 `_validate_schedules()` 进行完整的计划校验
        - 显示进度时使用 `multiprocessing.Pool.imap()` 进行流式处理，
          内存占用较低；不显示进度时使用 `Pool.map()` 效率更高
        - 统计汇总与评分计算由 `ScoringSystem` 类完成
        - 输出包含：总抽数、6星数、UP角色数、资源使用、评分等级等
        - 四维评分体系：目标达成效用40%、资源利用效率20%、
          风险控制能力25%、策略灵活性15%
        - 3:2:1价值权重：当期UP:往期UP:常驻6星

        Examples
        --------
        >>> from scheduler import Scheduler, DOSSIER, OPRT, UP_OPRT
        >>> scheduler = Scheduler()
        >>> # 添加计划，使用 name 参数指定卡池
        >>> scheduler.banner([DOSSIER, OPRT], name="config_3")
        >>> scheduler.banner([UP_OPRT], name="config_5")
        >>> # 执行评估
        >>> raw_stats = scheduler.evaluate(scale=10000, workers=8)
        >>> print(f"核心目标达成概率: {raw_stats.p_core * 100:.1f}%")
        """
        # 参数校验
        if scale <= 0:
            raise ValueError("scale must be greater than 0")
        if workers is not None and workers < 0:
            raise ValueError("workers must be a non-negative integer")

        if workers is None:
            workers = max(1, int(cpu_count() * 0.75))
        if workers > cpu_count():
            workers = cpu_count()

        # 执行完整校验
        self._validate_schedules()

        # 策略评估逻辑
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
                        SchedulerDisplay.print(
                            f"[bold red]模拟过程中发生错误: {e}[/red bold]"
                        )
                        raise
            else:
                try:
                    SchedulerDisplay.print(f"[bold green]模拟已启动...[/green bold]")
                    results = pool.map(_worker_wrapper, tasks)
                except Exception as e:
                    SchedulerDisplay.print(
                        f"[bold red]模拟过程中发生错误: {e}[/red bold]"
                    )
                    raise

        elapsed_time = time.time() - start_time

        # 转换结果为评分系统所需格式
        adapted_results = self._adapt_results(results)
        raw_stats = ScoringSystem.calculate_raw_statistics(adapted_results)

        # 计算初始总资源折算为标准抽数（k_total）
        # 角色池抽卡折算：
        # - 特许寻访凭证：1抽/张
        # - 嵌晶玉：1抽/500个
        # - 衍质源石：1抽/约6.67个（1源石=75嵌晶玉）
        # 加上所有计划的资源增量
        initial_char_draws = (
            self.resource.chartered_permits
            + self.resource.oroberyl // 500
            + (self.resource.origeometry * 75) // 500
        )
        # 加上每个计划的资源增量
        total_increment_draws = 0
        for plan in self.schedules:
            total_increment_draws += (
                plan.resource_increment.chartered_permits
                + plan.resource_increment.oroberyl // 500
                + (plan.resource_increment.origeometry * 75) // 500
            )
        k_total = float(initial_char_draws + total_increment_draws)
        # 确保k_total至少为100（避免过小值导致评分异常）
        k_total = max(k_total, 100.0)

        # 打印统计报告
        comprehensive_scores = ScoringSystem.calculate_comprehensive_score(
            [raw_stats], mode="absolute", k_total=k_total
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
