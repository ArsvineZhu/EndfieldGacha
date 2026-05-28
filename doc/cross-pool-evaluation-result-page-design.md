# 跨卡池方案评估器结果页设计说明

> 本文档用于指导“跨卡池方案评估器”结果页的视觉重构。设计参考对象为图二中的战术结算界面；内容替换对象为图一中的策略评分结果页。

---

## 1. 设计目标

当前页面已经具备基本的数据内容，但视觉呈现仍偏向普通网页后台：信息被放置在常规卡片中，缺少强烈的结果反馈、视觉重心和结算页冲击力。

本次设计目标是将页面从普通网页卡片式布局改造为：

```text
战术结算界面 / 战报评级页 / 策略评估终端
```

用户进入结果页后，应该首先看到最终评级与总分，然后通过雷达图理解评分来源，最后再查看任务 ID、目标完成率、收益倍率等辅助信息。

信息阅读顺序应为：

```text
[C] 69.1
↓
五维雷达图
↓
目标完成率、收益倍率、任务 ID 等元信息
```

---

## 2. 图二设计结构拆解

图二不是传统仪表盘，而是一个横向 16:9 的结算画面。它的核心结构是：

```text
左侧：分项能力雷达图
中部：巨大半透明 RESULTS 背景字
右侧：评级徽标与最终分数
底部：状态标签与说明信息
```

整体视觉由以下几层构成。

### 2.1 背景层

背景并非纯黑，而是带有终端屏幕质感的深黑灰底。

主要元素包括：

```text
深黑背景
+ 横向扫描线
+ 微弱噪点
+ 暗角
+ 左右边缘磨损条
+ 低透明度红色斜切图形
```

背景的作用不是装饰，而是建立“战术终端 / 结算屏幕 / 后朋克工业界面”的氛围。

### 2.2 红色几何结构层

图二的红色区域承担视觉动势。

结构包括：

```text
左侧：大面积半透明红色斜切平行四边形
中部：横向暗红色信息带
右侧：穿过大分数的红色光晕横线
```

红色几何块的方向大多是斜切的，能够制造速度感和战术界面的攻击性。

### 2.3 主信息层

主信息层分为三块。

```text
左侧：雷达图 / 分项指标
中间：巨大半透明 RESULTS 背景字
右侧：等级与总分
```

图二真正的视觉中心不是几何背景，而是“左侧分项解释”和“右侧最终判定”之间的张力。

### 2.4 辅助信息层

底部原本用于展示能力词条或状态标签。在本项目中，可以替换为策略评估元信息。

```text
左下：方案状态、评估对象、目标完成率
右下：综合等级、收益倍率、任务 ID
最右下：继续 / 查看详情按钮
```

---

## 3. 图一内容整理

图一页面中目前已有的关键内容如下。

### 3.1 页面身份

```text
跨卡池方案评估器
```

### 3.2 当前阶段

```text
评估结果
```

### 3.3 说明文案

```text
这是一套套卡池方案在当前偏好下的评分结果。
```

### 3.4 任务信息

```text
任务 ID：8F17B807DFF44764B0AD6845EC26D222
```

### 3.5 综合评分

```text
等级：[C]
总分：69.1
```

### 3.6 五维指标

```text
目标达成：22.8
期望收益：88.4
资源机会：100.0
风险稳定：65.2
目标完成率：25.3
```

### 3.7 底部数值

```text
目标完成率：0.253
收益倍率：1.2255
```

---

## 4. 内容替换后的整体版式

建议将结果页设计为一个 16:9 的横向结算屏。

整体布局如下：

```text
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  跨卡池方案评估器                                          │
│  评估结果                                                  │
│                                                            │
│        目标完成率 25.3        目标达成 22.8                │
│                                                            │
│   风险稳定 65.2       [五轴雷达图]       期望收益 88.4      │
│                                                            │
│                  资源机会 100.0                            │
│                                                            │
│                         RESULTS / EVALUATION               │
│                                                            │
│                                      [ C ]                  │
│                                      69.1                   │
│                                                            │
│              ■ 当前偏好评分结果       ■ 综合等级：C          │
│              ■ 目标完成率 0.253       ■ 收益倍率 1.2255      │
│              ■ 套装卡池方案           ■ 任务 ID：8F17...222  │
│                                                            │
│                                                   >>查看详情 │
└────────────────────────────────────────────────────────────┘
```

---

## 5. 雷达图设计方案

图二原图使用的是六轴雷达图，但图一实际内容只有五个核心指标，因此不建议强行凑成六轴。应使用五边形雷达图。

### 5.1 指标顺序

五个指标建议按顺时针方向排列。

```text
顶部：目标达成 22.8
右上：期望收益 88.4
右下：资源机会 100.0
左下：风险稳定 65.2
左上：目标完成率 25.3
```

该顺序的好处是：

```text
目标类指标集中在上方与左上方
收益类指标位于右侧
资源类指标位于右下方
风险稳定指标位于左下方
```

