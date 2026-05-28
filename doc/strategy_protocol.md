# 策略数据协议

**更新日期**：2026-05-28

本协议由 `scheduler/strategy_protocol.py` 实现，当前只接受结构化策略树。

## 1. 顶层格式

```json
{
  "protocol_version": "strategy-protocol-v1",
  "kind": "structured",
  "rule": {}
}
```

### 顶层字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `protocol_version` | string | 固定为 `strategy-protocol-v1` |
| `kind` | string | 固定为 `structured` |
| `rule` | object | 结构化策略树根节点 |

`StrategyProtocolAdapter.from_payload(...)` 会拒绝：

- `list` 类型的旧策略输入
- `kind == "legacy_magic"` 的旧协议
- 不支持的 `protocol_version`

## 2. 节点结构

### 2.1 规则组

```json
{
  "node_type": "group",
  "match": "all",
  "version": "strategy-structured",
  "tags": ["example"],
  "children": []
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `node_type` | string | 固定为 `group` |
| `match` | string | `all` 或 `any` |
| `version` | string | 默认 `strategy-structured` |
| `tags` | array[string] | 可选标签 |
| `children` | array | 子节点，元素可为 `group` 或 `condition` |

### 2.2 条件节点

```json
{
  "node_type": "condition",
  "kind": "draws",
  "operator": ">=",
  "value": 120
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `node_type` | string | 固定为 `condition` |
| `kind` | string | 条件字段名 |
| `operator` | string | 比较运算符 |
| `value` | number / boolean / string | 比较值 |

## 3. 支持的运算符

- `==`
- `!=`
- `>`
- `<`
- `>=`
- `<=`
- `in`

## 4. 支持的字段

### 数值字段

- `draws`
- `current_up`
- `six_star_count`
- `resource_left`
- `potential`
- `hard_pity`

### 布尔字段

- `urgent`
- `dossier`
- `soft_pity`
- `up_oprt`
- `oprt`

### 兼容别名

- `draw_count` -> `draws`
- `urgent_recruitment` -> `urgent`
- `headhunting_dossier` -> `dossier`
- `current_up_count` -> `current_up`
- `up_operator_count` -> `current_up`
- `six_star_obtained_count` -> `six_star_count`

## 5. 示例

### 5.1 `(dossier or oprt) and urgent`

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

### 5.2 `current_up >= 1 or draws >= 120`

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

## 6. Backend behaviour

- `StrategyProtocolAdapter.from_payload(...)` converts a structured payload into `StrategyRuleSet`
- `StrategyProtocolAdapter.to_payload(...)` serializes `StrategyRuleSet` or `StrategyCondition` back to the same protocol
- `Scheduler.banner(...)` and `Scheduler.evaluate_multiple_strategies(...)` both call the adapter automatically

`StrategyRuleEngine.describe(...)` is a separate display helper and returns `type` keys, not protocol payload keys.
