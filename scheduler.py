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
    """基于魔数编码的抽卡终止策略编译与执行系统。

    本类将一组使用 32 位整数编码的抽卡条件与终止目标（如急单、保底、
    目标干员等）编译为可执行的判定逻辑，在抽卡循环中通过
    :meth:`terminate` 进行统一判定。

    设计要点
    -------
    - 终止目标默认值与条件参数完全隔离，互不覆盖；
    - 终止目标的默认参数作为兜底，在用户未指定数值时自动生效；
    - 支持旧版「一维列表」与新版「分组列表」两种策略格式；
    - 支持条件 + 终止目标的二元组形式，便于表达复杂策略。

    Parameters
    ----------
    strategy : list
        策略描述列表。支持以下几种形式：

        - ``[int, int, ...]``：旧版一维魔数列表，每个元素表示一个条件或终止目标；
        - ``[[...], [...], ...]``：新版分组列表，每一子列表视为一组「与」关系，
          不同分组之间为「或」关系；
        - ``[(cond_magic, stop_magic), ...]``：条件与终止目标成对出现的二元组形式，
          用于更精细的控制。

        其中魔数的高位用于标记终止类型（如 ``URGENT``、``DOSSIER`` 等），
        中间若干位用于条件运算符（``GT``、``LT``、``GE``、``LE``），低 16 位为参数。

    Notes
    -----
    - 本类本身不关心抽卡结果，只根据「抽数」与「状态字典」进行判定；
    - 状态字典的键约定见 :func:`initialize_banner_state` 与
      :func:`process_gacha_result`；
    - 所有内部回调在异常（如类型错误）时会安全返回 ``False``，避免中断模拟。

    Examples
    --------
    只根据抽卡总次数终止::

        strategy = GachaStrategy([90])
        while not strategy.terminate(draw_cnt, state):
            ...

    组合条件与终止目标::

        strategy = GachaStrategy([
            [DOSSIER, UP_OPRT],              # 抽到 60 抽或达成 UP 干员
            [URGENT, LE ^ 43, UP_OPRT],      # 或在急单池 43 抽内获取 UP
        ])
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
        """初始化策略实例。

        Parameters
        ----------
        strategy : list
            原始策略描述列表。具体支持的格式与语义见类文档。
        """
        self._raw_strategy = strategy
        self._compiled_groups = []
        self._compile()

    def _compile(self):
        """将原始策略编译为可执行的判定函数列表。

        Notes
        -----
        编译结果保存在 ``self._compiled_groups`` 中，其结构为::

            List[Callable[[int, dict], bool]]

        每个 group 表示一个「与」关系的规则组，不同 group 之间为「或」关系。
        """
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
        """解析条件魔数。

        Parameters
        ----------
        magic : int
            含有条件运算符与参数的 32 位整数。

        Returns
        -------
        cond_func : Callable or None
            对应的比较函数（如 ``operator.gt`` 风格的函数），如果无法识别则为 ``None``。
        cond_param : int
            与抽卡计数比较的阈值参数。
        """
        if not isinstance(magic, int):
            return None, 0
        magic_32 = magic & 0xFFFFFFFF
        cond_mask = (magic_32 >> 16) & 0xFF
        cond_param = magic_32 & 0xFFFF
        cond_func = self._COND_MAP.get(cond_mask << 16)
        return cond_func, cond_param

    def _parse_stop_magic(self, magic: int) -> Tuple[str | None, int]:
        """解析终止魔数。

        Parameters
        ----------
        magic : int
            含有终止类型与参数的 32 位整数。

        Returns
        -------
        stop_target : str or None
            终止目标名称，如 ``\"URGENT\"``、``\"DOSSIER\"`` 等；解析失败时为 ``None``。
        stop_param : int
            终止阈值。若魔数未携带自定义参数，则使用对应目标的默认值。
        """
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
        """判断是否应当终止当前抽卡轮次。

        Parameters
        ----------
        draw_cnt : int
            当前已进行的抽卡次数（同一 banner 内计数）。
        state : dict, optional
            抽卡状态字典。约定键包括 ``\"urgent\"``、``\"dossier\"``、
            ``\"soft_pity\"``、``\"up_oprt\"``、``\"potential\"``、
            ``\"oprt\"`` 等，具体更新逻辑见 :func:`process_gacha_result`。

        Returns
        -------
        bool
            若任意一组编译规则满足，则返回 ``True`` 表示应终止；若策略非法或
            计数异常也会保护性返回 ``True``。
        """
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
        """更新原始策略并重新编译。

        Parameters
        ----------
        new_strategy : list
            新的策略描述列表，语义同 ``strategy`` 初始化参数。
        """
        self._raw_strategy = new_strategy
        self._compile()

    def get_raw_strategy(self) -> list:
        """返回当前保存的原始策略描述。

        Returns
        -------
        list
            用于构造本实例的原始策略列表（浅拷贝语义，由调用方自行约束修改）。
        """
        return self._raw_strategy

    @staticmethod
    def decode_magic(magic) -> str:
        """将单个魔数或带分隔符的字符串解码为可读说明。

        Parameters
        ----------
        magic : int or str
            魔数整数，或形如 ``\"A ^ B\"`` 的字符串表达式。

        Returns
        -------
        str
            可读的条件/终止目标说明字符串；无法识别时以十六进制原始形式返回。
        """
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
        """将一整套策略解码为可读形式。

        Parameters
        ----------
        strategy : list
            与 :class:`GachaStrategy` 初始化参数相同的策略描述列表。

        Returns
        -------
        list
            解码后的列表结构，内部元素为字符串或字符串列表，便于展示和日志记录。
        """
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
    """抽卡所需资源的归一化描述。

    所有字段都可以通过简单换算统一为「等效单抽次数」，用于统计与评分。

    Parameters
    ----------
    chartered_permits : int, optional
        合约证数量，每 1 个可进行 1 次抽卡。
    oroberyl : int, optional
        黄票数量。按照游戏内汇率，每 500 单位视为 1 次抽卡。
    arsenal_tickets : int, optional
        其他可能影响资源策略的票券数量，本模块中仅用于统计展示。
    origeometry : int, optional
        源石数量。通常在 ``use_origeometry=True`` 时按 75 黄票/个进行折算。
    """
    chartered_permits: int = 0
    oroberyl: int = 0
    arsenal_tickets: int = 0
    origeometry: int = 0


class ScoringSystem:
    """抽卡结果综合评分系统（0–100 分百分制）。

    该系统从「运气评估」「资源效率」「目标达成」三个维度对一次完整的
    抽卡规划进行量化打分，并根据总分给出等级评价。

    评分维度
    --------
    1. 运气评估（0–60 分）
       依据 6 星与 UP 干员的实际获取率相对于期望值的偏差，权重最高；
       其中 UP 的权重是普通 6 星的 2 倍。
    2. 资源效率（0–20 分）
       在是否完成目标的前提下，根据资源消耗比例进行加减分。
    3. 目标达成（0–20 分）
       是否完成预定目标、UP/6 星数量等因素的奖励得分。

    等级划分
    --------
    - S（约 90–100）：极佳运气，资源高效利用；
    - A（约 80–89）：优秀表现，明显超出预期；
    - B（约 70–79）：良好表现，大体符合预期；
    - C（约 60–69）：一般表现，略有不足；
    - D（约 50–59）：较差表现，需要改进；
    - E（0–49）：失败，资源严重不足或运气极差。
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
        """计算一次完整抽卡规划的综合评分。

        Parameters
        ----------
        total_draws : int
            实际进行的总抽卡次数。
        six_stars : int
            获得的 6 星干员数量（含 UP 与常驻）。
        up_chars : int
            获得的 UP 干员数量。
        resource_left : int
            剩余资源折算后的「等效抽卡次数」，通常为
            ``券 + (黄票 + 源石换算) // 500``。
        complete : bool
            是否完成了预设的全部抽卡目标。
        banners_count : int, optional
            本轮规划涉及的卡池数量，仅用于部分评分维度的归一化。

        Returns
        -------
        dict
            包含以下键的字典：

            - ``\"total_score\"``：综合评分（0–100）；
            - ``\"luck_score\"``：运气维度得分（0–60）；
            - ``\"efficiency_score\"``：资源效率得分（0–20）；
            - ``\"achievement_score\"``：目标达成得分（0–20）；
            - ``\"grade\"``：等级字母（S/A/B/C/D/E）；
            - ``\"grade_name\"``：等级中文描述；
            - ``\"grade_style\"``：适用于 Rich 的风格字符串。
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
        """计算运气评估得分（0–60 分）。

        评分设计
        --------
        - 恰好达到期望出率时约为 54 分；
        - 明显低于期望时按比例递减，最低 0 分；
        - 高于期望时递增至上限 60 分；
        - UP 的权重为普通 6 星的 2 倍。
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
        """计算资源效率得分（0–20 分）。

        评估标准
        --------
        - 基础分：完成目标时为 20 分，未完成为 10 分；
        - 资源消耗率：抽卡越多（在同等总资源下），扣分越高，最多 -10 分；
        - 若从未抽卡（``total_draws == 0``），视作资源未利用，给予最大扣分。
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
        """计算目标达成得分（0–20 分）。

        评估标准
        --------
        - 完成所有目标：+8 分；
        - UP 干员：每个 +4 分，最高 +8 分；
        - 6 星干员：每个 +2 分，最高 +4 分。
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
        """根据总分获取评分等级。

        Parameters
        ----------
        score : float
            经过裁剪的综合得分（通常在 0–100 之间）。

        Returns
        -------
        grade : str
            等级字母（S/A/B/C/D/E）。
        name : str
            等级中文名称。
        style : str
            适合 Rich 控制台输出的风格字符串。
        """
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
        """调度并评估多卡池抽卡策略的总控类。

        该类负责：

        - 从配置目录加载各个卡池配置；
        - 组织多段抽卡计划（schedule）及其初始计数、资源增量；
        - 提供单次可视化模拟 (:meth:`simulate`) 与大规模评估
          (:meth:`evaluate`) 两种模式。

        Parameters
        ----------
        config_dir : str, optional
            抽卡配置文件所在目录路径，通常为 ``\"configs\"``。
        arrange : str, optional
            用于描述卡池顺序的文件名。文件按行存放各个配置文件名，
            每一行对应一个 banner。
        resource : Resource, optional
            初始资源对象；若为 ``None``，则使用零资源初始化。
        """
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
        """当前已登记的抽卡计划列表。

        Returns
        -------
        list of tuple
            每个元素为 ``(rules, counters, check_in, use_origeometry, resource_inc)``：

            - ``rules``：传入 :class:`GachaStrategy` 的策略描述列表；
            - ``counters``：起始计数器 :class:`Counters`；
            - ``check_in``：是否视为当日已签到（影响合约证获取）；
            - ``use_origeometry``：是否允许消耗源石换算为抽卡；
            - ``resource_inc``：在本计划开始前额外发放的资源。
        """
        return self.__schedules

    @schedules.setter
    def schedules(self, value):
        """设置抽卡计划集合。

        Parameters
        ----------
        value : list
            由若干五元组组成的列表，结构同只读属性 ``schedules``。

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

        每次调用会在内部 ``schedules`` 列表末尾添加一个计划。在一次
        :meth:`evaluate` 调用中，这些计划会按顺序依次执行。

        Parameters
        ----------
        rules : list
            策略描述，将直接传入 :class:`GachaStrategy` 构造函数。
        resource_increment : Resource, optional
            在本计划开始前额外增加的资源。若为 ``None``，
            则使用一个包含少量每日收益的默认值。
        init_counters : Counters, optional
            初始计数器。对于第一个计划，可用于承接已有进度；
            之后的计划若为 ``None``，则自动继承上一计划结果中的部分计数。
        check_in : bool, optional
            是否视为完成签到任务，影响增加的合约证数量。
        use_origeometry : bool, optional
            是否允许在券与黄票不足时继续消耗源石进行换算抽卡。

        Notes
        -----
        - 建议在调用 :meth:`evaluate` 之前先连续调用本方法，构造完整抽卡流程；
        - 本方法不进行任何模拟，仅记录配置。
        """
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
        """按当前计划执行一次顺序模拟，并可选地打印详细过程。

        Parameters
        ----------
        change : bool, optional
            是否在不同计划之间切换至对应的卡池配置；若为 ``False``，
            则所有计划都使用第一个配置文件。
        display : bool, optional
            是否在标准输出中打印每步抽卡过程与结果。

        Returns
        -------
        None
            本方法主要用于调试与验证策略，不返回统计结果。
        """
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
        """进行大规模多进程模拟并输出详细统计报告。

        Parameters
        ----------
        scale : int, optional
            模拟次数（样本数量），即 worker 被调用的总次数。
        change : bool, optional
            是否在各计划间切换卡池配置。与 :meth:`simulate` 中参数含义一致。
        workers : int or None, optional
            进程数。如果为 ``None``，则自动设为
            ``max(1, min(int(cpu_count() * 0.75), 4))``；
            若指定值大于 ``cpu_count()``，则会被裁剪到 CPU 核心数。

        Returns
        -------
        None
            计算结果通过 Rich 表格与面板直接输出到终端，不以返回值形式提供。

        Notes
        -----
        - 使用 :func:`multiprocessing.Pool` 与 ``imap`` 进行流式处理，
          在较大样本规模下仍保持较低内存占用；
        - 统计汇总与评分计算由 :meth:`_print_statistics` 完成。
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
        """打印评估任务的配置概览。

        Parameters
        ----------
        scale : int
            模拟次数。
        workers : int
            实际使用的进程数。
        change : bool
            是否开启卡池切换。
        schedules_data : list of dict
            序列化后的计划配置数据。
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
        """根据 worker 返回结果打印统计与评分报告。

        Parameters
        ----------
        results : list of dict
            每个 worker 返回的统计记录，字段包括分数、抽数、获得 6 星、
            UP 数量与剩余资源等。
        elapsed_time : float
            本次评估总耗时（秒）。
        workers : int
            使用的进程数，用于性能分析展示。
        """
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
        """计算列表数据的近似分位数。

        Parameters
        ----------
        data : list
            数值列表。
        p : float
            分位数百分比（0–100）。

        Returns
        -------
        float
            对应分位上的数据值（使用简单下标截取方式近似）。
        """
        sorted_data = sorted(data)
        idx = int(len(data) * p / 100)
        if idx >= len(sorted_data):
            idx = len(sorted_data) - 1
        return sorted_data[idx]


