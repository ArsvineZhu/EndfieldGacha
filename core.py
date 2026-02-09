import json
import random
import os
from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Dict, List, Tuple, Any


@dataclass
class GachaResult:
    """抽卡结果数据类，包含干员名称、星级、配额以及保底标记"""

    name: str  # 干员名称
    star: int  # 星级
    quota: int  # 配额数量
    is_up_g: bool = False  # UP保底标记，默认为False
    is_6_g: bool = False  # 6星保底标记，默认为False
    is_5_g: bool = False  # 5星保底标记，默认为False


# ===================== 全局配置加载器=====================
class GlobalConfigLoader:
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 加载全局常量
            cls._instance.constants = cls._instance._load_constants()
            # 设置精度
            getcontext().prec = cls._instance.constants["default_values"][
                "default_precision"
            ]
        return cls._instance

    def _load_constants(self) -> Dict[str, Any]:
        """加载全局常量配置"""
        # 硬编码常量文件路径，避免循环依赖
        constants_path = os.path.join(
            os.path.dirname(__file__), "config", "constants.json"
        )
        try:
            with open(constants_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"全局常量配置文件 `{constants_path}` 不存在")
        except json.JSONDecodeError:
            raise ValueError("全局常量配置文件格式错误")

    def _get_config_path(self, file_name: str) -> str:
        """获取配置文件路径"""
        config_dir = self.constants["dir_names"]["config_dir"]
        return os.path.join(os.path.dirname(__file__), config_dir, file_name)

    def load_config(self, file_name: str) -> Dict[str, Any]:
        """加载指定配置文件"""
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

    def get_pool_data(self, pool_type: str) -> Dict[str, List[Dict]]:
        """获取卡池数据"""
        file_name = f"{pool_type}_pool.json"
        return self.load_config(file_name)

    def get_rule_config(self, pool_type: str) -> Dict[str, Any]:
        """获取抽卡规则配置，统一类型转换"""
        rules = self.load_config("gacha_rules.json")[pool_type]
        # 类型转换：str键→int键，概率→Decimal
        rules["quota_rule"] = {int(k): int(v) for k, v in rules["quota_rule"].items()}
        rules["base_prob"] = {
            int(k): Decimal(str(v)) for k, v in rules["base_prob"].items()
        }
        return rules

    def get_text(self, key: str) -> str:
        """获取文本常量"""
        return self.constants["text_constants"][key]

    def get_default(self, key: str) -> Any:
        """获取默认值"""
        return self.constants["default_values"][key]


