# 开发者参考

**更新日期**：2026-05-26

本文档以当前代码实现为准，记录仓库里真正存在的模块、接口和配置。

## 1. 运行入口

| 命令 | 说明 |
|---|---|
| `uv run run.py` | 显示统一帮助 |
| `uv run run.py demo` | 抽卡演示与统计 |
| `uv run run.py eval` | 策略评估 |
| `uv run run.py exam` | 概率验证 |
| `uv run run.py server` | 启动 Web 服务 |
| `uv run server.py --dev` | Web 服务开发模式 |
| `uv run server.py --waitress --port 5000` | Waitress 生产模式 |

## 2. 核心模块

### `gacha_core/`

| 符号 | 说明 |
|---|---|
| `BatchRandom` | 批量随机数生成器，支持种子复现 |
| `GachaResult` | 抽卡结果数据类 |
| `Counters` | 抽卡状态计数器 |
| `GlobalConfigLoader` | 读取 `constants.json`、`gacha_rules.json`、`char_pool_base.json`、`char_banner.json`、`weapon_pool_base.json`、`weapon_banners.json` |
| `CharGacha` | 角色池抽卡逻辑 |
| `WeaponGacha` | 武器池申领逻辑 |

### `CharGacha`

```python
char_gacha = CharGacha(config=None, seed=-1, size=1024)
result = char_gacha.attempt(disable_guarantee=False)
rewards = char_gacha.get_accumulated_reward()
```

- `attempt()` 返回单个 `GachaResult`
- `disable_guarantee=True` 可用于分布统计
- 计数器字段：
  - `total`
  - `no_6star`
  - `no_5star_plus`
  - `no_up`
  - `guarantee_used`
  - `urgent_used`

### `WeaponGacha`

```python
weapon_gacha = WeaponGacha(config=None, seed=-1, size=1024)
results = weapon_gacha.attempt(disable_guarantee=False)
rewards = weapon_gacha.get_accumulated_reward()
```

- `attempt()` 返回 `List[GachaResult]`
- 每次申领固定 10 抽
- 计数器字段：
  - `total`
  - `no_6star`
  - `no_up`
  - `guarantee_used`

### `GlobalConfigLoader`

| 方法 | 说明 |
|---|---|
| `get_pool_data(pool_type)` | 读取角色/武器卡池数据（两类卡池都由 base pool + banner 配置组装） |
| `get_rule_config(pool_type)` | 读取抽卡规则，并转换数值类型 |
| `get_pool_info(pool_type)` | 返回当前配置集的卡池名和时间信息 |
| `get_text(key)` | 返回硬编码文案和卡池名 |
| `get_default_precision()` | 返回 `default_precision` |

默认配置路径来自 `configs/arrangement` 的第一行；如果文件不存在，则回退到 `configs/config_1`。

## 3. 策略与评分

### `scheduler/__init__.py`

对外导出：

- `Scheduler`
- `StrategyRuleSet`
- `StrategyCondition`
- `StrategyRuleEngine`
- `StrategyProtocolAdapter`
- `STRATEGY_PROTOCOL_VERSION`
- `ScoringSystem`
- `ScoringPreferences`
- `StrategyGoal`
- `StrategyTrace`
- `StageTrace`
- `StrategyScoreReport`
- `BaselineEstimator`
- `Resource`
- `LogMapConfig`

### `scheduler/strategy_rules.py`

#### 结构化节点

- `StrategyCondition(kind, operator, value)`
- `StrategyRuleSet(match="all"|"any", conditions=[...], version="strategy-structured", tags=[])`

#### 当前支持的字段

- `draws`
- `current_up`
- `six_star_count`
- `resource_left`
- `potential`
- `hard_pity`
- `urgent`
- `dossier`
- `soft_pity`
- `up_oprt`
- `oprt`

#### 兼容别名

- `draw_count` -> `draws`
- `urgent_recruitment` -> `urgent`
- `headhunting_dossier` -> `dossier`
- `current_up_count` -> `current_up`
- `up_operator_count` -> `current_up`
- `six_star_obtained_count` -> `six_star_count`

### `scheduler/strategy_protocol.py`

- 协议版本固定为 `strategy-protocol-v1`
- 顶层 `kind` 目前只接受 `structured`
- `legacy_magic` 顶层载荷会被拒绝
- `list` 类型的旧策略输入会被拒绝
- `Scheduler.banner(...)` 和 `Scheduler.evaluate_multiple_strategies(...)` 会自动调用适配层

### `scheduler/scoring.py`

