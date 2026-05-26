# 终末地卡池 | Endfield Gacha

**更新日期**：2026-05-26

**项目版本**：`2.0.0`

[中文](README.md) | [English](README_en.md)

---

《明日方舟：终末地》寻访与申领模拟工具。当前仓库实现了角色池、武器池、Web 服务、策略评估、评分系统和统计工具，所有说明以实际代码为准。

## 当前能力

- 角色卡池模拟：`CharGacha`
- 武器卡池模拟：`WeaponGacha`
- 配置加载：`GlobalConfigLoader`
- 单次结果对象：`GachaResult`
- 计数器状态：`Counters`
- Web 服务与用户数据：`server/`
- 结构化策略评估：`scheduler/`
- 概率统计与演示：`tools/`

## 仓库结构

```text
EndfieldGacha/
├── run.py
├── gacha_core/
├── server.py
├── server/
├── scheduler/
├── tools/
├── app/
├── configs/
├── doc/
├── legacy/
├── test/
├── pic/
└── ref.md
```

## 运行入口

```bash
uv sync

uv run run.py          # 显示帮助
uv run run.py demo     # 抽卡演示与统计
uv run run.py eval     # 策略评估
uv run run.py exam     # 概率分布验证
uv run run.py server   # 启动 Web 服务

uv run server.py --dev
uv run server.py --waitress --port 5000
```

`run.py` 是统一入口；`server.py` 是 Web 服务命令行包装器。默认 Web 端口为 `5000`。
Web 端当前默认读取 `configs/config_7`，也就是复刻池配置。

## 核心实现

### `gacha_core/`

- `gacha_core/randomizer.py`：`BatchRandom`
- `gacha_core/config.py`：`GlobalConfigLoader`
- `gacha_core/char.py`：`CharGacha`
- `gacha_core/weapon.py`：`WeaponGacha`
- `gacha_core/models.py`：`GachaResult`、`Counters`

### 角色池

- 单次抽卡消耗 1 张特许寻访凭证，或 500 个嵌晶玉
- 基础概率为 6★ 0.8%、5★ 8%、4★ 91.2%
- 5★ 保底为 10 抽
- 6★ 软保底从第 66 抽开始，每抽增加 5%，第 80 抽保底
- 当期 UP 6★ 硬保底为 120 抽
- 角色池结果会发放武库配额：6★ 2000、5★ 200、4★ 20
- 累计奖励当前实现为 30 抽加急招募、60 抽寻访情报书、240 抽周期性 UP 信物

### 武器池

- 每次申领固定为 10 抽，消耗 1980 个武库配额
- 基础概率为 6★ 4%、5★ 15%、4★ 81%
- `per_apply_must_have=true` 时，每次申领至少出现 1 个 5★+ 结果
- 6★ 保底为 4 次申领
- 当期 UP 6★ 保底为 8 次申领
- 保底优先级为 UP > 6★ > 5★
- 武器池结果会发放集成配额：6★ 50、5★ 10、4★ 1
- 累计奖励当前实现为从第 10 次申领开始，按 8 次周期交替发放两类奖励

### 结构化策略

- `scheduler/strategy_rules.py` 只支持结构化规则树
- `scheduler/strategy_protocol.py` 使用 `strategy-protocol-v1`
- 旧版魔数策略保留为存档文件，不再作为协议输入
- `Scheduler.banner(...)` 和 `Scheduler.evaluate_multiple_strategies(...)` 会自动做协议适配

### 评分系统

- 评分主实现位于 `scheduler/scoring.py`
- 当前版本号：`SCORING_VERSION = 2.3.0`
- 四个评分维度为目标、收益、资源、风险
- `BaselineEstimator` 使用文件缓存，并可对近邻状态做三次样条插值
- 当前评分仅面向角色池，不纳入武器池

### Web 服务

- 应用工厂：`server/app.py`
- 路由：`server/routes.py`
- 用户存储：SQLite 数据库 `userdata.db`
- 用户身份：由 IP + User-Agent 生成 MD5 标识
- 资源操作：充值、兑换、抽卡、加急招募

### 工具脚本

- `tools/demo.py`：`demo_char_draw()`、`demo_weapon_apply()`、`stats_char_quota()`、`stats_weapon_quota()`、`stats_char_up_prob()`、`stats_char_potential()`
- `tools/evaluation.py`：基于 `evaluation_examples.json` 的策略评估
- `tools/examination.py`：概率分布验证

## 配置文件

当前代码实际读取的配置文件只有：

- `configs/constants.json`
- `configs/char_pool_base.json`
- `configs/config_*/char_banner.json`
- `configs/weapon_pool_base.json`
- `configs/config_*/weapon_banners.json`
- `configs/config_*/gacha_rules.json`
- `configs/arrangement`
- `configs/arrange1`

角色池和武器池都只接受显式 banner 配置；旧 `char_pool.json` / `weapon_pool.json` 只保留在 `legacy/configs/` 归档目录。`configs/config_1` 是默认加载目录；`arrangement` 的第一行也可决定默认配置。`gacha_rules.json` 只保留当期奖励覆盖，通用规则与 banner 默认值都来自 `constants.json`。`char_banner.json` 的 `featured.normal` 一旦显式给出，就会覆盖共享 6 星普通池；`weapon_banners.json` 则允许同一配置目录声明多个武器池，运行时默认读取 `default_banner_id` 指向的条目。

## 文档导航

- [中文机制说明](doc/mechanics.md)
- [English mechanics](doc/mechanics_en.md)
- [策略协议](doc/strategy_protocol.md)
- [角色池配置迁移记录](doc/implementation_records/2026-05-26-char-config.md)
- [运行时包拆分记录](doc/implementation_records/2026-05-26-runtime-package-split.md)
- [评分系统记录](doc/implementation_records/2026-05-26-scoring-followup.md)
- [旧评分设计归档](legacy/doc/策略评分系统设计方案.md)
- [开发参考](ref.md)

## 开发命令

```bash
uv run pytest test/ -v
uv run ruff check .
uv run pyright
uv run python app/utils/compress.py
```

## 需要注意的实现事实

- 当前代码没有独立的“重复角色 / 重复武器兑换”系统实现，重复结果只会更新收藏与资源计数
- `configs/config_1` 中的当前示例卡池名为 `「熔火灼痕」` 和 `「熔铸申领」`
- `gacha_rules.json` 仅保存当期差异；默认规则来自 `configs/constants.json`
- 旧版 `legacy_magic` 策略不再被协议层接受
