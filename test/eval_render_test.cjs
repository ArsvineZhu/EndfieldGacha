const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function loadRenderApp(overrides = {}) {
  const constants = {
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
    ...(overrides.constants || {}),
  };
  const rules = {
    describeMatch: () => "",
    getOperatorsForCondition: () => [],
    goalNeedsCharacter: () => false,
    goalNeedsStage: () => false,
    ...(overrides.rules || {}),
  };
  const questionnaire = {
    getConsistencyHint: () => "",
    getCurrentPair: () => null,
    getQuestionnaireProgress: () => 0,
    ...(overrides.questionnaire || {}),
  };
  const source = fs.readFileSync(path.join(process.cwd(), "web/static/pages/eval/js/render.js"), "utf8");
  const context = {
    window: {
      EvalConstants: constants,
      EvalRules: rules,
      EvalQuestionnaire: questionnaire,
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
  assert.match(html, /eval-result-radial-slot-shell/);
  assert.match(html, /eval-result-radial-arm is-cap/);
  assert.match(html, /eval-result-radial-arm is-score/);
  assert.match(html, /eval-result-score-char is-digit/);
  assert.match(html, /eval-result-rank-brackets/);
  assert.match(html, /eval-result-meta-zone/);
  assert.match(html, />> 查看详情/);
  assert.match(html, /8F17B807\.\.\.C26D222/);
  assert.doesNotMatch(html, /平均实际收益/);
  assert.doesNotMatch(html, /eval-result-radar-shape/);
  assert.doesNotMatch(html, /eval-result-radar-node/);
  assert.doesNotMatch(html, /eval-result-taskline/);
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

test("result radial arms render score length independently from full-score slots", () => {
  const renderApp = loadRenderApp();
  const html = renderApp(buildState());
  const scoreArms = [...html.matchAll(/eval-result-radial-arm is-score [^"]*" style="--arm-scale:([0-9.]+); --arm-angle:([-0-9.]+)deg;/g)];
  const capArms = [...html.matchAll(/eval-result-radial-arm is-cap [^"]*" style="--arm-scale:1; --arm-angle:([-0-9.]+)deg;/g)];

  assert.equal(scoreArms.length, 5, "should render five score arms");
  assert.equal(capArms.length, 5, "should render five full-score arms");
  assert.ok(scoreArms.some(([, scale]) => Number(scale) < 0.4), "low scores should produce short score arms");
  assert.ok(scoreArms.some(([, scale]) => Number(scale) > 0.95), "full scores should nearly fill the slot");
});

test("eval result styles do not depend on remote font providers", () => {
  const css = fs.readFileSync(path.join(process.cwd(), "web/static/pages/eval/css/layout.css"), "utf8");

  assert.doesNotMatch(css, /fonts\.googleapis\.com/);
  assert.match(css, /--eval-font-ui:/);
  assert.match(css, /--eval-font-display:/);
});

test("banner picker moves action beside pool name and hides raw config id prefix", () => {
  const renderApp = loadRenderApp();
  const html = renderApp(buildState({
    currentView: "banners",
    job: null,
    availableConfigs: [
      { id: "config_1", pool_name: "测试卡池", open_time: "2026-06-01", current_up: ["A"], past_up: ["B"] },
    ],
  }));

  assert.match(html, /eval-banner-option-head/);
  assert.match(html, /eval-banner-add-btn/);
  assert.match(html, /aria-label="加入规划"/);
  assert.match(html, />\s*\+\s*</);
  assert.doesNotMatch(html, />\s*加入规划\s*</);
  assert.doesNotMatch(html, /config_1 ·/);
  assert.match(html, /title="将该卡池加入当前规划"/);
});

test("operator selectors render text labels instead of symbolic operators", () => {
  const renderApp = loadRenderApp({
    constants: {
      CONDITION_FIELDS: { draws: { label: "当前卡池已抽数", type: "number" } },
    },
    rules: {
      describeMatch: () => "任一条件触发就停",
      getOperatorsForCondition: () => ["==", ">=", "<="],
    },
  });
  const html = renderApp(buildState({
    currentView: "banners",
    job: null,
    availableConfigs: [{ id: "config_1", pool_name: "测试卡池", open_time: "2026-06-01", current_up: [], past_up: [] }],
    bannerPlans: [{
      config_name: "config_1",
      check_in: true,
      use_origeometry: false,
      resource_increment: { chartered_permits: 5, oroberyl: 0, arsenal_tickets: 0, origeometry: 0 },
      rule: { match: "any", children: [{ node_type: "condition", kind: "draws", operator: ">=", value: 60 }] },
    }],
  }));

  assert.match(html, />等于</);
  assert.match(html, />不少于</);
  assert.match(html, />不高于</);
  assert.doesNotMatch(html, />>=</);
  assert.doesNotMatch(html, /><=</);
});

test("result screen removes grade brackets and uppercases task ids", () => {
  const renderApp = loadRenderApp();
  const html = renderApp(buildState({
    job: {
      status: "succeeded",
      job_id: "8f17b807dff44764b0ad6845ec26d222",
      result: buildState().job.result,
    },
  }));

  assert.match(html, /eval-result-rank">C</);
  assert.doesNotMatch(html, /\[C\]/);
  assert.match(html, /8F17B807\.\.\.C26D222/);
  assert.match(html, /title="8F17B807DFF44764B0AD6845EC26D222"/);
});

test("checkboxes use custom skin and result fonts keep original preferred families with fallback", () => {
  const layoutCss = fs.readFileSync(path.join(process.cwd(), "web/static/pages/eval/css/layout.css"), "utf8");
  const componentCss = fs.readFileSync(path.join(process.cwd(), "web/static/pages/eval/css/components.css"), "utf8");

  assert.match(layoutCss, /"Bebas Neue"/);
  assert.match(layoutCss, /"IBM Plex Sans Condensed"/);
  assert.match(componentCss, /\.eval-check-field input\s*\{/);
  assert.match(componentCss, /appearance:\s*none/);
  assert.match(componentCss, /input:checked \+ span::before/);
});

test("result screen band runs full width and centers RESULTS within the highlighted strip", () => {
  const layoutCss = fs.readFileSync(path.join(process.cwd(), "web/static/pages/eval/css/layout.css"), "utf8");

  assert.match(layoutCss, /\.eval-result-screen-band\s*\{[\s\S]*left:\s*0;[\s\S]*right:\s*0;/);
  assert.match(layoutCss, /\.eval-result-screen-band\s*\{[\s\S]*height:\s*16%;/);
  assert.match(layoutCss, /\.eval-result-screen-band\s*\{[\s\S]*linear-gradient\(90deg,\s*rgba\(161,\s*26,\s*30,\s*0\.02\)[\s\S]*rgba\(161,\s*26,\s*30,\s*0\.38\)\s*74%[\s\S]*rgba\(161,\s*26,\s*30,\s*0\.04\)\s*100%/);
  assert.match(layoutCss, /\.eval-result-screen-band\s*\{[\s\S]*top:\s*42%;/);
  assert.match(layoutCss, /\.eval-result-backdrop-title\s*\{[\s\S]*top:\s*50%;/);
});

test("result view keeps footer at the bottom and allows detail expansion scrolling", () => {
  const layoutCss = fs.readFileSync(path.join(process.cwd(), "web/static/pages/eval/css/layout.css"), "utf8");

  assert.match(layoutCss, /\.eval-stage-result\s*\{[\s\S]*overflow:\s*auto;/);
  assert.match(layoutCss, /\.eval-result-screen\s*\{[\s\S]*display:\s*flex;[\s\S]*flex-direction:\s*column;/);
  assert.match(layoutCss, /\.eval-result-layout\s*\{[\s\S]*margin-top:\s*40px;/);
  assert.match(layoutCss, /\.eval-result-meta-zone\s*\{[\s\S]*margin-top:\s*auto;[\s\S]*padding-top:\s*48px;/);
});

test("result screen defines slab, title, radial burst, and score roll animations", () => {
  const layoutCss = fs.readFileSync(path.join(process.cwd(), "web/static/pages/eval/css/layout.css"), "utf8");

  assert.match(layoutCss, /@keyframes eval-result-slab-slide/);
  assert.match(layoutCss, /@keyframes eval-result-title-drift/);
  assert.match(layoutCss, /@keyframes eval-result-radial-burst/);
  assert.match(layoutCss, /@keyframes eval-result-score-roll/);
  assert.match(layoutCss, /\.eval-result-screen-slab\s*\{[\s\S]*animation:\s*eval-result-slab-slide/);
  assert.match(layoutCss, /\.eval-result-backdrop-title\s*\{[\s\S]*animation:\s*eval-result-title-drift/);
  assert.match(layoutCss, /\.eval-result-radial-arm-body\s*\{[\s\S]*animation:\s*eval-result-radial-burst/);
  assert.match(layoutCss, /\.eval-result-score-char\s*\{[\s\S]*animation:\s*eval-result-score-roll/);
  assert.match(layoutCss, /\.eval-result-backdrop-title\s*\{[\s\S]*font-weight:\s*700;/);
  assert.match(layoutCss, /\.eval-result-backdrop-title\s*\{[\s\S]*scaleY\(0\.72\)/);
  assert.match(layoutCss, /\.eval-result-score-value\s*\{[\s\S]*font-weight:\s*700;/);
});
