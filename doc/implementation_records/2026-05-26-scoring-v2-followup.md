# 新评分系统后端实现归档

- 日期：2026-05-26
- 归档版本：`SCORING_V2_VERSION = 2.3.0`
- 适用范围：角色池 V2 评分内核、策略运行时、缓存与复查标签

## 本次实现目标

1. 在保留旧魔数策略系统的前提下，引入更完整的结构化策略判断系统。
2. 为 V2 评分系统补齐文件缓存、可复查标签、已有潜能、历史 UP 名单、6 星分布估计数据。
3. 将 `G(c,s;theta)` 的工程实现固定为“确定性 Monte Carlo + 文件缓存 + 邻近点三次样条插值”。
4. 对未完成或待上线项目做显式标记，避免与已实现能力混淆。

## 已实现内容

### 1. 评分与报告

- `scheduler/scoring.py`
  - `ScoringPreferences`
    - 默认 `O_ref = 60`
    - `future_value_policy = "current"`
    - `questionnaire_status = "pending"`
    - `past_up_character_names`
    - `owned_character_potentials`
  - `StrategyScoreReport`
    - 新增 `scoring_version`
    - 新增 `parameter_tags`
    - 新增 `cache_tags`
  - `BaselineEstimator`
    - 默认缓存文件：`logs/scoring_v2_cache.json`
    - 支持 `estimate(...)`
    - 支持 `estimate_six_star_distribution(...)`
    - 缺失直接缓存时，若存在足够的状态近邻点，优先三次样条插值

### 2. 策略系统

- 保留旧系统：`scheduler/strategy.py`
- 新增新系统：`scheduler/strategy_v2.py`
  - `StrategyCondition`
  - `StrategyRuleSet`
  - `StrategyRuleEngine`
  - 支持嵌套布尔组，可表达 `((A or B) and C)` 形式
  - 显式兼容旧语义字段：`urgent`、`dossier`、`soft_pity`、`up_oprt`、`oprt`、`hard_pity`
- 新增网页端兼容层：`scheduler/strategy_protocol.py`
  - 协议版本：`strategy-protocol-v1`
  - 支持 `structured` 与 `legacy_magic` 两种顶层策略载荷
  - `Scheduler.banner(...)` 与 `Scheduler.evaluate_multiple_strategies(...)` 已接入自动解析
- 新增旧系统稳定入口：`scheduler/strategy_magic.py`
  - `LegacyMagicStrategy`
  - `LEGACY_STRATEGY_VERSION = "magic-v1"`
- `scheduler/workers.py`
  - 引入 `StrategyRuntime`
  - 同时支持旧魔数策略与新结构化规则
  - 结构化规则当前可直接使用的状态字段：
    - `draws`
    - `current_up`
    - `six_star_count`
    - `resource_left`
    - `potential`
    - `dossier`
- `scheduler/display.py`
  - 展示层同时支持旧魔数策略解码与结构化规则描述输出

### 3. 模拟系统增强

- worker 轨迹保留：
  - 阶段起止计数器
  - `paid_draws`
  - `bonus_draws`
  - 逐抽结果
  - `resource_left`
- 评分主链路使用 `paid_draws` 作为主消耗 `C_i`
- 加急招募只作为 `bonus_draws` 进入轨迹与价值，不计入主付费抽数

### 4. 潜能与历史名单

- 已有角色潜能记录通过 `owned_character_potentials` 参与增量价值计算
- 历史 UP 使用 `past_up_character_names` 名称列表输入
- 新评分不接入武器池

## 缓存策略

### 基准价值缓存

- 缓存键核心维度：
  - `config_name`
  - `counters_signature`
  - `paid_draws`
  - `preferences_signature`
  - `samples`
  - `seed`
- 命中直接值时返回缓存结果
- 未命中但存在 3 个及以上状态近邻点时，使用三次样条插值
- 再未命中时执行确定性模拟并写回缓存

### 6 星分布缓存

- 输出用于以下可扩展统计：
  - `E_6(c,s)`
  - `P(N_6 = k | c,s)`
  - `P(N_6 >= k | c,s)`
- 该部分已缓存化，但当前主要作为评分解释数据与后续扩展接口

## 参数标签与复查

当前报告会携带参数标签，示例：

- `scoring:2.3.0`
- `preset:balanced`
- `o_ref:60.0`
- `baseline_samples:64`
- `baseline_seed:20260525`
- `questionnaire:pending`
- `future_value:current`
- `past_up_count:N`
- `owned_potential_count:N`
- `weapon:excluded`
- `goal_mode:and`
- `baseline_interp:near-state-cubic-spline`
- `extensions:enabled`

## 明确未做或仅标记扩展

1. 武器池纳入 V2 评分：未做
2. 问卷前端与问卷参数生成：未做，仅保留状态位与标签
3. `theta_future` 独立未来价值体系：未做，当前等同于 `current`
4. 复杂目标逻辑（OR、层级目标、软硬目标）：未做，当前仅完整支持多个目标 AND 聚合
   - 显式约束：评分调用必须至少提供一个目标；传入空目标列表会报错
5. 评分解释报告的完整展示层：部分具备，保留为扩展项
6. 更复杂的结构化策略状态字段：保留扩展

## 存疑与保留现状

- 加急招募内部模拟机制沿用现有项目逻辑，仅补充了 V2 评分所需轨迹字段
- 部分旧文档历史章节仍保留旧评分表述，实际运行以 `scheduler/scoring.py` 与本归档为准

## 涉及文件

- `scheduler/scoring.py`
- `scheduler/workers.py`
- `scheduler/engine.py`
- `scheduler/strategy_v2.py`
- `scheduler/__init__.py`
- `scheduler/display.py`
- `test/scoring_v2_test.py`
- `README.md`
- `AGENTS.md`
- `scheduler/AGENTS.md`
