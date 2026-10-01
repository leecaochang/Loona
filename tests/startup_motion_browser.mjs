// Real browser animations inside pinned HuiCard and real Lit, without an HA login.
import "./fixtures/frontend/hui-card.ts";
import "../custom_components/loona/frontend/graph-loading.js";
const check = (condition, message) => { if (!condition) throw new Error(message); };
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(predicate) {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (predicate()) return;
    await sleep(10);
  }
  throw new Error(`Timeout: ${JSON.stringify(window.loonaStartupMotionReport())}`);
}
const policy = { version: "0.5.0", enabled: false, dashboards: ["wall-panel"],
  quiet_ms: 30, poll_ms: 10, trace_limit: 200, profiles: { sensor: { height: 120, size: 3, columns: 6, rows: 2 } },
  motion: { enabled: true, quiet_ms: 30, poll_ms: 10, max_ms: 250,
    view_tags: ["HUI-SECTIONS-VIEW", "HUI-MASONRY-VIEW"], progress_tags: ["HA-SPINNER"] } };
function makeHass(override = {}) {
  const connection = { connected: true, commands: new Map(),
    subscribeMessage(callback) { this.publish = callback; return Promise.resolve(() => {}); } };
  return { connection, config: { loona_graph_loading: { ...policy, ...override } }, states: { test: 1 } };
}
class AnimatedCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" }).innerHTML = `
      <style>:host { display:block; width:200px; height:100px; } span { display:inline-block; }
      @keyframes loona-test-spin { to { transform:rotate(360deg); } }
      #css { animation:loona-test-spin 5s linear infinite; }</style>
      <span id="css">CSS rotating icon</span>
      <span id="loop">rotating icon</span><span id="finite">transition</span>
      <span id="paused">already paused</span><span role="progressbar" id="progress">loading</span>
      <ha-spinner><span id="spinner">native loading</span></ha-spinner>
      <button>control</button><output></output>`;
    const animate = (id, iterations = Infinity) => this.shadowRoot.getElementById(id)
      .animate([{ transform: "rotate(0deg)" }, { transform: "rotate(360deg)" }], { duration: 5000, iterations });
    this.loop = animate("loop");
    this.finite = animate("finite", 1);
    this.prepaused = animate("paused"); this.prepaused.pause();
    this.progress = animate("progress"); this.spinner = animate("spinner");
    this.shadowRoot.querySelector("button").onclick = () => this.clicks = (this.clicks ?? 0) + 1;
  }
  connectedCallback() { this.css = this.shadowRoot.getElementById("css").getAnimations()[0]; }
  setConfig(config) { this.config = config; }
  set hass(value) { this._hass = value; this.shadowRoot.querySelector("output").textContent = value.states.test; }
  get hass() { return this._hass; }
  getCardSize() { return 1; }
}
customElements.define("test-animated-card", AnimatedCard);
window.loonaNativeFactory = (config) => {
  if (config.type === "custom:loona-graph-placeholder") {
    const placeholder = document.createElement("loona-graph-placeholder");
    placeholder.setConfig(config);
    return placeholder;
  }
  const child = document.createElement("test-animated-card"); child.setConfig(config); return child;
};
async function card(hass = makeHass(), options = {}) {
  const view = document.createElement(options.panel ? "hui-panel-view" : "hui-sections-view");
  const owner = document.createElement("hui-card");
  Object.assign(owner, { config: { type: "custom:test-animation" }, hass,
    preview: Boolean(options.preview), layout: options.panel ? "panel" : undefined });
  view.append(owner); document.body.append(view);
  await owner.updateComplete; await sleep(0);
  return { view, owner, child: owner._element, hass };
}
const report = () => window.loonaStartupMotionReport();
async function remove(test) {
  test.view.remove();
  // If still loading, the next poll restores disconnected animations too.
  await until(() => report().paused === 0);
}

try {
  // Graphs can be disabled while startup motion works independently.
  const first = await card();
  await until(() => first.child.loop.playState === "paused");
  await until(() => first.child.css?.playState === "paused");
  check(first.child.css instanceof CSSAnimation, "Exercise real CSS animations");
  check(first.child.finite.playState === "running", "Finite transitions must continue");
  check(first.child.progress.playState === "running", "ARIA loading indicator must continue");
  check(first.child.spinner.playState === "running", "Native loading indicator must continue");
  check(first.child.prepaused.playState === "paused", "Preserve existing paused state");
  first.owner.hass = { ...first.hass, states: { test: 2 } };
  await first.owner.updateComplete;
  check(first.child.shadowRoot.querySelector("output").textContent === "2", "Live values must still update");
  first.child.shadowRoot.querySelector("button").click();
  check(first.child.clicks === 1, "Native controls still work");
  await until(() => report().phase === "settled");
  check(first.child.loop.playState === "running", "Automatically restore continuous motion");
  check(first.child.css.playState === "running", "Automatically restore CSS animations");
  check(first.child.prepaused.playState === "paused", "Do not resume someone else's pause");
  check(report().resumed_after_ms < policy.motion.max_ms, "Use early idle opportunity");
  await sleep(80);
  check(first.child.loop.playState === "running" && report().paused === 0, "Settled cards must not be paused again");
  await remove(first);

  // Visible render and one-shot HA requests gate early restoration. Stock
  // subscriptions do not. Newly attached shadow roots are picked up.
  let resolveRender;
  const busyHass = makeHass({ motion: { ...policy.motion, max_ms: 600 } });
  busyHass.connection.commands.set(1, { resolve() {} });
  const busy = await card(busyHass);
  busy.child.updateComplete = new Promise((resolve) => resolveRender = resolve);
  await until(() => busy.child.loop.playState === "paused");
  const host = document.createElement("div"); busy.child.shadowRoot.append(host);
  host.attachShadow({ mode: "open" }).innerHTML = '<span>late icon</span>';
  const late = host.shadowRoot.firstChild.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 5000, iterations: Infinity });
  await until(() => late.playState === "paused");
  busyHass.connection.commands.clear();
  busyHass.connection.commands.set(2, { subscribe() {} });
  await sleep(80);
  check(report().phase === "loading", "Visible unfinished render must hold pause");
  resolveRender();
  await until(() => report().phase === "settled");
  check(late.playState === "running", "Late shadow animation restored");
  await remove(busy);

  // Restoring motion gets the first idle opportunity before off-screen graphs.
  const bothHass = makeHass({ enabled: true });
  bothHass.connection.commands.set(1, { resolve() {} });
  const both = await card(bothHass);
  const graph = document.createElement("hui-card");
  Object.assign(graph, { config: { type: "sensor", graph: "line" }, hass: bothHass });
  graph.style.marginTop = "2000px";
  both.view.append(graph);
  await graph.updateComplete;
  await until(() => both.child.loop.playState === "paused");
  check(graph._element.tagName === "LOONA-GRAPH-PLACEHOLDER", "Off-screen graph waits during startup pause");
  bothHass.connection.commands.clear();
  await until(() => report().phase === "settled");
  check(both.child.loop.playState === "running", "Restore visible motion at first idle opportunity");
  await until(() => graph._element.tagName === "TEST-ANIMATED-CARD");
  check(graph._element.loop.playState === "running", "Later background graphs do not restart the pause");
  await remove(both);

  const timeoutHass = makeHass(); timeoutHass.connection.commands.set(1, { resolve() {} });
  const timeout = await card(timeoutHass);
  await until(() => timeout.child.loop.playState === "paused");
  await until(() => report().phase === "time-limit");
  check(timeout.child.loop.playState === "running", "Maximum pause is enforced despite stalled request");
  await remove(timeout);

  for (const action of ["disabled", "interaction", "navigation", "removed", "preview"]) {
    history.replaceState({}, "", "/wall-panel/main");
    const hass = makeHass(); hass.connection.commands.set(1, { resolve() {} });
    const test = await card(hass);
    await until(() => test.child.loop.playState === "paused");
    if (action === "disabled") hass.connection.publish({ ...policy, motion: { ...policy.motion, enabled: false } });
    if (action === "interaction") test.child.shadowRoot.querySelector("button").dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, composed: true }));
    if (action === "navigation") { history.replaceState({}, "", "/other/main"); window.dispatchEvent(new Event("location-changed")); }
    if (action === "removed") test.view.remove();
    if (action === "preview") { test.owner.preview = true; await test.owner.updateComplete; }
    await until(() => report().paused === 0);
    if (action !== "preview") check(test.child.loop.playState === "running", `${action} restores owned animation`);
    await remove(test);
  }
  history.replaceState({}, "", "/wall-panel/main");
  for (const options of [{ preview: true }, { panel: true }, {}]) {
    const hass = makeHass(options.preview || options.panel ? {} : { dashboards: ["other"] });
    const bypass = await card(hass, options);
    await sleep(40);
    check(bypass.child.loop.playState === "running", "Preview, panel and out-of-scope pages stay native");
    await remove(bypass);
  }
  const disabled = await card(makeHass({ motion: { ...policy.motion, enabled: false } }));
  await sleep(40);
  check(disabled.child.loop.playState === "running", "Default disabled behavior keeps animations running");
  await remove(disabled);
  document.body.dataset.result = "passed";
  document.body.textContent = "Native HuiCard startup animation checks passed";
} catch (error) {
  document.body.dataset.result = "failed";
  document.body.textContent = error.stack;
}
