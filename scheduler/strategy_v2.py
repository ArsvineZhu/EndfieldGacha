# -*- coding: utf-8 -*-
"""结构化策略判断系统。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, TypeAlias


@dataclass(frozen=True)
class StrategyCondition:
    """单个结构化条件。"""

    kind: str
    operator: str
    value: int | float | bool | str


@dataclass(frozen=True)
class StrategyRuleSet:
    """结构化策略规则集合。"""

    match: Literal["all", "any"] = "all"
    conditions: List[StrategyCondition | StrategyRuleSet] = field(default_factory=list)
    version: str = "strategy-v2"
    tags: List[str] = field(default_factory=list)


StrategyNode: TypeAlias = StrategyCondition | StrategyRuleSet


class StrategyRuleEngine:
    """结构化规则判断器。"""

    _KIND_ALIASES = {
        "draw_count": "draws",
        "urgent_recruitment": "urgent",
        "headhunting_dossier": "dossier",
        "current_up_count": "current_up",
        "up_operator_count": "current_up",
        "six_star_obtained_count": "six_star_count",
    }

    _OPERATORS = {
        "==": lambda left, right: left == right,
        "!=": lambda left, right: left != right,
        ">": lambda left, right: left > right,
        "<": lambda left, right: left < right,
        ">=": lambda left, right: left >= right,
        "<=": lambda left, right: left <= right,
        "in": lambda left, right: left in right,
    }

    @classmethod
    def should_stop(
        cls, rule_set: StrategyRuleSet | Dict[str, Any], draw_count: int, state: Dict[str, Any]
    ) -> bool:
        rule_set = cls._coerce(rule_set)
        if not rule_set.conditions:
            return True

        evaluations = [
            cls._evaluate_node(condition, draw_count=draw_count, state=state)
            for condition in rule_set.conditions
        ]
        if rule_set.match == "any":
            return any(evaluations)
        return all(evaluations)

    @classmethod
    def describe(cls, rule_set: StrategyRuleSet | Dict[str, Any]) -> Dict[str, Any]:
        rule_set = cls._coerce(rule_set)
        return {
            "version": rule_set.version,
            "match": rule_set.match,
            "tags": list(rule_set.tags),
            "conditions": [cls._describe_node(condition) for condition in rule_set.conditions],
        }

    @classmethod
    def _evaluate_condition(
        cls, condition: StrategyCondition, draw_count: int, state: Dict[str, Any]
    ) -> bool:
        if condition.operator not in cls._OPERATORS:
            raise ValueError(f"不支持的比较运算符: {condition.operator}")

        left = cls._resolve_value(condition.kind, draw_count, state)
        return cls._OPERATORS[condition.operator](left, condition.value)

    @staticmethod
    def _resolve_value(kind: str, draw_count: int, state: Dict[str, Any]) -> Any:
        kind = StrategyRuleEngine._KIND_ALIASES.get(kind, kind)
        if kind == "draws":
            return draw_count
        if kind == "current_up":
            return state.get("current_up", 0)
        if kind == "six_star_count":
            return state.get("six_star_count", 0)
        if kind == "urgent":
            return bool(state.get("urgent", False))
        if kind == "dossier":
            return bool(state.get("dossier", False))
        if kind == "soft_pity":
            return bool(state.get("soft_pity", False))
        if kind == "up_oprt":
            return bool(state.get("up_oprt", False))
        if kind == "oprt":
            return bool(state.get("oprt", False))
        if kind == "resource_left":
            return state.get("resource_left", 0)
        if kind == "potential":
            return state.get("potential", 0)
        if kind == "hard_pity":
            return draw_count
        if kind == "flag":
            return bool(state.get("flag", False))
        return state.get(kind)

    @staticmethod
    def _coerce(rule_set: StrategyRuleSet | Dict[str, Any]) -> StrategyRuleSet:
        if isinstance(rule_set, StrategyRuleSet):
            return rule_set
        if isinstance(rule_set, dict):
            conditions = [StrategyRuleEngine._coerce_node(condition) for condition in rule_set.get("conditions", [])]
            return StrategyRuleSet(
                match=rule_set.get("match", "all"),
                conditions=conditions,
                version=rule_set.get("version", "strategy-v2"),
                tags=list(rule_set.get("tags", [])),
            )
        raise TypeError(f"无法解析的结构化策略类型: {type(rule_set)}")

    @classmethod
    def _coerce_node(cls, node: StrategyNode | Dict[str, Any]) -> StrategyNode:
        if isinstance(node, StrategyCondition):
            return node
        if isinstance(node, StrategyRuleSet):
            return cls._coerce(node)
        if isinstance(node, dict):
            if "conditions" in node:
                return cls._coerce(node)
            return StrategyCondition(**node)
        raise TypeError(f"无法解析的结构化策略节点类型: {type(node)}")

    @classmethod
    def _describe_node(cls, node: StrategyNode) -> Dict[str, Any]:
        if isinstance(node, StrategyCondition):
            return {
                "type": "condition",
                "kind": node.kind,
                "operator": node.operator,
                "value": node.value,
            }
        return {"type": "group", **cls.describe(node)}

    @classmethod
    def _evaluate_node(
        cls, node: StrategyNode, draw_count: int, state: Dict[str, Any]
    ) -> bool:
        if isinstance(node, StrategyCondition):
            return cls._evaluate_condition(node, draw_count=draw_count, state=state)
        return cls.should_stop(node, draw_count=draw_count, state=state)


def is_structured_strategy(rule_definition: Any) -> bool:
    return isinstance(rule_definition, (StrategyRuleSet, dict))


__all__ = [
    "StrategyCondition",
    "StrategyRuleEngine",
    "StrategyRuleSet",
    "is_structured_strategy",
]
