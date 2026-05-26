# -*- coding: utf-8 -*-
"""配置加载与标准化。"""

import json
import os
from copy import deepcopy
from decimal import Decimal, getcontext
from typing import Any, Dict, List

CHAR_BANNER_SCHEMA_VERSION = "char-banner"
CHAR_POOL_BASE_SCHEMA_VERSION = "char-pool-base"
GLOBAL_CONSTANTS_SCHEMA_VERSION = "global-constants"
WEAPON_BANNER_SCHEMA_VERSION = "weapon-banner"
WEAPON_BANNERS_SCHEMA_VERSION = "weapon-banners"
WEAPON_POOL_BASE_SCHEMA_VERSION = "weapon-pool-base"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


class GlobalConfigLoader:
    """全局配置加载器，负责加载全局常量和各类配置文件，并提供统一接口访问

    用于加载和管理所有配置文件，包括全局常量、卡池数据、抽卡规则等。

    Examples
    --------
    >>> from gacha_core import GlobalConfigLoader
    >>> # 获取配置加载器实例
    >>> config = GlobalConfigLoader()
    >>> # 加载角色卡池数据
    >>> config = GlobalConfigLoader("configs/config_1")
    >>> char_pool_data = config.get_pool_data("char")
    >>> # 获取角色卡池规则配置
    >>> char_rules = config.get_rule_config("char")
    """

    @staticmethod
    def _get_default_config_path() -> str:
        """从 arrangement 文件获取默认配置路径"""
        arrangement_path = os.path.join(
            BASE_DIR, "configs", "arrangement"
        )
        try:
            with open(arrangement_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if first_line:
                    return os.path.join("configs", first_line)
        except FileNotFoundError:
            pass
        return "configs/config_1"

    def __init__(self, path: str | None = None, weapon_banner_id: str | None = None):
        """初始化配置加载器

        Parameters
        ----------
        path : str, optional
            配置文件路径，默认从 arrangement 文件第一行获取
        """
        if path is None:
            path = self._get_default_config_path()
        self._current_path = path
        self._weapon_banner_id = weapon_banner_id
        self._config_root = os.path.dirname(path) or "configs"
        self._cache: Dict[str, Any] = {}
        self.constants = self._load_constants()
        getcontext().prec = self.constants.get("default_precision", 6)

    def _load_constants(self) -> Dict[str, Any]:
        """加载全局常量配置（constants.json + 当前目录覆盖）

        Returns
        -------
        Dict[str, Any]
            包含全局常量的字典

        Raises
        ------
        FileNotFoundError
            当 constants.json 或 gacha_rules.json 配置文件不存在时
        ValueError
            当配置文件格式错误时
        """
        base_payload = self._load_root_config("constants.json")
        if base_payload.get("schema_version") != GLOBAL_CONSTANTS_SCHEMA_VERSION:
            raise ValueError("constants.json 缺少有效的 schema_version")
        local_rules = self.load_config("gacha_rules.json")
        merged = self._deep_merge(deepcopy(base_payload), local_rules)
        if "char" not in merged or "weapon" not in merged:
            raise ValueError("gacha_rules.json 与 constants.json 合并后缺少 char/weapon 规则")
        return merged

    def _get_banner_defaults(self, pool_type: str) -> Dict[str, Any]:
        defaults = self.constants.get("banner_defaults", {})
        if not isinstance(defaults, dict):
            return {}
        payload = defaults.get(pool_type, {})
        if not isinstance(payload, dict):
            return {}
        return deepcopy(payload)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                base[key] = GlobalConfigLoader._deep_merge(base[key], value)
            else:
                base[key] = deepcopy(value)
        return base

    def _get_config_path(self, file_name: str) -> str:
        """获取配置文件路径

        Parameters
        ----------
        file_name : str
            配置文件名称

        Returns
        -------
        str
            配置文件的完整路径
        """
        return os.path.join(BASE_DIR, self._current_path, file_name)

    def _get_root_config_path(self, file_name: str) -> str:
        return os.path.join(BASE_DIR, self._config_root, file_name)

    def load_config(self, file_name: str) -> Dict[str, Any]:
        """加载指定配置文件

        Parameters
        ----------
        file_name : str
            配置文件名称

        Returns
        -------
        Dict[str, Any]
            配置文件内容

        Raises
        ------
        FileNotFoundError
            当配置文件不存在时
        ValueError
            当配置文件格式错误时
        """
        if file_name in self._cache:
            return self._cache[file_name]
        config_path = self._get_config_path(file_name)
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache[file_name] = data
                return data
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件 {config_path} 不存在")
        except json.JSONDecodeError:
            raise ValueError(f"配置文件 {file_name} 格式错误")

    def _load_root_config(self, file_name: str) -> Dict[str, Any]:
        cache_key = f"root::{file_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        config_path = self._get_root_config_path(file_name)
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache[cache_key] = data
                return data
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件 {config_path} 不存在")
        except json.JSONDecodeError:
            raise ValueError(f"配置文件 {file_name} 格式错误")

    @staticmethod
    def _normalize_name_list(payload: Any, field_name: str) -> List[str]:
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

    @staticmethod
    def _normalize_optional_name_list(payload: Any, field_name: str) -> List[str]:
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

    @staticmethod
    def _normalize_weapon_entries(
        payload: Any, field_name: str, *, allow_empty: bool
    ) -> List[Dict[str, str]]:
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

    def _load_char_pool_base(self) -> Dict[str, Any]:
        cache_key = "normalized::char_pool_base"
        if cache_key in self._cache:
            return self._cache[cache_key]

        payload = self._load_root_config("char_pool_base.json")
        if payload.get("schema_version") != CHAR_POOL_BASE_SCHEMA_VERSION:
            raise ValueError("char_pool_base.json 缺少有效的 schema_version")

        shared_pools = payload.get("shared_pools")
        if not isinstance(shared_pools, dict) or not shared_pools:
            raise ValueError("char_pool_base.json.shared_pools 必须是非空对象")

        normalized_profiles: Dict[str, Dict[str, List[str]]] = {}
        for profile_name, profile in shared_pools.items():
            if not isinstance(profile_name, str) or not isinstance(profile, dict):
                raise ValueError("char_pool_base.json.shared_pools 存在非法条目")
            normalized_profiles[profile_name] = {
                "six_star_normal": self._normalize_optional_name_list(
                    profile.get("six_star_normal", []),
                    f"shared_pools.{profile_name}.six_star_normal",
                ),
                "five_star": self._normalize_name_list(
                    profile.get("five_star"),
                    f"shared_pools.{profile_name}.five_star",
                ),
                "four_star": self._normalize_name_list(
                    profile.get("four_star"),
                    f"shared_pools.{profile_name}.four_star",
                ),
            }

        normalized = {
            "schema_version": CHAR_POOL_BASE_SCHEMA_VERSION,
            "shared_pools": normalized_profiles,
        }
        self._cache[cache_key] = normalized
        return normalized

    def _load_char_banner(self) -> Dict[str, Any]:
        cache_key = "normalized::char_banner"
        if cache_key in self._cache:
            return self._cache[cache_key]

        raw_payload = self.load_config("char_banner.json")
        payload = self._deep_merge(self._get_banner_defaults("char"), raw_payload)
        if payload.get("schema_version") != CHAR_BANNER_SCHEMA_VERSION:
            raise ValueError("char_banner.json 缺少有效的 schema_version")

        base_profile = payload.get("base_profile")
        if not isinstance(base_profile, str) or not base_profile:
            raise ValueError("char_banner.json.base_profile 必须是非空字符串")

        base_config = self._load_char_pool_base()
        shared_profiles = base_config["shared_pools"]
        if base_profile not in shared_profiles:
            raise ValueError(f"未知角色池基础配置: {base_profile}")

        featured = payload.get("featured")
        if not isinstance(featured, dict):
            raise ValueError("char_banner.json.featured 必须是对象")

        current_up = self._normalize_optional_name_list(
            featured.get("current_up", []), "featured.current_up"
        )
        past_up = self._normalize_optional_name_list(
            featured.get("past_up", []), "featured.past_up"
        )
        raw_featured = raw_payload.get("featured", {})
        if not isinstance(raw_featured, dict):
            raw_featured = {}
        if "normal" in raw_featured:
            normal = self._normalize_optional_name_list(
                featured.get("normal", []), "featured.normal"
            )
        else:
            normal = list(shared_profiles[base_profile]["six_star_normal"])

        combined_featured = current_up + past_up + normal
        if len(set(combined_featured)) != len(combined_featured):
            raise ValueError("featured.current_up / past_up / normal 之间存在角色冲突")

        rates = payload.get("rates")
        if not isinstance(rates, dict):
            raise ValueError("char_banner.json.rates 必须是对象")
        try:
            up_6star_total_prob = float(rates["up_6star_total_prob"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("rates.up_6star_total_prob 必须是数字") from exc
        if up_6star_total_prob < 0 or up_6star_total_prob > 1:
            raise ValueError("rates.up_6star_total_prob 必须位于 [0, 1] 区间")
        if current_up and up_6star_total_prob <= 0:
            raise ValueError("featured.current_up 非空时，rates.up_6star_total_prob 必须大于 0")
        if not current_up and up_6star_total_prob != 0:
            raise ValueError("featured.current_up 为空时，rates.up_6star_total_prob 必须为 0")

        primary_current_up = payload.get("primary_current_up")
        if primary_current_up is None:
            primary_current_up = current_up[0] if current_up else ""
        if current_up:
            if primary_current_up not in current_up:
                raise ValueError("primary_current_up 必须属于 featured.current_up")
        elif primary_current_up not in ("", None):
            raise ValueError("featured.current_up 为空时，primary_current_up 必须为空字符串")

        pool_overrides = payload.get("pool_overrides", {})
        if pool_overrides is None:
            pool_overrides = {}
        if not isinstance(pool_overrides, dict):
            raise ValueError("char_banner.json.pool_overrides 必须是对象")

        six_star_pool = list(dict.fromkeys(combined_featured))

        normalized = {
            "schema_version": CHAR_BANNER_SCHEMA_VERSION,
            "base_profile": base_profile,
            "pool_name": str(payload.get("pool_name", "")).strip(),
            "open_time": str(payload.get("open_time", "")).strip(),
            "close_time": str(payload.get("close_time", "")).strip(),
            "featured": {
                "current_up": current_up,
                "past_up": past_up,
                "normal": normal,
            },
            "rates": {"up_6star_total_prob": up_6star_total_prob},
            "primary_current_up": primary_current_up,
            "pool_overrides": pool_overrides,
            "six_star_pool": six_star_pool,
            "shared_pool": shared_profiles[base_profile],
        }
        self._cache[cache_key] = normalized
        return normalized

    def _load_weapon_pool_base(self) -> Dict[str, Any]:
        cache_key = "normalized::weapon_pool_base"
        if cache_key in self._cache:
            return self._cache[cache_key]

        payload = self._load_root_config("weapon_pool_base.json")
        if payload.get("schema_version") != WEAPON_POOL_BASE_SCHEMA_VERSION:
            raise ValueError("weapon_pool_base.json 缺少有效的 schema_version")

        shared_pools = payload.get("shared_pools")
        if not isinstance(shared_pools, dict) or not shared_pools:
            raise ValueError("weapon_pool_base.json.shared_pools 必须是非空对象")

        normalized_profiles: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
        for profile_name, profile in shared_pools.items():
            if not isinstance(profile_name, str) or not isinstance(profile, dict):
                raise ValueError("weapon_pool_base.json.shared_pools 存在非法条目")
            normalized_profiles[profile_name] = {
                "six_star_normal": self._normalize_weapon_entries(
                    profile.get("six_star_normal"),
                    f"shared_pools.{profile_name}.six_star_normal",
                    allow_empty=False,
                ),
                "five_star": self._normalize_weapon_entries(
                    profile.get("five_star"),
                    f"shared_pools.{profile_name}.five_star",
                    allow_empty=False,
                ),
                "four_star": self._normalize_weapon_entries(
                    profile.get("four_star"),
                    f"shared_pools.{profile_name}.four_star",
                    allow_empty=False,
                ),
            }
        normalized = {
            "schema_version": WEAPON_POOL_BASE_SCHEMA_VERSION,
            "shared_pools": normalized_profiles,
        }
        self._cache[cache_key] = normalized
        return normalized

    @staticmethod
    def _normalize_banner_id(payload: Any, field_name: str) -> str:
        if not isinstance(payload, str) or not payload.strip():
            raise ValueError(f"{field_name} 必须是非空字符串")
        return payload.strip()

    def _load_weapon_banners(self) -> Dict[str, Any]:
        cache_key = "normalized::weapon_banners"
        if cache_key in self._cache:
            return self._cache[cache_key]

        base_config = self._load_weapon_pool_base()
        shared_profiles = base_config["shared_pools"]
        payload = self.load_config("weapon_banners.json")
        if payload.get("schema_version") != WEAPON_BANNERS_SCHEMA_VERSION:
            raise ValueError("weapon_banners.json 缺少有效的 schema_version")

        raw_banners = payload.get("banners")
        if not isinstance(raw_banners, list) or not raw_banners:
            raise ValueError("weapon_banners.json.banners 必须是非空数组")

        defaults = self._get_banner_defaults("weapon")
        normalized_banners: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        for index, raw_banner in enumerate(raw_banners):
            if not isinstance(raw_banner, dict):
                raise ValueError("weapon_banners.json.banners 中存在非法条目")
            banner = self._deep_merge(defaults, raw_banner)
            banner_id = self._normalize_banner_id(banner.get("id"), f"banners[{index}].id")
            if banner_id in seen_ids:
                raise ValueError(f"weapon_banners.json.banners 中存在重复 id: {banner_id}")
            seen_ids.add(banner_id)

            base_profile = banner.get("base_profile")
            if not isinstance(base_profile, str) or not base_profile:
                raise ValueError(f"banners[{index}].base_profile 必须是非空字符串")
            if base_profile not in shared_profiles:
                raise ValueError(f"未知武器池基础配置: {base_profile}")

            featured = banner.get("featured")
            if not isinstance(featured, dict):
                raise ValueError(f"banners[{index}].featured 必须是对象")
            current_up = self._normalize_weapon_entries(
                featured.get("current_up"),
                f"banners[{index}].featured.current_up",
                allow_empty=True,
            )
            current_up_names = [item["name"] for item in current_up]

            rates = banner.get("rates")
            if not isinstance(rates, dict):
                raise ValueError(f"banners[{index}].rates 必须是对象")
            try:
                up_6star_total_prob = float(rates["up_6star_total_prob"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"banners[{index}].rates.up_6star_total_prob 必须是数字") from exc
            if up_6star_total_prob < 0 or up_6star_total_prob > 1:
                raise ValueError("rates.up_6star_total_prob 必须位于 [0, 1] 区间")
            if current_up and up_6star_total_prob <= 0:
                raise ValueError("featured.current_up 非空时，rates.up_6star_total_prob 必须大于 0")
            if not current_up and up_6star_total_prob != 0:
                raise ValueError("featured.current_up 为空时，rates.up_6star_total_prob 必须为 0")

            primary_current_up = banner.get("primary_current_up")
            if primary_current_up is None:
                primary_current_up = current_up_names[0] if current_up_names else ""
            if current_up_names:
                if primary_current_up not in current_up_names:
                    raise ValueError("primary_current_up 必须属于 featured.current_up")
            elif primary_current_up not in ("", None):
                raise ValueError("featured.current_up 为空时，primary_current_up 必须为空字符串")

            pool_overrides = banner.get("pool_overrides", {})
            if pool_overrides is None:
                pool_overrides = {}
            if not isinstance(pool_overrides, dict):
                raise ValueError("weapon banner pool_overrides 必须是对象")

            six_star_add = self._normalize_weapon_entries(
                pool_overrides.get("six_star_add", []),
                f"banners[{index}].pool_overrides.six_star_add",
                allow_empty=True,
            )

            shared_pool = shared_profiles[base_profile]
            shared_name_map = {
                item["name"]: item
                for item in shared_pool["six_star_normal"] + shared_pool["five_star"] + shared_pool["four_star"]
            }
            current_name_set = set(current_up_names)
            overlap_with_shared = current_name_set & set(shared_name_map.keys())
            if overlap_with_shared:
                names = ",".join(sorted(overlap_with_shared))
                raise ValueError(f"featured.current_up 与共享武器池重复: {names}")

            six_star_name_map = {item["name"]: item for item in shared_pool["six_star_normal"]}
            for item in six_star_add:
                six_star_name_map[item["name"]] = item
            for item in current_up:
                six_star_name_map[item["name"]] = item

            normalized_banners.append(
                {
                    "id": banner_id,
                    "schema_version": WEAPON_BANNER_SCHEMA_VERSION,
                    "base_profile": base_profile,
                    "pool_name": str(banner.get("pool_name", "")).strip(),
                    "open_time": str(banner.get("open_time", "")).strip(),
                    "close_time": str(banner.get("close_time", "")).strip(),
                    "featured": {"current_up": current_up},
                    "rates": {"up_6star_total_prob": up_6star_total_prob},
                    "primary_current_up": primary_current_up,
                    "pool_overrides": {"six_star_add": six_star_add},
                    "shared_pool": shared_pool,
                    "six_star_pool": [six_star_name_map[name] for name in six_star_name_map],
                }
            )

        default_banner_id = payload.get("default_banner_id")
        if default_banner_id is None:
            default_banner_id = normalized_banners[0]["id"]
        default_banner_id = self._normalize_banner_id(default_banner_id, "default_banner_id")
        if default_banner_id not in seen_ids:
            raise ValueError("default_banner_id 必须指向已声明的 weapon banner")

        normalized = {
            "schema_version": WEAPON_BANNERS_SCHEMA_VERSION,
            "default_banner_id": default_banner_id,
            "banners": normalized_banners,
        }
        self._cache[cache_key] = normalized
        return normalized

    def _load_weapon_banner(self) -> Dict[str, Any]:
        payload = self._load_weapon_banners()
        banner_id = self._weapon_banner_id or payload["default_banner_id"]
        for banner in payload["banners"]:
            if banner["id"] == banner_id:
                return banner
        raise ValueError(f"未知 weapon banner id: {banner_id}")

    def get_weapon_banners(self) -> List[Dict[str, Any]]:
        payload = self._load_weapon_banners()
        return deepcopy(payload["banners"])

    def get_active_weapon_banner_id(self) -> str:
        return self._load_weapon_banner()["id"]

    def get_char_featured_names(self) -> Dict[str, List[str]]:
        banner = self._load_char_banner()
        return {
            "current_up": list(banner["featured"]["current_up"]),
            "past_up": list(banner["featured"]["past_up"]),
            "normal": list(banner["featured"]["normal"]),
        }

    def _build_char_pool_data(self) -> Dict[str, List[Dict[str, Any]]]:
        banner = self._load_char_banner()
        current_up = banner["featured"]["current_up"]
        past_up = banner["featured"]["past_up"]
        normal = banner["featured"]["normal"]
        total_up_prob = banner["rates"]["up_6star_total_prob"]
        up_prob = total_up_prob / len(current_up) if current_up else 0.0

        six_star_pool = [
            {"name": name, "up_prob": up_prob}
            for name in current_up
        ] + [
            {"name": name, "up_prob": 0.0}
            for name in past_up + normal
        ]

        return {
            "6": six_star_pool,
            "5": [{"name": name, "up_prob": 0.0} for name in banner["shared_pool"]["five_star"]],
            "4": [{"name": name, "up_prob": 0.0} for name in banner["shared_pool"]["four_star"]],
        }

    def _build_weapon_pool_data(self) -> Dict[str, List[Dict[str, Any]]]:
        banner = self._load_weapon_banner()
        current_up = banner["featured"]["current_up"]
        shared_pool = banner["shared_pool"]
        total_up_prob = banner["rates"]["up_6star_total_prob"]
        up_prob = total_up_prob / len(current_up) if current_up else 0.0
        current_up_names = {item["name"] for item in current_up}

        six_star_pool = [
            {"name": item["name"], "type": item["type"], "up_prob": up_prob}
            for item in current_up
        ] + [
            {"name": item["name"], "type": item["type"], "up_prob": 0.0}
            for item in banner["six_star_pool"]
            if item["name"] not in current_up_names
        ]
        five_star_pool = [
            {"name": item["name"], "type": item["type"], "up_prob": 0.0}
            for item in shared_pool["five_star"]
        ]
        four_star_pool = [
            {"name": item["name"], "type": item["type"], "up_prob": 0.0}
            for item in shared_pool["four_star"]
        ]

        return {
            "6": six_star_pool,
            "5": five_star_pool,
            "4": four_star_pool,
        }

    def get_pool_data(self, pool_type: str) -> Dict[str, List[Dict]]:
        """获取卡池数据

        Parameters
        ----------
        pool_type : str
            卡池类型，如 "char"或 "weapon"（武器卡池）

        Returns
        -------
        Dict[str, List[Dict]]
            卡池数据，包含不同星级的干员或武器列表
        """
        if pool_type == "char":
            return deepcopy(self._build_char_pool_data())
        if pool_type == "weapon":
            return deepcopy(self._build_weapon_pool_data())
        raise ValueError(f"未知卡池类型: {pool_type}")

    def get_rule_config(self, pool_type: str) -> Dict[str, Any]:
        """获取抽卡规则配置，返回隔离副本并统一类型转换

        Parameters
        ----------
        pool_type : str
            卡池类型，如 "char"或 "weapon"（武器卡池）

        Returns
        -------
        Dict[str, Any]
            抽卡规则配置副本，包含概率、保底规则等。
            返回值不会回写到内部 JSON 缓存。
        """
        try:
            rules = deepcopy(self.constants[pool_type])
        except KeyError as exc:
            raise KeyError(f"缺少 {pool_type} 抽卡规则配置") from exc
        # 类型转换：str键→int键，概率→Decimal
        rules["quota_rule"] = {int(k): int(v) for k, v in rules["quota_rule"].items()}
        rules["base_prob"] = {
            int(k): Decimal(str(v)) for k, v in rules["base_prob"].items()
        }
        if pool_type == "char":
            banner = self._load_char_banner()
            rules["up_char_name"] = banner["primary_current_up"]
        if pool_type == "weapon":
            banner = self._load_weapon_banner()
            rules["up_weapon_name"] = banner["primary_current_up"]
        return rules

    def get_text(self, key: str) -> str:
        """获取文本常量(基本废弃)

        注意：text_constants字段已从配置文件中移除，现在返回硬编码值

        Parameters
        ----------
        key : str
            文本常量的键名

        Returns
        -------
        str
            对应的文本常量值
        """
        # 硬编码的文本常量值（原text_constants字段内容）
        text_constants = {
            "char_quota_name": "武库配额",
            "weapon_quota_name": "集成配额",
            "draw_text": "寻访",
            "apply_text": "申领",
            "weapon_draw_text": "抽",
            "star_text": "星",
            "up_text": "概率提升",
            "rate_text": "出率",
            "time_text": "秒",
            "total_time_text": "总耗时",
            "per_second_text": "每秒",
        }

        # 特殊处理：卡池名称从pool_info获取
        if key == "char_pool_name":
            return self._load_char_banner().get("pool_name", "")
        elif key == "weapon_pool_name":
            return self._load_weapon_banner().get("pool_name", "")

        # 返回硬编码的文本常量
        if key in text_constants:
            return text_constants[key]

        # 如果键不存在，返回空字符串
        return ""

    def get_default(self, key: str) -> Any:
        """获取默认值（已弃用，使用get_default_precision代替）

        Parameters
        ----------
        key : str
            默认值的键名

        Returns
        -------
        Any
            对应的默认值
        """
        # 兼容旧代码，default_precision现在直接在根层级
        if key == "default_precision":
            return self.constants.get("default_precision", 6)
        return None

    def get_default_precision(self) -> int:
        """获取默认精度

        Returns
        -------
        int
            默认精度值
        """
        return self.constants.get("default_precision", 6)

    def get_pool_info(self, pool_type: str) -> Dict[str, Any]:
        """获取卡池信息（开放时间、结束时间等）

        Parameters
        ----------
        pool_type : str
            卡池类型，如 "char"或 "weapon"

        Returns
        -------
        Dict[str, Any]
            卡池信息，包含开放时间、结束时间等
        """
        if pool_type == "char":
            banner = self._load_char_banner()
            return {
                "name": banner.get("pool_name", ""),
                "open_time": banner.get("open_time", ""),
                "close_time": banner.get("close_time", ""),
            }
        if pool_type == "weapon":
            banner = self._load_weapon_banner()
            return {
                "name": banner.get("pool_name", ""),
                "open_time": banner.get("open_time", ""),
                "close_time": banner.get("close_time", ""),
            }
        return {"name": "", "open_time": "", "close_time": ""}

