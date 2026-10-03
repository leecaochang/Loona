// Execute Loona against the pinned, verbatim native HuiCard class and real Lit.
import assert from "node:assert/strict";
import { build } from "esbuild";
import { Window } from "happy-dom";

const window = new Window({ url: "http://ha.test/wall-panel/main" });
for (const key of ["window", "document", "customElements", "HTMLElement", "Element", "Node",
  "ShadowRoot", "MutationObserver", "CustomEvent", "Event", "Document", "CSSStyleSheet", "location"]) {
  globalThis[key] = key === "window" ? window : window[key];
}
Object.defineProperty(document, "hidden", { value: false });
window.innerHeight = 768;
window.innerWidth = 1024;
const observers = new Set();
globalThis.IntersectionObserver = class {
  constructor(callback) { this.callback = callback; observers.add(this); }
  observe(owner) {
    this.owner = owner;
    queueMicrotask(() => this.callback([{ isIntersecting: Boolean(owner.visible), time: performance.now() }]));
  }
  disconnect() { observers.delete(this); }
};
HTMLElement.prototype.getBoundingClientRect = function () {
  const visible = this.visible ?? this.parentElement?.visible ?? this.getRootNode()?.host?.visible ?? false;
  return visible ? { top: 0, left: 0, bottom: 100, right: 100 }
    : { top: 2000, left: 0, bottom: 2100, right: 100 };
};

