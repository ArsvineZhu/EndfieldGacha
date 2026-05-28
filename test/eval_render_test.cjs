const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function loadRenderApp() {
  const source = fs.readFileSync(path.join(process.cwd(), "web/static/pages/eval/js/render.js"), "utf8");
  const context = {
    window: {
      EvalConstants: {
        ADVANCED_GROUPS: [],
        BOOLEAN_OPERATORS: [],
        CONDITION_FIELDS: {},
        GOAL_TYPES: {},
        MODULES: {},
        PAIRS: [],
        STATUS_LABELS: { succeeded: "已完成" },
        STEP_LABELS: {
          intro: "引导",
          questionnaire: "问卷",
          questionnaire_result: "问卷结果",
          setup: "全局设置",
          banners: "卡池阶段",
          goals: "目标",
          submit: "提交",
          result: "结果",
        },
        STRENGTH_OPTIONS: [],
      },
      EvalRules: {
        describeMatch: () => "",
        getOperatorsForCondition: () => [],
        goalNeedsCharacter: () => false,
        goalNeedsStage: () => false,
      },
      EvalQuestionnaire: {
        getConsistencyHint: () => "",
        getCurrentPair: () => null,
        getQuestionnaireProgress: () => 0,
      },
    },
  };

  vm.runInNewContext(source, context, { filename: "render.js" });
  return context.window.EvalRender.renderApp;
}

function buildState(overrides = {}) {
  return {
    currentView: "result",
    availableConfigs: [],
    questionnaire: { pairIndex: 0 },
    preferences: {},
    resources: {},
    initialCounters: {},
    scale: 2000,
    bannerPlans: [],
    goals: [],
    error: "",
    lastProgress: { from: 0, to: 0 },
    job: {
      status: "succeeded",
      job_id: "8F17B807DFF44764B0AD6845EC26D222",
      result: {
        goal_score: 22.8,
        utility_score: 88.4,
        resource_score: 100,
        risk_score: 65.2,
        goal_completion_rate: 0.253,
        utility_ratio: 1.2255,
        opportunity_ratio: 1.3482,
        simulations: 2000,
        mean_utility: 812.4,
        mean_baseline: 662.9,
        mean_opportunity: 94.8,
        tail_risk_mean: 37.1,
        scoring_version: "v2.3.0",
        grade: "C",
        raw_score: 69.1,
      },
    },
    ...overrides,
  };
}

test("renderApp builds the tactical result screen for evaluation results", () => {
  const renderApp = loadRenderApp();
  const html = renderApp(buildState());

  assert.doesNotMatch(html, /eval-topbar/);
  assert.doesNotMatch(html, /eval-stage-rail/);
  assert.match(html, /eval-result-screen/);
  assert.match(html, /eval-result-backdrop-title"[^>]*>RESULTS</);
  assert.match(html, /eval-result-radar/);
  assert.match(html, /eval-result-rank-brackets/);
  assert.match(html, /eval-result-meta-zone/);
  assert.match(html, />> 查看详情/);
  assert.match(html, /8F17B807\.\.\.C26D222/);
  assert.doesNotMatch(html, /平均实际收益/);
});

test("renderApp removes the global navigation chrome for setup flow screens", () => {
  const renderApp = loadRenderApp();
  const html = renderApp(buildState({ currentView: "intro", job: null }));

  assert.doesNotMatch(html, /eval-topbar/);
  assert.doesNotMatch(html, /eval-stage-rail/);
  assert.match(html, /eval-stage-intro/);
  assert.match(html, /eval-main/);
});

test("radar labels stay close to the pentagon vertices", () => {
  const renderApp = loadRenderApp();
  const html = renderApp(buildState());

  const topMatch = html.match(/eval-result-radar-label is-top" style="left:([0-9.]+)%; top:([0-9.]+)%;/);
  const leftTopMatch = html.match(/eval-result-radar-label is-left-top" style="left:([0-9.]+)%; top:([0-9.]+)%;/);
  const rightTopMatch = html.match(/eval-result-radar-label is-right-top" style="left:([0-9.]+)%; top:([0-9.]+)%;/);

  assert.ok(topMatch, "top radar label should exist");
  assert.ok(leftTopMatch, "left-top radar label should exist");
  assert.ok(rightTopMatch, "right-top radar label should exist");

  const [, topLeft, topTop] = topMatch;
  const [, leftTopLeft, leftTopTop] = leftTopMatch;
  const [, rightTopLeft, rightTopTop] = rightTopMatch;

  assert.equal(Number(topLeft).toFixed(0), "50");
  assert.ok(Number(topTop) >= 8, `top label should not sit too high: ${topTop}`);
  assert.ok(Number(leftTopLeft) >= 14.5, `left-top label should stay inside the radar zone: ${leftTopLeft}`);
  assert.ok(Number(leftTopTop) >= 38, `left-top label should stay closer to the polygon shoulder: ${leftTopTop}`);
  assert.ok(Number(rightTopLeft) <= 88, `right-top label should not overshoot too far right: ${rightTopLeft}`);
  assert.ok(Number(rightTopTop) >= 38, `right-top label should sit closer to the vertex: ${rightTopTop}`);
});

test("eval result styles do not depend on remote font providers", () => {
  const css = fs.readFileSync(path.join(process.cwd(), "web/static/pages/eval/css/layout.css"), "utf8");

  assert.doesNotMatch(css, /fonts\.googleapis\.com/);
  assert.match(css, /--eval-font-ui:/);
  assert.match(css, /--eval-font-display:/);
});