def get_token(gacha: CharGacha) -> int:
    """统计当前累计奖励中「信物」的数量。

    Parameters
    ----------
    gacha : CharGacha
        抽卡对象实例。

    Returns
    -------
    int
        名称以 ``\"的信物\"`` 结尾的奖励条目数量。
    """
    rewards = gacha.get_accumulated_reward()
    count = 0
    for i in rewards:
        if i[0].endswith("的信物"):
            count += 1
    return count


def consume_resource(resource: Resource, use_origeometry: bool) -> bool:
    """按既定优先级消耗一次抽卡所需资源。

    资源消耗顺序为：

    1. 优先消耗合约证；
    2. 若不足，则尝试消耗黄票；
    3. 若开启 ``use_origeometry``，在黄票不足时可用源石按 75 黄票/个
       的比例补足。

    Parameters
    ----------
    resource : Resource
        当前资源状态，会在函数内部就地更新。
    use_origeometry : bool
        是否允许使用源石进行折算补足。

    Returns
    -------
    bool
        若成功支付一次抽卡费用则为 ``True``，否则表示资源不足返回
        ``False``。
    """
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
    """根据单次抽卡结果更新状态与评分。

    Parameters
    ----------
    result
        本次抽卡返回的角色/结果对象，需至少包含 ``name`` 与 ``star`` 属性。
    gacha : CharGacha
        抽卡对象，用于查询 UP 名单与计数器。
    state : dict
        抽卡状态字典，会被就地更新。约定键包括
        ``\"oprt\"``、``\"up_oprt\"``、``\"soft_pity\"``、``\"potential\"`` 等。
    potential : int
        当前累计的潜能计数（不含信物）。
    score : int
        当前累计得分。

    Returns
    -------
    state : dict
        更新后的状态字典。
    potential : int
        更新后的潜能计数。
    score : int
        更新后的得分。
    """
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
    """执行一次「急单」十连并更新相关状态。

    本函数会在单独的急单卡池上执行固定次数（10 次）抽卡，
    并将结果反馈到主计数与评分体系中。

    Parameters
    ----------
    config
        用于构造急单池 :class:`CharGacha` 的配置对象。
    gacha : CharGacha
        主卡池的抽卡对象，用于获取 UP 名单与共享计数逻辑。
    cnts : Counters
        主计数器对象，其中 ``urgent_used`` 标志会在本函数中被置为 ``True``。
    state : dict
        当前抽卡状态字典，会被就地更新。
    potential : int
        当前潜能计数。
    score : int
        当前得分。

    Returns
    -------
    state : dict
        更新后的状态字典。
    potential : int
        更新后的潜能计数。
    score : int
        更新后的得分。
    results : list
        本次急单十连的所有抽卡结果列表。
    """
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
    """根据计数器初始化单个 banner 的状态字典。

    Parameters
    ----------
    cnts : Counters
        当前 banner 开始前的计数器状态。

    Returns
    -------
    dict
        状态字典，包含键 ``\"urgent\"``、``\"up_oprt\"``、``\"oprt\"``、
        ``\"soft_pity\"``、``\"potential\"`` 等。
    """
    return {
        "urgent": cnts.urgent_used,
        "up_oprt": False,
        "oprt": False,
        "soft_pity": False,
        "potential": 0,
    }