const creations = [];
let holdRender;
let StackCard;
let rejectPlaceholder = false;
class NativeGraph extends HTMLElement {
  setConfig(config) { this.config = config; }
  getCardSize() { return 7; }
  getGridOptions() { return { columns: 8, rows: 4 }; }
}
customElements.define("test-native-graph", NativeGraph);
globalThis.loonaNativeFactory = (config) => {
  if (config.type === "custom:loona-graph-placeholder") {
    if (rejectPlaceholder) throw new Error("Placeholder unavailable in native registry");
    const card = document.createElement("loona-graph-placeholder");
    card.setConfig(config);
    return card;
  }
  if (config.type === "vertical-stack") {
    const card = document.createElement("test-native-stack");
    card.setConfig(config);
    return card;
  }
  creations.push(config);
  if (config.throw) throw new Error("Native config error");
  const card = document.createElement("test-native-graph");
  card.setConfig(config);
  card.updateComplete = holdRender ?? Promise.resolve();
  return card;
};
const nativeImports = `
export const ConditionalListenerMixin = (base) => class extends base { _conditionContext = {}; };
export const fireEvent = (node, type, detail) => node.dispatchEvent(new CustomEvent(type, {detail, bubbles:true, composed:true}));
export const computeCardSize = (node) => node.getCardSize();
export const computeRTLDirection = () => 'ltr';
export const migrateLayoutToGridOptions = (options) => options;
export const getConfigEntityId = (config) => config.entity;
export const checkConditionsMet = (conditions, hass) => conditions.every((condition) => hass.states[condition.entity]?.state === condition.state);
export const tryCreateCardElement = (config) => globalThis.loonaNativeFactory(config);
export const createErrorCardElement = (config) => { const card = document.createElement('test-native-graph'); card.setConfig(config); return card; };
`;
const compiled = await build({
  stdin: { contents: `export { HuiCard } from './tests/fixtures/frontend/hui-card.ts';
    export { HuiStackCard } from './tests/fixtures/frontend/hui-stack-card.ts';`,
    resolveDir: process.cwd(), loader: "js" },
  bundle: true, write: false, format: "esm", platform: "browser",
  alias: { "lit/decorators": "lit/decorators.js" },
  tsconfigRaw: { compilerOptions: { experimentalDecorators: true, useDefineForClassFields: false } },
  plugins: [{ name: "native-boundaries", setup(builder) {
    builder.onResolve({ filter: /^\.\.?\// }, (args) => /hui-(?:stack-)?card\.ts$/.test(args.importer)
      ? { path: args.path, namespace: "native" } : undefined);
    builder.onLoad({ filter: /.*/, namespace: "native" }, () => ({ contents: nativeImports, loader: "js" }));
  } }],
});
const native = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputFiles[0].text).toString("base64")}`);
StackCard = class extends native.HuiStackCard {};
customElements.define("test-native-stack", StackCard);
const moduleSource = (await build({ entryPoints: ["custom_components/loona/frontend/graph-loading.js"],
  bundle: true, write: false, format: "esm" })).outputFiles[0].text;
const missingHook = process.argv[2];
const probedNativeLoad = native.HuiCard.prototype._loadElement;
if (missingHook) delete native.HuiCard.prototype[missingHook];
await import(`data:text/javascript;base64,${Buffer.from(moduleSource).toString("base64")}`);
await Promise.resolve();

if (missingHook) {
  assert.equal(window.__loonaGraphCapability.status, "unavailable");
  assert.equal(native.HuiCard.prototype._loadElement, missingHook === "_loadElement" ? undefined : probedNativeLoad);
  assert.equal(customElements.get("loona-graph-placeholder"), undefined);
  console.log("Missing native hook preserves ordinary graph loading");
  await window.happyDOM.abort();
  process.exit(0);
}
assert.equal(window.__loonaGraphCapability.status, "available");

const profiles = {
  sensor: { height: 120, size: 3, columns: 6, rows: 2 },
  "custom:mini-graph-card": { height: 150, size: 3, columns: 6, rows: 3 },
  "custom:apexcharts-card": { height: 250, size: 5, columns: 6, rows: 5 },
};
const initialPolicy = { version: "0.9.5", enabled: true, dashboards: ["wall-panel"],
  quiet_ms: 20, poll_ms: 5, trace_limit: 200, profiles };
function makeHass(policy = initialPolicy) {
  const connection = {
    connected: true, commands: new Map(),
    subscriptions: 0, listeners: new Map(),
    addEventListener(name, callback) { this.listeners.set(name, callback); },
    removeEventListener(name) { this.listeners.delete(name); },
    subscribeMessage(callback, message, options) {
      assert.equal(message.type, "loona/subscribe_graph_loading");
      assert.equal(options.resubscribe, false);
      this.subscriptions++;
      if (this.failNext) { this.failNext = false; return Promise.reject({code:"unknown_command"}); }
      this.publish = callback;
      return Promise.resolve(() => {});
    },
  };
  return { config: { version: "2026.9.4", loona_graph_loading: policy }, connection,
    states: { "input_boolean.visible": { state: "off" } } };
}
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(predicate) {
  for (let i = 0; i < 400; i++) {
    if (predicate()) return;
    await sleep(5);
  }
  assert.fail(`Condition timed out: ${JSON.stringify(window.loonaGraphLoadingReport())}`);
}
async function owner(config, { hass = makeHass(), visible = false, preview = false, layout,
  view = document.createElement("hui-sections-view") } = {}) {
  view.visible = true;
  const element = document.createElement("hui-card");
  Object.assign(element, { config, hass, visible, preview, layout });
  view.append(element);
  if (!view.isConnected) document.body.append(view);
  await element.updateComplete;
  await Promise.resolve();
  return element;
}
function scrollInto(element) {
  element.visible = true;
  for (const observer of observers) {
    if (observer.owner === element) observer.callback([{ isIntersecting: true, time: performance.now() }]);
  }
}
async function cleanup() {
  document.body.replaceChildren();
  holdRender = undefined;
  await until(() => window.loonaGraphLoadingReport().connected === 0);
  assert.equal(window.loonaGraphLoadingReport().connected, 0);
}

// A visible first render and a genuine pending native command block background,
// while newly visible cards bypass both gates.
let resolveFirst;
holdRender = new Promise((resolve) => { resolveFirst = resolve; });
const hass = makeHass();
const firstConfig = { type: "sensor", graph: "line", entity: "sensor.first", grid_options: { rows: 6 } };
const first = await owner(firstConfig, { hass, visible: true });
holdRender = undefined;
const secondConfig = { type: "custom:apexcharts-card", series: [{ entity: "sensor.second" }] };
const second = await owner(secondConfig, { hass });
assert.equal(first._element.tagName, "TEST-NATIVE-GRAPH");
assert.equal(second._element.tagName, "LOONA-GRAPH-PLACEHOLDER");
assert.equal(second.config, secondConfig);
assert.equal(second._elementConfig, secondConfig);
assert.deepEqual(second.getGridOptions(), { columns: 6, rows: 5 });
await sleep(70);
assert.equal(second._element.tagName, "LOONA-GRAPH-PLACEHOLDER");
hass.connection.commands.set(100, { resolve() {} });
scrollInto(second);
assert.equal(second._element.tagName, "TEST-NATIVE-GRAPH");
assert.equal(second._element.config, secondConfig);
assert.equal(second.firstElementChild, second._element);
assert.deepEqual(first.getGridOptions(), { columns: 8, rows: 6 });
assert.equal(second.getCardSize(), 7);
resolveFirst();
hass.connection.commands.clear();
await until(() => window.loonaGraphLoadingReport().active_loads === 0);
await cleanup();

// Visible non-graph card rendering also gates background work. Once that card
// leaves the viewport, its unfinished render must not starve off-screen graphs.
let resolveOrdinary;
holdRender = new Promise((resolve) => { resolveOrdinary = resolve; });
const ordinary = await owner({ type: "entity", entity: "sensor.visible" }, { visible: true });
holdRender = undefined;
const deferred = await owner({ type: "sensor", graph: "line" }, {
  hass: ordinary.hass, view: ordinary.parentElement,
});
await sleep(70);
assert.equal(deferred._element.tagName, "LOONA-GRAPH-PLACEHOLDER");
assert.ok(window.loonaGraphLoadingReport().pending_renders > 0);
ordinary.visible = false;
await until(() => deferred._element.tagName === "TEST-NATIVE-GRAPH");
resolveOrdinary();
await cleanup();

// Background cards create serially after visible work settles. Subscription
// records in the stock Connection commands map do not block readiness.
const backgroundHass = makeHass();
backgroundHass.connection.commands.set(1, { subscribe() {} });
let resolveBackground;
holdRender = new Promise((resolve) => { resolveBackground = resolve; });
const a = await owner({ type: "sensor", graph: "line", entity: "sensor.a" }, { hass: backgroundHass });
const b = await owner({ type: "sensor", graph: "line", entity: "sensor.b" }, { hass: backgroundHass });
await until(() => a._element.tagName === "TEST-NATIVE-GRAPH");
assert.equal(b._element.tagName, "LOONA-GRAPH-PLACEHOLDER");
holdRender = undefined;
await sleep(60);
assert.equal(b._element.tagName, "LOONA-GRAPH-PLACEHOLDER");
resolveBackground();
await until(() => b._element.tagName === "TEST-NATIVE-GRAPH");
await cleanup();

// Live disable immediately releases queued cards, then all creation is native.
const toggleHass = makeHass();
const queued = await owner({ type: "sensor", graph: "line", entity: "sensor.queued" }, { hass: toggleHass });
assert.equal(queued._element.tagName, "LOONA-GRAPH-PLACEHOLDER");
toggleHass.connection.publish({ ...initialPolicy, enabled: false });
assert.equal(queued._element.tagName, "TEST-NATIVE-GRAPH");
const disabled = await owner({ type: "sensor", graph: "line" }, { hass: toggleHass });
assert.equal(disabled._element.tagName, "TEST-NATIVE-GRAPH");
await cleanup();

// Preview uses real cards and native edits retain the original configuration.
const editHass = makeHass();
const edit = await owner({ type: "sensor", graph: "line", entity: "sensor.before" }, { hass: editHass });
const editedConfig = { type: "sensor", graph: "line", entity: "sensor.after", name: "Edited" };
edit.config = editedConfig;
await edit.updateComplete;
assert.equal(edit._elementConfig, editedConfig);
assert.equal(edit._element._config, editedConfig);
edit.preview = true;
await edit.updateComplete;
assert.equal(edit._element.tagName, "TEST-NATIVE-GRAPH");
assert.equal(edit._element.config, editedConfig);
assert.equal(edit._element.preview, true);
assert.equal(edit._element.editMode, true);
edit._element.dispatchEvent(new CustomEvent("ll-rebuild", { bubbles: true, composed: true }));
assert.equal(edit._element.tagName, "TEST-NATIVE-GRAPH");
assert.equal(edit._element.config, editedConfig);
await cleanup();

// Native visibility keeps a hidden conditional graph uncreated. Showing it
// enrolls the placeholder; scrolling creates it before background quietness.
const conditionalHass = makeHass();
const conditional = await owner({ type: "sensor", graph: "line", visibility: [
  { condition: "state", entity: "input_boolean.visible", state: "on" },
] }, { hass: conditionalHass });
assert.equal(conditional.hidden, true);
assert.equal(conditional.childElementCount, 0);
await sleep(50);
assert.equal(conditional._element.tagName, "LOONA-GRAPH-PLACEHOLDER");
conditional.hass = { ...conditionalHass, states: { "input_boolean.visible": { state: "on" } } };
await conditional.updateComplete;
assert.equal(conditional.hidden, false);
scrollInto(conditional);
assert.equal(conditional._element.tagName, "TEST-NATIVE-GRAPH");
await cleanup();

// Navigation cancels queued work; reconnecting enrolls a pending placeholder.
const nav = await owner({ type: "sensor", graph: "line" });
const navView = nav.parentElement;
navView.remove();
assert.equal(window.loonaGraphLoadingReport().pending, 0);
await sleep(50);
assert.equal(nav._element.tagName, "LOONA-GRAPH-PLACEHOLDER");
document.body.append(navView);
scrollInto(nav);
assert.equal(nav._element.tagName, "TEST-NATIVE-GRAPH");
await cleanup();

// Unsupported policy, dashboards, cards, and panel/preview layouts stay native.
rejectPlaceholder = true;
const fallbackConfig = { type: "sensor", graph: "line", entity: "sensor.fallback" };
const fallback = await owner(fallbackConfig);
assert.equal(fallback._element.tagName, "TEST-NATIVE-GRAPH");
assert.equal(fallback._element.config, fallbackConfig);
rejectPlaceholder = false;
await cleanup();

const stack = await owner({ type: "vertical-stack", cards: [
  { type: "sensor", graph: "line", entity: "sensor.nested" },
] });
await stack._element.updateComplete;
const nested = stack._element._cards[0];
await nested.updateComplete;
assert.equal(nested._element.tagName, "LOONA-GRAPH-PLACEHOLDER");
scrollInto(nested);
assert.equal(nested._element.tagName, "TEST-NATIVE-GRAPH");
assert.equal(nested._element.hass, stack.hass);
await cleanup();

for (const options of [
  { hass: makeHass({ ...initialPolicy, enabled: false }) },
  { hass: makeHass({ ...initialPolicy, dashboards: ["other-dashboard"] }) },
  { hass: makeHass({ ...initialPolicy, version: "unknown" }) },
  { preview: true }, { layout: "panel" },
]) {
  const bypass = await owner({ type: "sensor", graph: "line" }, options);
  assert.equal(bypass._element.tagName, "TEST-NATIVE-GRAPH");
  await cleanup();
}
for (const config of [{ type: "sensor" }, { type: "entity" }, { type: "custom:other-card" }]) {
  const bypass = await owner(config);
  assert.equal(bypass._element.tagName, "TEST-NATIVE-GRAPH");
  await cleanup();
}
const error = await owner({ type: "sensor", graph: "line", throw: true }, { visible: true });
assert.equal(error._element.config.type, "error");
await cleanup();
// Optional policy subscriptions retry a handled startup error after reconnect.
const recoveryHass = makeHass();
await owner({type:"sensor",graph:"line"}, {hass:recoveryHass,visible:true});
await cleanup();
recoveryHass.connection.failNext = true;
recoveryHass.connection.listeners.get("ready")();
await sleep(2100);
assert.equal(recoveryHass.connection.subscriptions,3);
recoveryHass.connection.publish({...initialPolicy,active:false});
assert.equal(recoveryHass.connection.listeners.has("ready"),false);
const originalLoad = customElements.get("hui-card").prototype._loadElement;
await import(`data:text/javascript;base64,${Buffer.from(`${moduleSource}\n// second import`).toString("base64")}`);
assert.equal(customElements.get("hui-card").prototype._loadElement, originalLoad);
assert.ok(window.loonaGraphLoadingTrace().length <= initialPolicy.trace_limit);
console.log("Native HuiCard graph scheduling checks passed");
window.happyDOM.abort();
