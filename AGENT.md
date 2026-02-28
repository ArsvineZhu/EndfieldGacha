# Endfield Gacha 项目技术索引

## 0. 目录索引

### 0.1 主要章节
- [1. 项目架构概述](#1-项目架构概述)
- [2. 核心功能模块说明](#2-核心功能模块说明)
- [3. API接口规范](#3-api接口规范)
- [4. 数据模型定义](#4-数据模型定义)
- [5. 业务逻辑流程](#5-业务逻辑流程)
- [6. 开发环境配置指南](#6-开发环境配置指南)
- [7. 常用工具与依赖说明](#7-常用工具与依赖说明)
- [8. Agent开发相关资源路径](#8-agent开发相关资源路径)
- [9. 调用方式](#9-调用方式)
- [10. 代码规范与最佳实践](#10-代码规范与最佳实践)
- [11. 扩展与定制](#11-扩展与定制)
- [12. 故障排除](#12-故障排除)
- [13. 版本历史](#13-版本历史)
- [14. 开发者信息](#14-开发者信息)
- [15. 关键词索引](#15-关键词索引)
- [16. 索引更新机制](#16-索引更新机制)

### 0.2 快速导航
- [核心模块调用示例](#91-核心模块调用)
- [客户端调用示例](#92-客户端调用)
- [演示工具调用示例](#93-演示工具调用)
- [配置文件路径](#82-配置文件路径)
- [常见问题解决方案](#121-常见问题)

## 1. 项目架构概述

### 1.1 整体架构
- **核心层**：`core.py` - 实现抽卡核心逻辑，包含角色和武器卡池的抽卡机制
- **客户端层**：`client.py` - 提供控制台交互界面，处理用户输入和资源管理
- **演示层**：`demo.py` - 提供抽卡模拟和统计分析功能
- **配置层**：`config/` 目录 - 存储卡池数据、抽卡规则和全局常量
- **资源层**：`pic/` 目录 - 存储图片资源
- **文档层**：`doc/` 目录 - 存储游戏机制说明文档

### 1.2 模块依赖关系
```
client.py → core.py ← demo.py
  ↓           ↓
config/     config/
```

## 2. 核心功能模块说明

### 2.1 核心抽卡模块 (`core.py`)
- **BatchRandom**：批量随机数生成器，支持预生成和种子复现
- **GachaResult**：抽卡结果数据类，包含名称、星级、配额和保底标记
- **GlobalConfigLoader**：全局配置加载器，单例模式，管理所有配置文件
- **CharGacha**：角色卡池类，实现角色抽卡逻辑和保底机制
- **WeaponGacha**：武器卡池类，实现武器抽卡逻辑和保底机制

### 2.2 客户端模块 (`client.py`)
- **GachaClient**：控制台客户端类，处理用户交互、资源管理和抽卡操作
- 支持角色池单抽、10连抽、武器池10连抽和加急招募
- 实现资源转换和抽卡历史记录管理

### 2.3 演示工具模块 (`demo.py`)
- **GachaTestTool**：抽卡测试工具类，提供各种抽卡模拟和统计功能
- 支持配额统计、UP概率统计、满潜所需抽数统计等
- 提供数据可视化功能（需要matplotlib）

## 3. API接口规范

### 3.1 核心模块接口

#### BatchRandom 类
- `__init__(seed=-1, size=1024)`：初始化随机数生成器
- `pop()`：获取一个随机数
- `batch(size=1024)`：静态方法，生成指定数量的随机数

#### GachaResult 数据类
- 属性：`name`, `star`, `quota`, `is_up_g`, `is_6_g`, `is_5_g`

#### GlobalConfigLoader 类
- `get_pool_data(pool_type)`：获取卡池数据
- `get_rule_config(pool_type)`：获取抽卡规则配置
- `get_text(key)`：获取文本常量
- `get_default(key)`：获取默认值

#### CharGacha 类
- `__init__(seed=-1, size=1024)`：初始化角色卡池
- `draw_once(disable_guarantee=False)`：单次抽卡
- `get_accumulated_reward()`：获取累计奖励

#### WeaponGacha 类
- `__init__(seed=-1, size=1024)`：初始化武器卡池
- `apply_once(disable_guarantee=False)`：单次申领（通常为10连抽）
- `get_accumulated_reward()`：获取累计奖励

### 3.2 客户端模块接口

#### GachaClient 类
- `__init__(chartered_permits=0, oroberyl=0, arsenal_tickets=0, origeometry=0, urgent_recruitment=0)`：初始化客户端
- `add_resources()`：添加资源
- `convert_origeometry()`：转换衍质源石
- `draw_char_once()`：角色池单抽
- `draw_char_ten()`：角色池10连抽
- `draw_urgent_recruitment()`：加急招募10连抽
- `draw_weapon_ten()`：武器池10连抽
- `view_history()`：查看抽卡历史
- `save_history(filename)`：保存抽卡历史
- `run()`：运行控制台应用

### 3.3 演示工具接口

#### GachaTestTool 类
- `demo_char_draw(draw_times=5)`：角色卡池抽卡示例
- `demo_weapon_apply(apply_times=1)`：武器卡池申领示例
- `stats_char_quota(draw_times=50000, gragh=False)`：统计角色池配额
- `stats_weapon_quota(draw_times=50000, gragh=False)`：统计武器池配额
- `stats_char_draw(draw_times=50000, gragh=False)`：统计角色池6星数量
- `stats_weapon_draw(draw_times=50000, gragh=False)`：统计武器池6星数量
- `stats_char_up_prob(test_times=50000, gragh=False, limit=0)`：统计抽中UP角色所需抽数
- `stats_weapon_up_prob(test_times=50000, gragh=False, limit=0)`：统计抽中UP武器所需抽数
- `stats_urgent_quota(draw_times=50000, gragh=False)`：统计加急招募配额
- `stats_char_potential(draw_times=50000, gragh=False)`：统计角色满潜所需抽数

## 4. 数据模型定义

### 4.1 抽卡结果数据模型
```python
@dataclass
class GachaResult:
    name: str          # 干员或武器名称
    star: int          # 星级（4/5/6）
    quota: int         # 配额数量
    is_up_g: bool = False  # UP保底标记
    is_6_g: bool = False   # 6星保底标记
    is_5_g: bool = False   # 5星保底标记
```

### 4.2 配置文件数据模型

#### 角色卡池配置 (`char_pool.json`)
```json
{
  "6": [
    {
      "name": "洁尔佩塔",
      "remove_after": 3,
      "up_prob": 0.50
    },
    ...
  ],
  "5": [...],
  "4": [...]
}
```

#### 武器卡池配置 (`weapon_pool.json`)
```json
{
  "6": [
    {
      "name": "使命必达",
      "type": "施术单元",
      "up_prob": 0.25
    },
    ...
  ],
  "5": [...],
  "4": [...]
}
```

#### 抽卡规则配置 (`gacha_rules.json`)
```json
{
  "char": {
    "base_prob": {"6": 0.008, "5": 0.08, "4": 0.912},
    "guarantee_5star_plus_draw": 10,
    "guarantee_6star_draw": 80,
    "6star_prob_increase_start": 65,
    "prob_increase": 0.05,
    "prob_upper_limit": 1.0,
    "up_guarantee_draw": 120,
    "quota_rule": {"6": 2000, "5": 200, "4": 20},
    "rewards": {...},
    "up_char_name": "洁尔佩塔"
  },
  "weapon": {...}
}
```

### 4.3 客户端数据结构
- **资源数据**：特许寻访凭证、嵌晶玉、武库配额、衍质源石、加急招募
- **抽卡历史**：时间戳、卡池类型、抽卡方式、消耗、结果列表

## 5. 业务逻辑流程

### 5.1 角色卡池抽卡流程
1. 检查资源是否充足
2. 消耗对应资源
3. 计算当前6星概率（含递增）
4. 检查是否触发UP保底（120抽）
5. 检查是否触发6星保底（80抽）
6. 检查是否触发5星保底（10抽）
7. 执行正常抽卡逻辑
8. 重置对应计数器
9. 计算并发放累计奖励
10. 记录抽卡历史

### 5.2 武器卡池抽卡流程
1. 检查资源是否充足
2. 消耗对应资源
3. 执行基础抽卡（按配置次数）
4. 检查是否触发UP保底（8次申领）
5. 检查是否触发6星保底（4次申领）
6. 检查是否触发5星保底（未出5星及以上）
7. 执行最后1抽替换
8. 更新对应计数器
9. 计算并发放累计奖励
10. 记录抽卡历史

### 5.3 资源管理流程
1. 资源添加：手动添加各种资源
2. 资源转换：将衍质源石转换为嵌晶玉或武库配额
3. 资源消耗：抽卡时消耗对应资源
4. 资源获取：通过抽卡获得武库配额

### 5.4 历史记录管理流程
1. 记录抽卡历史：每次抽卡后记录详细信息
2. 查看历史记录：展示所有抽卡历史
3. 保存历史记录：将历史记录保存到JSON文件

## 6. 开发环境配置指南

### 6.1 环境要求
- Python 3.10+
- 操作系统：Windows/Linux/macOS

### 6.2 依赖安装
```bash
pip install -r requirements.txt
```

### 6.3 主要依赖说明
- **numpy**：用于批量随机数生成
- **rich**：用于控制台美化输出
- **matplotlib**：用于数据可视化（可选）
- **scipy**：用于统计分析（可选）
- **tqdm**：用于进度条显示（可选）

### 6.4 运行方式
```bash
# 运行客户端
python client.py

# 运行演示工具
python demo.py
```

## 7. 常用工具与依赖说明

### 7.1 核心依赖
- **json**：配置文件解析
- **random**：随机数生成
- **time**：时间戳生成
- **collections**：高效数据结构
- **numpy**：批量随机数生成
- **decimal**：高精度概率计算
- **dataclasses**：数据类定义

### 7.2 客户端依赖
- **rich**：控制台美化输出
- **datetime**：时间戳记录
- **subprocess**：控制台清理

### 7.3 演示工具依赖
- **tqdm**：进度条显示
- **matplotlib**：数据可视化
- **scipy**：统计分析

## 8. Agent开发相关资源路径

### 8.1 核心模块路径
- `core.py`：核心抽卡逻辑
- `client.py`：客户端交互
- `demo.py`：演示工具

### 8.2 配置文件路径
- `config/char_pool.json`：角色卡池配置
- `config/weapon_pool.json`：武器卡池配置
- `config/gacha_rules.json`：抽卡规则配置
- `config/constants.json`：全局常量配置

### 8.3 数据文件路径
- `pic/`：图片资源目录
- `doc/`：文档目录

### 8.4 工具脚本路径
- `demo.py`：抽卡模拟和统计工具

## 9. 调用方式

### 9.1 核心模块调用
```python
from core import CharGacha, WeaponGacha

# 角色卡池抽卡
char_gacha = CharGacha()
result = char_gacha.draw_once()

# 武器卡池抽卡
weapon_gacha = WeaponGacha()
results = weapon_gacha.apply_once()
```

### 9.2 客户端调用
```python
from client import GachaClient

# 创建客户端实例
client = GachaClient(
    chartered_permits=10,
    oroberyl=5000,
    arsenal_tickets=2000,
    origeometry=100
)

# 运行客户端
client.run()
```

### 9.3 演示工具调用
```python
from demo import GachaTestTool

# 创建测试工具实例
tool = GachaTestTool()

# 运行抽卡示例
tool.demo_char_draw(10)
tool.demo_weapon_apply(1)

# 运行统计分析
tool.stats_char_up_prob(10000, gragh=True)
```

## 10. 代码规范与最佳实践

### 10.1 命名规范
- 类名：大驼峰命名法（如 `CharGacha`）
- 方法名：小驼峰命名法（如 `draw_once`）
- 变量名：小驼峰命名法（如 `up_prob`）
- 常量名：全大写下划线分隔（如 `DEFAULT_PRECISION`）

### 10.2 代码风格
- 缩进：4个空格
- 行宽：不超过120字符
- 注释：使用文档字符串和内联注释
- 类型注解：使用Python类型注解

### 10.3 错误处理
- 使用 try-except 捕获异常
- 抛出有意义的异常信息
- 提供详细的错误提示

### 10.4 性能优化
- 使用批量随机数生成提升性能
- 使用缓存减少文件IO操作
- 使用高效的数据结构

## 11. 扩展与定制

### 11.1 配置文件定制
- 修改 `config/char_pool.json` 添加新角色
- 修改 `config/weapon_pool.json` 添加新武器
- 修改 `config/gacha_rules.json` 调整抽卡规则

### 11.2 功能扩展
- 新增卡池类型
- 新增奖励机制
- 新增统计分析功能

### 11.3 集成建议
- 与其他系统集成时，建议使用核心模块的API
- 如需自定义界面，建议基于客户端模块进行扩展
- 如需批量测试，建议使用演示工具模块

## 12. 故障排除

### 12.1 常见问题
- **配置文件不存在**：确保配置文件路径正确
- **配置文件格式错误**：检查JSON格式是否正确
- **资源不足**：确保有足够的资源进行抽卡
- **依赖缺失**：运行 `pip install -r requirements.txt` 安装依赖

### 12.2 调试建议
- 开启详细日志
- 使用演示工具进行测试
- 检查配置文件是否正确
- 验证依赖是否安装完整

## 13. 版本历史

### 1.1.0
- 新增批量随机数生成器
- 优化抽卡概率计算
- 完善保底机制
- 新增累计奖励功能

### 1.0.0
- 初始版本
- 实现基本抽卡功能
- 支持角色和武器卡池
- 提供控制台客户端

## 14. 开发者信息

- **作者**：Arsvine
- **版本**：1.1.0
- **最后修改时间**：2026-02-24
- **编码**：utf-8
- **适用Python版本**：3.10+

## 15. 关键词索引

### 15.1 核心概念
- **抽卡**：角色卡池抽卡、武器卡池抽卡、单抽、10连抽、加急招募
- **保底**：UP保底、6星保底、5星保底、概率递增
- **配额**：武库配额、角色配额、武器配额
- **资源**：特许寻访凭证、嵌晶玉、武库配额、衍质源石、加急招募

### 15.2 模块索引
- **core**：BatchRandom、GachaResult、GlobalConfigLoader、CharGacha、WeaponGacha
- **client**：GachaClient、资源管理、历史记录
- **demo**：GachaTestTool、统计分析、数据可视化

### 15.3 配置索引
- **char_pool.json**：角色卡池配置、UP角色、概率配置
- **weapon_pool.json**：武器卡池配置、UP武器、武器类型
- **gacha_rules.json**：抽卡规则、概率配置、保底规则、奖励配置
- **constants.json**：全局常量、默认值、文本常量

### 15.4 流程索引
- **抽卡流程**：角色卡池抽卡流程、武器卡池抽卡流程、保底判定
- **资源流程**：资源添加、资源转换、资源消耗、资源获取
- **历史流程**：记录历史、查看历史、保存历史

### 15.5 问题索引
- **配置问题**：配置文件不存在、配置文件格式错误
- **资源问题**：资源不足、资源转换失败
- **依赖问题**：依赖缺失、版本不兼容
- **运行问题**：模块导入失败、运行时错误

## 16. 索引更新机制

### 16.1 更新触发条件
- 项目版本更新时
- 核心功能变更时
- 配置文件结构变更时
- API接口变更时
- 业务逻辑变更时

### 16.2 更新流程
1. **检查变更**：识别项目中的变更内容
2. **更新内容**：修改文档中对应的部分
3. **更新索引**：修改关键词索引和目录
4. **验证完整性**：确保文档内容与项目保持一致
5. **更新时间戳**：更新文档最后修改时间

### 16.3 版本控制
- 文档版本与项目版本保持一致
- 每次更新记录变更内容
- 保留历史版本的文档备份

### 16.4 验证机制
- **内容验证**：确保文档内容与代码实现一致
- **链接验证**：确保目录和索引链接正确
- **完整性验证**：确保所有核心信息都已覆盖
- **准确性验证**：确保信息准确无误

### 16.5 Agent使用指南
- **快速检索**：通过关键词索引快速定位信息
- **层级导航**：通过目录结构层级导航
- **代码示例**：参考调用方式中的代码示例
- **故障排除**：参考常见问题解决方案
- **扩展开发**：参考扩展与定制部分

## 17. 文档维护指南

### 17.1 维护职责
- 项目维护者负责文档的更新
- 功能开发者负责对应的文档部分
- 版本发布时进行文档完整性检查

### 17.2 维护工具
- 使用Markdown编辑器编辑文档
- 使用版本控制系统管理文档变更
- 使用链接检查工具验证链接有效性

### 17.3 维护规范
- 保持文档结构清晰一致
- 确保术语统一
- 及时更新变更内容
- 定期检查文档完整性

### 17.4 反馈机制
- 鼓励开发者提供文档改进建议
- 收集用户使用过程中的问题
- 定期评估文档的实用性和准确性