def _worker_wrapper(args):
    """多进程 worker 的薄封装，便于 ``imap`` 传参。"""
    return _run_simulation_worker(*args)


def _run_simulation_worker(
    config_dir: str,
    arrangement: List[str],
    schedules: List[Dict],
    change: bool,
    seed: int,
    init_resource: Dict[str, int],
) -> Dict[str, Any]:
    """在子进程中执行一次完整的抽卡规划模拟。

    Parameters
    ----------
    config_dir : str
        抽卡配置目录。
    arrangement : list of str
        卡池配置文件名列表。
    schedules : list of dict
        经过序列化的计划配置列表，仅包含基础类型与字典。
    change : bool
        是否在计划之间切换卡池配置。
    seed : int
        随机数种子，用于保证不同 worker 之间的独立性与可复现性。
    init_resource : dict
        初始资源字典，将用于构造 :class:`Resource` 实例。

    Returns
    -------
    dict
        单次规划的统计结果字典，包含键 ``\"score\"``、``\"total_draws\"``、
        ``\"six_stars\"``、``\"up_chars\"``、``\"resource_left\"`` 与
        ``\"complete\"`` 等。
    """
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
    """模块自测与示例入口。

    Notes
    -----
    - 使用硬编码的示例配置与资源，构造若干策略并执行评估；
    - 在作为库被导入时通常不需要调用本函数。
    """
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
