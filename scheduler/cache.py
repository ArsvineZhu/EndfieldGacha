# -*- coding: utf-8 -*-
"""JSON 文件缓存。"""

import atexit
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

from .models import SCORING_CACHE_VERSION


class JsonFileCache:
    """简单 JSON 文件缓存。"""

    def __init__(self, cache_path: str, section: str, flush_interval: int = 32):
        self.cache_path = Path(cache_path)
        self.section = section
        self.flush_interval = max(1, int(flush_interval))
        self.cache_hits = 0
        self.cache_misses = 0
        self._dirty = False
        self._pending_writes = 0
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()
        self._data.setdefault("meta", {})
        self._data["meta"]["cache_version"] = SCORING_CACHE_VERSION
        self._data.setdefault(self.section, {})
        atexit.register(self.flush)

    def get(self, key: str) -> Any:
        section_data = self._data.get(self.section, {})
        if key in section_data:
            self.cache_hits += 1
            return section_data[key]
        self.cache_misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        self._data.setdefault("meta", {})
        self._data["meta"]["cache_version"] = SCORING_CACHE_VERSION
        self._data.setdefault(self.section, {})
        self._data[self.section][key] = value
        self._dirty = True
        self._pending_writes += 1
        if not self.cache_path.exists() or self._pending_writes >= self.flush_interval:
            self.flush()

    def flush(self) -> None:
        if not self._dirty:
            return
        self._save(self._data)
        self._dirty = False
        self._pending_writes = 0

    def _load(self) -> Dict[str, Any]:
        if not self.cache_path.exists():
            return {"meta": {"cache_version": SCORING_CACHE_VERSION}, self.section: {}}
        try:
            with self.cache_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {"meta": {"cache_version": SCORING_CACHE_VERSION}, self.section: {}}

    def _save(self, data: Dict[str, Any]) -> None:
        temp_fd, temp_name = tempfile.mkstemp(
            prefix=f"{self.cache_path.stem}.",
            suffix=".tmp",
            dir=str(self.cache_path.parent),
        )
        os.close(temp_fd)
        temp_path = Path(temp_name)
        try:
            with temp_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
            for attempt in range(5):
                try:
                    os.replace(temp_path, self.cache_path)
                    return
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass


__all__ = ["JsonFileCache"]
