# Scheduler Module Knowledge Base

**Generated:** 2026-03-07
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
└── workers.py     # 多进程worker与辅助方法
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| 创建新策略 | `strategy.py` | 使用魔数编码定义停止条件 |
| 执行批量评估 | `engine.py` | Scheduler.evaluate() 方法 |
| 自定义评分规则 | `scoring.py` | ScoringSystem 类 |
| 添加worker逻辑 | `workers.py` | 多进程处理函数 |
| 导入模块 | `__init__.py` | 已re-export所有核心符号 |

## CONVENTIONS
- 魔数编码：32位整数 `符号位(1) | 停止掩码(7) | 条件掩码(8) | 参数(16)`
- 策略定义使用大写常量命名，如 `UP_OPRT = 0b0000001`
- 多进程评估默认使用4个worker，可通过workers参数调整
- 配置顺序默认使用 `configs/arrange1`（config_3到config_7）

## ANTI-PATTERNS
- 不要直接导入子模块，优先使用 `from scheduler import Scheduler, ...`
- 不要修改魔数常量定义，会破坏现有策略兼容性
- 不要在调度器中添加业务逻辑，保持策略与核心抽卡逻辑分离
