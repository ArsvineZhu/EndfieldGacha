# 运行时包拆分记录

- 日期：2026-05-26
- 适用范围：运行时入口、核心抽卡实现、配置加载、文档

## 本次变更

1. 删除顶层 `core.py` 兼容入口，不再保留任何旧导入路径兼容。
2. 核心实现正式收敛到 `gacha_core/` 包：
   - `gacha_core/config.py`
   - `gacha_core/char.py`
   - `gacha_core/weapon.py`
   - `gacha_core/models.py`
   - `gacha_core/randomizer.py`
   - `gacha_core/pool_utils.py`
3. 仓库版本统一为 `2.0.0`。
4. 所有运行时代码与测试改为直接从 `gacha_core` 导入。

## 明确决定

- 不再提供 `core.py` 兼容层。
- 不再接受旧角色池 / 武器池配置作为运行时输入。
- 历史策略实现、旧池子配置和旧设计文档全部进入 `legacy/` 目录归档。

## 影响

- `server/routes.py`
- `scheduler/*.py`
- `tools/*.py`
- `test/*.py`
- `README.md`
- `README_en.md`
- `AGENTS.md`
- `ref.md`
