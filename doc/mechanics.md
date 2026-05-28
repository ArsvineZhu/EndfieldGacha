# 终末地卡池机制说明

**更新日期**：2026-05-28

**适用范围**：本文档描述当前仓库代码实现的抽卡、申领、资源与 Web 状态行为。若与旧版说明冲突，以代码实现为准。

---

## 1. 角色卡池

### 1.1 入口与消耗

- 对应类：`gacha_core.CharGacha`
- 单次抽卡
- 消耗 1 个 `chartered_permits`，或 500 个 `oroberyl`

### 1.2 基础概率

- 6★：0.8%
- 5★：8%
- 4★：91.2%

同星级内按配置文件中的 `up_prob` 和普通池拆分抽取。`configs/config_1` 中的当前示例卡池名为 `「熔火灼痕」`，UP 角色为 `莱万汀`。

### 1.3 保底规则

- 5★ 保底：连续 9 抽未出 5★+ 时，第 10 抽必出 5★+。
- 6★ 软保底：第 66 抽开始，每抽 6★ 概率增加 5%，最高封顶 100%。
- 6★ 硬保底：第 80 抽必出 6★。
- 当期 UP 6★ 硬保底：第 120 抽必出当期 UP 6★，且该状态由 `guarantee_used` 控制，只在当前运行状态内生效一次。

### 1.4 奖励与计数

每次角色抽卡会发放武库配额：

- 6★：2000
- 5★：200
- 4★：20

当前代码实现的累计奖励来自 `get_accumulated_reward()`：

- 30 抽：`加急招募`
- 60 抽：`寻访情报书`
- 每 240 抽：`Type_C` 对应的信物奖励

`configs/config_1` 中的 `Type_C` 文案为 `莱万汀的信物`。

---

## 2. 武器卡池

### 2.1 入口与消耗

- 对应类：`gacha_core.WeaponGacha`
- 每次申领固定为 10 抽
- 消耗 1980 个 `arsenal_tickets`

### 2.2 基础概率

- 6★：4%
- 5★：15%
- 4★：81%

同星级内按配置文件中的 `up_prob` 和普通池拆分抽取。`configs/config_1` 中的当前示例卡池名为 `「熔铸申领」`，UP 武器为 `熔铸火焰`。

### 2.3 保底规则

- 单次申领保底：若本次 10 抽没有 5★+，最后 1 抽会被替换为 5★+。
- 6★ 保底：连续 3 次申领未出 6★ 时，第 4 次申领会在最后 1 抽替换为 6★。
- UP 6★ 保底：连续 7 次申领未出当期 UP 6★ 时，第 8 次申领会在最后 1 抽替换为当期 UP 6★。
- 保底优先级：UP 6★ > 6★ > 5★

### 2.4 奖励与计数

每次武器申领会发放集成配额：

- 6★：50
- 5★：10
- 4★：1

当前代码实现的累计奖励来自 `get_accumulated_reward()`：

- 从第 10 次申领开始触发
- 之后每 8 次申领一轮，Type_A / Type_B 交替发放

---

## 3. Web 用户状态

### 3.1 用户存储

- 入口：`web/user.py`
- 数据库：`data/userdata.db`
- 用户 ID：IP + User-Agent 的 MD5

### 3.2 初始资源

新用户默认拥有：

- `chartered_permits`: 10
- `oroberyl`: 50000
- `arsenal_tickets`: 8000
- `origeometry`: 100
- `urgent_recruitment`: 0
- `urgent_used`: False

### 3.3 充值与兑换

- 充值档位：6 / 30 / 98 / 198 / 328 / 648
- `origeometry` 可兑换为：
  - `oroberyl`，比例 1:75
  - `arsenal_tickets`，比例 1:25

当前代码没有单独实现“重复角色 / 重复武器兑换为额外资源”的独立系统。重复结果只会更新收藏计数，并按抽取结果正常发放配额。

---

## 4. 配置文件

当前代码只读取以下文件：

- `configs/constants.json`
- `configs/char_pool_base.json`
- `configs/config_*/char_banner.json`
- `configs/weapon_pool_base.json`
- `configs/config_*/weapon_banners.json`
- `configs/config_*/gacha_rules.json`
- `configs/arrangement`
- `configs/arrange1`

`configs/constants.json` 提供通用概率、保底、配额和默认奖励；`config_*/gacha_rules.json` 只覆盖当期差异项。

---

## 5. 实现备注

- 抽卡结果使用 `GachaResult` 返回，包含 `name`、`star`、`quota`、`is_up_g`、`is_6_g`、`is_5_g`
- 角色池与武器池都使用 `BatchRandom` 做随机数预生成
- `disable_guarantee=True` 会禁用保底计数更新，适合做纯概率分布验证
- Web 服务中的 `compress_static_files()` 会在启动前压缩静态资源（可通过 `--dev` 跳过）


