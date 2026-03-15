# Scheduler Module Knowledge Base

**Generated:** 2026-03-15
**Module:** Strategy Scheduling System

## OVERVIEW

魔数编码策略调度系统，支持多卡池连续模拟、批量并行评估和科学评分体系，是Endfield Gacha的核心策略分析模块。

## STRUCTURE

```
scheduler/
├── __init__.py    # 模块导出（对外暴露核心接口）
├── engine.py      # 调度器主逻辑 Scheduler
├── strategy.py    # 魔数编码策略系统 GachaStrategy
├── scoring.py     # 资源与评分系统 Resource / ScoringSystem
├── workers.py     # 多进程worker与辅助方法
└── display.py     # 结果展示与报告生成
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| 创建新策略 | `strategy.py` | 使用魔数编码定义停止条件 |
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

四维科学评分系统，采用3:2:1价值权重（当期UP:往期UP:常驻6星）。

**四维评分体系：**

| 维度 | 权重 | 说明 |
|------|------|------|
| 目标达成效用 | 40% | 评估策略达成目标的能力 |
| 资源利用效率 | 20% | 评估资源使用的经济性 |
| 风险控制能力 | 25% | 评估策略的抗风险能力 |
| 策略灵活性 | 15% | 评估策略的调整潜力 |

**双模式支持：**

- **相对模式**：基于策略组内相对表现评分，适合同组策略对比
- **绝对模式**：基于绝对阈值评分，适合跨组策略评估

**评分等级：**

| 等级 | 分数区间 | 描述 |
|------|----------|------|
| S | 83.33-100 | 极佳 |
| A | 66.67-83.32 | 优秀 |
| B | 50.00-66.66 | 良好 |
| C | 33.33-49.99 | 一般 |
| D | 16.67-33.32 | 较差 |
| E | 0-16.67 | 失败 |

**核心方法：**

- `calculate_raw_statistics(results)`: 计算原生统计量
- `calculate_comprehensive_score(raw_stats, mode, ...)`: 计算综合评分
- `get_grade(score)`: 获取评分等级

### 3. NativeStatistics (scoring.py)

原生统计量数据结构，包含四类统计量：

**1. 分级目标达成类**

- `p_i_t`: 分级目标达成概率列表
- `p_t`: 总目标达成概率
- `p_core`: 核心目标达成概率
- `u_raw`: 原始效用值

**2. 资源消耗与留存类**

- `e_k_total`: 期望总抽数
- `e_w_total`: 期望总资源消耗
- `e_r_remain`: 期望剩余资源

**3. 风险控制类**

- `p_down`: 向下风险概率
- `cv`: 变异系数
- `p_zero`: 零收益概率

**4. 策略灵活性类**

- `e_r_flex`: 期望灵活性资源

### 4. GachaStrategy (strategy.py)

魔数编码策略系统，使用32位整数编码停止条件。

**魔数编码结构：**

```
符号位(1) | 停止掩码(7) | 条件掩码(8) | 参数(16)
```

**预定义魔数常量：**

- `DOSSIER`: 情报书
- `OPRT`: 6星角色
- `UP_OPRT`: UP角色
- `URGENT`: 加急招募
- `SOFT_PITY`: 软保底
- `HARD_PITY`: 硬保底
- `POTENTIAL`: 潜能

**比较运算符：**

- `GT`: 大于
- `LT`: 小于
- `GE`: 大于等于
- `LE`: 小于等于

## CONVENTIONS

- 魔数编码：32位整数 `符号位(1) | 停止掩码(7) | 条件掩码(8) | 参数(16)`
- 策略定义使用大写常量命名，如 `UP_OPRT = 0b0000001`
- 多进程评估默认使用4个worker，可通过workers参数调整
- 配置顺序默认使用 `configs/arrange1`（config_3到config_7）
- 评分系统使用3:2:1价值权重（当期UP:往期UP:常驻6星）
- 评分维度权重：目标达成40%、资源效率20%、风险控制25%、策略灵活性15%

## USAGE EXAMPLES

### 基本用法

```python
from scheduler import Scheduler, DOSSIER, OPRT, UP_OPRT

# 创建调度器
scheduler = Scheduler(config_dir="configs", arrange="arrange1")

# 添加计划 - 使用name参数指定卡池
scheduler.banner([DOSSIER, OPRT], name="config_3")
scheduler.banner([UP_OPRT], name="config_5")

# 或者批量添加
cycles = [
    {"rules": [DOSSIER, OPRT], "name": "config_3"},
    {"rules": [UP_OPRT], "name": "config_5", "use_ori": True},
]
scheduler.banners(cycles)

# 执行评估（自动校验）
scheduler.evaluate(scale=5000, workers=4)
```

### 评分系统使用

```python
from scheduler import ScoringSystem

# 计算原生统计量
raw_stats = ScoringSystem.calculate_raw_statistics(strategy_results)

# 计算综合评分（相对模式）
scores = ScoringSystem.calculate_comprehensive_score(
    [raw_stats],
    mode="relative"
)

# 获取等级
grade, grade_name, grade_style = ScoringSystem.get_grade(
    scores[0]["total_score"]
)
```

## ANTI-PATTERNS

- 不要直接导入子模块，优先使用 `from scheduler import Scheduler, ...`
- 不要修改魔数常量定义，会破坏现有策略兼容性
- 不要在调度器中添加业务逻辑，保持策略与核心抽卡逻辑分离
- 不要混用旧格式元组，只使用 BannerPlan 数据类
- 不要在调用 evaluate() 前跳过 _validate_schedules() 校验

## REFERENCES

- 详细设计文档：`策略评分系统设计方案.md`
- 项目主文档：`README.md`
