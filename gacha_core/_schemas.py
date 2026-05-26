# -*- coding: utf-8 -*-
"""Schema 版本常量与配置校验工具函数。"""

import os
from copy import deepcopy
from typing import Any, Dict, List

CHAR_BANNER_SCHEMA_VERSION = "char-banner"
CHAR_POOL_BASE_SCHEMA_VERSION = "char-pool-base"
GLOBAL_CONSTANTS_SCHEMA_VERSION = "global-constants"
WEAPON_BANNER_SCHEMA_VERSION = "weapon-banner"
WEAPON_BANNERS_SCHEMA_VERSION = "weapon-banners"
WEAPON_POOL_BASE_SCHEMA_VERSION = "weapon-pool-base"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并两个字典，override 覆盖 base。"""
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = deepcopy(value)
    return base


def _normalize_name_list(payload: Any, field_name: str) -> List[str]:
    """校验并标准化角色名称列表（非空、去重）。"""
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{field_name} 必须是非空数组")
    names: List[str] = []
    for item in payload:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} 中存在非法名称")
        names.append(item.strip())
    if len(set(names)) != len(names):
        raise ValueError(f"{field_name} 中存在重复名称")
    return names


def _normalize_optional_name_list(payload: Any, field_name: str) -> List[str]:
    """校验并标准化可选角色名称列表（允许为空）。"""
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError(f"{field_name} 必须是数组")
    names: List[str] = []
    for item in payload:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} 中存在非法名称")
        names.append(item.strip())
    if len(set(names)) != len(names):
        raise ValueError(f"{field_name} 中存在重复名称")
    return names


def _normalize_weapon_entries(
    payload: Any, field_name: str, *, allow_empty: bool
) -> List[Dict[str, str]]:
    """校验并标准化武器条目列表。"""
    if payload is None:
        if allow_empty:
            return []
        raise ValueError(f"{field_name} 不能为空")
    if not isinstance(payload, list):
        raise ValueError(f"{field_name} 必须是数组")
    if not payload and not allow_empty:
        raise ValueError(f"{field_name} 不能为空")
    entries: List[Dict[str, str]] = []
    names: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"{field_name} 中存在非法条目")
        name = item.get("name")
        weapon_type = item.get("type")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{field_name} 中存在非法武器名")
        if not isinstance(weapon_type, str) or not weapon_type.strip():
            raise ValueError(f"{field_name} 中存在非法武器类型")
        name = name.strip()
        if name in names:
            raise ValueError(f"{field_name} 中存在重复武器: {name}")
        names.add(name)
        entries.append({"name": name, "type": weapon_type.strip()})
    return entries


def _normalize_banner_id(payload: Any, field_name: str) -> str:
    """校验并标准化 banner ID。"""
    if not isinstance(payload, str) or not payload.strip():
        raise ValueError(f"{field_name} 必须是非空字符串")
    return payload.strip()


__all__ = [
    "BASE_DIR",
    "CHAR_BANNER_SCHEMA_VERSION",
    "CHAR_POOL_BASE_SCHEMA_VERSION",
    "GLOBAL_CONSTANTS_SCHEMA_VERSION",
    "WEAPON_BANNER_SCHEMA_VERSION",
    "WEAPON_BANNERS_SCHEMA_VERSION",
    "WEAPON_POOL_BASE_SCHEMA_VERSION",
    "_deep_merge",
    "_normalize_banner_id",
    "_normalize_name_list",
    "_normalize_optional_name_list",
    "_normalize_weapon_entries",
]
