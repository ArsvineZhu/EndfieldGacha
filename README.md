# 终末地卡池 | Endfield Gacha

**更新日期**：2026-05-28

**项目版本**：`2.5.0`

[中文](README.md) | [English](README_en.md)

---

《明日方舟：终末地》寻访与申领模拟工具。当前仓库实现了角色池、武器池、Web 服务、策略评估、评分系统和统计工具，所有说明以实际代码为准。

## 当前能力

- 角色卡池模拟：`CharGacha`
- 武器卡池模拟：`WeaponGacha`
- 配置加载：`GlobalConfigLoader`
- 单次结果对象：`GachaResult`
- 计数器状态：`Counters`
- Web 服务与用户数据：`web/`
- 结构化策略评估：`scheduler/`
- 概率统计与演示：`cli/`

## 仓库结构

```text
EndfieldGacha/
├── run.py              # 统一 CLI 入口
├── pyproject.toml      # 项目元数据与依赖
├── gacha_core/         # 抽卡引擎
├── scheduler/          # 策略规划与评分
├── web/                # Web 服务（Flask）
├── cli/                # CLI 工具
├── build/              # 构建工具
├── configs/            # JSON 配置文件
├── deploy/             # 部署模板
├── doc/                # 文档
├── scripts/            # 启动脚本
├── test/               # 测试
├── data/               # 运行时数据（gitignored）
└── legacy/             # 归档
```

## 运行入口

```bash
uv sync

uv run run.py          # 显示帮助
uv run run.py demo     # 抽卡演示与统计
uv run run.py eval     # 策略评估
uv run run.py exam     # 概率分布验证
uv run run.py server   # 启动 Web 服务 (http://localhost:5000)

uv run run.py server --dev                                    # 开发模式
uv run run.py server --waitress --port 5000                   # Waitress 生产模式
```

`run.py` 是统一入口。默认 Web 端口为 `5000`。生产模式需设置 `ENDFIELD_SECRET_KEY` 环境变量。

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
- 加急招募通过循环调用 `attempt()` 10 次实现（Web 端 `/api/urgent_recruitment` 接口）

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
- 当前版本号：`SCORING_VERSION = 2.4.0`
- 四个评分维度为目标、收益、资源、风险
- `BaselineEstimator` 使用文件缓存，并可对近邻状态做三次样条插值
- 当前评分仅面向角色池，不纳入武器池

### Web 服务

- 应用工厂：`web/app.py`
- 路由：`web/routes/`（gacha、info、resources、eval）
- 后台评估任务：`web/eval_jobs.py`（线程池 + job_id 轮询）
- 用户存储：SQLite 数据库 `data/userdata.db`
- 用户身份：由 IP + User-Agent 生成 MD5 标识
- 资源操作：充值、兑换、抽卡、加急招募
- 评估端点：`/api/eval/jobs`（异步）、`/api/eval/compare`（同步）
- 生产模式自动提供 `.br`/`.gz` 预压缩静态资源

### CLI 工具

- `cli/demo.py`：`GachaTestTool` 封装角色/武器演示与统计（底层调用 `_demo_char.py`、`_demo_weapon.py`）
- `cli/evaluation.py`：基于 `evaluation_examples.json` 的多场景策略评估
- `cli/examination.py`：概率分布验证（可禁用保底）

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

`configs/arrangement` 第一行决定默认配置目录。`configs/arrange1` 用于调度器默认顺序。目前存在 `config_1` 到 `config_7` 共七个配置目录。角色池和武器池都只接受显式 banner 配置；旧 `char_pool.json` / `weapon_pool.json` 只保留在 `legacy/configs/` 归档目录。`gacha_rules.json` 只保留当期奖励覆盖，通用规则与 banner 默认值都来自 `constants.json`。

## 文档导航

- [中文机制说明](doc/mechanics.md)
- [English mechanics](doc/mechanics_en.md)
- [策略协议](doc/strategy_protocol.md)
- [开发者参考](doc/developer-reference.md)
- [评估页面设计](doc/cross-pool-evaluation-result-page-design.md)
- [角色池配置迁移记录](doc/implementation_records/2026-05-26-char-config.md)
- [运行时包拆分记录](doc/implementation_records/2026-05-26-runtime-package-split.md)
- [评分系统记录](doc/implementation_records/2026-05-26-scoring-followup.md)
- [旧评分设计归档](legacy/doc/策略评分系统设计方案.md)

## 开发命令

```bash
uv run pytest test/ -v
uv run ruff check .
uv run pyright
npm install
uv run python build/compress.py
```

静态资源压缩说明：
- `build/compress.py` 使用本地锁定依赖：`terser` + `javascript-obfuscator`（JS）与 `lightningcss`（CSS）。
- 构建会为文本资源生成 `.gz` 与 `.br` 预压缩文件（Nginx 配合 `gzip_static on; brotli_static on;`）。
- 构建产物输出到 `dist/static`，源码静态文件保留在 `web/static`（生产模式默认从 `dist/static` 提供静态资源）。
- 生产模式下（含 Waitress）会根据 `Accept-Encoding` 优先返回 `.br` / `.gz`，并附加 `Vary: Accept-Encoding`。
- 相关 Nginx 模板见 `deploy/nginx/static-compression.conf`。
- 默认开启混淆（`ENABLE_ASSET_OBFUSCATION=1`）：JS 会进行二次混淆，source map 会去除 `sourcesContent`；可用 `ENABLE_ASSET_OBFUSCATION=0` 关闭。

## 需要注意的实现事实

- 当前代码没有独立的"重复角色 / 重复武器兑换"系统实现，重复结果只会更新收藏与资源计数
- `configs/config_1` 中的当前示例卡池名为 `「熔火灼痕」` 和 `「熔铸申领」`
- `gacha_rules.json` 仅保存当期差异；默认规则来自 `configs/constants.json`
- 旧版 `legacy_magic` 策略不再被协议层接受
- 生产模式必须设置 `ENDFIELD_SECRET_KEY` 环境变量
- Web 后台评估通过 `EvaluationJobManager`（线程池）执行，同一时间最多 2 个并发评估任务
