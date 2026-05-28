# 开发者参考

**更新日期**：2026-05-28

本文档以当前代码实现为准，记录仓库里真正存在的模块、接口和配置。

## 1. 运行入口

| 命令 | 说明 |
|---|---|
| `uv run run.py` | 显示统一帮助 |
| `uv run run.py demo` | 抽卡演示与统计 |
| `uv run run.py eval` | 策略评估 |
| `uv run run.py exam` | 概率验证 |
| `uv run run.py server` | 启动 Web 服务（默认端口 5000） |
| `uv run run.py server --dev` | 开发模式（跳过压缩、debug 模式） |
| `uv run run.py server --waitress --port 5000` | Waitress 生产模式 |

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
- `attempt_urgent()` — 不存在独立方法；Web 端通过循环调用 `attempt()` 10 次实现加急招募
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
| `get_char_featured_names()` | 返回当期 UP、过往 UP、普通池角色名称列表 |
| `get_weapon_banners()` | 返回所有武器池配置列表 |
| `get_active_weapon_banner_id()` | 返回当前默认武器池 ID |

默认配置路径来自 `configs/arrangement` 的第一行；如果文件不存在，则回退到 `configs/config_1`。

## 3. 策略与评分

### `scheduler/__init__.py`

对外导出：

- `Scheduler`
- `StrategyRuleSet`
- `StrategyCondition`
- `StrategyRuleEngine`
- `is_structured_strategy`
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
- `Counters`

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
| `SCORING_VERSION` | 当前为 `2.4.0` |
| `SCORING_CACHE_VERSION` | 当前为 `score-cache-v1` |
| `Resource` | 抽卡资源模型 |
| `StrategyGoal` | AND 目标定义 |
| `StageTrace` | 单阶段轨迹 |
| `StrategyTrace` | 单次完整策略轨迹 |
| `ScoringPreferences` | 评分偏好参数（含问卷状态） |
| `StrategyScoreReport` | 评分输出结果 |
| `BaselineEstimator` | 基准价值估计器 |
| `ScoringSystem` | 评分主系统 |

#### 当前实现事实

- `ScoringSystem.score_traces(...)` 至少需要一个目标
- 当前评分只面向角色池，不纳入武器池
- `BaselineEstimator` 默认缓存文件是 `data/baseline_cache.db`（SQLite WAL 模式）
- 缓存可通过 `build/precompute_cache.py` 离线预计算
- 近邻插值使用三次样条
- `ScoringPreferences` 支持历史 UP 名单、已有潜能记录和问卷状态（`questionnaire_status`、`questionnaire_consistency_ratio`）

### `scheduler/engine.py`

- `Scheduler.banner(...)`：添加单个计划
- `Scheduler.banners(...)`：批量添加计划
- `Scheduler.evaluate(...)`：执行单策略评估
- `Scheduler.evaluate_multiple_strategies(...)`：对比多个策略
- `Scheduler.initial_standard_draws()`：把当前资源折算成标准角色池抽数

当前调度器使用的计划对象是 `BannerPlan`，而不是旧的元组格式。

## 4. Web 服务

### `web/`

- `web/app.py`：Flask 应用工厂，包含环境变量加载、静态文件压缩触发、pre-compressed 静态资源服务
- `web/routes/__init__.py`：路由注册入口，整合所有子模块路由
- `web/routes/gacha.py`：抽卡、加急招募、累计奖励 API
- `web/routes/info.py`：主页、用户数据、历史记录、卡池信息 API
- `web/routes/resources.py`：充值、兑换 API
- `web/routes/eval.py`：异步评估任务、策略对比 API
- `web/resource.py`：充值、兑换、资源消耗逻辑
- `web/user.py`：用户数据读写（SQLite）
- `web/eval_jobs.py`：后台评估任务管理器（`EvaluationJobManager`，线程池实现）
- `web/evaluator.py`：评估负载验证与执行、基准策略构建

### Web 事实

