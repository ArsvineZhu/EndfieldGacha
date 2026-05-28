(function assignEvalQuestionnaire(global) {
    const { MODULES, PAIRS } = global.EvalConstants;
    const REVIEW_PAIR_COUNT = 2;

    function applyQuestionnaireWeights(questionnaire, preferences) {
        if (questionnaire.pairIndex < PAIRS.length) {
            return;
        }

        const keys = ["goal", "utility", "resource", "risk"];
        const matrix = Array.from({ length: keys.length }, () => Array.from({ length: keys.length }, () => 1));

        Object.values(questionnaire.answers).forEach((entry) => {
            const [left, right] = entry.pair;
            const leftIndex = keys.indexOf(left);
            const rightIndex = keys.indexOf(right);
            let ratio = 1;
            if (entry.direction === left) {
                ratio = entry.strength;
            } else if (entry.direction === right) {
                ratio = 1 / entry.strength;
            }
            matrix[leftIndex][rightIndex] = ratio;
            matrix[rightIndex][leftIndex] = 1 / ratio;
        });

        const rawWeights = matrix.map((row) => Math.pow(row.reduce((acc, value) => acc * value, 1), 1 / row.length));
        const total = rawWeights.reduce((acc, value) => acc + value, 0);
        const weights = rawWeights.map((value) => value / total);
        const weightedMatrix = matrix.map((row) => row.reduce((acc, value, index) => acc + value * weights[index], 0));
        const lambdaMax = weightedMatrix.reduce((acc, value, index) => acc + value / weights[index], 0) / weights.length;
        const ci = (lambdaMax - weights.length) / (weights.length - 1);
        const cr = ci / 0.9;

        preferences.goal_weight = roundTo(weights[0], 4);
        preferences.utility_weight = roundTo(weights[1], 4);
        preferences.resource_weight = roundTo(weights[2], 4);
        preferences.risk_weight = roundTo(weights[3], 4);
        preferences.questionnaire_consistency_ratio = roundTo(cr, 4);

        if (cr > 0.1) {
            preferences.questionnaire_status = questionnaire.review_completed
                ? "reviewed_inconsistent"
                : "inconsistent";
        } else {
            preferences.questionnaire_status = "completed";
        }

        applySecondaryPreferences(preferences);
    }

    function applySecondaryPreferences(preferences) {
        const goalW = clamp(preferences.goal_weight, 0, 1);
        const utilityW = clamp(preferences.utility_weight, 0, 1);
        const resourceW = clamp(preferences.resource_weight, 0, 1);
        const riskW = clamp(preferences.risk_weight, 0, 1);

        preferences.alpha = roundTo(0.85 + goalW * 0.9, 4);
        preferences.utility_log_map = {
            low: roundTo(0.55 + (1 - utilityW) * 0.1, 4),
            high: roundTo(1.2 + utilityW * 0.45, 4),
            curve: roundTo(0.9 + (1 - utilityW) * 0.5, 4),
        };
        preferences.resource_log_map = {
            low: roundTo(0.55 + (1 - resourceW) * 0.1, 4),
            high: roundTo(1.2 + resourceW * 0.55, 4),
            curve: roundTo(0.9 + (1 - resourceW) * 0.4, 4),
        };
        preferences.opportunity_reference = Math.round(40 + resourceW * 120);
        preferences.risk_utility_weight = roundTo(clamp(0.35 + utilityW * 0.5, 0.2, 0.9), 4);
        preferences.tail_ratio = roundTo(clamp(0.08 + riskW * 0.25, 0.05, 0.35), 4);
        preferences.future_resource_income = Math.round(10 + resourceW * 60);
    }

    function prepareConflictReview(questionnaire, preferences) {
        const conflictPairs = pickConflictPairs(questionnaire.answers);
        return {
            ...questionnaire,
            in_review: true,
            review_pairs: conflictPairs,
            review_cursor: 0,
            step: "direction",
            pendingDirection: null,
            review_completed: false,
            review_required: true,
            review_required_count: REVIEW_PAIR_COUNT,
            review_done_count: 0,
            last_consistency_ratio: preferences.questionnaire_consistency_ratio || 0,
        };
    }

    function getQuestionnaireProgress(questionnaire) {
        if (questionnaire.in_review) {
            const total = Math.max(1, questionnaire.review_pairs.length);
            return questionnaire.review_cursor / total;
        }
        return questionnaire.pairIndex >= PAIRS.length ? 1 : questionnaire.pairIndex / PAIRS.length;
    }

    function getCurrentPair(questionnaire) {
        if (questionnaire.in_review && questionnaire.review_pairs.length) {
            return questionnaire.review_pairs[Math.min(questionnaire.review_cursor, questionnaire.review_pairs.length - 1)];
        }
        return PAIRS[Math.min(questionnaire.pairIndex, PAIRS.length - 1)];
    }

    function getSelectedModules(questionnaire) {
        const pair = getCurrentPair(questionnaire);
        const [left, right] = pair;
        if (questionnaire.step === "strength" && questionnaire.pendingDirection) {
            return [
                MODULES[questionnaire.pendingDirection],
                MODULES[questionnaire.pendingDirection === left ? right : left],
            ];
        }
        return [MODULES[left], MODULES[right]];
    }

    function createQuestionnaireState() {
        return {
            pairIndex: 0,
            step: "direction",
            pendingDirection: null,
            answers: {},
            in_review: false,
            review_pairs: [],
            review_cursor: 0,
            review_required: false,
            review_required_count: REVIEW_PAIR_COUNT,
            review_done_count: 0,
            review_completed: false,
            last_consistency_ratio: 0,
        };
    }

    function saveQuestionnaireAnswer(questionnaire, direction, strength) {
        const pair = getCurrentPair(questionnaire);
        questionnaire.answers[pair.join("-")] = { pair, direction, strength };
        if (questionnaire.in_review) {
            questionnaire.review_cursor += 1;
            questionnaire.review_done_count = questionnaire.review_cursor;
            questionnaire.step = "direction";
            questionnaire.pendingDirection = null;
            if (questionnaire.review_cursor >= questionnaire.review_pairs.length) {
                questionnaire.in_review = false;
                questionnaire.review_completed = true;
                questionnaire.pairIndex = PAIRS.length;
            }
            return;
        }

        questionnaire.pairIndex += 1;
        questionnaire.step = "direction";
        questionnaire.pendingDirection = null;
    }

    function getConsistencyHint(consistencyRatio, questionnaireStatus) {
        if (questionnaireStatus === "reviewed_inconsistent") {
            return "你已完成冲突复核，系统会保留这组偏好并允许继续评估。";
        }
        return consistencyRatio > 0.1
            ? "你的取舍里存在相互冲突，需先完成冲突复核才能继续提交。"
            : "当前取舍关系基本一致，可以直接沿用这组结果继续评估。";
    }

    function pickConflictPairs(answers) {
        const scored = Object.values(answers).map((entry) => {
            const score = Math.abs(Math.log(entry.strength || 1));
            return { pair: entry.pair, score };
        });
        scored.sort((a, b) => b.score - a.score);
        const top = scored.slice(0, REVIEW_PAIR_COUNT).map((item) => item.pair);
        if (top.length >= REVIEW_PAIR_COUNT) {
            return top;
        }
        const fallback = PAIRS.filter((pair) => !top.some((p) => p[0] === pair[0] && p[1] === pair[1]));
        return top.concat(fallback.slice(0, REVIEW_PAIR_COUNT - top.length));
    }

    function isReviewRequired(preferences, questionnaire) {
        return (
            preferences.questionnaire_status === "inconsistent"
            && preferences.questionnaire_consistency_ratio > 0.1
            && !questionnaire.review_completed
        );
    }

    function clamp(value, min, max) {
        return Math.min(max, Math.max(min, value));
    }

    function roundTo(value, digits) {
        const factor = 10 ** digits;
        return Math.round(value * factor) / factor;
    }

    global.EvalQuestionnaire = {
        applyQuestionnaireWeights,
        createQuestionnaireState,
        getConsistencyHint,
        getCurrentPair,
        getQuestionnaireProgress,
        getSelectedModules,
        isReviewRequired,
        prepareConflictReview,
        roundTo,
        saveQuestionnaireAnswer,
    };
}(window));
