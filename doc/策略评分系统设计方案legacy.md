# 旧评分系统设计归档

**归档日期**：2026-05-26

这是一份历史设计归档，不是当前实现说明。当前有效实现位于 `scheduler/scoring.py`，版本为 `SCORING_V2_VERSION = 2.3.0`。

## 归档目的

- 保留旧评分体系的设计背景
- 方便对比 V2 评分系统与旧方案的差异
- 防止把旧公式误认为当前代码行为

## 当前代码与旧设计的差异

### 已确认的当前实现

- 评分对象是 `StrategyTrace` 和 `StageTrace`
- 评分偏好对象是 `ScoringPreferences`
- 评分结果对象是 `StrategyScoreReport`
- 基准值估计器是 `BaselineEstimator`
- 近邻状态插值使用三次样条
- 评分缓存文件默认位于 `logs/scoring_v2_cache.json`
- 当前评分只面向角色池，不纳入武器池

### 旧设计中不应再直接引用的内容

- 旧的数学推导公式
- 旧的“理论全周期 100 万次模拟”默认前提
- 旧的相对 / 绝对评分公式全文
- 旧的多层目标分级推导

这些内容已经被当前代码实现取代。若需要阅读现行规则，请直接查看：

- `scheduler/scoring.py`
- `doc/implementation_records/2026-05-26-scoring-v2-followup.md`
- `README.md`

## 建议的使用方式

如果你只想确认“当前系统如何工作”，不要再把本文件当作说明书。它仅作为历史资料保留。