视觉上会形成“目标不足、收益较高、资源充足、风险中等”的偏斜形态，能够很好地解释为什么综合评价为 C。

### 5.2 雷达图结构

雷达图建议由以下元素构成：

```text
外框：红色五边形描边
中框：低透明度深灰五边形描边
轴线：从中心向五个方向发散
数据面：暗红色半透明填充
数据线：高亮红色描边
数据点：小型红白节点
```

### 5.3 文本标签

每个指标标签建议采用上下两行结构。

```text
目标达成
22.8
```

其中：

```text
指标名：较小字号，白色或浅灰
指标值：较大字号，白色，使用压缩数字字体
```

---

## 6. 右侧评分区设计方案

右侧评分区是整个页面的视觉锚点，应替换图二中的 `[S] 755`。

### 6.1 替换内容

原图二：

```text
[S]
755
```

替换为：

```text
[C]
69.1
```

### 6.2 结构建议

```text
上方：红色方括号装饰
中间：[ C ]
下方：69.1
背景：红色水平光晕
```

### 6.3 字号建议

```text
[C]：约 84px—108px
69.1：约 150px—190px
```

分数一定要比其他所有信息更大。用户进入页面时，第一眼必须看到最终评分。

### 6.4 颜色建议

```text
等级与分数：接近白色的暖灰
括号装饰：高饱和红色
光晕：半透明红色
```

---

## 7. 中央背景字设计方案

图二中部有巨大的半透明：

```text
RESULTS
```

本项目中可以继续使用英文大字，不建议直接使用巨大中文“评估结果”。原因是中文大字在该风格下容易显得过实，削弱工业 UI 的抽象感。

推荐方案：

```text
RESULTS
```

或：

```text
EVALUATION
```

也可以采用组合方式：

```text
大字：RESULTS
小字：跨卡池方案评估结果
```

样式建议：

```css
font-size: 160px;
font-weight: 900;
letter-spacing: 0.02em;
color: #ffffff;
opacity: 0.06;
```

位置建议：

```text
画面中部偏右
位于雷达图和总分之间
作为背景信息，不参与主要阅读
```

---

## 8. 底部信息替换方案

图二底部的能力标签可以替换为策略评估元信息。

### 8.1 左侧信息组

```text
■ 当前偏好评分结果
■ 套装卡池方案
■ 目标完成率 0.253
```

### 8.2 右侧信息组

```text
■ 综合等级 C
■ 收益倍率 1.2255
■ 任务 ID：8F17B807...C26D222
```

完整任务 ID 不建议直接铺满画面，可以进行截断显示：

```text
8F17B807...C26D222
```

完整内容可以放入 hover tooltip、详情页或复制按钮中。

---

## 9. 最终文案整理

### 9.1 顶部标题

```text
跨卡池方案评估器
```

### 9.2 当前页面标题

```text
评估结果
```

### 9.3 页面说明

```text
这是一套套卡池方案在当前偏好下的评分结果。
```

### 9.4 主评分

```text
[C]
69.1
```

### 9.5 雷达图指标

```text
目标达成
22.8

期望收益
88.4

资源机会
100.0

风险稳定
65.2

目标完成率
25.3
```

### 9.6 底部数值

```text
目标完成率
0.253

收益倍率
1.2255
```

### 9.7 任务信息

```text
任务 ID
8F17B807DFF44764B0AD6845EC26D222
```

### 9.8 操作按钮

```text
>> 查看详情
```

若该页是流程终点，也可以使用：

```text
>> 继续
```

---

## 10. 视觉参数建议

### 10.1 颜色变量

```css
:root {
  --bg: #080909;
  --panel-dark: #111315;
  --red-main: #c91f24;
  --red-deep: #5d1115;
  --red-glow: rgba(255, 38, 38, 0.45);
  --text-main: #f2f0e8;
  --text-muted: #8a8a8a;
  --line-muted: rgba(255, 255, 255, 0.16);
}
```

### 10.2 字体建议

中文字体：

```text
思源黑体
Noto Sans SC
HarmonyOS Sans SC
```

英文与数字字体：

```text
DIN Condensed
Rajdhani
Bebas Neue
Orbitron
```

数字部分应优先使用压缩感强、工业感强的字体。图二的关键气质很大程度来自大数字、窄体字、红色斜切图形和扫描线质感。

---

## 11. DOM 结构建议

页面可以拆成以下结构。

