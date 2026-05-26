# -*- coding: utf-8 -*-
"""网页端策略 JSON 协议转换层。"""

from __future__ import annotations

from typing import Any, Dict

from .strategy_rules import StrategyCondition, StrategyRuleEngine, StrategyRuleSet

STRATEGY_PROTOCOL_VERSION = "strategy-protocol-v1"


class StrategyProtocolAdapter:
    """在前端 JSON 协议与后端结构化策略对象之间转换。"""

    @classmethod
    def from_payload(cls, payload: Any) -> StrategyRuleSet:
        if isinstance(payload, StrategyRuleSet):
            return payload
        if isinstance(payload, StrategyCondition):
            return StrategyRuleSet(conditions=[payload])
        if isinstance(payload, list):
            raise TypeError("仅支持结构化策略规则，不再支持旧版魔数策略列表")
        if not isinstance(payload, dict):
            raise TypeError(f"无法解析的策略类型: {type(payload)}")

        protocol_version = payload.get("protocol_version")
        if protocol_version not in (None, STRATEGY_PROTOCOL_VERSION):
            raise ValueError(f"不支持的策略协议版本: {protocol_version}")

        kind = payload.get("kind")
        if kind == "structured":
            if "rule" not in payload:
                raise ValueError("structured 策略协议缺少 rule 字段")
            return cls._ensure_rule_set(cls._parse_node(payload["rule"]))
        if kind == "legacy_magic":
            raise ValueError("不再支持旧版魔数策略协议，请改用 structured 协议")

        if "node_type" in payload:
            return cls._ensure_rule_set(cls._parse_node(payload))
        return StrategyRuleEngine._coerce(payload)

    @classmethod
    def to_payload(cls, strategy: Any) -> Dict[str, Any]:
        if isinstance(strategy, StrategyCondition):
            strategy = StrategyRuleSet(conditions=[strategy])
        if isinstance(strategy, StrategyRuleSet):
            return {
                "protocol_version": STRATEGY_PROTOCOL_VERSION,
                "kind": "structured",
                "rule": cls._serialize_node(strategy),
            }
        raise TypeError(f"无法序列化的策略类型: {type(strategy)}")

    @staticmethod
    def _ensure_rule_set(
        node: StrategyRuleSet | StrategyCondition,
    ) -> StrategyRuleSet:
        if isinstance(node, StrategyRuleSet):
            return node
        return StrategyRuleSet(conditions=[node])

    @classmethod
    def _parse_node(cls, node: Any) -> StrategyRuleSet | StrategyCondition:
        if isinstance(node, StrategyRuleSet):
            return node
        if isinstance(node, StrategyCondition):
            return node
        if not isinstance(node, dict):
            raise TypeError(f"无法解析的策略节点类型: {type(node)}")

        node_type = node.get("node_type")
        if node_type == "condition":
            return StrategyCondition(
                kind=node["kind"],
                operator=node["operator"],
                value=node["value"],
            )
        if node_type == "group":
            children = [cls._parse_node(child) for child in node.get("children", [])]
            return StrategyRuleSet(
                match=node.get("match", "all"),
                conditions=children,
                version=node.get("version", "strategy-structured"),
                tags=list(node.get("tags", [])),
            )

        return StrategyRuleEngine._coerce(node)

    @classmethod
    def _serialize_node(cls, node: StrategyRuleSet | StrategyCondition) -> Dict[str, Any]:
        if isinstance(node, StrategyCondition):
            return {
                "node_type": "condition",
                "kind": node.kind,
                "operator": node.operator,
                "value": node.value,
            }
        return {
            "node_type": "group",
            "match": node.match,
            "version": node.version,
            "tags": list(node.tags),
            "children": [cls._serialize_node(child) for child in node.conditions],
        }


__all__ = ["STRATEGY_PROTOCOL_VERSION", "StrategyProtocolAdapter"]

