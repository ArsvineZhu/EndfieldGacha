import os
from math import ceil
from hashlib import md5
from dataclasses import dataclass
from typing import List, Tuple, Any, Callable, Dict
from multiprocessing import Pool, cpu_count
from copy import deepcopy
from pprint import pformat
import random
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
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from rich import box
from core import CharGacha, Counters, GlobalConfigLoader

console = Console()


class GachaStrategy:
    """
    基于魔数的抽卡策略预编译执行系统（改进版）

    设计意图适配：
    1. 终止目标默认值与前置条件参数完全隔离，无互相覆盖风险；
    2. 终止目标默认值作为兜底，用户未指定参数时自动生效。
    """

    URGENT = (-1 << 31) | (0b0000001 << 24)
    DOSSIER = (-1 << 31) | (0b0000010 << 24)
    SOFT_PITY = (-1 << 31) | (0b0000100 << 24)
    UP_OPRT = (-1 << 31) | (0b0001000 << 24)
    HARD_PITY = (-1 << 31) | (0b0010000 << 24)
    POTENTIAL = (-1 << 31) | (0b0100000 << 24)
    OPRT = (-1 << 31) | (0b1000000 << 24)

    _STOP_DEFAULT_PARAM = {
        "URGENT": 30,
        "DOSSIER": 60,
        "SOFT_PITY": 85,
        "UP_OPRT": 120,
        "HARD_PITY": 120,
        "POTENTIAL": 6,
        "OPRT": 85,
    }

    GT = 0b00000001 << 16
    LT = 0b00000010 << 16
    GE = 0b00000100 << 16
    LE = 0b00001000 << 16

    _COND_MAP = {
        GT: lambda a, b: a > b,
        LT: lambda a, b: a < b,
        GE: lambda a, b: a >= b,
        LE: lambda a, b: a <= b,
    }

    _STOP_LOGIC = {
        "URGENT": lambda cnt, state, param: state.get("urgent", False),
        "DOSSIER": lambda cnt, state, param: state.get("dossier", False)
        or cnt >= param,
        "SOFT_PITY": lambda cnt, state, param: state.get("soft_pity", False)
        or cnt >= param,
        "UP_OPRT": lambda cnt, state, param: state.get("up_oprt", False)
        or cnt >= param,
        "HARD_PITY": lambda cnt, state, param: cnt >= param,
        "POTENTIAL": lambda cnt, state, param: state.get("potential", 0) >= param,
        "OPRT": lambda cnt, state, param: state.get("oprt", False) or cnt >= param,
    }

    _STOP_MASK = {
        0b0000001: "URGENT",
        0b0000010: "DOSSIER",
        0b0000100: "SOFT_PITY",
        0b0001000: "UP_OPRT",
        0b0010000: "HARD_PITY",
        0b0100000: "POTENTIAL",
        0b1000000: "OPRT",
    }

    def __init__(self, strategy: list):
        self._raw_strategy = strategy
        self._compiled_groups = []
        self._compile()

    def _compile(self):
        strategy = self._raw_strategy
        compiled_groups = []

        if not isinstance(strategy, list) or len(strategy) == 0:
            self._compiled_groups = []
            return
        is_old_format = all(not isinstance(item, list) for item in strategy)
        normalized_strategy = [strategy] if is_old_format else []
        if not is_old_format:
            for item in strategy:
                normalized_strategy.append(item if isinstance(item, list) else [item])

        for rule_group in normalized_strategy:
            if not isinstance(rule_group, list) or len(rule_group) == 0:
                continue

            compiled_rules = []
            for rule in rule_group:
                if isinstance(rule, tuple):
                    cond_magic, stop_magic = rule
                    cond_func, cond_param = self._parse_cond_magic(cond_magic)
                    stop_target, stop_param = self._parse_stop_magic(stop_magic)
                    if cond_func and stop_target and stop_target in self._STOP_LOGIC:
                        logic_func = self._STOP_LOGIC[stop_target]

                        def cond_stop_check(
                            cnt,
                            s,
                            cf=cond_func,
                            lf=logic_func,
                            cp=cond_param,
                            sp=stop_param,
                        ):
                            try:
                                return cf(cnt, cp) and lf(cnt, s, sp)
                            except (TypeError, ValueError):
                                return False

                        compiled_rules.append(cond_stop_check)
                    continue

                if not isinstance(rule, int):
                    continue
                magic_32 = rule & 0xFFFFFFFF
                sign_bit = (magic_32 >> 31) & 1

                if magic_32 == rule and rule >= 0 and (magic_32 >> 16) == 0:

                    def fixed_check(cnt, s, m=rule):
                        try:
                            return cnt >= m
                        except (TypeError, ValueError):
                            return False

                    compiled_rules.append(fixed_check)
                    continue

                if sign_bit == 1:
                    stop_target, stop_param = self._parse_stop_magic(rule)
                    if stop_target and stop_target in self._STOP_LOGIC:
                        logic_func = self._STOP_LOGIC[stop_target]

                        def stop_check(cnt, s, lf=logic_func, sp=stop_param):
                            try:
                                return lf(cnt, s, sp)
                            except (TypeError, ValueError):
                                return False

                        compiled_rules.append(stop_check)
                    continue

                cond_func, cond_param = self._parse_cond_magic(rule)
                if cond_func:

                    def pure_cond_check(cnt, s, cf=cond_func, cp=cond_param):
                        try:
                            return cf(cnt, cp)
                        except (TypeError, ValueError):
                            return False

                    compiled_rules.append(pure_cond_check)

            if compiled_rules:

                def group_check(cnt, s, rules=compiled_rules):
                    return all(rule(cnt, s) for rule in rules)

                compiled_groups.append(group_check)

        self._compiled_groups = compiled_groups

    def _parse_cond_magic(self, magic: int) -> Tuple[Callable | None, int]:
        if not isinstance(magic, int):
            return None, 0
        magic_32 = magic & 0xFFFFFFFF
        cond_mask = (magic_32 >> 16) & 0xFF
        cond_param = magic_32 & 0xFFFF
        cond_func = self._COND_MAP.get(cond_mask << 16)
        return cond_func, cond_param

    def _parse_stop_magic(self, magic: int) -> Tuple[str | None, int]:
        if not isinstance(magic, int):
            return None, 0
        magic_32 = magic & 0xFFFFFFFF
        stop_mask = (magic_32 >> 24) & 0b01111111
        user_param = magic_32 & 0xFFFF
        stop_target = self._STOP_MASK.get(stop_mask, "")
        stop_param = (
            user_param
            if user_param != 0
            else self._STOP_DEFAULT_PARAM.get(stop_target, 0)
        )
        return stop_target, stop_param

    def terminate(self, draw_cnt: int, state: dict = {}) -> bool:
        if not isinstance(draw_cnt, int) or draw_cnt < 0:
            return True
        if not isinstance(state, dict):
            state = {}
        if len(self._compiled_groups) == 0:
            return True
        return any(
            group_check(draw_cnt, state) for group_check in self._compiled_groups
        )

    def update_strategy(self, new_strategy: list):
        self._raw_strategy = new_strategy
        self._compile()

    def get_raw_strategy(self) -> list:
        return self._raw_strategy

    @staticmethod
    def decode_magic(magic) -> str:
        if not isinstance(magic, (int, str)):
            return str(magic)

        if isinstance(magic, str):
            if "^" in magic:
                parts = magic.split("^")
                if len(parts) == 2:
                    return f"{parts[0].strip()} {parts[1].strip()}"
            return magic

        magic_32 = magic & 0xFFFFFFFF
        sign_bit = (magic_32 >> 31) & 1
        parts = []

        if magic_32 == magic and magic >= 0 and (magic_32 >> 16) == 0:
            return f"CNT >= {magic}"

        if sign_bit == 1:
            stop_mask = (magic_32 >> 24) & 0b01111111
            user_param = magic_32 & 0xFFFF
            for bit, name in GachaStrategy._STOP_MASK.items():
                if stop_mask & bit:
                    default_param = GachaStrategy._STOP_DEFAULT_PARAM.get(name, 0)
                    param = user_param if user_param != 0 else default_param
                    parts.append(
                        f"{name}({param})" if param != default_param else f"{name}"
                    )
            return " | ".join(parts) if parts else f"UNK(0x{magic_32:08X})"

        cond_mask = (magic_32 >> 16) & 0xFF
        cond_name = {0x01: "GT", 0x02: "LT", 0x04: "GE", 0x08: "LE"}.get(cond_mask)
        if cond_name:
            cond_param = magic_32 & 0xFFFF
            return f"{cond_name} {cond_param}"

        return f"RAW({magic})"

    @staticmethod
    def decode_strategy(strategy: list) -> list:
        result = []
        for item in strategy:
            if isinstance(item, list):
                group = [
                    GachaStrategy.decode_magic(x) if isinstance(x, int) else str(x)
                    for x in item
                ]
                result.append(group)
            elif isinstance(item, int):
                result.append(GachaStrategy.decode_magic(item))
            else:
                result.append(str(item))
        return result


