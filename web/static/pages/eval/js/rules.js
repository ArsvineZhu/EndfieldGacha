(function assignEvalRules(global) {
    const {
        BOOLEAN_OPERATORS,
        CONDITION_FIELDS,
        GOAL_TYPES,
        NUMERIC_OPERATORS,
        buildDefaultConditionNode,
        buildDefaultRule,
        buildDefaultSubgroup,
    } = global.EvalConstants;

    function cloneRule(rule) {
        return {
            node_type: "group",
            match: rule.match || "any",
            children: (rule.children || []).map((child) => (
                child.node_type === "group" ? cloneRule(child) : { ...child }
            )),
        };
    }

    function normalizeRule(rule, legacyMatch = "any", legacyConditions = []) {
        if (rule && rule.node_type === "group") {
            return cloneRule(rule);
        }
        return {
            node_type: "group",
            match: legacyMatch,
            children: (legacyConditions || []).length
                ? legacyConditions.map((condition) => ({ node_type: "condition", ...condition }))
                : [buildDefaultConditionNode()],
        };
    }

    function createBannerPlan(configId) {
        return {
            config_name: configId,
            check_in: true,
            use_origeometry: false,
            is_core: true,
            resource_increment: {
                chartered_permits: 0,
                oroberyl: 0,
                arsenal_tickets: 0,
                origeometry: 0,
            },
            rule: buildDefaultRule(),
        };
    }

    function addRootCondition(rule) {
        rule.children.push(buildDefaultConditionNode());
    }

    function addSubgroup(rule) {
        rule.children.push(buildDefaultSubgroup());
    }

    function addSubCondition(rule, subgroupIndex) {
        const subgroup = rule.children[subgroupIndex];
        if (!subgroup || subgroup.node_type !== "group") {
            return;
        }
        subgroup.children.push(buildDefaultConditionNode());
    }

    function removeRootChild(rule, nodeIndex) {
        rule.children.splice(nodeIndex, 1);
        if (!rule.children.length) {
            rule.children.push(buildDefaultConditionNode());
        }
    }

    function removeSubCondition(rule, subgroupIndex, conditionIndex) {
        const subgroup = rule.children[subgroupIndex];
        if (!subgroup || subgroup.node_type !== "group") {
            return;
        }
        subgroup.children.splice(conditionIndex, 1);
        if (!subgroup.children.length) {
            subgroup.children.push(buildDefaultConditionNode());
        }
    }

    function updateRootMatch(rule, match) {
        rule.match = match;
    }

    function updateSubgroupMatch(rule, subgroupIndex, match) {
        const subgroup = rule.children[subgroupIndex];
        if (!subgroup || subgroup.node_type !== "group") {
            return;
        }
        subgroup.match = match;
    }

    function updateConditionNode(condition, field, value) {
        if (field === "kind") {
            condition.kind = value;
            const meta = CONDITION_FIELDS[value];
            condition.operator = meta.type === "boolean" ? "==" : ">=";
            condition.value = meta.type === "boolean" ? true : 1;
            return;
        }
        if (field === "operator") {
            condition.operator = value;
            return;
        }
        const meta = CONDITION_FIELDS[condition.kind];
        condition.value = meta.type === "boolean" ? value === "true" : readNumber(value);
    }

    function getOperatorsForCondition(condition) {
        return CONDITION_FIELDS[condition.kind].type === "boolean" ? BOOLEAN_OPERATORS : NUMERIC_OPERATORS;
    }

    function serializeRule(rule) {
        return {
            node_type: "group",
            match: rule.match,
            children: rule.children.map((child) => (
                child.node_type === "group"
                    ? {
                        node_type: "group",
                        match: child.match,
                        children: child.children.map((condition) => ({
                            node_type: "condition",
                            kind: condition.kind,
                            operator: condition.operator,
                            value: normalizeConditionValue(condition),
                        })),
                    }
                    : {
                        node_type: "condition",
                        kind: child.kind,
                        operator: child.operator,
                        value: normalizeConditionValue(child),
                    }
            )),
        };
    }

    function normalizeConditionValue(condition) {
        const meta = CONDITION_FIELDS[condition.kind];
        return meta.type === "boolean" ? Boolean(condition.value) : readNumber(condition.value);
    }

    function sanitizeGoal(goal) {
        const payload = { kind: goal.kind, target: readNumber(goal.target) };
        if (goal.kind === "character_count") {
            payload.character_name = (goal.character_name || "").trim();
        }
        if (goal.kind === "stage_paid_draws_at_most") {
            payload.stage_index = readNumber(goal.stage_index || 0);
        }
        return payload;
    }

    function resetGoalShape(goal) {
        delete goal.character_name;
        delete goal.stage_index;
        goal.target = 1;
    }

    function createDefaultGoal() {
        return { kind: "current_up", target: 1 };
    }

    function describeMatch(match) {
        return match === "all" ? "所有条件都触发才停" : "任一条件触发就停";
    }

    function goalNeedsStage(goal) {
        return GOAL_TYPES[goal.kind].mode === "stage";
    }

    function goalNeedsCharacter(goal) {
        return GOAL_TYPES[goal.kind].mode === "character";
    }

    function readNumber(value) {
        const number = Number(value);
        return Number.isFinite(number) ? number : 0;
    }

    global.EvalRules = {
        addRootCondition,
        addSubCondition,
        addSubgroup,
        cloneRule,
        createBannerPlan,
        createDefaultGoal,
        describeMatch,
        getOperatorsForCondition,
        goalNeedsCharacter,
        goalNeedsStage,
        normalizeConditionValue,
        normalizeRule,
        readNumber,
        removeRootChild,
        removeSubCondition,
        resetGoalShape,
        sanitizeGoal,
        serializeRule,
        updateConditionNode,
        updateRootMatch,
        updateSubgroupMatch,
    };
}(window));
