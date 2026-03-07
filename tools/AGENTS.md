# Tools Module Knowledge Base

**Generated:** 2026-03-07
**Module:** 工具包 - 抽卡演示、统计分析、策略评估

## OVERVIEW
可直接运行的工具集合，提供抽卡演示、概率分布验证、策略对比评估等功能。

## STRUCTURE
```
tools/
├── __init__.py      # 模块初始化
├── demo.py          # 抽卡演示与统计分析工具
├── evaluation.py    # 策略评估脚本（预置多种抽卡策略）
└── examination.py   # 概率分布验证工具
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| 统计UP角色抽数分布 | `demo.py` | stats_char_up_prob() |
| 统计配额分布 | `demo.py` | stats_char_quota() / stats_weapon_quota() |
| 对比不同抽卡策略 | `evaluation.py` | 预置策略函数，可添加自定义策略 |
| 验证概率正确性 | `examination.py` | 验证卡池概率是否符合配置 |
| 运行工具 | 命令行: `python -m tools.demo` 或 `python run.py demo` |

## CONVENTIONS
- 所有工具函数默认生成matplotlib图表，设置`graph=False`可禁用
- 统计分析默认使用10万次模拟规模，可通过test_times参数调整
- 策略评估默认使用5000次模拟，可通过scale参数调整
- 输出默认使用rich美化格式，终端支持ANSI颜色

## ANTI-PATTERNS
- 不要在工具中修改核心抽卡逻辑，仅做统计和演示
- 不要硬编码配置路径，使用GlobalConfigLoader加载
- 避免在工具中添加业务逻辑，保持工具的通用性
