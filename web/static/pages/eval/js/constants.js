(function assignEvalConstants(global) {
    const PAIRS = [
        ["goal", "utility"],
        ["goal", "resource"],
        ["goal", "risk"],
        ["utility", "resource"],
        ["utility", "risk"],
        ["resource", "risk"],
    ];

    const MODULES = {
        goal: {
            label: "目标达成",
            summary: "优先保证你设定的目标能真正完成。",
            impact: "提高目标完成率在总分中的分量。",
            prompt: "如果两者不能兼得，你更不能牺牲哪一项？",
        },
        utility: {
            label: "期望收益",
            summary: "优先考虑平均能拿到多少有价值的内容。",
            impact: "提高平均收益和综合产出的权重。",
            prompt: "如果两者不能兼得，你更不能牺牲哪一项？",
        },
        resource: {
            label: "资源机会",
            summary: "优先保留资源，给后续卡池留更大操作空间。",
            impact: "提高剩余资源和未来选择余地的权重。",
            prompt: "如果两者不能兼得，你更不能牺牲哪一项？",
        },
        risk: {
            label: "风险稳定",
            summary: "优先避免翻车，接受均值低一点但结果更稳。",
            impact: "提高低尾风险和稳定性的权重。",
            prompt: "如果两者不能兼得，你更不能牺牲哪一项？",
        },
    };

    const STRENGTH_OPTIONS = [
        { label: "只是略微偏向", value: 3, hint: "更希望这样，但还能接受让步。" },
        { label: "明显更重要", value: 5, hint: "这项更关键，另一项只能适度妥协。" },
        { label: "很难牺牲", value: 7, hint: "除非代价很小，否则不愿意放弃。" },
        { label: "完全不能牺牲", value: 9, hint: "这是底线，宁愿放掉另一项。" },
    ];

    const CONDITION_FIELDS = {
        draws: { label: "当前卡池已抽数", type: "number" },
        current_up: { label: "当前 UP 数量", type: "number" },
        six_star_count: { label: "6 星数量", type: "number" },
        resource_left: { label: "剩余标准抽数", type: "number" },
        potential: { label: "当前 UP 潜能", type: "number" },
        urgent: { label: "是否触发加急", type: "boolean" },
        dossier: { label: "是否获得档案", type: "boolean" },
        soft_pity: { label: "是否进入软保底", type: "boolean" },
        up_oprt: { label: "是否出过当期 UP", type: "boolean" },
        oprt: { label: "是否出过任意 6 星", type: "boolean" },
    };

    const GOAL_TYPES = {
        current_up: { label: "总当前 UP 数量", mode: "number" },
        character_count: { label: "指定角色获取数量", mode: "character" },
        resource_at_least: { label: "最终剩余抽数不少于", mode: "number" },
        stage_paid_draws_at_most: { label: "单阶段付费抽数最多", mode: "stage" },
        six_star_count: { label: "总 6 星数量", mode: "number" },
    };

    const NUMERIC_OPERATORS = ["==", "!=", ">", "<", ">=", "<="];
    const BOOLEAN_OPERATORS = ["==", "!="];

    const STATUS_LABELS = {
        queued: "排队中",
        running: "评估中",
        succeeded: "已完成",
        failed: "失败",
    };

    const STEP_LABELS = {
        intro: "引导",
        questionnaire: "问卷",
        questionnaire_result: "问卷结果",
        advanced: "高级设置",
        setup: "全局设置",
        banners: "卡池阶段",
        goals: "目标",
        submit: "提交",
        result: "结果",
    };

    function buildDefaultConditionNode() {
        return {
            node_type: "condition",
            kind: "draws",
            operator: ">=",
            value: 60,
        };
    }

    function buildDefaultRule(match = "any") {
        return {
            node_type: "group",
            match,
            children: [buildDefaultConditionNode()],
        };
    }

    function buildDefaultSubgroup() {
        return {
            node_type: "group",
            match: "all",
            children: [buildDefaultConditionNode()],
        };
    }

    function buildDefaultPreferences() {
        return {
            goal_weight: 0.35,
            utility_weight: 0.3,
            resource_weight: 0.2,
            risk_weight: 0.15,
            alpha: 1.0,
            current_up_value: 100.0,
            past_up_value: 85.0,
            normal_six_value: 70.0,
            five_star_value: 6.0,
            four_star_value: 1.0,
            utility_log_map: { low: 0.6, high: 1.4, curve: 1.0 },
            utility_absolute_log_map: { low: 0.6, high: 1.4, curve: 1.0 },
            utility_absolute_reference: 700.0,
            utility_mix_weight: 0.5,
            resource_log_map: { low: 0.6, high: 1.5, curve: 1.0 },
            opportunity_reference: 60.0,
            risk_utility_weight: 0.6,
            tail_ratio: 0.2,
            future_resource_income: 30,
            baseline_samples: 64,
            baseline_seed: 20260525,
            questionnaire_status: "pending",
            questionnaire_consistency_ratio: 0,
        };
    }

    const ADVANCED_GROUPS = [
        {
            title: "权重覆盖",
            description: "直接改问卷生成的四项权重。",
            fields: [
                ["goal_weight", "goal_weight", "目标达成权重"],
                ["utility_weight", "utility_weight", "期望收益权重"],
                ["resource_weight", "resource_weight", "资源机会权重"],
                ["risk_weight", "risk_weight", "风险稳定权重"],
            ],
        },
        {
            title: "收益与角色价值",
            description: "控制不同类型收益在评分中的基础价值。",
            fields: [
                ["alpha", "alpha", "目标曲线 alpha"],
                ["current_up_value", "current_up_value", "当期 UP 价值"],
                ["past_up_value", "past_up_value", "往期 UP 价值"],
                ["normal_six_value", "normal_six_value", "普通 6 星价值"],
                ["five_star_value", "five_star_value", "5 星价值"],
                ["four_star_value", "four_star_value", "4 星价值"],
                ["utility_absolute_reference", "utility_absolute_reference", "绝对收益参考值"],
                ["utility_mix_weight", "utility_mix_weight", "收益混合权重"],
            ],
        },
        {
            title: "映射曲线",
            description: "控制收益与资源倍率如何映射到分数。",
            fields: [
                ["utility_log_map.low", "utility_log_map.low", "收益映射低点"],
                ["utility_log_map.high", "utility_log_map.high", "收益映射高点"],
                ["utility_log_map.curve", "utility_log_map.curve", "收益映射曲线"],
                ["resource_log_map.low", "resource_log_map.low", "资源映射低点"],
                ["resource_log_map.high", "resource_log_map.high", "资源映射高点"],
                ["resource_log_map.curve", "resource_log_map.curve", "资源映射曲线"],
                ["opportunity_reference", "opportunity_reference", "资源机会参考值"],
            ],
        },
        {
            title: "风险与基准",
            description: "控制风险统计、未来资源和基准模拟设置。",
            fields: [
                ["risk_utility_weight", "risk_utility_weight", "风险中的收益权重"],
                ["tail_ratio", "tail_ratio", "低尾观察比例"],
                ["future_resource_income", "future_resource_income", "未来额外抽数"],
                ["baseline_samples", "baseline_samples", "基准采样数"],
                ["baseline_seed", "baseline_seed", "基准随机种子"],
            ],
        },
    ];

    global.EvalConstants = {
        ADVANCED_GROUPS,
        BOOLEAN_OPERATORS,
        CONDITION_FIELDS,
        GOAL_TYPES,
        MODULES,
        NUMERIC_OPERATORS,
        PAIRS,
        STATUS_LABELS,
        STEP_LABELS,
        STRENGTH_OPTIONS,
        buildDefaultConditionNode,
        buildDefaultPreferences,
        buildDefaultRule,
        buildDefaultSubgroup,
    };
}(window));
