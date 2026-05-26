# -*- coding: utf-8 -*-
"""策略规划器核心逻辑。"""

from __future__ import annotations

import os
import time
from copy import deepcopy
from dataclasses import dataclass
from multiprocessing import Pool, cpu_count
from typing import Any, Dict, List, Optional, Tuple

from gacha_core import Counters
from scheduler.display import SchedulerDisplay
from scheduler.scoring import (
    BaselineEstimator,
    Resource,
    ScoringPreferences,
    ScoringSystem,
    StrategyGoal,
    StrategyScoreReport,
    StrategyTrace,
    resource_to_standard_draws,
)
from scheduler.strategy_protocol import StrategyProtocolAdapter
from scheduler.workers import _worker_wrapper


@dataclass
class BannerPlan:
    """单个卡池计划。"""

    rules: Any
    init_counters: Counters
    check_in: bool
    use_origeometry: bool
    resource_increment: Resource
    is_core: bool
    name: Optional[str] = None


class Scheduler:
    """策略规划器。"""

    def __init__(
        self,
        config_dir: str = "configs",
        arrange: str = "arrangement",
        resource: Resource | None = None,
        increment: Resource | None = None,
    ):
        self.config_dir = config_dir
        self.arrange_name = arrange
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

        self.arrangement: List[str] = []
        with open(os.path.join(config_dir, arrange), "r", encoding="utf-8") as file:
            for line in file.readlines():
                if line:
                    self.arrangement.append(line.strip())

        self.resource = Resource() if not resource else resource
        self.__schedules: Dict[str, BannerPlan] = {}
        self.__schedule_order: List[str] = []

    @property
    def schedules(self) -> List[BannerPlan]:
        return [self.__schedules[name] for name in self.__schedule_order]

    @schedules.setter
    def schedules(self, value: List[BannerPlan]) -> None:
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
        rules: Any,
        name: str | None = None,
        resource_increment: Resource | None = None,
        init_counters: Counters | None = None,
        check_in: bool = True,
        use_origeometry: bool = False,
        is_core: bool = True,
    ) -> None:
        normalized_rules = StrategyProtocolAdapter.from_payload(rules)
        plan = BannerPlan(
            rules=normalized_rules,
            init_counters=init_counters if init_counters else Counters(),
            check_in=check_in,
            use_origeometry=use_origeometry,
            resource_increment=resource_increment if resource_increment else self.increment,
            is_core=is_core,
            name=name,
        )

        plan_name = name if name else f"plan_{len(self.__schedule_order)}"
        self.__schedules[plan_name] = plan
        self.__schedule_order.append(plan_name)

    def banners(self, cycles: List[Dict[str, Any]]) -> None:
        if not isinstance(cycles, list):
            raise ValueError("cycles must be a list")

        for cycle_config in cycles:
            if not isinstance(cycle_config, dict):
                raise ValueError(f"Invalid cycle config: {cycle_config}")

            rules = cycle_config.get("rules")
            if rules is None:
                raise ValueError(f"Missing 'rules' key in cycle config: {cycle_config}")

            self.banner(
                rules=rules,
                name=cycle_config.get("name"),
                init_counters=cycle_config.get("counters"),
                check_in=cycle_config.get("check_in", True),
                resource_increment=cycle_config.get("increment", Resource()),
                use_origeometry=cycle_config.get("use_ori", False),
                is_core=cycle_config.get("is_core", True),
            )

    def _build_schedules_data(self) -> List[Dict[str, Any]]:
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
                    "is_core": plan.is_core,
                }
            )
        return schedules_data

    def _validate_schedules(self) -> None:
        named_plans: Dict[str, int] = {}
        unnamed_plans: List[int] = []

        for idx, plan in enumerate(self.schedules):
            plan_name = plan.name
            if plan_name:
                if plan_name in named_plans:
                    raise ValueError(
                        f"计划名称冲突：卡池 '{plan_name}' 被多个计划指定（索引 {named_plans[plan_name]} 和 {idx}）"
                    )
                named_plans[plan_name] = idx
            else:
                unnamed_plans.append(idx)

        for plan_name in named_plans:
            if plan_name not in self.arrangement:
                raise ValueError(
                    f"指定的卡池名称 '{plan_name}' 不在安排文件中。可用名称: {self.arrangement}"
                )

        used_pools = set(named_plans.keys())
        remaining_pools = [pool for pool in self.arrangement if pool not in used_pools]

        if len(unnamed_plans) > len(remaining_pools):
            raise ValueError(
                f"计划数量超过可用卡池数量。已指定名称的计划: {len(named_plans)} 个, "
                f"未指定名称的计划: {len(unnamed_plans)} 个, "
                f"剩余可用卡池: {len(remaining_pools)} 个"
            )

        total_planned = len(named_plans) + len(unnamed_plans)
        if total_planned < len(self.arrangement):
            unplanned_pools = self.arrangement[total_planned:]
            SchedulerDisplay.print(
                f"[yellow]警告: 安排文件中有 {len(unplanned_pools)} 个卡池未被规划: {unplanned_pools}[/yellow]"
            )

    def _build_tasks(
        self, schedules_data: List[Dict[str, Any]], change: bool, scale: int
    ) -> List[Tuple[Any, ...]]:
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
                index,
                resource_data,
            )
            for index in range(scale)
        ]

    def _simulate(
        self,
        scale: int,
        change: bool,
        workers: Optional[int],
        show_progress: bool,
    ) -> Tuple[List[StrategyTrace], float, int]:
        if scale <= 0:
            raise ValueError("scale must be greater than 0")
        if workers is not None and workers < 0:
            raise ValueError("workers must be a non-negative integer")

        if workers is None:
            workers = max(1, int(cpu_count() * 0.75))
        if workers > cpu_count():
            workers = cpu_count()

        self._validate_schedules()
        schedules_data = self._build_schedules_data()
        tasks = self._build_tasks(schedules_data, change, scale)
        if not tasks:
            return [], 0.0, workers

        results: List[StrategyTrace] = []
        start_time = time.time()

        with Pool(processes=workers) as pool:
            if show_progress:
                with SchedulerDisplay.create_progress() as progress:
                    task = progress.add_task("模拟进度", total=scale)
                    batch_size = max(1, scale // 100)
                    batch_results: List[StrategyTrace] = []
                    for result in pool.imap(_worker_wrapper, tasks):
                        batch_results.append(result)
                        if len(batch_results) >= batch_size:
                            results.extend(batch_results)
                            progress.update(task, advance=len(batch_results))
                            batch_results = []
                    if batch_results:
                        results.extend(batch_results)
                        progress.update(task, advance=len(batch_results))
            else:
                SchedulerDisplay.print("[bold green]模拟已启动...[/bold green]")
                results = pool.map(_worker_wrapper, tasks)

        return results, time.time() - start_time, workers

    def _build_baseline_estimator(
        self, preferences: ScoringPreferences
    ) -> BaselineEstimator:
        return BaselineEstimator(
            config_dir=self.config_dir,
            samples=preferences.baseline_samples,
            base_seed=preferences.baseline_seed,
        )

    def evaluate(
        self,
        scale: int = 20000,
        change: bool = True,
        workers: int | None = None,
        scoring_mode: str = "raw",
        weights: Optional[Dict[str, Dict[str, float]]] = None,
        show_progress: bool = True,
        preferences: Optional[ScoringPreferences | Dict[str, Any] | str] = None,
        goals: Optional[List[StrategyGoal] | List[Dict[str, Any]] | str] = None,
        return_traces: bool = False,
    ) -> StrategyScoreReport:
        del scoring_mode
        del weights

        preferences = ScoringSystem.normalize_preferences(preferences)
        goals = ScoringSystem.normalize_goals(goals)

        traces, elapsed_time, workers = self._simulate(
            scale=scale,
            change=change,
            workers=workers,
            show_progress=show_progress,
        )
        if not traces:
            raise ValueError("无可用模拟结果")

        baseline_estimator = self._build_baseline_estimator(preferences)
        report = ScoringSystem.score_traces(
            traces=traces,
            preferences=preferences,
            goals=goals,
            baseline_estimator=baseline_estimator,
            include_traces=return_traces,
        )
        baseline_estimator.flush_cache()

        SchedulerDisplay.print_header(scale, workers, change, self.schedules)
        SchedulerDisplay.print_statistics(
            traces,
            elapsed_time,
            workers,
            report,
            len(self.schedules),
        )
        return report

    def evaluate_multiple_strategies(
        self,
        strategies: List[Any],
        scale: int = 20000,
        change: bool = True,
        workers: int | None = None,
        show_progress: bool = True,
        preferences: Optional[ScoringPreferences | Dict[str, Any] | str] = None,
        goals: Optional[List[StrategyGoal] | List[Dict[str, Any]] | str] = None,
        return_traces: bool = False,
    ) -> List[StrategyScoreReport]:
        if not strategies:
            raise ValueError("strategies不能为空")

        preferences = ScoringSystem.normalize_preferences(preferences)
        goals = ScoringSystem.normalize_goals(goals)

        payloads: List[Dict[str, Any]] = []
        reports: List[StrategyScoreReport] = []

        for index, strategy_rules in enumerate(strategies, start=1):
            strategy_scheduler = self._clone_for_strategy(
                StrategyProtocolAdapter.from_payload(strategy_rules)
            )
            traces, elapsed_time, resolved_workers = strategy_scheduler._simulate(
                scale=scale,
                change=change,
                workers=workers,
                show_progress=show_progress,
            )
            baseline_estimator = strategy_scheduler._build_baseline_estimator(
                preferences
            )
            report = ScoringSystem.score_traces(
                traces=traces,
                preferences=preferences,
                goals=goals,
                baseline_estimator=baseline_estimator,
                include_traces=return_traces,
            )
            baseline_estimator.flush_cache()
            reports.append(report)
            payloads.append(
                {
                    "strategy_id": f"S{index}",
                    "strategy_rules": strategy_rules,
                    "traces": traces,
                    "elapsed_time": elapsed_time,
                    "workers": resolved_workers,
                }
            )

        ScoringSystem.rank_reports(reports)
        SchedulerDisplay.print_multi_strategy_report(payloads, reports, "raw")
        return reports

    def _clone_for_strategy(self, strategy_rules: Any) -> "Scheduler":
        clone = Scheduler(
            config_dir=self.config_dir,
            arrange=self.arrange_name,
            resource=deepcopy(self.resource),
            increment=deepcopy(self.increment),
        )

        if not self.schedules:
            clone.banner(strategy_rules, name=self.arrangement[0], is_core=True)
            return clone

        core_indices = [idx for idx, plan in enumerate(self.schedules) if plan.is_core]
        if len(core_indices) != 1:
            raise ValueError(
                "evaluate_multiple_strategies 目前仅支持零个或一个核心计划"
            )

        cloned_schedules: List[BannerPlan] = []
        for idx, plan in enumerate(self.schedules):
            new_plan = deepcopy(plan)
            if idx == core_indices[0]:
                new_plan.rules = strategy_rules
            cloned_schedules.append(new_plan)

        clone.schedules = cloned_schedules
        return clone

    def initial_standard_draws(self) -> float:
        total = resource_to_standard_draws(self.resource)
        for plan in self.schedules:
            total += resource_to_standard_draws(plan.resource_increment)
        return float(total)


__all__ = ["BannerPlan", "Scheduler"]

