# -*- coding: utf-8 -*-
"""随机数工具。"""

from decimal import Decimal
from time import time
from typing import List

from numpy import random as np_rand


class BatchRandom:
    """批量随机数生成器

    核心能力：
    1. 预生成浮点随机数序列，按需弹出
    2. 提供 Decimal 兼容接口，供旧调用方复用
    3. 统一随机状态，支持种子复现
    """

    def __init__(self, seed: int = -1, size: int = 1024):
        """初始化批量随机生成器

        Parameters
        ----------
        seed : int, optional
            随机数种子，默认-1（自动基于时间戳+微秒生成）
        size : int, optional
            预生成序列的大小，默认1024
        """
        # 优化种子生成
        if seed < 0:
            seed = int(time() * 1_000_000) % (2**32)
        self.seed = seed
        self.np_rand = np_rand.RandomState(seed)  # 独立随机状态
        self.__sequence: List[float] = []
        self._index = 0
        self.size = size
        self._randomize()

    def _randomize(self) -> List[float]:
        """生成指定数量的浮点随机数，覆盖内部序列。"""
        self.__sequence = self.np_rand.random(self.size).tolist()
        self._index = 0
        return self.__sequence.copy()

    @staticmethod
    def batch(size: int = 1024) -> List[Decimal]:
        """静态方法，直接生成指定数量的 Decimal 随机数。"""
        if not isinstance(size, int) or size <= 0:
            raise ValueError(f"随机数数量必须是正整数，当前传入: {size}")
        np_rands = np_rand.random(size)
        return [Decimal(str(num)) for num in np_rands.tolist()]

    def pop_float(self) -> float:
        """从内部随机数序列中弹出一个浮点随机数。"""
        if self._index >= len(self.__sequence):
            self._randomize()
        value = self.__sequence[self._index]
        self._index += 1
        return value

    def pop(self) -> Decimal:
        """从内部随机数序列中弹出一个 Decimal 随机数。"""
        return Decimal(str(self.pop_float()))

    @property
    def sequence(self) -> List[Decimal]:
        """返回剩余随机数序列的 Decimal 副本。"""
        return [Decimal(str(num)) for num in self.__sequence[self._index :]]