- 用户数据保存在 SQLite 数据库 `data/userdata.db`
- 用户 ID 由 IP + User-Agent 生成 MD5
- 默认用户资源包括：
  - `chartered_permits`: 10
  - `oroberyl`: 50000
  - `arsenal_tickets`: 8000
  - `origeometry`: 100
  - `urgent_recruitment`: 0
  - `urgent_used`: False
  - `total_recharge`: 0
  - `first_recharge`: 各档位首充标记
- 充值档位只接受 `6 / 30 / 98 / 198 / 328 / 648`
- 兑换只支持 `origeometry -> oroberyl`（1:75）或 `origeometry -> arsenal_tickets`（1:25）
- 资源操作记录在用户数据的 `char_gacha.operations` / `weapon_gacha.operations` 数组中
- 生产模式要求 `ENDFIELD_SECRET_KEY` 环境变量
- Web 端默认加载 `configs/config_6`（info 路由）或 `configs/arrangement` 第一行（evaluator 路由）

### 评估端点

- `POST /api/eval/jobs`：提交异步评估任务，返回 `job_id`，状态码 202
- `GET /api/eval/jobs/<job_id>`：查询任务状态（queued/running/succeeded/failed）
- `POST /api/eval/compare`：同步策略对比，最多 20 个策略，并发上限 2
- `GET /api/eval/configs`：列出可用卡池配置及 UP 信息

## 5. CLI 工具

### `cli/demo.py`

`GachaTestTool` 封装类（底层调用 `_demo_char.py`、`_demo_weapon.py`、`_demo_ui.py`）：

| 方法 | 默认值 | 说明 |
|---|---|---|
| `demo_char_draw(draw_times=5)` | `5` | 角色池演示 |
| `demo_weapon_apply(apply_times=1)` | `1` | 武器池演示 |
| `stats_char_quota(draw_times=50000, gragh=False)` | `50000` | 角色池配额分布 |
| `stats_weapon_quota(draw_times=50000, gragh=False)` | `50000` | 武器池配额分布 |
| `stats_char_draw(draw_times=50000, gragh=False)` | `50000` | 角色池 6★ 数量分布 |
| `stats_weapon_draw(draw_times=50000, gragh=False)` | `50000` | 武器池 6★ 数量分布 |
| `stats_char_up_prob(test_times=50000, gragh=False, limit=0)` | `50000` | 抽到 UP 角色所需抽数 |
| `stats_weapon_up_prob(test_times=50000, gragh=False, limit=0)` | `50000` | 抽到 UP 武器所需申领数 |
| `stats_urgent_quota(draw_times=50000, gragh=False)` | `50000` | 加急招募 10 连配额分布 |
| `stats_char_potential(draw_times=50000, gragh=False)` | `50000` | 满潜所需抽数 |

### `cli/evaluation.py`

- 默认读取 `cli/evaluation_examples.json`
- 支持 `shared`、`scenarios`、`run_order`
- 每个场景可以覆盖资源、计数器、权重、目标、模拟规模和 worker 数
- `run_scenario(name, scale=5000)` 执行单个场景
- `run_all()` 按 `run_order` 执行全部场景

### `cli/examination.py`

- 通过关闭保底机制验证纯概率分布
- 角色池和武器池都使用当前配置文件
- 默认读取 `configs/config_4`

## 6. 配置目录

### 实际存在的配置文件

- `configs/constants.json`
- `configs/char_pool_base.json`
- `configs/config_1/` 到 `configs/config_7/`，每个目录包含：
  - `char_banner.json`
  - `weapon_banners.json`
  - `gacha_rules.json`
- `configs/arrangement` — 列出全部 7 个配置目录，第一行为默认加载目录
- `configs/arrange1` — 调度器默认顺序（config_3 ~ config_7）

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
- 旧的游戏机制描述如果无法在代码里找到实现，应写成"未实现"而不是"已实现"
- 更新文档后，至少执行一次 `ruff`、`pyright` 和相关测试
