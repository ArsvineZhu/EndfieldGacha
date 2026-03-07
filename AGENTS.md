# Endfield Gacha AI助手专用文档

## 项目概述

Endfield Gacha 是一个《明日方舟：终末地》寻访与申领系统的模拟工具，提供完整的抽卡逻辑、统计分析、策略评估和Web界面。本项目采用模块化设计，支持多配置集、用户数据持久化和科学评分体系。

**核心功能**：

- 角色/武器卡池抽卡模拟（支持三级保底机制）
- Web界面交互与用户管理系统
- 策略调度与批量评估（魔数编码策略）
- 丰富的统计分析工具（概率分布、可视化）

## 模块索引

### 根目录导航（按用途分组）

- **统一入口（推荐）**
  - `run.py`：`python run.py [demo|eval|exam|server]` 一键运行

- **核心文件**
  - `core.py`：抽卡核心逻辑（角色池 / 武器池）
  - `server.py`：Web 服务入口（Flask）
  - `start.ps1`：Windows 一键启动 Web 服务

- **策略包** `scheduler/`
  - `engine.py`：调度器主逻辑
  - `strategy.py`：魔数编码策略与预定义常量
  - `scoring.py`：资源与评分系统
  - `workers.py`：多进程 worker

- **工具包** `tools/`
  - `demo.py`：抽卡演示与统计
  - `evaluation.py`：策略评估脚本
  - `examination.py`：概率分布验证

- **配置 / 数据 / 文档**
  - `configs/`：卡池与规则配置
  - `users/`：用户数据（运行时自动创建）
  - `doc/`：机制说明文档
  - `pic/`：图片资源
  - `test/`：测试代码

### 核心模块 (`core.py`)

- **`BatchRandom`**：批量随机数生成器（支持种子复现）
- **`GachaResult`**：抽卡结果数据类（名称、星级、配额、保底标记）
- **`GlobalConfigLoader`**：全局配置加载器（单例模式）
- **`CharGacha`**：角色卡池类（6星概率递增、UP保底120抽、6星保底85抽、5星保底10抽）
- **`WeaponGacha`**：武器卡池类（申领式抽卡、最后1抽替换机制）

### 服务模块 (`server.py`)

- Flask Web服务器，提供完整用户管理、资源管理、抽卡历史记录
- **关键函数**：`get_or_create_current_user()`（基于IP和User-Agent生成用户ID）
- **数据存储**：`users/`目录下每个用户独立JSON文件

### 策略模块 (`scheduler/` 包)

- **`strategy.py`**：包含 `GachaStrategy` 以及所有预定义魔数常量  
  - `GachaStrategy`：魔数编码策略系统（32位整数编码条件）  
  - 预定义魔数：`URGENT`（加急招募）、`DOSSIER`（情报书）、`SOFT_PITY`（软保底）、`UP_OPRT`（UP角色）、`HARD_PITY`（硬保底）、`POTENTIAL`（潜能）、`OPRT`（6星角色）  
  - 比较运算符常量：`GT`、`LT`、`GE`、`LE`
- **`scoring.py`**：资源与科学评分系统  
  - `Resource`：抽卡资源归一化描述（合约证、黄票、武库配额、源石）  
  - `ScoringSystem`：三维评分系统（运气0-60、效率0-20、目标0-20）
- **`workers.py`**：调度用 worker 与辅助方法  
  - 单次抽卡处理：`process_gacha_result()`、`handle_urgent_gacha()`、`initialize_banner_state()` 等  
  - 多进程 worker 封装：`_worker_wrapper()`（供 `Scheduler.evaluate()` 使用）
- **`engine.py`**：调度器主逻辑  
  - `Scheduler`：策略调度器（支持多卡池连续模拟、批量并行评估，内部使用上述子模块）  
  - 对外仍 re-export 关键符号：可以继续从 `scheduler` 导入 `Scheduler`、`GachaStrategy`、`Resource` 及各魔数常量

### 工具模块 (`tools/` 包)

- **`demo.py`**：抽卡演示与统计工具（`stats_char_up_prob()`、`stats_char_quota()`等）
- **`evaluation.py`**：策略评估脚本（预置多种抽卡策略）
- **`examination.py`**：概率分布验证工具

### 前端模块 (`app/`)

- **`templates/`**：HTML模板文件
- **`static/`**：压缩后的CSS、JS、图片资源（使用`app/utils/compress.py`压缩）
- **`utils/compress.py`**：静态资源压缩和混淆工具

