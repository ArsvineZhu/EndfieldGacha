# 策略数据协议

- 协议版本：`strategy-protocol-v1`
- 目标：为网页端策略编辑器提供稳定的 structured JSON 输入输出格式。
- 当前状态：仅支持结构化策略；旧版魔数策略文件仅保留为存档，不再接受为协议输入。

## 1. 顶层结构

顶层对象统一使用：

```json
{
  "protocol_version": "strategy-protocol-v1",
  "kind": "structured",
  "rule": {}
}
```

### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `protocol_version` | string | 是 | 当前固定为 `strategy-protocol-v1` |
| `kind` | string | 是 | 当前固定为 `structured` |
| `rule` | object | 是 | 结构化策略规则树 |

## 2. 结构化策略

结构化策略是一棵布尔规则树。

### 2.1 规则组节点

```json
{
  "node_type": "group",
  "match": "all",
  "version": "strategy-v2",
  "tags": ["example"],
  "children": []
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `node_type` | string | 是 | 固定为 `group` |
| `match` | string | 是 | `all` 表示与，`any` 表示或 |
| `version` | string | 否 | 当前默认 `strategy-v2` |
| `tags` | string[] | 否 | 前端可附带标签，后端保留 |
| `children` | array | 是 | 子节点列表，元素可以是 `group` 或 `condition` |

### 2.2 条件节点

```json
{
  "node_type": "condition",
  "kind": "dossier",
  "operator": "==",
  "value": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `node_type` | string | 是 | 固定为 `condition` |
| `kind` | string | 是 | 条件字段名 |
| `operator` | string | 是 | 比较运算符 |
| `value` | number / boolean / string | 是 | 比较值 |

### 2.3 支持的比较运算符

- `==`
- `!=`
- `>`
- `<`
- `>=`
- `<=`
- `in`

### 2.4 当前支持的条件字段

#### 数值字段

- `draws`
- `current_up`
- `six_star_count`
- `resource_left`
- `potential`
- `hard_pity`

#### 布尔字段

- `urgent`
- `dossier`
- `soft_pity`
- `up_oprt`
- `oprt`

#### 兼容别名

- `draw_count` -> `draws`
- `urgent_recruitment` -> `urgent`
- `headhunting_dossier` -> `dossier`
- `current_up_count` -> `current_up`
- `up_operator_count` -> `current_up`
- `six_star_obtained_count` -> `six_star_count`

## 3. 结构化策略示例

### 3.1 `(获得情报书 or 抽到六星) and 获得加急寻访`

```json
{
  "protocol_version": "strategy-protocol-v1",
  "kind": "structured",
  "rule": {
    "node_type": "group",
    "match": "all",
    "children": [
      {
        "node_type": "group",
        "match": "any",
        "children": [
          {
            "node_type": "condition",
            "kind": "dossier",
            "operator": "==",
            "value": true
          },
          {
            "node_type": "condition",
            "kind": "oprt",
            "operator": "==",
            "value": true
          }
        ]
      },
      {
        "node_type": "condition",
        "kind": "urgent",
        "operator": "==",
        "value": true
      }
    ]
  }
}
```

### 3.2 `获得当期 UP >= 1 or 抽数 >= 120`

```json
{
  "protocol_version": "strategy-protocol-v1",
  "kind": "structured",
  "rule": {
    "node_type": "group",
    "match": "any",
    "children": [
      {
        "node_type": "condition",
        "kind": "current_up",
        "operator": ">=",
        "value": 1
      },
      {
        "node_type": "condition",
        "kind": "draws",
        "operator": ">=",
        "value": 120
      }
    ]
  }
}
```

## 4. 后端适配行为

后端入口 `StrategyProtocolAdapter` 负责：

1. `from_payload(payload)`：
   - 把前端 JSON 转成 `StrategyRuleSet`
   - 拒绝旧版 `legacy_magic` 或裸 list 输入
2. `to_payload(strategy)`：
   - 把后端结构化规则对象转回 structured JSON 协议

调度器 `Scheduler.banner(...)`、`Scheduler.evaluate_multiple_strategies(...)` 已自动调用该适配层，因此网页端可以直接提交本协议对象。