```html
<section class="eval-result-screen">
  <div class="eval-bg-noise"></div>
  <div class="eval-bg-scanline"></div>
  <div class="eval-bg-red-slab"></div>
  <div class="eval-bg-title">RESULTS</div>

  <header class="eval-topbar">
    <div class="eval-product">跨卡池方案评估器</div>
    <nav class="eval-nav">
      <!-- 引导 / 问卷 / 问卷结果 / 全局设置 / 卡池阶段 / 目标 / 提交 / 结果 -->
    </nav>
  </header>

  <main class="eval-result-layout">
    <section class="eval-radar-zone">
      <!-- 五维雷达图 -->
    </section>

    <section class="eval-score-zone">
      <div class="eval-rank">[ C ]</div>
      <div class="eval-score">69.1</div>
    </section>
  </main>

  <footer class="eval-meta-zone">
    <div class="eval-meta-left">
      <div>■ 当前偏好评分结果</div>
      <div>■ 套装卡池方案</div>
      <div>■ 目标完成率 0.253</div>
    </div>

    <div class="eval-meta-right">
      <div>■ 综合等级 C</div>
      <div>■ 收益倍率 1.2255</div>
      <div>■ 任务 ID：8F17B807...C26D222</div>
    </div>

    <button class="eval-next">&gt;&gt; 查看详情</button>
  </footer>
</section>
```

---

## 12. CSS 结构建议

以下是页面结构级 CSS 示例。具体尺寸可根据实际页面容器继续微调。

```css
.eval-result-screen {
  position: relative;
  width: 100%;
  min-height: 100vh;
  overflow: hidden;
  background: var(--bg);
  color: var(--text-main);
  font-family: "Noto Sans SC", "HarmonyOS Sans SC", sans-serif;
}

.eval-bg-scanline {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    to bottom,
    rgba(255, 255, 255, 0.035) 0,
    rgba(255, 255, 255, 0.035) 1px,
    transparent 1px,
    transparent 4px
  );
  opacity: 0.35;
}

.eval-bg-red-slab {
  position: absolute;
  left: -8%;
  top: 12%;
  width: 62%;
  height: 72%;
  background: linear-gradient(
    110deg,
    rgba(160, 20, 24, 0.42),
    rgba(80, 10, 14, 0.18)
  );
  transform: skewX(-22deg);
}

.eval-bg-title {
  position: absolute;
  left: 47%;
  top: 39%;
  transform: translate(-50%, -50%);
  font-family: "Rajdhani", "DIN Condensed", sans-serif;
  font-size: clamp(120px, 12vw, 220px);
  font-weight: 900;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.07);
  white-space: nowrap;
  pointer-events: none;
}

.eval-topbar {
  position: relative;
  z-index: 2;
  padding: 40px 56px 0;
}

.eval-product {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.eval-result-layout {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: 58% 42%;
  min-height: 620px;
  align-items: center;
  padding: 40px 72px 0;
}

.eval-radar-zone {
  position: relative;
  min-height: 520px;
}

.eval-score-zone {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.eval-score-zone::before {
  content: "";
  position: absolute;
  width: 520px;
  height: 4px;
  background: linear-gradient(
    90deg,
    transparent,
    var(--red-glow),
    transparent
  );
  filter: blur(4px);
}

.eval-rank {
  position: relative;
  z-index: 1;
  font-family: "Rajdhani", "DIN Condensed", sans-serif;
  font-size: clamp(72px, 6vw, 108px);
  font-weight: 900;
  color: var(--text-main);
  letter-spacing: 0.08em;
}

.eval-score {
  position: relative;
  z-index: 1;
  font-family: "Rajdhani", "DIN Condensed", sans-serif;
  font-size: clamp(128px, 11vw, 190px);
  font-weight: 900;
  line-height: 0.9;
  color: var(--text-main);
}

.eval-meta-zone {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 48px;
  align-items: end;
  padding: 0 72px 56px;
  color: var(--text-muted);
  font-size: 18px;
  line-height: 1.8;
}

.eval-next {
  border: none;
  background: transparent;
  color: var(--text-main);
  font-size: 22px;
  font-weight: 700;
  cursor: pointer;
}
```

---

## 13. 当前页面的主要改造方向

当前图一的问题不是数据内容不足，而是视觉层级不够清晰。

应从以下方向改造：

```text
普通网页卡片
↓
战术结算界面

数据表述
↓
评级画面

组件堆叠
↓
主舞台构图
```

最终页面要让用户第一眼看到结果，第二眼理解原因，第三眼查看细节。

```text
第一眼：[C] 69.1
第二眼：五维雷达图
第三眼：目标完成率、收益倍率、任务 ID
```

---

## 14. 结论

图二的设计关键不是单纯的红黑配色，而是完整的信息秩序：

```text
分项解释在左
最终判断在右
巨大背景字建立结算氛围
红色斜切图形制造战术动势
扫描线与噪点塑造终端质感
```

将图一内容替换进去后，页面应围绕以下核心视觉结果展开：

```text
[ C ]
69.1
```

雷达图用于解释该结果：资源机会很高，期望收益较高，风险稳定中等，但目标达成与目标完成率偏低，因此最终综合评级为 C。

这会比当前卡片式页面更接近“策略评估完成后的战报结算页”，也更符合跨卡池方案评估器的系统气质。