### 数据模块

- **`configs/`**：多套卡池配置（config_1 到 config_7），包含：
  - `char_pool.json`：角色卡池数据
  - `weapon_pool.json`：武器卡池数据
  - `gacha_rules.json`：抽卡规则配置
  - `constants.json`：全局常量配置
- **`users/`**：用户数据存储（JSON格式）
- **`pic/`**：图片资源文件
- **`doc/`**：游戏机制说明文档

## 快速参考

### 关键类与方法

| 模块 | 类/函数 | 关键方法 | 说明 |
|------|---------|----------|------|
| `core.py` | `CharGacha` | `attempt(disable_guarantee=False)` | 角色卡池单次抽卡 |
| `core.py` | `WeaponGacha` | `attempt(disable_guarantee=False)` | 武器卡池单次申领 |
| `core.py` | 全局 | `get_accumulated_reward()` | 获取累计奖励列表 |
| `scheduler.py` | `GachaStrategy` | `terminate(counters, resource)` | 检查策略终止条件 |
| `scheduler.py` | `ScoringSystem` | `calculate_score(results)` | 计算综合评分 |
| `scheduler.py` | `Scheduler` | `evaluate(scale=5000, workers=4)` | 执行批量评估 |
| `server.py` | 全局 | `get_or_create_current_user()` | 获取或创建用户数据 |
| `demo.py` | `GachaTestTool` | `stats_char_up_prob(test_times=50000)` | 统计UP角色所需抽数 |

### 配置路径

| 配置类型 | 默认路径 | 说明 |
|----------|----------|------|
| 默认配置 | `configs/config_1/` | 主配置目录 |
| 配置顺序 | `configs/arrangement` | 默认配置顺序（config_1 到 config_7） |
| 调度配置 | `configs/arrange1` | 调度器专用配置顺序（config_3 到 config_7） |
| 用户数据 | `users/{user_id}.json` | 用户数据文件（MD5哈希命名） |

### 资源类型

| 资源名称 | 变量名 | 说明 |
|----------|--------|------|
| 特许寻访凭证 | `chartered_permits` | 角色池单抽消耗1 |
| 嵌晶玉 | `oroberyl` | 角色池单抽消耗75 |
| 武库配额 | `arsenal_tickets` | 武器池申领消耗1980 |
| 衍质源石 | `origeometry` | 可兑换为嵌晶玉(1:75)或武库配额(1:25) |
| 加急招募 | `urgent_recruitment` | 10连抽次数 |

## 开发工作流

### 常用命令

```bash
# 安装项目依赖
pip install -r requirements.txt

# 统一入口（推荐）
python run.py demo         # 抽卡演示
python run.py eval         # 策略评估（调用evaluation.py）
python run.py exam         # 概率验证（调用examination.py）
python run.py server       # 启动 Web 服务

# 或直接运行
python server.py           # Windows 快捷启动: .\start.ps1
python -m tools.demo
python -m tools.evaluation  # 直接运行评估脚本
python -m tools.examination # 直接运行验证脚本

# 运行测试套件
python -m pytest test/ -v

# 压缩前端静态资源（修改前端后执行）
python app/utils/compress.py
```

### 代码风格规范

#### 命名约定

- 类名：大驼峰命名法（PascalCase），如 `CharGacha`、`GlobalConfigLoader`
- 函数/方法名：小写下划线命名法（snake_case），如 `attempt()`、`_randomize()`
- 变量名：小写下划线命名法，如 `up_prob`、`chartered_permits`
- 常量/全局变量：全大写下划线命名法，如 `DEFAULT_CONFIG`、`__version__`

#### 导入规范

- 导入顺序：标准库 → 第三方库 → 本地模块，组间用空行分隔
- 避免通配符导入（`from module import *`），仅在模块 `__all__` 明确导出时使用
- 优先使用绝对路径导入，避免相对路径歧义

#### 类型与注释

- 所有公共方法、函数必须添加完整类型注解（参数类型 + 返回值类型）
- 模块、类、公共方法必须包含详细docstring，说明功能、参数、返回值、异常
- 复杂逻辑添加行内注释，避免无意义重复代码的注释
- 优先使用精确类型，避免不必要的 `Any` 类型

#### 格式规范

- 4空格缩进，不使用制表符
- 文件编码统一为UTF-8，首行添加 `# -*- coding: utf-8 -*-`
- 单行长度不超过120字符
- 逻辑块之间使用空行分隔，保持代码可读性

