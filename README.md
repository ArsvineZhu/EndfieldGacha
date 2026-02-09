# 终末地卡池 | Endfield Gacha

**文 / A**：[**中文**](README.md) | [**English**](README_en.md)

---

## 终末地卡池

《明日方舟：终末地》的卡池系统，包括但不限于统计、模拟。

## 项目介绍

### 1. 环境要求

- **Python** 3.10+

- 依赖库：
      - matplotlib 3.10.8
      - rich 14.3.2
      - tqdm 4.67.3

### 2. 安装步骤

#### 克隆仓库

```bash
git clone https://github.com/ArsvineZhu/EndfieldGacha.git
cd EndfieldGacha
```

#### 安装依赖

```bash
pip install -r requirements.txt
```

### 项目结构

```plaintext
EndfieldGacha/
├── config/                   # 配置文件目录
│   ├── char_pool.json        # 角色卡池配置
│   ├── constants.json        # 常量数值配置
│   ├── gacha_rules.json      # 卡池规则配置
│   └── weapon_pool.json      # 武器卡池配置
├── pic/                      # 图片存储目录
│   ├── char.png              # 角色卡池规则原图
│   ├── weapon.png            # 武器卡池规则原图
│   └── stats/                # 统计结果图片存储目录
├── client.py                 # 控制台客户端
├── core.py                   # 卡池系统核心
└── demo.py                   # 演示与统计
```

## 声明

部分图片素材来自于《明日方舟：终末地》游戏截图。

## 致谢

- **上海鹰角网络科技有限公司**

- **《明日方舟：终末地》**

> （注：文档及代码部分内容可能由 AI 生成）