# ===================== 角色卡池类（CharGacha）=====================
class CharGacha:
    def __init__(self):
        self.pool_type = "char"
        self.config = GlobalConfigLoader()
        # 加载配置
        self.pool_data = self.config.get_pool_data(self.pool_type)
        self.rule_config = self.config.get_rule_config(self.pool_type)
        # 预缓存数据
        self._precache_data()
        # 初始化计数器
        self._init_counters()
        # 读取UP角色名称
        self.up_char_name = self.rule_config["up_char_name"]
        # 从配置读取6星概率递增起始次数（6星保底起始次数）
        self.six_star_increase_start = self.rule_config["6star_prob_increase_start"]

    def _precache_data(self):
        """预缓存UP/普通干员"""
        self.star_up_prob: Dict[int, Tuple[List[str], List[Decimal]]] = {}
        self.star_normal: Dict[int, List[str]] = {}

        for star_str in ["6", "5", "4"]:
            star = int(star_str)
            items = self.pool_data[star_str]
            up_names, up_probs, normal_names = [], [], []
            prob_acc = Decimal("0.0")

            for item in items:
                prob = Decimal(str(item["up_prob"]))
                if prob > 0:
                    up_names.append(item["name"])
                    prob_acc += prob
                    up_probs.append(prob_acc)
                else:
                    normal_names.append(item["name"])

            self.star_up_prob[star] = (up_names, up_probs)
            self.star_normal[star] = normal_names

        # 读取概率递增参数
        self.prob_increase = Decimal(str(self.rule_config["prob_increase"]))
        self.prob_upper = Decimal(str(self.rule_config["prob_upper_limit"]))

    def _init_counters(self):
        """初始化计数器"""
        self.total_draws = 0  # 累计抽卡次数
        self.no_6star_draw = 0  # 连续未出6星的抽卡次数（6星保底计数）
        self.no_5star_plus_draw = 0  # 连续未出5星/6星的抽卡次数（5星保底计数）
        self.no_up_draw = 0  # 连续未出UP角色的抽卡次数
        self.up_guarantee_used = False  # 是否已使用UP角色保底

    def _get_char_by_star(self, star: int) -> Tuple[str, int, bool]:
        """按星级随机获取干员"""
        up_names, up_probs = self.star_up_prob[star]
        normal_names = self.star_normal[star]

        if up_names:
            rand = Decimal(str(random.random()))
            for idx, prob_acc in enumerate(up_probs):
                if rand < prob_acc:
                    return up_names[idx], star, True
            return random.choice(normal_names), star, False
        else:
            return random.choice(normal_names), star, False

    def _get_up_char(self, star: int = 6) -> Tuple[str, int]:
        """获取UP干员（默认6星），等概率返回"""
        if not hasattr(self, "_up_chars"):
            self._up_chars = []
            up_names, _ = self.star_up_prob[star]
            self._up_chars.extend([(n, star) for n in up_names])
        return random.choice(self._up_chars)

    def draw_once(self) -> GachaResult:
        """角色卡池单次抽卡

        返回值：(干员名称, 星级, 配额, 是否5星保底, 是否UP保底)"""
        self.total_draws += 1
        self.no_6star_draw += 1
        self.no_5star_plus_draw += 1
        self.no_up_draw += 1

        # 步骤1：计算当前6星概率（含递增）
        base_6star_prob = self.rule_config["base_prob"][6]  # 基础0.8%
        current_6star_prob = base_6star_prob
        # 核心：从配置读取递增起始次数
        if self.no_6star_draw > self.six_star_increase_start:
            current_6star_prob += (
                self.no_6star_draw - self.six_star_increase_start
            ) * self.prob_increase
            if current_6star_prob > self.prob_upper:
                current_6star_prob = self.prob_upper

        # 步骤2：UP角色保底（连续120抽未出）- 最高优先级
        if (
            not self.up_guarantee_used
            and self.no_up_draw >= self.rule_config["up_guarantee_draw"]
        ):
            result, star_int = self._get_up_char()
            # 重置所有相关计数器
            self.no_up_draw = 0
            self.no_6star_draw = 0
            self.no_5star_plus_draw = 0
            self.up_guarantee_used = True
            quota = self.rule_config["quota_rule"][star_int]
            return GachaResult(
                name=result, star=star_int, quota=quota, is_up_g=True
            )  # UP保底触发，标记为True

        # 步骤3：判定是否触发6星保底（连续80抽未出6星，这也太非了）
        if self.no_6star_draw >= self.rule_config["guarantee_6star_draw"]:
            # 6星保底：6星100%，5/4星0%
            result, star_int, is_up = self._get_char_by_star(6)
            # 重置所有计数器
            self.no_6star_draw = 0
            self.no_5star_plus_draw = 0
            if is_up:
                self.no_up_draw = 0
            quota = self.rule_config["quota_rule"][6]
            return GachaResult(
                name=result, star=star_int, quota=quota, is_6_g=True
            )  # 6星保底触发，标记为True

        # 步骤4：判定是否触发5星保底（连续10抽未出5/6星）
        is_5star_guarantee = (
            self.no_5star_plus_draw >= self.rule_config["guarantee_5star_plus_draw"]
        )
        rand = Decimal(str(random.random()))

        if is_5star_guarantee:
            # 5星保底：6星概率=当前6星概率（0.8%/递增后），5星=1-6星概率，4星0%
            if rand < current_6star_prob:
                # 出6星：重置所有计数器
                result, star_int, is_up = self._get_char_by_star(6)
                self.no_6star_draw = 0
                self.no_5star_plus_draw = 0
                if is_up:
                    self.no_up_draw = 0
            else:
                # 出5星：仅重置5星保底计数器
                result, star_int, is_up = self._get_char_by_star(5)
                self.no_5star_plus_draw = 0
            quota = self.rule_config["quota_rule"][star_int]
            return GachaResult(
                name=result, star=star_int, quota=quota, is_5_g=True
            )  # 5星保底触发，标记为True

        # 步骤5：无保底阶段（正常抽卡）：6星概率提升后，五星与四星按比例重新映射
        base_5star_prob = self.rule_config["base_prob"][5]  # 基础8%
        base_4star_prob = self.rule_config["base_prob"][4]  # 基础91.2%
        
        # 计算剩余概率并按比例重新映射五星和四星概率
        remaining_prob = Decimal("1.0") - current_6star_prob
        if remaining_prob > 0:
            # 计算五星和四星的基础概率比例
            total_base_prob = base_5star_prob + base_4star_prob
            base_5star_ratio = base_5star_prob / total_base_prob
            
            # 重新计算五星和四星概率
            adjusted_5star_prob = remaining_prob * base_5star_ratio
            # adjusted_4star_prob = remaining_prob * (Decimal("1.0") - base_5star_ratio)
        else:
            # 剩余概率为0，所有概率都被六星挤占
            adjusted_5star_prob = Decimal("0.0")
            # adjusted_4star_prob = Decimal("0.0")
        
        if rand < current_6star_prob:
            # 出6星：重置所有计数器
            result, star_int, is_up = self._get_char_by_star(6)
            self.no_6star_draw = 0
            self.no_5star_plus_draw = 0
            if is_up:
                self.no_up_draw = 0
                self.up_guarantee_used = True  # 出6星UP时视同触发UP保底，永久失效
        elif rand < current_6star_prob + adjusted_5star_prob:
            # 出5星：重置5星保底计数器
            result, star_int, is_up = self._get_char_by_star(5)
            self.no_5star_plus_draw = 0
        else:
            # 出4星：计数器继续累积
            result, star_int, is_up = self._get_char_by_star(4)
        quota = self.rule_config["quota_rule"][star_int]

        # 改造返回值：新增保底标记
        return GachaResult(
            name=result, star=star_int, quota=quota
        )  # 无保底，标记均为False

    def get_accumulated_reward(self) -> List[Tuple[str, int]]:
        """获取累计奖励"""
        # 统计奖励出现次数
        reward_counts = {}
        reward_config = self.rule_config["rewards"]

        # 30抽奖励（一次性）
        if self.total_draws >= 30:
            reward = reward_config.get("Type_A", "加急招募")
            reward_counts[reward] = reward_counts.get(reward, 0) + 1

        # 60抽奖励（一次性）
        if self.total_draws >= 60:
            reward = reward_config.get("Type_B", "寻访情报书")
            reward_counts[reward] = reward_counts.get(reward, 0) + 1

        # 240抽奖励（可重复获取，每240次）
        repeat_count = self.total_draws // 240
        if repeat_count > 0:
            reward = reward_config.get("Type_C", "概率提升干员的信物")
            reward_counts[reward] = reward_counts.get(reward, 0) + repeat_count

        # 格式化奖励列表
        return [(reward, count) for reward, count in reward_counts.items()]