#### 错误处理

- 抛出明确的异常类型（`FileNotFoundError`、`ValueError`等），附带详细错误信息
- 避免空 `except` 块，捕获具体异常类型
- 概率计算使用 `Decimal` 类型避免浮点误差

### AI助手工作规则

- 优先参考本AGENTS.md文档获取项目结构和API信息
- 不得新增卡池类型，当前仅支持角色/武器两种卡池
- 修改代码后需运行对应测试验证功能正确性
- 文档修改需同步更新相关引用（README、ref.md等）
- 所有代码修改必须符合现有代码风格规范
- 无Cursor/Copilot自定义规则，遵循本规范即可

## 调用模式

### 基础抽卡调用

```python
# 角色卡池单抽
from core import CharGacha, GlobalConfigLoader
config = GlobalConfigLoader("configs/config_1")
gacha = CharGacha(config, size=1024)
result = gacha.attempt()  # 返回 GachaResult 对象

# 武器卡池申领
from core import WeaponGacha
weapon_gacha = WeaponGacha(config, size=1024)
results = weapon_gacha.attempt()  # 返回 GachaResult 列表（通常10个）
```

### Web服务调用

```python
# 启动Web服务
python server.py
# 访问 http://localhost:5000

# API接口示例
POST /api/gacha
{
    "pool_type": "char",  # "char" 或 "weapon"
    "count": 1           # 抽卡次数（角色池单次，武器池固定为申领次数）
}
```

### 策略评估调用

```python
from scheduler import Scheduler, DOSSIER, OPRT, UP_OPRT

# 创建调度器
scheduler = Scheduler(config_dir="configs", arrange="arrange1")

# 定义策略序列
scheduler.schedule([DOSSIER, OPRT])           # 策略1：获取情报书和6星角色
scheduler.schedule([UP_OPRT], use_origeometry=True)  # 策略2：获取UP角色，使用源石

# 执行批量评估（5000次模拟，4进程）
scheduler.evaluate(scale=5000, workers=4)
```

### 统计分析调用

```python
from demo import GachaTestTool

tool = GachaTestTool()
# 统计UP角色所需抽数（50000次测试）
tool.stats_char_up_prob(test_times=50000, gragh=True)

# 统计120抽角色池配额分布
tool.stats_char_quota(draw_times=50000, gragh=True)
```

## 配置文件指南

### 配置目录结构

```
configs/
├── arrangement           # 默认配置顺序：config_1 到 config_7
├── arrange1             # 调度器专用配置顺序：config_3 到 config_7
├── config_1/            # 配置集1
│   ├── char_pool.json   # 角色卡池数据
│   ├── weapon_pool.json # 武器卡池数据
│   ├── gacha_rules.json # 抽卡规则配置
│   └── constants.json   # 全局常量配置
└── config_2/ ... config_7/  # 其他配置集
```

### 关键配置项

**`gacha_rules.json` - 抽卡规则**：

```json
{
  "char": {
    "base_prob": {"6": 0.008, "5": 0.08, "4": 0.912},
    "guarantee_5star_plus_draw": 10,      # 5星保底抽数
    "guarantee_6star_draw": 85,           # 6星保底抽数（原AGENTS.md写80，实际为85）
    "6star_prob_increase_start": 65,      # 概率递增起始抽数
    "prob_increase": 0.05,                # 每次递增概率
    "up_guarantee_draw": 120,             # UP保底抽数
    "quota_rule": {"6": 2000, "5": 200, "4": 20}  # 配额发放规则
  }
}
```

**`char_pool.json` - 角色卡池**：

```json
{
  "6": [
    {"name": "洁尔佩塔", "remove_after": 4, "up_prob": 0.0},
    {"name": "莱万汀", "remove_after": 3, "up_prob": 0.5},  # UP角色
    {"name": "伊冯", "remove_after": 5, "up_prob": 0.0}
  ]
}
```

## 故障排除

| 问题现象 | 可能原因 | 解决方案 |
|----------|----------|----------|
| 配置文件不存在 | 路径错误或文件缺失 | 检查`configs/config_1/`目录是否存在，确认`arrangement`文件 |
| 导入模块失败 | 依赖未安装或Python版本不匹配 | 运行`pip install -r requirements.txt`，确保Python 3.10+ |
| Web服务无法启动 | 端口占用或Flask依赖缺失 | 检查端口5000是否被占用，安装`Flask, Flask-Cors, waitress` |
| 用户数据无法保存 | `users/`目录权限不足 | 确保`users/`目录可写，或手动创建该目录 |
| 抽卡结果异常 | 配置概率设置有误 | 检查`gacha_rules.json`中的概率总和应为1，UP概率配置正确 |

