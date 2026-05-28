(function assignEvalRender(global) {
    const {
        ADVANCED_GROUPS,
        BOOLEAN_OPERATORS,
        CONDITION_FIELDS,
        GOAL_TYPES,
        MODULES,
        PAIRS,
        STATUS_LABELS,
        STEP_LABELS,
        STRENGTH_OPTIONS,
    } = global.EvalConstants;
    const {
        describeMatch,
        getOperatorsForCondition,
        goalNeedsCharacter,
        goalNeedsStage,
    } = global.EvalRules;
    const {
        getConsistencyHint,
        getCurrentPair,
        getQuestionnaireProgress,
    } = global.EvalQuestionnaire;

    const outputScore = String(Math.floor(Math.random() * 40) + 60).padStart(2, "0");

    function renderApp(state) {
        return `
        <div class="eval-shell">
            <div class="eval-orbit eval-orbit-a"></div>
            <div class="eval-orbit eval-orbit-b"></div>
            <div class="eval-halo eval-halo-a"></div>
            <div class="eval-halo eval-halo-b"></div>
            <div class="eval-grain"></div>
            <header class="eval-topbar">
                <div class="eval-topbar-inner">
                    <div class="eval-title-block">
                        <span class="eval-kicker">终末地策略评估</span>
                        <h1>跨卡池方案评估器</h1>
                    </div>
                    <a class="eval-link" href="/gacha">前往 /gacha</a>
                </div>
            </header>
            <main class="eval-main">
                <div class="eval-stage-shell">
                    <div class="eval-stage-rail">${renderStageRail(state)}</div>
                    ${renderCurrentView(state)}
                    ${state.error ? `<div class="eval-error">${escapeHtml(state.error)}</div>` : ""}
                </div>
            </main>
        </div>
    `;
    }

    function renderStageRail(state) {
        const steps = [
            "intro",
            "questionnaire",
            "questionnaire_result",
            "setup",
            "banners",
            "goals",
            "submit",
        ];
        if (state.job) {
            steps.push("result");
        }
        return steps
            .map((step) => `<span class="eval-rail-chip ${step === state.currentView ? "is-active" : ""}">${escapeHtml(STEP_LABELS[step])}</span>`)
            .join("");
    }

    function renderCurrentView(state) {
        switch (state.currentView) {
            case "intro":
                return renderIntro(state);
            case "questionnaire":
                return renderQuestionnaire(state);
            case "questionnaire_result":
                return renderQuestionnaireResult(state);
            case "advanced":
                return renderAdvanced(state);
            case "setup":
                return renderSetup(state);
            case "banners":
                return renderBanners(state);
            case "goals":
                return renderGoals(state);
            case "submit":
                return renderSubmit(state);
            case "result":
                return renderResult(state);
            default:
                return renderIntro(state);
        }
    }

    function renderIntro(state) {
        return `
        <section class="eval-stage eval-stage-intro">
            <div class="eval-hero-grid">
                <div class="eval-hero-copy">
                    <div class="eval-section-tag">系统用途</div>
                    <h2>在一条轨道中，<br>评估你的多卡池规划。</h2>
                    <p class="eval-copy">
                        这里评估的不是单次手气，而是一整套跨卡池方案。你会先做几道取舍题，让系统理解你更看重“目标能不能成”、“平均收益高不高”、“要不要留资源”，还是“结果够不够稳”。
                    </p>
                    <p class="eval-copy">
                        问卷结束后会先生成一份偏好结果：你可以直接继续，也可以手动改高级设置，再去配置卡池阶段、停止条件和评分目标。
                    </p>
                    <div class="eval-scroll-hint" data-action="start-questionnaire">
                        <span>向下滚动进入</span>
                        <svg class="eval-scroll-icon" viewBox="0 0 20 20" fill="none">
                            <path d="M10 3v14M5 12l5 5 5-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                </div>
                <div class="eval-hero-side">
                    <div class="eval-hero-metric">
                        <span class="label">卡池阶段</span>
                        <span class="value">${String(state.availableConfigs.length).padStart(2, "0")}</span>
                    </div>
                    <div class="eval-hero-metric">
                        <span class="label">问卷题组</span>
                        <span class="value">${String(PAIRS.length).padStart(2, "0")}</span>
                    </div>
                    <div class="eval-hero-metric">
                        <span class="label">输出结果</span>
                        <span class="value" data-output-score="true">${outputScore}</span>
                    </div>
                </div>
            </div>
        </section>
    `;
    }

    function renderQuestionnaire(state) {
        const completed = state.questionnaire.pairIndex >= PAIRS.length;
        if (completed && !state.questionnaire.in_review) {
            return renderQuestionnaireResult(state);
        }
        const pair = getCurrentPair(state.questionnaire);
        const progress = getQuestionnaireProgress(state.questionnaire);
        const totalCount = state.questionnaire.in_review ? Math.max(1, state.questionnaire.review_pairs.length) : PAIRS.length;
        const currentCount = state.questionnaire.in_review ? state.questionnaire.review_cursor + 1 : state.questionnaire.pairIndex + 1;
        const title = state.questionnaire.in_review ? "冲突复核" : "取舍问卷";
        const description = state.questionnaire.in_review
            ? "你的取舍存在冲突，请重答冲突最大的两组比较后再继续。"
            : "系统会通过 6 组取舍题，判断你更看重哪类结果。";
        return `
        <section class="eval-stage">
            ${renderSectionHead(title, description, [
            button("返回引导", "go-intro"),
        ])}
            <div class="eval-progress-row">
                <div class="eval-progress-bar">
                    <div class="eval-progress-value" data-progress-value="true" data-progress-from="${state.lastProgress.from}" data-progress-to="${progress}"></div>
                </div>
                <span class="eval-progress-count">${currentCount} / ${totalCount}</span>
            </div>
            <div class="eval-question-block" data-question-block="true">
                ${renderCurrentQuestion(state, pair)}
            </div>
        </section>
    `;
    }

    function renderCurrentQuestion(state, pair) {
        const [left, right] = pair;
        const directionPrompt = state.questionnaire.in_review
            ? "请重新确认这组冲突取舍，你更不能牺牲哪一项？"
            : "如果两者不能兼得，你更不能牺牲哪一项？";
        const strengthPrompt = state.questionnaire.in_review
            ? "请确认这次复核中的偏向强度。"
            : "你对这项偏向有多强？";
        if (state.questionnaire.step === "direction") {
            return `
            <p class="eval-question-lead">${directionPrompt}</p>
            <div class="eval-question-pair">
                ${renderModulePanel(left, true)}
                <div class="eval-vs">取舍</div>
                ${renderModulePanel(right, true)}
            </div>
            <div class="eval-choice-grid">
                <button class="eval-choice-card" data-action="direction" data-choice="${left}">
                    <strong>${escapeHtml(MODULES[left].label)}</strong>
                    <span>${escapeHtml(MODULES[left].impact)}</span>
                </button>
                <button class="eval-choice-card" data-action="direction" data-choice="equal">
                    <strong>同等重要</strong>
                    <span>这两项对你来说暂时不分先后。</span>
                </button>
                <button class="eval-choice-card" data-action="direction" data-choice="${right}">
                    <strong>${escapeHtml(MODULES[right].label)}</strong>
                    <span>${escapeHtml(MODULES[right].impact)}</span>
                </button>
            </div>
        `;
        }

        const chosen = state.questionnaire.pendingDirection;
        const other = chosen === left ? right : left;
        return `
        <p class="eval-question-lead">${strengthPrompt}</p>
        <div class="eval-question-pair">
            ${renderModulePanel(chosen, true)}
            <div class="eval-vs">强度</div>
            ${renderModulePanel(other, false)}
        </div>
        <div class="eval-choice-grid eval-choice-grid-strength">
            ${STRENGTH_OPTIONS.map((option) => `
                <button class="eval-choice-card" data-action="strength" data-value="${option.value}">
                    <strong>${escapeHtml(option.label)}</strong>
                    <span>${escapeHtml(option.hint)}</span>
                </button>
            `).join("")}
        </div>
    `;
    }

    function renderQuestionnaireResult(state) {
        const ratio = state.preferences.questionnaire_consistency_ratio;
        return `
        <section class="eval-stage">
            ${renderSectionHead("问卷结果", "系统已经根据你的取舍，生成了本次评分偏好。", [
            button("重做问卷", "reset-questionnaire"),
            button("调整高级设置", "open-advanced"),
            button("继续配置", "go-setup", true),
        ])}
            <div class="eval-result-grid">
                ${renderWeightMetric("目标达成", state.preferences.goal_weight, MODULES.goal.summary)}
                ${renderWeightMetric("期望收益", state.preferences.utility_weight, MODULES.utility.summary)}
                ${renderWeightMetric("资源机会", state.preferences.resource_weight, MODULES.resource.summary)}
                ${renderWeightMetric("风险稳定", state.preferences.risk_weight, MODULES.risk.summary)}
            </div>
            <div class="eval-summary-panel">
                <p class="eval-summary-title">这组结果会直接影响最终评分。</p>
                <p class="eval-copy">一致性 CR：${formatNumber(ratio, 4)}。${escapeHtml(getConsistencyHint(ratio, state.preferences.questionnaire_status))}</p>
                <ul class="eval-bullet-list">
                    ${Object.values(MODULES).map((module) => `<li><strong>${escapeHtml(module.label)}</strong>：${escapeHtml(module.impact)}</li>`).join("")}
                </ul>
            </div>
        </section>
    `;
    }

    function renderAdvanced(state) {
        return `
        <section class="eval-stage">
            ${renderSectionHead("高级设置", "只有在你想手动覆盖问卷结果时，才需要修改这些数值。", [
            button("返回问卷结果", "back-to-questionnaire-result"),
            button("继续配置", "go-setup", true),
        ])}
            <div class="eval-advanced-grid">
                ${ADVANCED_GROUPS.map((group) => `
                    <section class="eval-panel">
                        <h3>${escapeHtml(group.title)}</h3>
                        <p class="eval-note">${escapeHtml(group.description)}</p>
                        <div class="eval-form-grid">
                            ${group.fields.map(([path, key, label]) => renderPrefInput(state, path, key, label)).join("")}
                        </div>
                    </section>
                `).join("")}
            </div>
        </section>
    `;
    }

    function renderSetup(state) {
        return `
        <section class="eval-stage">
            ${renderSectionHead("全局设置", "先把初始资源、保底状态和模拟次数定下来。", [
            button("返回问卷结果", "back-to-questionnaire-result"),
            button("继续到卡池阶段", "go-banners", true),
        ])}
            <div class="eval-form-grid eval-form-grid-wide">
                ${renderNumberField("初始特许寻访凭证", "chartered_permits", state.resources.chartered_permits, "resource-key")}
                ${renderNumberField("初始嵌晶玉", "oroberyl", state.resources.oroberyl, "resource-key")}
                ${renderNumberField("初始武库配额", "arsenal_tickets", state.resources.arsenal_tickets, "resource-key")}
                ${renderNumberField("初始衍质源石", "origeometry", state.resources.origeometry, "resource-key")}
                ${renderNumberField("初始总抽数", "total", state.initialCounters.total, "counter-key")}
                ${renderNumberField("初始 6 星保底计数", "no_6star", state.initialCounters.no_6star, "counter-key")}
                ${renderNumberField("初始 5 星保底计数", "no_5star_plus", state.initialCounters.no_5star_plus, "counter-key")}
                ${renderNumberField("初始 UP 保底计数", "no_up", state.initialCounters.no_up, "counter-key")}
                <label class="eval-check-field">
                    <input type="checkbox" ${state.initialCounters.guarantee_used ? "checked" : ""} data-counter-key="guarantee_used">
                    <span>已使用 UP 保底</span>
                </label>
                <label class="eval-check-field">
                    <input type="checkbox" ${state.initialCounters.urgent_used ? "checked" : ""} data-counter-key="urgent_used">
                    <span>已触发加急</span>
                </label>
                <div class="eval-field">
                    <label>模拟次数</label>
                    <input class="eval-input" type="number" min="1" max="20000" value="${state.scale}" data-scale-input="true">
                </div>
            </div>
        </section>
    `;
    }

    function renderBanners(state) {
        return `
        <section class="eval-stage">
            ${renderSectionHead("卡池阶段", "从已有卡池中加入阶段，并为每个阶段写出自己的停止条件。", [
            button("返回全局设置", "go-setup"),
            button("继续到目标", "go-goals", true),
        ])}
            <div class="eval-banner-layout">
                <div class="eval-banner-picker">
                    ${state.availableConfigs.map((config) => {
            const selected = state.bannerPlans.some((plan) => plan.config_name === config.id);
            return `
                            <article class="eval-panel eval-banner-option">
                                <h3>${escapeHtml(config.pool_name)}</h3>
                                <p class="eval-note">${escapeHtml(config.id)} · ${escapeHtml(config.open_time || "未填写开放时间")}</p>
                                <p class="eval-copy eval-copy-compact">当期 UP：${escapeHtml((config.current_up || []).join(" / ") || "无")}</p>
                                <p class="eval-copy eval-copy-compact">往期 UP：${escapeHtml((config.past_up || []).join(" / ") || "无")}</p>
                                <div class="eval-actions">
                                    <button class="eval-btn ${selected ? "" : "primary"}" data-action="add-banner" data-config-id="${config.id}" ${selected ? "disabled" : ""}>
                                        ${selected ? "已加入" : "加入方案"}
                                    </button>
                                </div>
                            </article>
                        `;
        }).join("")}
                </div>
                <div class="eval-stage-list">
                    ${state.bannerPlans.length
                ? state.bannerPlans.map((plan, index) => renderBannerStage(state, plan, index)).join("")
                : `<div class="eval-panel"><p class="eval-copy">还没有加入卡池阶段。</p></div>`}
                </div>
            </div>
        </section>
    `;
    }

    function renderBannerStage(state, plan, index) {
        const config = state.availableConfigs.find((item) => item.id === plan.config_name);
        const rule = plan.rule;
        return `
        <article class="eval-panel eval-banner-stage">
            <div class="eval-banner-head">
                <div>
                    <div class="eval-section-tag">阶段 ${index + 1}</div>
                    <h3>${escapeHtml(config ? config.pool_name : plan.config_name)}</h3>
                    <p class="eval-note">${escapeHtml(plan.config_name)}</p>
                </div>
                <div class="eval-inline-actions">
                    <button class="eval-icon-btn" data-action="move-banner" data-index="${index}" data-delta="-1" ${index === 0 ? "disabled" : ""}>↑</button>
                    <button class="eval-icon-btn" data-action="move-banner" data-index="${index}" data-delta="1" ${index === state.bannerPlans.length - 1 ? "disabled" : ""}>↓</button>
                    <button class="eval-btn danger" data-action="remove-banner" data-index="${index}">移除</button>
                </div>
            </div>
            <div class="eval-banner-grid">
                <section class="eval-subpanel eval-subpanel-resource">
                    <h4>阶段资源与补给</h4>
                    <div class="eval-form-grid">
                        <label class="eval-check-field">
                            <input type="checkbox" ${plan.check_in ? "checked" : ""} data-plan-index="${index}" data-plan-field="check_in">
                            <span>启用签到补给</span>
                        </label>
                        <label class="eval-check-field">
                            <input type="checkbox" ${plan.use_origeometry ? "checked" : ""} data-plan-index="${index}" data-plan-field="use_origeometry">
                            <span>允许消耗源石</span>
                        </label>
                        ${renderPlanResourceField(index, "chartered_permits", "特许寻访凭证", plan.resource_increment.chartered_permits)}
                        ${renderPlanResourceField(index, "oroberyl", "嵌晶玉", plan.resource_increment.oroberyl)}
                        ${renderPlanResourceField(index, "arsenal_tickets", "武库配额", plan.resource_increment.arsenal_tickets)}
                        ${renderPlanResourceField(index, "origeometry", "衍质源石", plan.resource_increment.origeometry)}
                    </div>
                </section>
                <section class="eval-subpanel eval-subpanel-rule">
                    <div class="eval-result-head">
                        <div>
                            <h4>停止条件</h4>
                            <p class="eval-note">${escapeHtml(describeMatch(rule.match))}</p>
                        </div>
                        <div class="eval-inline-actions">
                            <button class="eval-btn" data-action="add-root-condition" data-plan-index="${index}">添加条件</button>
                            <button class="eval-btn" data-action="add-subgroup" data-plan-index="${index}">添加子组</button>
                        </div>
                    </div>
                    ${renderRuleGroup(index, rule, true)}
                </section>
            </div>
        </article>
    `;
    }

    function renderRuleGroup(planIndex, group, isRoot, groupIndex = -1) {
        return `
        <div class="eval-rule-group ${isRoot ? "is-root" : ""}">
            <div class="eval-rule-group-head">
                <label class="eval-field eval-field-inline">
                    <span>${isRoot ? "根组逻辑" : "子组逻辑"}</span>
                    <select class="eval-select"
                        ${isRoot ? `data-root-match="${planIndex}"` : `data-group-match="${planIndex}" data-group-index="${groupIndex}"`}>
                        <option value="all" ${group.match === "all" ? "selected" : ""}>全部满足</option>
                        <option value="any" ${group.match === "any" ? "selected" : ""}>任一满足</option>
                    </select>
                </label>
                ${isRoot ? "" : `<button class="eval-btn danger" data-action="remove-root-child" data-plan-index="${planIndex}" data-node-index="${groupIndex}">移除子组</button>`}
            </div>
            <div class="eval-rule-children">
                ${group.children.map((child, index) => (
            child.node_type === "group"
                ? renderRuleGroup(planIndex, child, false, index)
                : renderConditionRow(planIndex, child, isRoot ? "root" : "sub", index, groupIndex)
        )).join("")}
            </div>
            ${isRoot ? "" : `
                <div class="eval-actions">
                    <button class="eval-btn" data-action="add-sub-condition" data-plan-index="${planIndex}" data-group-index="${groupIndex}">在子组里添加条件</button>
                </div>
            `}
        </div>
    `;
    }

    function renderConditionRow(planIndex, condition, parentKind, conditionIndex, groupIndex) {
        const fieldMeta = CONDITION_FIELDS[condition.kind];
        const operators = getOperatorsForCondition(condition);
        const attrs = parentKind === "root"
            ? `data-plan-index="${planIndex}" data-parent-kind="root" data-node-index="${conditionIndex}"`
            : `data-plan-index="${planIndex}" data-parent-kind="sub" data-group-index="${groupIndex}" data-node-index="${conditionIndex}"`;
        return `
        <div class="eval-condition-row">
            <select class="eval-select" ${attrs} data-condition-field="kind">
                ${Object.entries(CONDITION_FIELDS).map(([key, meta]) => `
                    <option value="${key}" ${condition.kind === key ? "selected" : ""}>${escapeHtml(meta.label)}</option>
                `).join("")}
            </select>
            <select class="eval-select" ${attrs} data-condition-field="operator">
                ${operators.map((operator) => `<option value="${operator}" ${condition.operator === operator ? "selected" : ""}>${operator}</option>`).join("")}
            </select>
            ${fieldMeta.type === "boolean"
                ? `
                    <select class="eval-select" ${attrs} data-condition-field="value">
                        <option value="true" ${condition.value === true ? "selected" : ""}>是</option>
                        <option value="false" ${condition.value === false ? "selected" : ""}>否</option>
                    </select>
                `
                : `<input class="eval-input" type="number" value="${condition.value}" ${attrs} data-condition-field="value">`
            }
            <button class="eval-btn danger"
                data-action="${parentKind === "root" ? "remove-root-child" : "remove-sub-condition"}"
                data-plan-index="${planIndex}"
                ${parentKind === "root" ? `data-node-index="${conditionIndex}"` : `data-group-index="${groupIndex}" data-node-index="${conditionIndex}"`}>
                删除
            </button>
        </div>
    `;
    }

    function renderGoals(state) {
        return `
        <section class="eval-stage">
            ${renderSectionHead("评分目标", "这些目标会一起判断；只有全部满足，才算这次目标完成。", [
            button("返回卡池阶段", "go-banners"),
            button("继续到提交", "go-submit", true),
            button("添加目标", "add-goal"),
        ])}
            <div class="eval-goal-list">
                ${state.goals.map((goal, index) => renderGoalRow(state, goal, index)).join("")}
            </div>
        </section>
    `;
    }

    function renderGoalRow(state, goal, index) {
        return `
        <div class="eval-panel eval-goal-row">
            <select class="eval-select" data-goal-index="${index}" data-goal-field="kind">
                ${Object.entries(GOAL_TYPES).map(([key, item]) => `<option value="${key}" ${goal.kind === key ? "selected" : ""}>${escapeHtml(item.label)}</option>`).join("")}
            </select>
            ${goalNeedsCharacter(goal)
                ? `<input class="eval-input" type="text" placeholder="角色名称" value="${escapeHtml(goal.character_name || "")}" data-goal-index="${index}" data-goal-field="character_name">`
                : ""}
            ${goalNeedsStage(goal)
                ? `<select class="eval-select" data-goal-index="${index}" data-goal-field="stage_index">
                    ${state.bannerPlans.map((plan, planIndex) => {
                    const config = state.availableConfigs.find((item) => item.id === plan.config_name);
                    const label = config ? config.pool_name : plan.config_name;
                    return `<option value="${planIndex}" ${Number(goal.stage_index || 0) === planIndex ? "selected" : ""}>阶段 ${planIndex + 1} - ${escapeHtml(label)}</option>`;
                }).join("")}
                </select>`
                : ""}
            <input class="eval-input" type="number" value="${goal.target}" data-goal-index="${index}" data-goal-field="target">
            <button class="eval-btn danger" data-action="remove-goal" data-goal-index="${index}">删除</button>
        </div>
    `;
    }

    function renderSubmit(state) {
        return `
        <section class="eval-stage">
            ${renderSectionHead("提交评估", "确认前面的配置后，就可以把这套跨卡池方案送去评估。", [
            button("返回目标", "go-goals"),
            state.job ? button("查看结果", "go-result") : "",
        ])}
            <div class="eval-panel eval-submit-panel">
                <p class="eval-copy">服务端一次只评估一套整体方案，默认最多并行处理 2 个任务，其余会自动排队。</p>
                <div class="eval-actions">
                    <button class="eval-btn primary" data-action="submit-eval">提交评估任务</button>
                </div>
            </div>
        </section>
    `;
    }

    function renderResult(state) {
        if (!state.job) {
            return `
            <section class="eval-stage">
                ${renderSectionHead("评估结果", "任务提交后，这里会显示排队状态、评估进度和最终得分。", [
                button("返回提交", "go-submit"),
            ])}
            </section>
        `;
        }
        const result = state.job.result;
        return `
        <section class="eval-stage">
            ${renderSectionHead("评估结果", "这是一整套跨卡池方案在当前偏好下的评分结果。", [
            button("返回提交", "go-submit"),
        ], `<span class="eval-status-badge ${state.job.status}">${STATUS_LABELS[state.job.status] || state.job.status}</span>`)}
            <div class="eval-panel eval-result-meta">
                <p class="eval-note">任务 ID：${escapeHtml(state.job.job_id)}${state.job.status === "queued" ? ` · 排队位置：${state.job.queue_position}` : ""}</p>
                ${state.job.error ? `<div class="eval-error">${escapeHtml(state.job.error)}</div>` : ""}
            </div>
            ${result ? `
                ${renderResultHero(result)}
                <div class="eval-result-detail-block">
                    <div class="eval-result-highlight-metrics eval-result-highlight-metrics-secondary">
                        ${renderResultAccent("目标完成率", result.goal_completion_rate)}
                        ${renderResultAccent("收益倍率", result.utility_ratio)}
                        ${renderResultAccent("资源倍率", result.opportunity_ratio)}
                        ${renderResultAccent("模拟次数", result.simulations)}
                    </div>
                    <div class="eval-result-grid">
                        ${renderResultMetric("平均实际收益", result.mean_utility)}
                        ${renderResultMetric("平均基准收益", result.mean_baseline)}
                        ${renderResultMetric("平均资源机会", result.mean_opportunity)}
                        ${renderResultMetric("低尾风险均值", result.tail_risk_mean)}
                        ${renderResultMetric("评分版本", result.scoring_version)}
                    </div>
                </div>
            ` : `<div class="eval-panel"><p class="eval-copy">任务已提交，正在等待结果。</p></div>`}
        </section>
    `;
    }

    function renderSectionHead(title, description, actions, extra = "") {
        return `
        <div class="eval-stage-head">
            <div>
                <div class="eval-section-tag">${escapeHtml(title)}</div>
                <h2>${escapeHtml(title)}</h2>
                <p class="eval-copy">${escapeHtml(description)}</p>
            </div>
            <div class="eval-stage-nav">
                ${extra}
                ${actions.filter(Boolean).join("")}
            </div>
        </div>
    `;
    }

    function renderModulePanel(key, emphasize) {
        const module = MODULES[key];
        return `
        <article class="eval-module-panel ${emphasize ? "is-emphasized" : ""}">
            <h3>${escapeHtml(module.label)}</h3>
            <p class="eval-copy eval-copy-compact">${escapeHtml(module.summary)}</p>
            <p class="eval-note">${escapeHtml(module.impact)}</p>
        </article>
    `;
    }

    function renderWeightMetric(label, value, note) {
        return `
        <div class="eval-panel eval-result-metric">
            <div class="label">${escapeHtml(label)}</div>
            <div class="value">${formatNumber(value, 4)}</div>
            <p class="eval-note">${escapeHtml(note)}</p>
        </div>
    `;
    }

    function renderResultMetric(label, value) {
        return `
        <div class="eval-panel eval-result-metric">
            <div class="label">${escapeHtml(label)}</div>
            <div class="value">${escapeHtml(String(formatMaybe(value)))}</div>
        </div>
    `;
    }

    function renderResultAccent(label, value) {
        return `
        <div class="eval-result-accent">
            <span class="label">${escapeHtml(label)}</span>
            <span class="value">${escapeHtml(String(formatMaybe(value)))}</span>
        </div>
    `;
    }

    function renderResultHero(result) {
        const completionScore = Number(result.goal_completion_rate) * 100;
        return `
        <div class="eval-panel eval-result-hero">
            <div class="eval-result-radial">
                <div class="eval-result-radial-core" aria-hidden="true"></div>
                <div class="eval-result-radial-ring" aria-hidden="true"></div>
                ${renderRadialArm("目标达成", result.goal_score, -90)}
                ${renderRadialArm("期望收益", result.utility_score, -18)}
                ${renderRadialArm("资源机会", result.resource_score, 54)}
                ${renderRadialArm("风险稳定", result.risk_score, 126)}
                ${renderRadialArm("目标完成率", completionScore, 198)}
            </div>
            <div class="eval-result-main-score">
                <div class="eval-result-main-grade">${escapeHtml(`[${result.grade}]`)}</div>
                <div class="eval-result-main-value">${escapeHtml(String(formatFixed(result.raw_score, 1)))}</div>
            </div>
        </div>
    `;
    }

    function renderRadialArm(label, value, angle) {
        const score = clampScore(value);
        return `
        <div class="eval-result-radial-arm" style="--arm-angle:${angle}deg; --arm-score:${score};">
            <span class="eval-result-radial-lanes" aria-hidden="true">
                <i class="eval-result-radial-track-full"></i>
                <i class="eval-result-radial-track-current" style="--arm-score:${score};"></i>
            </span>
            <span class="eval-result-radial-label">
                <strong>${escapeHtml(label)}</strong>
                <em>${escapeHtml(String(formatFixed(score, 1)))}</em>
            </span>
        </div>
    `;
    }

    function clampScore(value) {
        const num = Number(value);
        if (!Number.isFinite(num)) {
            return 0;
        }
        return Math.max(0, Math.min(100, num));
    }

    function renderPrefInput(state, path, key, label) {
        const value = readByPath(state.preferences, key);
        return `
        <div class="eval-field">
            <label>${escapeHtml(label)}</label>
            <input class="eval-input" type="number" step="any" value="${value}" data-pref-key="${path}">
        </div>
    `;
    }

    function renderNumberField(label, key, value, attrName) {
        return `
        <div class="eval-field">
            <label>${escapeHtml(label)}</label>
            <input class="eval-input" type="number" value="${value}" data-${attrName}="${key}">
        </div>
    `;
    }

    function renderPlanResourceField(planIndex, key, label, value) {
        return `
        <div class="eval-field">
            <label>${escapeHtml(label)}</label>
            <input class="eval-input" type="number" value="${value}" data-plan-index="${planIndex}" data-resource-field="${key}">
        </div>
    `;
    }

    function button(label, action, primary = false) {
        return `<button class="eval-btn ${primary ? "primary" : ""}" data-action="${action}">${escapeHtml(label)}</button>`;
    }

    function readByPath(source, path) {
        return path.split(".").reduce((cursor, key) => cursor[key], source);
    }

    function formatNumber(value, digits) {
        if (!Number.isFinite(Number(value))) {
            return value;
        }
        return Number(value).toFixed(digits);
    }

    function formatMaybe(value) {
        if (typeof value !== "number") {
            return value;
        }
        return Math.round(value * 10000) / 10000;
    }

    function formatFixed(value, digits) {
        if (!Number.isFinite(Number(value))) {
            return value;
        }
        return Number(value).toFixed(digits);
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    global.EvalRender = { renderApp };
}(window));
