# -*- coding: utf-8 -*-
"""评分系统。"""

from __future__ import annotations

import json
import os
from math import ceil
from typing import Any, Dict, List, Optional, Tuple

from gacha_core import GlobalConfigLoader

from .baseline import BaselineEstimator
from .models import (
    SCORING_CACHE_VERSION,
    SCORING_VERSION,
    ScoringPreferences,
    StrategyGoal,
    StrategyScoreReport,
    StrategyTrace,
    _flatten_results,
    calculate_trace_utility,
    log_map,
    mixed_utility_score,
)


class ScoringSystem:
    """评分系统。"""

    GRADE_THRESHOLDS: List[Tuple[float, str, str]] = [
        (90.0, "S", "极佳"),
        (80.0, "A", "优秀"),
        (70.0, "B", "良好"),
        (60.0, "C", "一般"),
        (50.0, "D", "较差"),
        (0.0, "E", "失败"),
    ]

    @staticmethod
    def default_preferences() -> ScoringPreferences:
        return ScoringPreferences()

    @staticmethod
    def default_goals() -> List[StrategyGoal]:
        return [StrategyGoal(kind="current_up", target=1)]

    @staticmethod
    def normalize_preferences(
        preferences: Optional[ScoringPreferences | Dict[str, Any] | str],
    ) -> ScoringPreferences:
        if preferences is None:
            return ScoringSystem.default_preferences()
        if isinstance(preferences, ScoringPreferences):
            return preferences
        if isinstance(preferences, dict):
            return ScoringPreferences.from_dict(preferences)
        if isinstance(preferences, str):
            return ScoringPreferences.from_json_file(preferences)
        raise TypeError(f"不支持的 preferences 类型: {type(preferences)}")

    @staticmethod
    def normalize_goals(
        goals: Optional[List[StrategyGoal] | List[Dict[str, Any]] | str],
    ) -> List[StrategyGoal]:
        if goals is None:
            return ScoringSystem.default_goals()
        if isinstance(goals, str):
            with open(goals, "r", encoding="utf-8") as file:
                payload: Any = json.load(file)
            if isinstance(payload, dict):
                payload = payload.get("goals")
            if not isinstance(payload, list):
                raise TypeError("goals JSON 文件必须是列表或包含 goals 列表字段")
            goals = payload
        if not isinstance(goals, list):
            raise TypeError("goals 必须是列表或 JSON 文件路径")
        normalized: List[StrategyGoal] = []
        for item in goals:
            if isinstance(item, StrategyGoal):
                normalized.append(item)
            elif isinstance(item, dict):
                normalized.append(StrategyGoal.from_dict(item))
            else:
                raise TypeError(f"不支持的 goal 节点类型: {type(item)}")
        return normalized

    @staticmethod
    def score_traces(
        traces: List[StrategyTrace],
        preferences: Optional[ScoringPreferences] = None,
        goals: Optional[List[StrategyGoal]] = None,
        baseline_estimator: Optional[BaselineEstimator] = None,
        include_traces: bool = False,
    ) -> StrategyScoreReport:
        if not traces:
            raise ValueError("traces不能为空")

        preferences = ScoringSystem.normalize_preferences(preferences)
        goals = ScoringSystem.normalize_goals(goals)
        if not goals:
            raise ValueError("至少需要一个目标")

        baseline_estimator = baseline_estimator or BaselineEstimator(
            samples=preferences.baseline_samples,
            base_seed=preferences.baseline_seed,
        )
        ScoringSystem._annotate_past_up_flags(traces, preferences, baseline_estimator.config_dir)

        scored_samples = [
            ScoringSystem._score_single_trace(
                trace=trace,
                preferences=preferences,
                goals=goals,
                baseline_estimator=baseline_estimator,
            )
            for trace in traces
        ]

        goal_completion_rate = sum(sample["goal_met"] for sample in scored_samples) / len(
            scored_samples
        )
        goal_score = round(100.0 * (goal_completion_rate ** preferences.alpha), 4)

        mean_utility = sum(sample["utility"] for sample in scored_samples) / len(
            scored_samples
        )
        mean_baseline = sum(sample["baseline"] for sample in scored_samples) / len(
            scored_samples
        )
        utility_ratio = mean_utility / mean_baseline if mean_baseline > 0 else 0.0
        utility_absolute_ratio = (
            mean_utility / preferences.utility_absolute_reference
            if preferences.utility_absolute_reference > 0
            else 0.0
        )
        utility_score = (
            mixed_utility_score(
                utility_ratio, utility_absolute_ratio, preferences
            )
            if mean_baseline > 0 and preferences.utility_absolute_reference > 0
            else 0.0
        )

        mean_opportunity = sum(sample["opportunity"] for sample in scored_samples) / len(
            scored_samples
        )
        opportunity_ratio = (
            mean_opportunity / preferences.opportunity_reference
            if preferences.opportunity_reference > 0
            else 0.0
        )
        resource_score = (
            log_map(opportunity_ratio, preferences.resource_log_map)
            if preferences.opportunity_reference > 0
            else 0.0
        )

        tail_count = max(1, ceil(len(scored_samples) * preferences.tail_ratio))
        tail_quality = sorted(sample["quality"] for sample in scored_samples)[:tail_count]
        tail_risk_mean = sum(tail_quality) / len(tail_quality)
        risk_score = round(tail_risk_mean, 4)

        raw_score = round(
            preferences.goal_weight * goal_score
            + preferences.utility_weight * utility_score
            + preferences.resource_weight * resource_score
            + preferences.risk_weight * risk_score,
            4,
        )
        grade, grade_name = ScoringSystem.get_grade(raw_score)

        cache_tags = [
            f"cache:{SCORING_CACHE_VERSION}",
            f"baseline_cache:{baseline_estimator.cache_path}",
            f"distribution_cache:{baseline_estimator.cache_path}",
            f"cache_hits:{baseline_estimator.cache_hits}",
            "baseline_interp:near-state-cubic-spline",
        ]

        return StrategyScoreReport(
            raw_score=raw_score,
            goal_score=goal_score,
            utility_score=round(utility_score, 4),
            resource_score=round(resource_score, 4),
            risk_score=round(risk_score, 4),
            goal_completion_rate=round(goal_completion_rate, 4),
            mean_utility=round(mean_utility, 4),
            mean_baseline=round(mean_baseline, 4),
            utility_ratio=round(utility_ratio, 4),
            mean_opportunity=round(mean_opportunity, 4),
            opportunity_ratio=round(opportunity_ratio, 4),
            tail_risk_mean=round(tail_risk_mean, 4),
            simulations=len(traces),
            grade=grade,
            grade_name=grade_name,
            baseline_samples=baseline_estimator.samples,
            baseline_seed=baseline_estimator.base_seed,
            scoring_version=SCORING_VERSION,
            parameter_tags=preferences.parameter_tags,
            cache_tags=cache_tags,
            traces=traces if include_traces else None,
        )

    @staticmethod
    def rank_reports(reports: List[StrategyScoreReport]) -> List[StrategyScoreReport]:
        if not reports:
            return reports

        ranked = sorted(
            enumerate(reports),
            key=lambda item: item[1].raw_score,
            reverse=True,
        )
        best_score = ranked[0][1].raw_score
        best_goal = ranked[0][1].goal_completion_rate
        best_opportunity = ranked[0][1].mean_opportunity
        total = len(ranked)

        for rank, (_, report) in enumerate(ranked, start=1):
            report.rank = rank
            report.percentile = round(((total - rank + 1) / total) * 100.0, 2)
            report.score_delta_from_best = round(report.raw_score - best_score, 4)
            report.goal_delta_from_best = round(
                report.goal_completion_rate - best_goal, 4
            )
            report.opportunity_delta_from_best = round(
                report.mean_opportunity - best_opportunity, 4
            )

        return reports

    @staticmethod
    def get_grade(score: float) -> Tuple[str, str]:
        for threshold, grade, grade_name in ScoringSystem.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade, grade_name
        return "E", "失败"

    @staticmethod
    def _score_single_trace(
        trace: StrategyTrace,
        preferences: ScoringPreferences,
        goals: List[StrategyGoal],
        baseline_estimator: BaselineEstimator,
    ) -> Dict[str, Any]:
        utility = calculate_trace_utility(trace, preferences)
        baseline = sum(
            baseline_estimator.estimate(
                stage.config_name,
                stage.start_counters,
                stage.paid_draws,
                preferences,
            )
            for stage in trace.stages
        )
        goal_met = all(ScoringSystem._evaluate_goal(trace, goal) for goal in goals)

        if trace.stages:
            final_stage = trace.stages[-1]
            future_draws = trace.final_resource_left + preferences.future_resource_income
            opportunity = baseline_estimator.estimate(
                final_stage.config_name,
                final_stage.end_counters,
                future_draws,
                preferences,
            )
        else:
            opportunity = 0.0

        utility_ratio = utility / baseline if baseline > 0 else 0.0
        utility_absolute_ratio = (
            utility / preferences.utility_absolute_reference
            if preferences.utility_absolute_reference > 0
            else 0.0
        )
        opportunity_ratio = (
            opportunity / preferences.opportunity_reference
            if preferences.opportunity_reference > 0
            else 0.0
        )

        quality_utility = (
            mixed_utility_score(
                utility_ratio, utility_absolute_ratio, preferences
            )
            if baseline > 0 and preferences.utility_absolute_reference > 0
            else 0.0
        )
        quality_resource = (
            log_map(opportunity_ratio, preferences.resource_log_map)
            if preferences.opportunity_reference > 0
            else 0.0
        )
        quality = (
            preferences.risk_utility_weight * quality_utility
            + (1.0 - preferences.risk_utility_weight) * quality_resource
        )

        return {
            "utility": utility,
            "baseline": baseline,
            "opportunity": opportunity,
            "goal_met": int(goal_met),
            "quality": quality,
        }

    @staticmethod
    def _evaluate_goal(trace: StrategyTrace, goal: StrategyGoal) -> bool:
        results = _flatten_results(trace)

        if goal.kind == "current_up":
            if goal.character_name:
                count = sum(
                    1
                    for result in results
                    if result.get("is_current_up") and result.get("name") == goal.character_name
                )
            elif goal.stage_index is not None and 0 <= goal.stage_index < len(trace.stages):
                count = sum(
                    1
                    for result in trace.stages[goal.stage_index].results
                    if result.get("is_current_up")
                )
            else:
                count = sum(1 for result in results if result.get("is_current_up"))
            return count >= goal.target

        if goal.kind == "past_up":
            count = sum(1 for result in results if result.get("is_past_up"))
            return count >= goal.target

        if goal.kind == "resource_at_least":
            return trace.final_resource_left >= goal.target

        if goal.kind == "stage_paid_draws_at_most":
            if goal.stage_index is None or goal.stage_index >= len(trace.stages):
                return False
            return trace.stages[goal.stage_index].paid_draws <= goal.target

        if goal.kind == "six_star_count":
            count = sum(1 for result in results if int(result.get("star", 0)) == 6)
            return count >= goal.target

        if goal.kind == "character_count":
            if not goal.character_name:
                raise ValueError("character_count 目标必须提供 character_name")
            count = sum(1 for result in results if result.get("name") == goal.character_name)
            return count >= goal.target

        raise ValueError(f"不支持的目标类型: {goal.kind}")

    @staticmethod
    def _annotate_past_up_flags(
        traces: List[StrategyTrace], preferences: ScoringPreferences, config_dir: str = "configs"
    ) -> None:
        known_past_up_names = set(preferences.past_up_character_names)
        featured_cache: Dict[str, set[str]] = {}
        for trace in traces:
            for stage in trace.stages:
                stage_past_up_names = featured_cache.get(stage.config_name)
                if stage_past_up_names is None:
                    try:
                        config = GlobalConfigLoader(os.path.join(config_dir, stage.config_name))
                        stage_past_up_names = set(config.get_char_featured_names()["past_up"])
                    except (FileNotFoundError, ValueError):
                        stage_past_up_names = set()
                    featured_cache[stage.config_name] = stage_past_up_names
                for result in stage.results:
                    if result.get("star") != 6:
                        result["is_past_up"] = False
                        continue
                    result["is_past_up"] = (
                        not result.get("is_current_up", False)
                        and result.get("name")
                        in (stage_past_up_names | known_past_up_names)
                    )


__all__ = ["ScoringSystem"]
