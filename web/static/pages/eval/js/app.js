(function bootstrapEvalPage(global) {
const {
    buildDefaultPreferences,
    PAIRS,
} = global.EvalConstants;
const {
    addRootCondition,
    addSubCondition,
    addSubgroup,
    createBannerPlan,
    createDefaultGoal,
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
} = global.EvalRules;
const {
    applyQuestionnaireWeights,
    createQuestionnaireState,
    saveQuestionnaireAnswer,
} = global.EvalQuestionnaire;
const { renderApp } = global.EvalRender;

const root = document.getElementById("root");

const state = {
    started: false,
    currentView: "intro",
    questionnaire: createQuestionnaireState(),
    preferences: buildDefaultPreferences(),
    resources: {
        chartered_permits: 2,
        oroberyl: 61000,
        arsenal_tickets: 6000,
        origeometry: 100,
    },
    initialCounters: {
        total: 0,
        no_6star: 0,
        no_5star_plus: 0,
        no_up: 0,
        guarantee_used: false,
        urgent_used: false,
    },
    scale: 2000,
    availableConfigs: [],
    bannerPlans: [],
    goals: [createDefaultGoal()],
    job: null,
    error: "",
    lastProgress: { from: 0, to: 0 },
};

let pollTimer = null;

document.addEventListener("DOMContentLoaded", init);

async function init() {
    bindEvents();
    await loadConfigs();
    render();
}

function bindEvents() {
    root.addEventListener("click", handleClick);
    root.addEventListener("change", handleChange);
    root.addEventListener("input", handleInput);
}

async function loadConfigs() {
    try {
        const response = await fetch("/api/eval/configs");
        const payload = await response.json();
        state.availableConfigs = payload.configs || [];
    } catch (error) {
        state.error = "加载卡池配置失败，请刷新页面后重试。";
        console.error(error);
    }
}

function render() {
    root.innerHTML = renderApp(state);
    postRenderEffects();
}

function postRenderEffects() {
    const progress = root.querySelector("[data-progress-value='true']");
    if (progress) {
        const from = Number(progress.dataset.progressFrom || "0");
        const to = Number(progress.dataset.progressTo || "0");
        progress.style.width = `${from * 100}%`;
        requestAnimationFrame(() => {
            progress.style.width = `${to * 100}%`;
        });
    }
    const questionBlock = root.querySelector("[data-question-block='true']");
    if (questionBlock) {
        requestAnimationFrame(() => questionBlock.classList.add("is-visible"));
    }
}

function handleClick(event) {
    const target = event.target.closest("[data-action]");
    if (!target) {
        return;
    }
    const action = target.dataset.action;

    if (action === "start-questionnaire") {
        state.started = true;
        state.currentView = "questionnaire";
        state.error = "";
        render();
        return;
    }

    if (action === "go-intro") {
        state.currentView = "intro";
        state.error = "";
        render();
        return;
    }

    if (action === "go-setup") {
        state.currentView = "setup";
        state.error = "";
        render();
        return;
    }

    if (action === "go-banners") {
        state.currentView = "banners";
        state.error = "";
        render();
        return;
    }

    if (action === "go-goals") {
        state.currentView = "goals";
        state.error = "";
        render();
        return;
    }

    if (action === "go-submit") {
        state.currentView = "submit";
        state.error = "";
        render();
        return;
    }

    if (action === "go-result" && state.job) {
        state.currentView = "result";
        state.error = "";
        render();
        return;
    }

    if (action === "open-advanced") {
        state.currentView = "advanced";
        state.error = "";
        render();
        return;
    }

    if (action === "back-to-questionnaire-result") {
        state.currentView = "questionnaire_result";
        state.error = "";
        render();
        return;
    }

    if (action === "direction") {
        selectDirection(target.dataset.choice);
        return;
    }

    if (action === "strength") {
        selectStrength(Number(target.dataset.value));
        return;
    }

    if (action === "reset-questionnaire") {
        state.questionnaire = createQuestionnaireState();
        state.preferences = buildDefaultPreferences();
        state.currentView = "questionnaire";
        state.lastProgress = { from: 0, to: 0 };
        render();
        return;
    }

    if (action === "add-banner") {
        addBannerPlan(target.dataset.configId);
        return;
    }

    if (action === "move-banner") {
        moveBannerPlan(Number(target.dataset.index), Number(target.dataset.delta));
        return;
    }

    if (action === "remove-banner") {
        state.bannerPlans.splice(Number(target.dataset.index), 1);
        render();
        return;
    }

    if (action === "add-root-condition") {
        addRootCondition(state.bannerPlans[Number(target.dataset.planIndex)].rule);
        render();
        return;
    }

    if (action === "add-subgroup") {
        addSubgroup(state.bannerPlans[Number(target.dataset.planIndex)].rule);
        render();
        return;
    }

    if (action === "add-sub-condition") {
        addSubCondition(
            state.bannerPlans[Number(target.dataset.planIndex)].rule,
            Number(target.dataset.groupIndex),
        );
        render();
        return;
    }

    if (action === "remove-root-child") {
        removeRootChild(state.bannerPlans[Number(target.dataset.planIndex)].rule, Number(target.dataset.nodeIndex));
        render();
        return;
    }

    if (action === "remove-sub-condition") {
        removeSubCondition(
            state.bannerPlans[Number(target.dataset.planIndex)].rule,
            Number(target.dataset.groupIndex),
            Number(target.dataset.nodeIndex),
        );
        render();
        return;
    }

    if (action === "add-goal") {
        state.goals.push(createDefaultGoal());
        render();
        return;
    }

    if (action === "remove-goal") {
        state.goals.splice(Number(target.dataset.goalIndex), 1);
        if (!state.goals.length) {
            state.goals.push(createDefaultGoal());
        }
        render();
        return;
    }

    if (action === "submit-eval") {
        submitEvaluation();
    }
}

function handleChange(event) {
    const target = event.target;

    if (target.dataset.scaleInput !== undefined) {
        state.scale = Math.max(1, Math.min(20000, readNumber(target.value)));
        return;
    }

    if (target.dataset.prefKey) {
        setPreferenceValue(target.dataset.prefKey, target.value);
        return;
    }

    if (target.dataset.resourceKey) {
        state.resources[target.dataset.resourceKey] = readNumber(target.value);
        return;
    }

    if (target.dataset.counterKey) {
        state.initialCounters[target.dataset.counterKey] = target.type === "checkbox"
            ? target.checked
            : readNumber(target.value);
        return;
    }

    if (target.dataset.planIndex && target.dataset.planField) {
        const plan = state.bannerPlans[Number(target.dataset.planIndex)];
        plan[target.dataset.planField] = target.type === "checkbox" ? target.checked : target.value;
        return;
    }

    if (target.dataset.planIndex && target.dataset.resourceField) {
        const plan = state.bannerPlans[Number(target.dataset.planIndex)];
        plan.resource_increment[target.dataset.resourceField] = readNumber(target.value);
        return;
    }

    if (target.dataset.rootMatch !== undefined) {
        updateRootMatch(state.bannerPlans[Number(target.dataset.rootMatch)].rule, target.value);
        render();
        return;
    }

    if (target.dataset.groupMatch !== undefined) {
        updateSubgroupMatch(
            state.bannerPlans[Number(target.dataset.groupMatch)].rule,
            Number(target.dataset.groupIndex),
            target.value,
        );
        render();
        return;
    }

    if (target.dataset.conditionField) {
        updateConditionFromTarget(target);
        render();
        return;
    }

    if (target.dataset.goalIndex) {
        updateGoalField(target);
        render();
    }
}

function handleInput(event) {
    handleChange(event);
}

function selectDirection(choice) {
    if (choice === "equal") {
        saveAnswer("equal", 1);
        return;
    }
    state.questionnaire.pendingDirection = choice;
    state.questionnaire.step = "strength";
    render();
}

function selectStrength(value) {
    saveAnswer(state.questionnaire.pendingDirection, value);
}

function saveAnswer(direction, strength) {
    const from = state.questionnaire.pairIndex / PAIRS.length;
    saveQuestionnaireAnswer(state.questionnaire, direction, strength);
    applyQuestionnaireWeights(state.questionnaire, state.preferences);
    const to = Math.min(state.questionnaire.pairIndex / PAIRS.length, 1);
    state.lastProgress = { from, to };
    if (state.questionnaire.pairIndex >= PAIRS.length) {
        state.currentView = "questionnaire_result";
    }
    render();
}

function addBannerPlan(configId) {
    if (!configId || state.bannerPlans.some((plan) => plan.config_name === configId)) {
        return;
    }
    state.bannerPlans.push(createBannerPlan(configId));
    render();
}

function moveBannerPlan(index, delta) {
    const nextIndex = index + delta;
    if (nextIndex < 0 || nextIndex >= state.bannerPlans.length) {
        return;
    }
    const [item] = state.bannerPlans.splice(index, 1);
    state.bannerPlans.splice(nextIndex, 0, item);
    render();
}

function updateConditionFromTarget(target) {
    const plan = state.bannerPlans[Number(target.dataset.planIndex)];
    const parentKind = target.dataset.parentKind;
    let condition;
    if (parentKind === "root") {
        condition = plan.rule.children[Number(target.dataset.nodeIndex)];
    } else {
        condition = plan.rule.children[Number(target.dataset.groupIndex)].children[Number(target.dataset.nodeIndex)];
    }
    updateConditionNode(condition, target.dataset.conditionField, target.value);
}

function updateGoalField(target) {
    const goal = state.goals[Number(target.dataset.goalIndex)];
    const field = target.dataset.goalField;
    if (field === "kind") {
        goal.kind = target.value;
        resetGoalShape(goal);
        return;
    }
    if (field === "target") {
        goal.target = readNumber(target.value);
        return;
    }
    if (field === "character_name") {
        goal.character_name = target.value;
        return;
    }
    if (field === "stage_index") {
        goal.stage_index = readNumber(target.value);
    }
}

async function submitEvaluation() {
    state.error = "";
    if (state.questionnaire.pairIndex < PAIRS.length) {
        state.error = "请先完成问卷。";
        state.currentView = "questionnaire";
        render();
        return;
    }
    if (!state.bannerPlans.length) {
        state.error = "请至少加入一个卡池阶段。";
        state.currentView = "banners";
        render();
        return;
    }
    if (!state.goals.length) {
        state.error = "请至少设置一个目标。";
        state.currentView = "goals";
        render();
        return;
    }

    try {
        const response = await fetch("/api/eval/jobs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(buildPayload()),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "提交评估任务失败");
        }
        state.job = data;
        state.currentView = "result";
        startPolling(data.job_id);
        render();
    } catch (error) {
        state.error = error.message;
        render();
    }
}

function buildPayload() {
    return {
        resource: state.resources,
        initial_counters: state.initialCounters,
        preferences: buildPreferencesPayload(),
        goals: state.goals.map((goal) => sanitizeGoal(goal)),
        banner_plans: state.bannerPlans.map((plan) => ({
            config_name: plan.config_name,
            strategy: {
                protocol_version: "strategy-protocol-v1",
                kind: "structured",
                rule: serializeRule(normalizeRule(plan.rule)),
            },
            resource_increment: plan.resource_increment,
            check_in: plan.check_in,
            use_origeometry: plan.use_origeometry,
            is_core: true,
        })),
        scale: state.scale,
    };
}

function buildPreferencesPayload() {
    return {
        goal_weight: Number(state.preferences.goal_weight),
        utility_weight: Number(state.preferences.utility_weight),
        resource_weight: Number(state.preferences.resource_weight),
        risk_weight: Number(state.preferences.risk_weight),
        alpha: Number(state.preferences.alpha),
        current_up_value: Number(state.preferences.current_up_value),
        past_up_value: Number(state.preferences.past_up_value),
        normal_six_value: Number(state.preferences.normal_six_value),
        five_star_value: Number(state.preferences.five_star_value),
        four_star_value: Number(state.preferences.four_star_value),
        utility_log_map: {
            low: Number(state.preferences.utility_log_map.low),
            high: Number(state.preferences.utility_log_map.high),
            curve: Number(state.preferences.utility_log_map.curve),
        },
        utility_absolute_log_map: {
            low: Number(state.preferences.utility_absolute_log_map.low),
            high: Number(state.preferences.utility_absolute_log_map.high),
            curve: Number(state.preferences.utility_absolute_log_map.curve),
        },
        utility_absolute_reference: Number(state.preferences.utility_absolute_reference),
        utility_mix_weight: Number(state.preferences.utility_mix_weight),
        resource_log_map: {
            low: Number(state.preferences.resource_log_map.low),
            high: Number(state.preferences.resource_log_map.high),
            curve: Number(state.preferences.resource_log_map.curve),
        },
        opportunity_reference: Number(state.preferences.opportunity_reference),
        risk_utility_weight: Number(state.preferences.risk_utility_weight),
        tail_ratio: Number(state.preferences.tail_ratio),
        future_resource_income: Number(state.preferences.future_resource_income),
        baseline_samples: Number(state.preferences.baseline_samples),
        baseline_seed: Number(state.preferences.baseline_seed),
        questionnaire_status: state.preferences.questionnaire_status,
    };
}

function startPolling(jobId) {
    stopPolling();
    pollTimer = window.setInterval(async () => {
        try {
            const response = await fetch(`/api/eval/jobs/${jobId}`);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "轮询任务失败");
            }
            state.job = data;
            render();
            if (data.status === "succeeded" || data.status === "failed") {
                stopPolling();
            }
        } catch (error) {
            state.error = error.message;
            stopPolling();
            render();
        }
    }, 1500);
}

function stopPolling() {
    if (pollTimer !== null) {
        window.clearInterval(pollTimer);
        pollTimer = null;
    }
}

function setPreferenceValue(path, value) {
    const segments = path.split(".");
    let cursor = state.preferences;
    while (segments.length > 1) {
        cursor = cursor[segments.shift()];
    }
    cursor[segments[0]] = Number(value);
}

}(window));
