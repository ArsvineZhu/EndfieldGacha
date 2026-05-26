# 新评分系统后端实现记录

- 日期：2026-05-26
- 归档版本：`SCORING_VERSION = 2.3.0`
- 适用范围：角色池评分内核、策略运行时、缓存与复查标签

## 本次实现目标

1. 在现有代码中保留旧魔数策略文件作为历史存档，但不再把它们作为协议输入。
2. 让评分系统具备文件缓存、参数标签、已有潜能、历史 UP 名单和 6 星分布估计能力。
3. 将 `G(c,s;theta)` 的工程实现固定为“确定性 Monte Carlo + 文件缓存 + 邻近点三次样条插值”。

## 已实现内容

### 1. 评分与报告

- `scheduler/scoring.py`
  - `ScoringPreferences`
    - `goal_weight`
    - `utility_weight`
    - `resource_weight`
    - `risk_weight`
    - `utility_absolute_reference`
    - `opportunity_reference`
    - `baseline_samples`
    - `baseline_seed`
    - `past_up_character_names`
    - `owned_character_potentials`
    - `questionnaire_status`
    - `future_value_policy`
  - `StrategyScoreReport`
    - `scoring_version`
    - `parameter_tags`
    - `cache_tags`
  - `BaselineEstimator`
    - 默认缓存文件：`logs/scoring_cache.json`
    - `estimate(...)`
    - `estimate_six_star_distribution(...)`
    - 对近邻状态点做三次样条插值

### 2. 策略系统

- `scheduler/strategy_rules.py`
  - `StrategyCondition`
  - `StrategyRuleSet`
  - `StrategyRuleEngine`
  - 支持嵌套布尔组
  - 支持字段：
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
- `scheduler/strategy_protocol.py`
  - 协议版本：`strategy-protocol-v1`
  - 只接受 `structured` 载荷
  - 明确拒绝 `legacy_magic` 和旧版 list 输入
- `scheduler/workers.py`
  - `StrategyRuntime` 只包装 `StrategyRuleEngine`
  - 当前运行时只执行结构化规则
- `scheduler/display.py`
  - 可将结构化策略描述为展示文本

### 3. 模拟系统增强

- worker 轨迹保留：
  - 阶段起止计数器
  - `paid_draws`
  - `bonus_draws`
  - 逐抽结果
  - `resource_left`
- 评分主链路以 `paid_draws` 作为主要付费抽数口径
- 加急招募作为 `bonus_draws` 进入轨迹

### 4. 缓存策略

#### 基准价值缓存

- 缓存键维度：
  - `config_name`
  - `counters_signature`
  - `paid_draws`
  - `preferences_signature`
  - `samples`
  - `seed`
- 命中直接返回缓存结果
- 未命中但存在足够近邻点时，优先三次样条插值

#### 6 星分布缓存

- 输出用于：
  - `E_6(c,s)`
  - `P(N_6 = k | c,s)`
  - `P(N_6 >= k | c,s)`

### 5. 参数标签与复查

当前报告会携带参数标签，示例：

- `scoring:2.3.0`
- `preset:balanced`
- `o_ref:60.0`
- `u_ref:700.0`
- `baseline_samples:64`
- `baseline_seed:20260525`
- `questionnaire:pending`
- `future_value:current`
- `past_up_count:N`
- `owned_potential_count:N`
- `weapon:excluded`
- `goal_mode:and`
- `baseline_interp:near-state-cubic-spline`

## 明确未做或仅作为存档保留

1. 武器池纳入评分：未做
2. `legacy_magic` 策略继续作为输入：未做，协议层已拒绝
3. 复杂目标逻辑（OR、层级目标、软硬目标）：未做，当前仅支持多个目标 AND 聚合
4. 问卷前端与问卷参数生成：未做，仅保留状态位与标签

## 涉及文件

- `scheduler/scoring.py`
- `scheduler/workers.py`
- `scheduler/engine.py`
- `scheduler/strategy_rules.py`
- `scheduler/strategy_protocol.py`
- `scheduler/__init__.py`
- `scheduler/display.py`
- `README.md`
- `ref.md`
