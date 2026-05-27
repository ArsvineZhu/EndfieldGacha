(function assignEvalQuestionnaire(global) {
    const { MODULES, PAIRS } = global.EvalConstants;

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
        preferences.questionnaire_status = cr > 0.1 ? "inconsistent" : "completed";
        preferences.questionnaire_consistency_ratio = roundTo(cr, 4);
    }

    function getQuestionnaireProgress(questionnaire) {
        return questionnaire.pairIndex >= PAIRS.length ? 1 : questionnaire.pairIndex / PAIRS.length;
    }

    function getCurrentPair(questionnaire) {
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
        };
    }

    function saveQuestionnaireAnswer(questionnaire, direction, strength) {
        const pair = PAIRS[questionnaire.pairIndex];
        questionnaire.answers[pair.join("-")] = { pair, direction, strength };
        questionnaire.pairIndex += 1;
        questionnaire.step = "direction";
        questionnaire.pendingDirection = null;
    }

    function getConsistencyHint(consistencyRatio) {
        return consistencyRatio > 0.1
            ? "你的取舍里存在一些相互冲突的倾向，必要时可以到高级设置里微调。"
            : "当前取舍关系基本一致，可以直接沿用这组结果继续评估。";
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
        roundTo,
        saveQuestionnaireAnswer,
    };
}(window));
