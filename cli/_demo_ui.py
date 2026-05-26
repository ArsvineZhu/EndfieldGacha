# -*- coding: utf-8 -*-
"""终端颜色输出工具。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Color:
    WHITE: str = "\033[37m"
    RED: str = "\033[31m"
    YELLOW: str = "\033[33m"
    PURPLE: str = "\033[35m"
    BLUE: str = "\033[34m"
    RESET: str = "\033[0m"


def colorprint(text: str, color: str = Color.WHITE) -> None:
    print(f"{color}{text}{Color.RESET}")