| 符号 | 说明 |
|---|---|
| `SCORING_VERSION` | 当前为 `2.3.0` |
| `SCORING_CACHE_VERSION` | 当前为 `score-cache-v1` |
| `Resource` | 抽卡资源模型 |
| `StrategyGoal` | AND 目标定义 |
| `StageTrace` | 单阶段轨迹 |
| `StrategyTrace` | 单次完整策略轨迹 |
| `ScoringPreferences` | 评分偏好参数 |
| `StrategyScoreReport` | 评分输出结果 |
| `BaselineEstimator` | 基准价值估计器 |
| `ScoringSystem` | 评分主系统 |

#### 当前实现事实

- `ScoringSystem.score_traces(...)` 至少需要一个目标
- 当前评分只面向角色池，不纳入武器池
- `BaselineEstimator` 默认缓存文件是 `logs/scoring_cache.json`
- 近邻插值使用三次样条
- `ScoringPreferences` 支持历史 UP 名单、已有潜能记录和问卷状态

### `scheduler/engine.py`

- `Scheduler.banner(...)`：添加单个计划
- `Scheduler.banners(...)`：批量添加计划
- `Scheduler.evaluate(...)`：执行单策略评估
- `Scheduler.evaluate_multiple_strategies(...)`：对比多个策略
- `Scheduler.initial_standard_draws()`：把当前资源折算成标准角色池抽数

当前调度器使用的计划对象是 `BannerPlan`，而不是旧的元组格式。

## 4. Web 服务

### `server/`

- `server/app.py`：Flask 应用工厂
- `server/routes.py`：路由
- `server/resource.py`：充值、兑换和资源消耗
- `server/user.py`：用户数据读写

### Web 事实

- 用户数据保存在 SQLite 数据库 `userdata.db`
- 用户 ID 由 IP + User-Agent 生成 MD5
- 默认用户资源包括：
  - `chartered_permits`
  - `oroberyl`
  - `arsenal_tickets`
  - `origeometry`
  - `urgent_recruitment`
  - `urgent_used`
- 充值档位只接受 `6 / 30 / 98 / 198 / 328 / 648`
- 兑换只支持 `origeometry -> oroberyl` 或 `origeometry -> arsenal_tickets`

## 5. 工具包

### `tools/demo.py`

| 方法 | 默认值 | 说明 |
|---|---|---|
| `demo_char_draw(draw_times=5)` | `5` | 角色池演示 |
| `demo_weapon_apply(apply_times=1)` | `1` | 武器池演示 |
| `stats_char_quota(draw_times=50000, gragh=False)` | `50000` | 角色池配额分布 |
| `stats_weapon_quota(draw_times=50000, gragh=False)` | `50000` | 武器池配额分布 |
| `stats_char_up_prob(test_times=50000, gragh=False, limit=0)` | `50000` | 抽到 UP 角色所需抽数 |
| `stats_char_potential(draw_times=50000, gragh=False)` | `50000` | 满潜所需抽数 |

### `tools/evaluation.py`

- 默认读取 `tools/evaluation_examples.json`
- 支持 `shared`、`scenarios`、`run_order`
- 每个场景可以覆盖资源、计数器、权重、目标、模拟规模和 worker 数

### `tools/examination.py`

- 通过关闭保底机制验证纯概率分布
- 角色池和武器池都使用当前配置文件

## 6. 配置目录

### 实际存在的配置文件

- `configs/constants.json`
- `configs/char_pool_base.json`
- `configs/config_*/char_banner.json`
- `configs/weapon_pool_base.json`
- `configs/config_*/weapon_banners.json`
- `configs/config_*/gacha_rules.json`
- `configs/arrangement`
- `configs/arrange1`

### 重要事实

- `gacha_rules.json` 以覆盖方式合并到 `constants.json`
- `constants.json.banner_defaults` 为角色池和武器池提供共享 banner 默认值
- `config_1` 是默认示例配置
- `arrange1` 用于调度器默认顺序
- `arrangement` 的第一行决定默认加载目录

## 7. 术语对照

| 代码术语 | 含义 |
|---|---|
| `chartered_permits` | 特许寻访凭证 |
| `oroberyl` | 嵌晶玉 |
| `arsenal_tickets` | 武库配额 |
| `origeometry` | 衍质源石 |
| `urgent_recruitment` | 加急招募 |
| `guarantee_used` | 当期硬保底是否已消耗 |

## 8. 维护建议

- 新增文档前先确认代码中是否真的存在对应接口
- 旧的游戏机制描述如果无法在代码里找到实现，应写成“未实现”而不是“已实现”
- 更新文档后，至少执行一次 `ruff`、`pyright` 和相关测试