# ===================== 武器卡池类（WeaponGacha）=====================
class WeaponGacha:
    def __init__(self):
        self.pool_type = "weapon"
        self.config = GlobalConfigLoader()
        self.pool_data = self.config.get_pool_data(self.pool_type)
        self.rule_config = self.config.get_rule_config(self.pool_type)
        self._precache_data()
        self._init_counters()
        self.up_weapon_name = self.rule_config["up_weapon_name"]
        # 单次申领最后1抽的索引
        self.last_draw_idx = self.rule_config["apply_draws"] - 1

    def _precache_data(self):
        self.star_up_prob: Dict[int, Tuple[List[str], List[Decimal]]] = {}
        self.star_normal: Dict[int, List[str]] = {}

        for star_str in ["6", "5", "4"]:
            star = int(star_str)
            items = self.pool_data[star_str]
            up_names, up_probs, normal_names = [], [], []
            prob_acc = Decimal("0.0")

            for item in items:
                prob = Decimal(str(item["up_prob"]))
                if prob > 0:
                    up_names.append(item["name"])
                    prob_acc += prob
                    up_probs.append(prob_acc)
                else:
                    normal_names.append(item["name"])

            self.star_up_prob[star] = (up_names, up_probs)
            self.star_normal[star] = normal_names

    def _init_counters(self):
        self.total_draws = 0
        self.total_apply = 0
        self.no_6star_apply = 0  # 连续未出6星的申领次数
        self.no_up_apply = 0  # 连续未出UP的申领次数
        self.up_guarantee_used = False  # 标记UP保底是否已使用（仅生效一次）

    def _get_weapon_by_star(self, star: int) -> Tuple[str, int]:
        """按星级获取武器（优先UP，无UP则普通）"""
        up_names, up_probs = self.star_up_prob[star]
        normal_names = self.star_normal[star]

        if up_names:
            rand = Decimal(str(random.random()))
            for idx, prob_acc in enumerate(up_probs):
                if rand < prob_acc:
                    return up_names[idx], star
            return random.choice(normal_names), star
        else:
            return random.choice(normal_names), star

    def _get_only_up_weapon(self) -> Tuple[str, int]:
        """获取纯UP武器（6星，最高优先级）"""
        return self.up_weapon_name, 6

    def _get_only_6star_weapon(self) -> Tuple[str, int, bool]:
        """6星保底：从所有6星武器（含UP+通用）中随机抽取，UP概率=卡池设定值"""
        # 1. 读取6星UP武器的概率配置（通常UP占25%）
        up_names, up_probs = self.star_up_prob[6]
        normal_names = self.star_normal[6]

        # 2. 按概率判定是否出UP
        rand = Decimal(str(random.random()))
        if up_names:  # 有UP武器时
            for idx, prob_acc in enumerate(up_probs):
                if rand < prob_acc:
                    return up_names[idx], 6, True  # 出UP武器，标记为True

        # 3. 未出UP则出6星通用武器
        return random.choice(normal_names), 6, False

    def _get_only_5star_weapon(self) -> Tuple[str, int]:
        """获取5星通用武器（最低优先级）"""
        return random.choice(self.star_normal[5]), 5

    def apply_once(self) -> List[GachaResult]:
        """武器卡池单次申领：8次UP保底仅生效一次 + 固定最后1抽替换 + 优先级UP>6星>5星"""
        self.total_apply += 1
        results = []
        has_5star_plus = False  # 是否出5星及以上
        has_6star = False  # 是否出6星
        has_up = False  # 是否出UP武器
        is_6_guarantee = False  # 是否触发6星保底
        is_5_guarantee = False  # 是否触发5星保底
        is_up_guarantee = False  # 是否触发UP保底

        # 步骤1：基础抽卡（按配置次数抽卡，记录抽卡结果）
        for _ in range(self.rule_config["apply_draws"]):
            self.total_draws += 1
            rand = Decimal(str(random.random()))
            if rand < self.rule_config["base_prob"][6]:
                res, star = self._get_weapon_by_star(6)
                has_5star_plus = True
                has_6star = True
                self.no_6star_apply = 0  # 出6星重置6星保底计数
                if res == self.up_weapon_name:
                    self.no_up_apply = 0  # 出UP武器重置UP保底计数
                    has_up = True
                    self.up_guarantee_used = True  # 出6星UP视同触发UP保底，永久失效
            elif (
                rand
                < self.rule_config["base_prob"][6] + self.rule_config["base_prob"][5]
            ):
                res, star = self._get_weapon_by_star(5)
                has_5star_plus = True
            else:
                res, star = self._get_weapon_by_star(4)
            quota = self.rule_config["quota_rule"][star]
            results.append(GachaResult(name=res, star=star, quota=quota))

        # 步骤2：保底判定 + 固定替换最后1抽（优先级UP>6星>5星，UP保底仅生效一次）
        replace_weapon = None
        replace_quota = 0
        # 优先级1：UP武器保底（最高）- 仅未使用过且触发条件满足时生效
        is_up_guarantee = (
            not self.up_guarantee_used
            and not has_up
            and self.no_up_apply >= self.rule_config["up_guarantee_apply"] - 1
        )
        if is_up_guarantee:
            replace_weapon, star = self._get_only_up_weapon()
            replace_quota = self.rule_config["quota_rule"][star]
            self.up_guarantee_used = True  # 标记UP保底已使用，永久失效
            self.no_up_apply = 0
            self.no_6star_apply = 0  # 出UP必出6星，同步重置6星计数器
            has_6star = True
            has_up = True

        # 优先级2：6星武器保底（中）- 未触发UP保底时生效
        elif (
            not has_6star
            and self.no_6star_apply >= self.rule_config["guarantee_6star_apply"] - 1
        ):
            replace_weapon, star, is_up = self._get_only_6star_weapon()
            replace_quota = self.rule_config["quota_rule"][star]
            self.no_6star_apply = 0
            has_6star = True
            is_6_guarantee = True
            if is_up:
                self.no_up_apply = 0  # 出6星UP武器时同步重置UP计数器
                has_up = True

        # 优先级3：5星武器保底（最低）- 未触发前两级保底时生效
        elif not has_5star_plus and self.rule_config["per_apply_must_have"]:
            replace_weapon, star = self._get_only_5star_weapon()
            replace_quota = self.rule_config["quota_rule"][star]
            is_5_guarantee = True

        # 执行替换：固定替换最后1抽（有替换内容时）
        if replace_weapon:
            results[self.last_draw_idx] = GachaResult(
                name=replace_weapon,
                star=star,
                quota=replace_quota,
                is_up_g=is_up_guarantee,
                is_6_g=is_6_guarantee,
                is_5_g=is_5_guarantee,
            )

        # 步骤3：更新计数器（未出对应武器则计数+1；UP保底已使用则不再累计UP计数）
        if not has_up and not self.up_guarantee_used:
            self.no_up_apply += 1
        if not has_6star:
            self.no_6star_apply += 1

        # 改造返回值：新增保底标记
        return results

    def get_accumulated_reward(self) -> List[Tuple[str, int]]:
        """获取累计奖励"""
        reward_counts = {}  # 统计各奖励的次数
        reward_config = self.rule_config["rewards"]
        cycle_step = reward_config.get("cycle", 8)
        start_count = reward_config.get("start", 10)

        if self.total_apply >= start_count:
            total_cycles = (self.total_apply - start_count) // cycle_step + 1
            for round_num in range(total_cycles):
                reward = (
                    reward_config["Type_A"]
                    if round_num % 2 == 0
                    else reward_config["Type_B"]
                )
                reward_counts[reward] = reward_counts.get(reward, 0) + 1

        # 转换为 (奖励, 次数) 的格式
        rewards = [(name, count) for name, count in reward_counts.items()]
        return rewards