URGENT = GachaStrategy.URGENT
DOSSIER = GachaStrategy.DOSSIER
SOFT_PITY = GachaStrategy.SOFT_PITY
UP_OPRT = GachaStrategy.UP_OPRT
HARD_PITY = GachaStrategy.HARD_PITY
POTENTIAL = GachaStrategy.POTENTIAL
OPRT = GachaStrategy.OPRT

GT = GachaStrategy.GT
LT = GachaStrategy.LT
GE = GachaStrategy.GE
LE = GachaStrategy.LE


@dataclass
class Resource:
    chartered_permits: int = 0
    oroberyl: int = 0
    arsenal_tickets: int = 0
    origeometry: int = 0


class ScoringSystem:
    """
    科学的抽卡评分系统（0-100分百分制）

    评分维度：
    1. 运气评估（0-60分）：评估抽卡运气（权重最高）
    2. 资源效率（0-25分）：评估资源利用效率
    3. 目标达成（0-15分）：评估目标完成情况

    核心设计：
    - UP干员得分是普通6星的2倍
    - 运气权重最高，体现抽卡游戏的核心体验

    等级划分：
    S级（90-100）：极佳运气，资源高效利用
    A级（80-89）：优秀表现，超出预期
    B级（70-79）：良好表现，符合预期
    C级（60-69）：一般表现，略有不足
    D级（50-59）：较差表现，需要改进
    E级（0-49）：失败，资源严重不足或运气极差
    """

    GRADE_THRESHOLDS = {
        (100 / 6 * 5, 100): ("S", "极佳", "bold red"),
        (100 / 6 * 4, 100 / 6 * 5): ("A", "优秀", "bold yellow"),
        (100 / 6 * 3, 100 / 6 * 4): ("B", "良好", "bold green"),
        (100 / 6 * 2, 100 / 6 * 3): ("C", "一般", "bold blue"),
        (100 / 6, 100 / 6 * 2): ("D", "较差", "bold magenta"),
        (0, 100 / 6): ("E", "失败", "bold white"),
    }

    UP_SIX_STAR_RATIO = 2.0
    LUCK_MAX = 60.0
    RESOURCE_MAX = 20.0
    ACHIEVEMENT_MAX = 20.0

    @staticmethod
    def calculate_score(
        total_draws: int,
        six_stars: int,
        up_chars: int,
        resource_left: int,
        complete: bool,
        banners_count: int = 5,
    ) -> Dict[str, Any]:
        """
        计算综合评分

        Args:
            total_draws: 总抽卡次数
            six_stars: 获得的6星干员数量
            up_chars: 获得的UP干员数量
            resource_left: 剩余资源（等效抽卡次数）
            complete: 是否完成所有目标
            banners_count: 卡池数量

        Returns:
            包含详细评分信息的字典
        """
        luck_score = ScoringSystem._calculate_luck_score(
            total_draws + resource_left, six_stars, up_chars
        )
        efficiency_score = ScoringSystem._calculate_efficiency_score(
            total_draws, resource_left, complete
        )
        achievement_score = ScoringSystem._calculate_achievement_score(
            six_stars, up_chars, complete, banners_count
        )

        total_score = luck_score + efficiency_score + achievement_score
        total_score = max(0, min(100, total_score))

        grade, grade_name, grade_style = ScoringSystem.get_grade(total_score)

        return {
            "total_score": round(total_score, 1),
            "luck_score": round(luck_score, 1),
            "efficiency_score": round(efficiency_score, 1),
            "achievement_score": round(achievement_score, 1),
            "grade": grade,
            "grade_name": grade_name,
            "grade_style": grade_style,
        }

    @staticmethod
    def _calculate_luck_score(total_draws: int, six_stars: int, up_chars: int) -> float:
        """
        运气评估评分（0-60分）

        评分设计：
        - 基准60%：36分
        - 恰好达到期望：54分
        - 未达期望：按比例递减，最低0分
        - 超出期望：最多60分
        - UP权重是普通6星的2倍
        """
        MAX = ScoringSystem.LUCK_MAX
        if total_draws == 0:
            return MAX * 0.6

        up_ratio = up_chars / (total_draws * 0.0087)
        six_ratio = six_stars / (total_draws * 0.0174)

        total_weight = ScoringSystem.UP_SIX_STAR_RATIO + 1.0

        def calc_score(ratio: float, weight: float) -> float:
            w = weight / total_weight
            if ratio <= 0.6:
                return ratio * MAX * w
            elif ratio <= 1.0:
                return (0.6 + (ratio - 0.6) / 0.4 * 0.3) * MAX * w
            else:
                return min(MAX, (0.9 + (ratio - 1.0) * 0.1) * MAX) * w

        score = calc_score(up_ratio, ScoringSystem.UP_SIX_STAR_RATIO) + calc_score(
            six_ratio, 1.0
        )
        return max(0, min(MAX, score))

    @staticmethod
    def _calculate_efficiency_score(
        total_draws: int, resource_left: int, complete: bool
    ) -> float:
        """
        资源保有率评分（0-20分）

        评估标准：
        - 基础分：20分
        - 资源保有率：剩余资源越多消耗率越高（最高-10分）
        - 未完成惩罚：-10 分
        """
        base_score = 20 if complete else 10

        if total_draws > 0:
            efficiency_ratio = min(1.0, total_draws / (total_draws + resource_left))
            efficiency_bonus = -efficiency_ratio * 10
        else:
            efficiency_bonus = -10

        return max(0, min(ScoringSystem.RESOURCE_MAX, base_score + efficiency_bonus))

    @staticmethod
    def _calculate_achievement_score(
        six_stars: int, up_chars: int, complete: bool, banners_count: int
    ) -> float:
        """
        目标达成评分（0-20分）

        评估标准：
        - 完成所有目标：+8分
        - UP干员获取：每个+4分（最高+8分）
        - 6星干员获取：每个+2分（最高+4分）
        """
        score = 0.0

        if complete:
            score += 8.0

        up_score = min(8.0, up_chars * 4.0)
        score += up_score

        six_star_score = min(4.0, six_stars * 2.0)
        score += six_star_score

        return min(ScoringSystem.ACHIEVEMENT_MAX, score)

    @staticmethod
    def get_grade(score: float) -> Tuple[str, str, str]:
        """获取评分等级"""
        for (low, high), (grade, name, style) in ScoringSystem.GRADE_THRESHOLDS.items():
            if low <= score <= high:
                return grade, name, style
        return "E", "失败", "bold white"


