// Reproduce HA's real registry/HTMLElement replacement after an early module.
import assert from "node:assert/strict";
import { build } from "esbuild";
import { Window } from "happy-dom";
const window = new Window();
globalThis.window = window;
globalThis.self = window;
for (const key of ["document", "MutationObserver", "Element", "ShadowRoot"])
  globalThis[key] = window[key];
for (const key of ["customElements", "HTMLElement", "CustomElementRegistry"])
  Object.defineProperty(globalThis, key, { get: () => window[key], configurable: true });
const nativeRegistry = customElements;
const nativeHTMLElement = HTMLElement;
const source = (await build({ entryPoints: ["custom_components/loona/frontend/graph-loading.js"],
  bundle: true, write: false, format: "esm" })).outputFiles[0].text;
await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
assert.equal(customElements.get("loona-graph-placeholder"), undefined,
  "Placeholder registration must wait until after HA bootstrap");
await import("@webcomponents/scoped-custom-element-registry");
assert.notEqual(customElements, nativeRegistry);
assert.notEqual(HTMLElement, nativeHTMLElement);
// Only the readiness marker is needed here; real HuiCard behavior is tested in
// graph_loading.mjs. The real polyfill registers its native stand-in, resolving
// the early native-registry promise just as HA's HuiCard definition does.
class ReadyCard extends HTMLElement {
  _loadElement() {}
  _updateElement() {}
  _setElementVisibility() {}
}
if (process.argv[2] === "missing-container") {
  const policy = { version: "0.9.7", enabled: true, dashboards: ["wall-panel"], quiet_ms: 10,
    poll_ms: 10, probe_ms: 20, trace_limit: 10, profiles: {}, motion: { enabled: false } };
  window.loonaProbeFrontend({ connection: {}, config: { loona_graph_loading: policy } });
  await new Promise(resolve => setTimeout(resolve, 30));
  assert.equal(window.__loonaGraphCapability.status, "unavailable");
  assert.equal(customElements.get("loona-graph-placeholder"), undefined);

}
customElements.define("hui-card", ReadyCard);
await Promise.resolve();
await Promise.resolve();
const placeholder = customElements.get("loona-graph-placeholder");
assert.ok(placeholder, "Native card factory must find the placeholder in HA's current registry");
assert.equal(Object.getPrototypeOf(placeholder), HTMLElement,
  "Placeholder must extend the post-bootstrap HTMLElement constructor");
assert.notEqual(nativeRegistry.get("loona-graph-placeholder"), placeholder,
  "Exercise the scoped registry rather than the old native registry");
assert.ok(window.loonaGraphLoadingReport().hook_installed);
assert.equal(window.__loonaGraphCapability.status, "available");
console.log("Home Assistant registry replacement regression passed");
window.happyDOM.abort();
