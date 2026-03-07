# -*- coding: utf-8 -*-
"""魔数编码策略与预定义常量。

提供基于魔数编码的抽卡策略系统，支持复杂的条件组合和终止逻辑。

主要功能：
- 32位魔数编码策略定义
- 多条件组合策略（AND/OR逻辑）
- 预定义策略常量（URGENT, DOSSIER, UP_OPRT等）
- 比较运算符常量（GT, LT, GE, LE）
"""
from typing import Any, Callable, Dict, List, Tuple


class GachaStrategy:
    """基于魔数编码的抽卡终止策略编译与执行系统。

    使用32位整数编码策略条件，支持复杂的多条件组合。通过魔数编码可以
    定义复杂的抽卡终止逻辑，如"当获得UP干员且获得情报书时停止"等。

    Attributes
    ----------
    URGENT : int
        加急招募策略魔数 (0b0000001 << 24)。
    DOSSIER : int
        情报书策略魔数 (0b0000010 << 24)。
    SOFT_PITY : int
        软保底策略魔数 (0b0000100 << 24)。
    UP_OPRT : int
        UP角色策略魔数 (0b0001000 << 24)。
    HARD_PITY : int
        硬保底策略魔数 (0b0010000 << 24)。
    POTENTIAL : int
        潜能策略魔数 (0b0100000 << 24)。
    OPRT : int
        6星角色策略魔数 (0b1000000 << 24)。
    GT : int
        大于比较运算符 (0b00000001 << 16)。
    LT : int
        小于比较运算符 (0b00000010 << 16)。
    GE : int
        大于等于比较运算符 (0b00000100 << 16)。
    LE : int
        小于等于比较运算符 (0b00001000 << 16)。

    Examples
    --------
    >>> from scheduler import GachaStrategy, DOSSIER, UP_OPRT, GT
    >>> # 定义策略：当抽数大于50且获得情报书时，获取UP角色
    >>> strategy = GachaStrategy([[GT ^ 50, DOSSIER], UP_OPRT])
    >>> # 定义策略：获取情报书和6星角色
    >>> strategy2 = GachaStrategy([DOSSIER, OPRT])

    Notes
    -----
    - 魔数编码结构：符号位(1) | 停止掩码(7) | 条件掩码(8) | 参数(16)
    - 支持嵌套策略：[[条件1, 目标1], [条件2, 目标2], ...]
    - 策略组之间是OR关系，组内条件是AND关系
    """

    URGENT = (-1 << 31) | (0b0000001 << 24)
    DOSSIER = (-1 << 31) | (0b0000010 << 24)
    SOFT_PITY = (-1 << 31) | (0b0000100 << 24)
    UP_OPRT = (-1 << 31) | (0b0001000 << 24)
    HARD_PITY = (-1 << 31) | (0b0010000 << 24)
    POTENTIAL = (-1 << 31) | (0b0100000 << 24)
    OPRT = (-1 << 31) | (0b1000000 << 24)

    _STOP_DEFAULT_PARAM: Dict[str, int] = {
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

    _COND_MAP: Dict[int, Callable[[int, int], bool]] = {
        GT: lambda a, b: a > b,
        LT: lambda a, b: a < b,
        GE: lambda a, b: a >= b,
        LE: lambda a, b: a <= b,
    }

    _STOP_LOGIC: Dict[str, Callable[[int, Dict[str, Any], int], bool]] = {
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

    _STOP_MASK: Dict[int, str] = {
        0b0000001: "URGENT",
        0b0000010: "DOSSIER",
        0b0000100: "SOFT_PITY",
        0b0001000: "UP_OPRT",
        0b0010000: "HARD_PITY",
        0b0100000: "POTENTIAL",
        0b1000000: "OPRT",
    }

    def __init__(self, strategy: List[Any]):
        """初始化策略对象。

        Parameters
        ----------
        strategy : list
            策略描述列表，支持多种格式：
            - 简单格式：[DOSSIER, OPRT]  # 获取情报书和6星角色
            - 条件格式：[[GT ^ 50, DOSSIER], UP_OPRT]  # 当抽数>50且获得情报书时，获取UP角色
            - 嵌套格式：[[条件1, 目标1], [条件2, 目标2], ...]

        Notes
        -----
        - 策略组之间是OR关系：满足任意一组条件即停止
        - 组内条件是AND关系：需要满足组内所有条件
        - 支持旧格式兼容：所有元素都不是列表时视为一个组
        """
        self._raw_strategy = strategy
        self._compiled_groups: List[Callable[[int, Dict[str, Any]], bool]] = []
        self._compile()

    def _compile(self) -> None:
        strategy = self._raw_strategy
        compiled_groups: List[Callable[[int, Dict[str, Any]], bool]] = []

        if not isinstance(strategy, list) or len(strategy) == 0:
            self._compiled_groups = []
            return

        is_old_format = all(not isinstance(item, list) for item in strategy)
        normalized_strategy: List[List[Any]] = [strategy] if is_old_format else []
        if not is_old_format:
            for item in strategy:
                normalized_strategy.append(item if isinstance(item, list) else [item])

        for rule_group in normalized_strategy:
            if not isinstance(rule_group, list) or len(rule_group) == 0:
                continue

            compiled_rules: List[Callable[[int, Dict[str, Any]], bool]] = []
            for rule in rule_group:
                if isinstance(rule, tuple):
                    cond_magic, stop_magic = rule
                    cond_func, cond_param = self._parse_cond_magic(cond_magic)
                    stop_target, stop_param = self._parse_stop_magic(stop_magic)
                    if cond_func and stop_target and stop_target in self._STOP_LOGIC:
                        logic_func = self._STOP_LOGIC[stop_target]

                        def cond_stop_check(
                            cnt: int,
                            s: Dict[str, Any],
                            cf: Callable[[int, int], bool] = cond_func,
                            lf: Callable[[int, Dict[str, Any], int], bool] = logic_func,
                            cp: int = cond_param,
                            sp: int = stop_param,
                        ) -> bool:
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

                    def fixed_check(cnt: int, s: Dict[str, Any], m: int = rule) -> bool:
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

                        def stop_check(
                            cnt: int,
                            s: Dict[str, Any],
                            lf: Callable[[int, Dict[str, Any], int], bool] = logic_func,
                            sp: int = stop_param,
                        ) -> bool:
                            try:
                                return lf(cnt, s, sp)
                            except (TypeError, ValueError):
                                return False

                        compiled_rules.append(stop_check)
                    continue

                cond_func, cond_param = self._parse_cond_magic(rule)
                if cond_func:

                    def pure_cond_check(
                        cnt: int,
                        s: Dict[str, Any],
                        cf: Callable[[int, int], bool] = cond_func,
                        cp: int = cond_param,
                    ) -> bool:
                        try:
                            return cf(cnt, cp)
                        except (TypeError, ValueError):
                            return False

                    compiled_rules.append(pure_cond_check)

            if compiled_rules:

                def group_check(
                    cnt: int,
                    s: Dict[str, Any],
                    rules: List[Callable[[int, Dict[str, Any]], bool]] = compiled_rules,
                ) -> bool:
                    return all(rule(cnt, s) for rule in rules)

                compiled_groups.append(group_check)

        self._compiled_groups = compiled_groups

    def _parse_cond_magic(
        self, magic: int
    ) -> Tuple[Callable[[int, int], bool] | None, int]:
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

    def terminate(self, draw_cnt: int, state: Dict[str, Any] | None = None) -> bool:
        """检查是否满足策略终止条件。

        Parameters
        ----------
        draw_cnt : int
            当前累计抽数。
        state : dict or None, optional
            当前状态字典，包含各种触发标志，默认None。

        Returns
        -------
        bool
            True表示满足终止条件，应停止抽卡；False表示继续抽卡。

        Notes
        -----
        - 状态字典应包含以下可能的键：
        - urgent: bool - 是否已使用加急招募
        - dossier: bool - 是否已获得情报书
        - soft_pity: bool - 是否触发软保底
        - up_oprt: bool - 是否获得UP角色
        - oprt: bool - 是否获得6星角色
        - potential: int - 当前潜能数量
        - 如果没有任何策略组，默认返回True（立即停止）
        """
        if not isinstance(draw_cnt, int) or draw_cnt < 0:
            return True
        if state is None or not isinstance(state, dict):
            state = {}
        if len(self._compiled_groups) == 0:
            return True
        return any(
            group_check(draw_cnt, state) for group_check in self._compiled_groups
        )

    def update_strategy(self, new_strategy: List[Any]) -> None:
        """更新策略描述并重新编译。

        Parameters
        ----------
        new_strategy : list
            新的策略描述列表，格式同构造函数。
        """
        self._raw_strategy = new_strategy
        self._compile()

    def get_raw_strategy(self) -> List[Any]:
        """获取原始策略描述。

        Returns
        -------
        list
            原始策略描述列表。
        """
        return self._raw_strategy

    @staticmethod
    def decode_magic(magic: int | str) -> str:
        """解码魔数为其可读字符串表示。

        Parameters
        ----------
        magic : int or str
            魔数整数或字符串。

        Returns
        -------
        str
            可读的策略描述字符串。

        Examples
        --------
        >>> GachaStrategy.decode_magic(GachaStrategy.DOSSIER)
        'DOSSIER'
        >>> GachaStrategy.decode_magic(GachaStrategy.UP_OPRT)
        'UP_OPRT(120)'
        >>> GachaStrategy.decode_magic(50)
        'CNT >= 50'
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
        parts: List[str] = []

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
    def decode_strategy(strategy: List[Any]) -> List[Any]:
        result: List[Any] = []
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


__all__ = [
    "GachaStrategy",
    "URGENT",
    "DOSSIER",
    "SOFT_PITY",
    "UP_OPRT",
    "HARD_PITY",
    "POTENTIAL",
    "OPRT",
    "GT",
    "LT",
    "GE",
    "LE",
]
