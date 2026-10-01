// Reproduce HA's real registry/HTMLElement replacement after an early module.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
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
const source = await readFile("custom_components/loona/frontend/graph-loading.js", "utf8");
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
console.log("Home Assistant registry replacement regression passed");
window.happyDOM.abort();