## 扩展点

### 系统扩展说明

**注意**：本系统已经稳定，**不再添加新的卡池类型**。当前仅支持角色卡池和武器卡池两种类型，符合《明日方舟：终末地》游戏机制。

### 自定义策略

```python
# 使用魔数编码定义新策略
CUSTOM_STRATEGY = (-1 << 31) | (0b0000001 << 24) | (GT << 16) | 100
# 含义：当资源大于100时触发，停止条件为加急招募

# 在evaluation.py中添加策略函数
def custom_strategy():
    scheduler = Scheduler(config_dir="configs", arrange="arrange1")
    scheduler.schedule([CUSTOM_STRATEGY])
    scheduler.evaluate(scale=10000, workers=8)
```

### 界面定制

1. 修改`app/templates/index.html`前端模板
2. 更新`app/static/`中的CSS和JS文件
3. 运行`python app/utils/compress.py`压缩静态资源

### 数据分析扩展

1. 在`demo.py`中添加新的统计方法
2. 集成更多可视化库（如`plotly`、`seaborn`）
3. 添加数据导出功能（CSV、Excel格式）

## 注意事项

1. **随机种子**：`BatchRandom`支持种子复现，便于测试和调试
2. **配置缓存**：`GlobalConfigLoader`使用缓存机制，避免重复读取文件
3. **资源兑换**：衍质源石可兑换为嵌晶玉(1:75)或武库配额(1:25)
4. **保底优先级**：武器池保底优先级：UP保底 > 6星保底 > 5星保底
5. **评分等级**：S级(90-100)、A级(80-89)、B级(70-79)、C级(60-69)、D级(50-59)、E级(0-49)

## 相关文档引用

### 项目文档

| 文档文件 | 路径 | 说明 |
|----------|------|------|
| **README.md** | `README.md` | 项目主说明文档，包含项目介绍、技术架构、快速入门指南、统计结论、开发者指南 |
| **README_en.md** | `README_en.md` | 英文版README文档 |
| **ref.md** | `ref.md` | 开发者参考文档，包含详细的技术实现说明和算法分析 |

### 机制说明文档

| 文档文件 | 路径 | 说明 |
|----------|------|------|
| **游戏机制说明（中文）** | `doc/mechanics.md` | 《明日方舟：终末地》寻访与申领机制原理解释 |
| **游戏机制说明（英文）** | `doc/mechanics_en.md` | 英文版游戏机制说明文档 |

### 配置文件文档

| 配置文件 | 路径 | 说明 |
|----------|------|------|
| **角色卡池配置** | `configs/config_1/char_pool.json` | 角色卡池数据配置（角色列表、UP概率、移除规则） |
| **武器卡池配置** | `configs/config_1/weapon_pool.json` | 武器卡池数据配置（武器列表、类型、UP概率） |
| **抽卡规则配置** | `configs/config_1/gacha_rules.json` | 抽卡规则配置（概率、保底规则、奖励机制） |
| **全局常量配置** | `configs/config_1/constants.json` | 全局常量配置（文本常量、默认值、目录名称） |

### 代码文档

| 模块文件 | 路径 | 说明 |
|----------|------|------|
| **核心抽卡模块** | `core.py` | 核心抽卡逻辑实现，包含角色/武器卡池类 |
| **Web服务模块** | `server.py` | Flask Web服务器，提供用户管理和抽卡API |
| **策略调度模块** | `scheduler/` | 魔数编码策略系统和科学评分系统 |
| **演示工具模块** | `tools/demo.py` | 抽卡演示与统计分析工具 |
| **策略评估脚本** | `tools/evaluation.py` | 预置抽卡策略评估脚本 |
| **概率验证工具** | `tools/examination.py` | 概率分布验证工具 |

### 使用建议

1. **AI助手查阅**：优先参考本AGENTS.md文档，获取结构化项目信息
2. **开发者参考**：查看README.md的"开发者指南"章节和ref.md文档
3. **配置定制**：参考配置文件文档了解各配置项含义
4. **算法理解**：阅读游戏机制说明文档了解抽卡规则背景

---
*文档版本：2.2.0 | 最后更新：2026-03-06*
