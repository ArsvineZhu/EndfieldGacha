# Configs Module Knowledge Base

**Generated:** 2026-03-07
**Module:** 多卡池配置系统

## OVERVIEW
多套卡池配置集合，包含角色池、武器池、抽卡规则和全局常量，支持不同版本卡池切换。

## STRUCTURE
```
configs/
├── arrangement          # 默认配置顺序: config_1 → config_2 → ... → config_7
├── arrange1             # 调度器专用配置顺序: config_3 → config_4 → ... → config_7
├── config_1/            # 配置集1
│   ├── char_pool.json   # 角色卡池数据
│   ├── weapon_pool.json # 武器卡池数据
│   ├── gacha_rules.json # 抽卡规则配置
│   └── constants.json   # 全局常量配置
├── config_2/ ... config_7/  # 其他配置集（共7套）
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| 修改角色卡池 | `config_*/char_pool.json` | 支持UP概率、移除规则配置 |
| 修改武器卡池 | `config_*/weapon_pool.json` | 支持武器类型、UP概率配置 |
| 调整抽卡规则 | `config_*/gacha_rules.json` | 概率、保底、配额规则 |
| 切换配置顺序 | `arrangement` / `arrange1` | 每行一个配置目录名 |
| 加载配置 | `core.GlobalConfigLoader` | 自动按顺序加载配置 |

## CONVENTIONS
- 配置集编号从1到7，对应游戏不同版本卡池
- 所有概率值总和应为1，UP概率在同星级内分配
- 保底规则优先顺序：UP保底 > 6星保底 > 5星保底
- 配额规则保持统一，避免不同配置集差异过大

## ANTI-PATTERNS
- 不要修改配置文件格式，保持JSON结构一致
- 不要删除配置集，如需禁用可从arrangement文件中移除
- 避免在配置中添加非标准字段，核心逻辑依赖现有字段