class Scheduler:
    def __init__(
        self,
        config_dir: str = "configs",
        arrange: str = "arrangement",
        resource: Resource | None = None,
    ):
        self.config_dir = config_dir

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
        return self.__schedules

    @schedules.setter
    def schedules(self, value):
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
        self.schedules.append(
            (
                rules,
                init_counters if init_counters else Counters(),
                check_in,
                use_origeometry,
                (
                    resource_increment
                    if resource_increment
                    else Resource(
                        chartered_permits=5,
                        oroberyl=30 * 500,  # 45?
                        arsenal_tickets=250,
                        origeometry=25,  # 20?
                    )
                ),
            )
        )

    def simulate(self, change: bool = True, display: bool = True):
        scores: List[float] = []
        counters: Counters = Counters()
        outputs: List[List[Tuple[str, int, bool]]] = []

        dossier = False

        for idx, plan in enumerate(self.schedules):
            score = 60
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
                    score -= 60
                    break

                score -= 1
                result = gacha.attempt()
                output.append((result.name, result.star, False))

                state, potential, score = process_gacha_result(
                    result, gacha, state, potential, score
                )

                if gacha.counters.total == 30 and not cnts.urgent_used:
                    state, potential, score, urgent_results = handle_urgent_gacha(
                        config, gacha, cnts, state, potential, score
                    )
                    for result in urgent_results:
                        output.append((result.name, result.star, True))
                    continue

            scores.append(score)
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
            print(scores)
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
        """
        进行大量模拟并给出统计信息

        性能优化说明：
        - 默认进程数为 max(1, int(cpu_count() * 0.75))，避免过度占用CPU
        - 使用 imap 实现流式处理，减少内存占用
        - 批量处理结果，减少进度更新频率
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
        """打印报告头部"""
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
            f"S{md5(pformat(rules).encode("utf-8")).hexdigest()[:5].upper()}",
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
        """打印专业统计报告"""
        total = len(results)
        if total == 0:
            return

        scores = [r["score"] for r in results]
        total_draws = [r["total_draws"] for r in results]
        six_stars = [r["six_stars"] for r in results]
        up_chars = [r["up_chars"] for r in results]
        resource_left = [r["resource_left"] for r in results]
        complete_count = sum(1 for r in results if r["complete"])

        score_avg = sum(scores) / total
        score_max = max(scores)
        score_min = min(scores)
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
        eff_avg = sum(s["efficiency_score"] for s in new_scores) / total
        ach_avg = sum(s["achievement_score"] for s in new_scores) / total

        score_table.add_row(
            "获取评估", f"{luck_avg:.1f}", "60", f"{luck_avg/60*100:.1f}%"
        )
        score_table.add_row(
            "资源保有", f"{eff_avg:.1f}", "20", f"{eff_avg/20*100:.1f}%"
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
            title="[bold]分位数统计[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        percentile_table.add_column("分位", style="bold", ratio=1)
        percentile_table.add_column("新评分", justify="right", ratio=2)
        percentile_table.add_column("旧评分", justify="right", ratio=2)
        percentile_table.add_column("总抽数", justify="right", ratio=2)
        percentile_table.add_column("6星数", justify="right", ratio=2)

        percentiles = [10, 25, 50, 75, 90, 95, 99]
        for p in percentiles:
            percentile_table.add_row(
                f"P{p}",
                f"{self._percentile(new_score_values, p):.1f}",
                f"{self._percentile(scores, p):.0f}",
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
        # console.print(perf_table)
        # console.print()

        scoring_info = Panel(
            Columns(
                [
                    Panel(
                        "[bold]运气评估 (0-60分)[/bold]\n"
                        "• 基准分: 36分\n"
                        "• UP干员权重: 2x (是6星的2倍)\n"
                        "• 6星出率加成: 最高±15分\n"
                        "• UP出率加成: 最高±15分",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        "[bold]资源效率 (0-25分)[/bold]\n"
                        "• 完成目标: +12.5分\n"
                        "• 资源利用率: 最高+12.5分\n"
                        "• 未完成惩罚: -8分",
                        box=box.SIMPLE,
                    ),
                    Panel(
                        "[bold]目标达成 (0-15分)[/bold]\n"
                        "• 完成所有目标: +10分\n"
                        "• UP干员: 每个+1分(最高3分)\n"
                        "• 6星干员: 每个+0.5分(最高2分)",
                        box=box.SIMPLE,
                    ),
                ]
            ),
            title="[bold white]评分体系说明[/bold white]",
            box=box.ROUNDED,
        )
        # console.print(scoring_info)
        # console.print()

        footer = Panel(
            Text("报告结束", style="bold", justify="center"),
            box=box.DOUBLE,
            style="bold blue",
        )
        console.print(footer)

    def _percentile(self, data: List, p: float) -> float:
        sorted_data = sorted(data)
        idx = int(len(data) * p / 100)
        if idx >= len(sorted_data):
            idx = len(sorted_data) - 1
        return sorted_data[idx]


def get_token(gacha: CharGacha) -> int:
    rewards = gacha.get_accumulated_reward()
    count = 0
    for i in rewards:
        if i[0].endswith("的信物"):
            count += 1
    return count


def consume_resource(resource: Resource, use_origeometry: bool) -> bool:
    if resource.chartered_permits >= 1:
        resource.chartered_permits -= 1
        return True
    elif resource.oroberyl + resource.origeometry * 75 * int(use_origeometry) >= 500:
        if resource.oroberyl < 500 and use_origeometry:
            diff = 500 - resource.oroberyl
            cost = ceil(diff / 75)
            resource.origeometry -= cost
            resource.oroberyl = cost * 75 - diff
        else:
            resource.oroberyl -= 500
        return True
    else:
        return False


def process_gacha_result(
    result, gacha: CharGacha, state: dict, potential: int, score: int
) -> Tuple[dict, int, int]:
    up_names = gacha.star_up_prob.get(6, ([], []))[0]
    is_up = result.name in up_names if up_names else False

    state["oprt"] = state["oprt"] or (result.star == 6)
    state["up_oprt"] = state["up_oprt"] or is_up
    potential += int(is_up)
    state["potential"] = potential + get_token(gacha)
    state["soft_pity"] = state["soft_pity"] or (
        85 >= gacha.counters.no_6star > 65 and result.star == 6
    )

    score += 40 * int(result.star == 6) + 40 * int(is_up)

    return state, potential, score


def handle_urgent_gacha(
    config, gacha: CharGacha, cnts: Counters, state: dict, potential: int, score: int
) -> Tuple[dict, int, int, List[Any]]:
    cnts.urgent_used = True
    urgent = CharGacha(config)
    results = []

    for _ in range(10):
        result = urgent.attempt()
        results.append(result)

        state, potential, score = process_gacha_result(
            result, gacha, state, potential, score
        )
        state["urgent"] = True

    return state, potential, score, results


def initialize_banner_state(cnts: Counters) -> dict:
    return {
        "urgent": cnts.urgent_used,
        "up_oprt": False,
        "oprt": False,
        "soft_pity": False,
        "potential": 0,
    }


def _worker_wrapper(args):
    return _run_simulation_worker(*args)


def _run_simulation_worker(
    config_dir: str,
    arrangement: List[str],
    schedules: List[Dict],
    change: bool,
    seed: int,
    init_resource: Dict[str, int],
) -> Dict[str, Any]:
    random.seed(seed)

    resource = Resource(**init_resource)
    counters = Counters()
    dossier = False
    score = 60

    total_draws = 0
    six_stars = 0
    up_chars = 0

    for idx, plan in enumerate(schedules):
        rules = plan["rules"]
        cnts_data = (
            plan["init_counters"]
            if idx == 0
            else {
                "total": 0,
                "no_6star": 0,
                "no_5star_plus": counters.no_5star_plus,
                "no_up": counters.no_up,
                "guarantee_used": False,
                "urgent_used": False,
            }
        )
        cnts = Counters(**cnts_data)
        check = plan["check_in"]
        use_ori = plan["use_origeometry"]
        addition = Resource(**plan["resource_increment"])

        config = GlobalConfigLoader(
            os.path.join(
                config_dir,
                arrangement[idx] if change else arrangement[0],
            )
        )
        gacha = CharGacha(config)
        gacha.counters = deepcopy(cnts)
        resource.chartered_permits += (
            5 * int(check) + 10 * int(dossier) + addition.chartered_permits
        )
        resource.oroberyl += addition.oroberyl
        resource.arsenal_tickets += addition.arsenal_tickets
        resource.origeometry += addition.origeometry

        strategy = GachaStrategy(rules)
        state = initialize_banner_state(cnts)

        potential = 0

        while not (strategy.terminate(gacha.counters.total, state)):
            if not consume_resource(resource, use_ori):
                score -= 60
                return {
                    "score": score,
                    "total_draws": total_draws,
                    "six_stars": six_stars,
                    "up_chars": up_chars,
                    "resource_left": resource.chartered_permits
                    + (resource.oroberyl + resource.origeometry * 75) // 500,
                    "complete": False,
                }

            score -= 1
            result = gacha.attempt()
            total_draws += 1

            if result.star == 6:
                six_stars += 1
            up_names = gacha.star_up_prob.get(6, ([], []))[0]
            if up_names and result.name in up_names:
                up_chars += 1

            state, potential, score = process_gacha_result(
                result, gacha, state, potential, score
            )

            if gacha.counters.total == 30 and not cnts.urgent_used:
                state, potential, score, urgent_results = handle_urgent_gacha(
                    config, gacha, cnts, state, potential, score
                )
                for result in urgent_results:
                    if result.star == 6:
                        six_stars += 1
                    up_names = gacha.star_up_prob.get(6, ([], []))[0]
                    if up_names and result.name in up_names:
                        up_chars += 1
                continue

        dossier = gacha.counters.total >= 60
        counters = Counters(
            0,
            gacha.counters.no_6star,
            gacha.counters.no_5star_plus,
            0,
            False,
            False,
        )

    return {
        "score": score,
        "total_draws": total_draws,
        "six_stars": six_stars,
        "up_chars": up_chars,
        "resource_left": resource.chartered_permits
        + (resource.oroberyl + resource.origeometry * 75) // 500,
        "complete": True,
    }


__all__ = [
    "Counters",
    "GachaStrategy",
    "Resource",
    "Scheduler",
    "URGENT",
    "DOSSIER",
    "SOFT_PITY",
    "UP_OPRT",
    "OPRT",
    "HARD_PITY",
    "POTENTIAL",
    "GT",
    "LT",
    "GE",
    "LE",
]


def main():
    scheduler = Scheduler(
        config_dir="configs",
        arrange="arrange1",
        resource=Resource(2, 61000, 6000, 6975 // 75),
    )

    counters = Counters(5, 42, 1, 5, False, True)

    scheduler.schedule(
        [0], check_in=False, init_counters=counters, resource_increment=Resource()
    )
    scheduler.schedule(
        [[DOSSIER, [URGENT, LE ^ 43, UP_OPRT]]]
    )  # , [URGENT, LE ^ 43, UP_OPRT]
    scheduler.schedule([DOSSIER, OPRT])
    scheduler.schedule([DOSSIER, UP_OPRT], use_origeometry=True)
    scheduler.schedule([DOSSIER, OPRT])

    # scheduler.simulate()

    scheduler.evaluate(scale=5000, workers=16)

    # print(GachaStrategy.decode_strategy([[DOSSIER, GT ^ 43, UP_OPRT], [URGENT, LE ^ 43, UP_OPRT]]))


if __name__ == "__main__":
    main()
