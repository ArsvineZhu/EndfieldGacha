# Scheduler Module Knowledge Base

**Generated:** 2026-03-15
**Module:** Strategy Scheduling System

## OVERVIEW

结构化策略调度系统，支持多卡池连续模拟、批量并行评估和科学评分体系，是 Endfield Gacha 的核心策略分析模块。

## STRUCTURE

```
scheduler/
├── __init__.py    # 模块导出（对外暴露核心接口）
├── engine.py      # 调度器主逻辑 Scheduler
├── strategy_v2.py # 结构化策略规则系统 StrategyRuleSet / StrategyRuleEngine
├── strategy_protocol.py # 网页端 structured JSON 协议适配层
├── strategy.py    # 旧魔数策略存档
├── strategy_magic.py # 旧魔数策略存档入口
├── scoring.py     # 资源与评分系统 Resource / ScoringSystem
├── workers.py     # 多进程worker与辅助方法
└── display.py     # 结果展示与报告生成
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| 创建现行策略 | `strategy_v2.py` | 使用结构化条件定义停止条件 |
| 对接网页端策略 JSON | `strategy_protocol.py` | 解析/序列化 structured 协议对象 |
| 查阅历史魔数实现 | `strategy.py` / `strategy_magic.py` | 仅存档，不参与现行逻辑 |
| 执行批量评估 | `engine.py` | Scheduler.evaluate() 方法 |
| 自定义评分规则 | `scoring.py` | ScoringSystem 类 |
| 添加worker逻辑 | `workers.py` | 多进程处理函数 |
| 导入模块 | `__init__.py` | 已re-export所有核心符号 |
| 评分系统文档 | `策略评分系统设计方案.md` | 完整的设计方案文档 |

## CORE COMPONENTS

### 1. Scheduler (engine.py)

策略调度器主类，负责管理多卡池策略规划和批量评估。

**关键特性：**

- 支持 `banner(name=...)` 参数指定卡池配置
- 完整的校验机制：名称存在性、数量对应、名称冲突、完整性检查
- 使用 `BannerPlan` 数据类存储计划
- 支持批量评估和多策略对比

**核心方法：**

- `banner(rules, name=None, ...)`: 添加单个计划
- `banners(cycles)`: 批量添加计划
- `evaluate(scale, workers, ...)`: 执行批量评估
- `_validate_schedules()`: 完整的计划校验

### 2. ScoringSystem (scoring.py)

V2 科学评分系统，基于完整模拟轨迹、用户偏好参数和固定抽数状态基准估计。

**四模块评分体系：**

| 维度 | 权重 | 说明 |
|------|------|------|
| 目标达成分 | 可配置 | 基于 AND 目标集合完成率 |
| 期望收益分 | 可配置 | 基于 `mean_utility / mean_baseline` 的 LogMap |
| 资源机会分 | 可配置 | 基于未来机会价值倍率的 LogMap |
| 风险稳定分 | 可配置 | 最低 `q%` 样本质量均值 |

**核心数据结构：**

- `ScoringPreferences`
- `StrategyGoal`
- `StageTrace` / `StrategyTrace`
- `StrategyScoreReport`
- `BaselineEstimator`
- `StrategyRuleSet` / `StrategyRuleEngine`

**核心方法：**

- `score_traces(traces, preferences, goals, ...)`: 计算单策略原始分
- `rank_reports(reports)`: 生成同组排名与差值
- `log_map(value, config)`: 对数映射
- `estimate(config_name, counters, paid_draws, preferences)`: 估计 `G(c,s;θ)`
- `estimate_six_star_distribution(config_name, counters, paid_draws, preferences)`: 估计 6 星数量分布数据
- `get_grade(score)`: 获取评分等级

### 4. StrategyRuleEngine (strategy_v2.py)

结构化策略规则系统，用于替代仅依赖魔数的停止判断表达。

**核心特性：**

- 支持 `all` / `any` 两种匹配方式
- 支持嵌套规则组，可表达 `((A or B) and C)`、`((A and B) or (C and D))`
- 条件字段支持：
  - 新字段：`draws`、`current_up`、`six_star_count`、`resource_left`、`potential`
  - 旧语义兼容字段：`urgent` / `urgent_recruitment`、`dossier` / `headhunting_dossier`、`soft_pity`、`up_oprt`、`oprt`、`hard_pity`
- `workers.py` 中的 `StrategyRuntime` 只执行结构化规则

## CONVENTIONS

- 策略定义使用 `StrategyRuleSet` / `StrategyCondition`
- 多进程评估默认使用4个worker，可通过workers参数调整
- 配置顺序默认使用 `configs/arrange1`（config_3到config_7）
- 评分系统使用3:2:1价值权重（当期UP:往期UP:常驻6星）
- 评分维度权重：目标达成40%、资源效率20%、风险控制25%、策略灵活性15%
- `BaselineEstimator` 默认使用文件缓存，并可对状态近邻缓存点做三次样条插值
- `ScoringPreferences` 保留问卷状态、历史UP名单、已有潜能记录、版本标签和参数标签

## USAGE EXAMPLES

### 基本用法

```python
from scheduler import Scheduler, StrategyCondition, StrategyRuleSet

# 创建调度器
scheduler = Scheduler(config_dir="configs", arrange="arrange1")

# 添加计划 - 使用 name 参数指定卡池
scheduler.banner(
    StrategyRuleSet(
        match="all",
        conditions=[StrategyCondition(kind="draws", operator=">=", value=30)],
    ),
    name="config_3",
)
scheduler.banner(
    StrategyRuleSet(
        match="any",
        conditions=[
            StrategyCondition(kind="current_up", operator=">=", value=1),
            StrategyCondition(kind="draws", operator=">=", value=120),
        ],
    ),
    name="config_5",
)

# 或者批量添加
cycles = [
    {
        "rules": StrategyRuleSet(
            match="all",
            conditions=[StrategyCondition(kind="draws", operator=">=", value=30)],
        ),
        "name": "config_3",
    },
    {
        "rules": StrategyRuleSet(
            match="any",
            conditions=[
                StrategyCondition(kind="current_up", operator=">=", value=1),
                StrategyCondition(kind="draws", operator=">=", value=120),
            ],
        ),
        "name": "config_5",
        "use_ori": True,
    },
]
scheduler.banners(cycles)

# 执行评估（自动校验）
scheduler.evaluate(scale=5000, workers=4)
```

### 评分系统使用

```python
from scheduler import BaselineEstimator, ScoringPreferences, ScoringSystem

preferences = ScoringPreferences()
estimator = BaselineEstimator(config_dir="configs", samples=64, base_seed=20260525)

# traces 为完整 StrategyTrace 列表
report = ScoringSystem.score_traces(
    traces=traces,
    preferences=preferences,
    goals=None,
    baseline_estimator=estimator,
)

# 获取等级
grade, grade_name = ScoringSystem.get_grade(report.raw_score)
```

## ANTI-PATTERNS

- 不要直接导入子模块，优先使用 `from scheduler import Scheduler, ...`
- 不要向当前运行时重新接入旧魔数策略
- 不要在调度器中添加业务逻辑，保持策略与核心抽卡逻辑分离
- 不要混用旧格式元组，只使用 BannerPlan 数据类
- 不要在调用 evaluate() 前跳过 _validate_schedules() 校验

## REFERENCES

- 详细设计文档：`策略评分系统设计方案.md`
- 项目主文档：`README.md`
