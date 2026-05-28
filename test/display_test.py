import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scheduler.display import SchedulerDisplay
from scheduler.strategy_rules import StrategyCondition, StrategyRuleSet


def test_format_strategy_is_human_readable_for_nested_rules():
    rule = StrategyRuleSet(
        match="any",
        conditions=[
            StrategyCondition(kind="draws", operator=">=", value=120),
            StrategyRuleSet(
                match="all",
                conditions=[
                    StrategyCondition(kind="current_up", operator=">=", value=1),
                    StrategyCondition(kind="resource_left", operator=">=", value=60),
                ],
            ),
        ],
    )

    text = SchedulerDisplay._format_strategy(rule)

    assert "任一满足:" in text
    assert "总抽数 大于等于 120" in text
    assert "全部满足:" in text
    assert "当期UP数量 大于等于 1" in text
    assert "剩余资源 大于等于 60" in text


def test_format_strategy_renders_boolean_values_cleanly():
    rule = StrategyRuleSet(
        match="all",
        conditions=[StrategyCondition(kind="dossier", operator="==", value=True)],
    )

    text = SchedulerDisplay._format_strategy(rule)

    assert "寻访情报书 : 有" in text
