import assert from "node:assert/strict";
import {measure} from "../custom_components/loona/frontend/performance.js";

globalThis.location = {pathname:"/wall-panel/main", origin:"http://test"};
globalThis.window = {loonaSubscriptionReport: () => [{type:"subscribe_events/state_changed", count:1}]};
let disconnected = 0;
let submitted;
let now = 100;
Object.defineProperty(globalThis, "performance", {value:{now: () => now}, configurable:true});
class Observer {
  static supportedEntryTypes = ["long-animation-frame"];
  constructor(callback) { this.callback = callback; }
  observe() {
    this.callback({getEntries: () => [{startTime:50, blockingDuration:8,
      scripts:[{sourceURL:"http://test/hacsfiles/card.js?private=value",duration:20}]},
      {startTime:110, blockingDuration:30, scripts:[{sourceURL:"http://test/uix/uix.js",duration:60,forcedStyleAndLayoutDuration:10},
        {sourceURL:"http://other.invalid/private.js",duration:100}]}]});
  }
  takeRecords() { return []; }
  disconnect() { disconnected++; }
}
globalThis.PerformanceObserver = Observer;
const nativeTimeout = globalThis.setTimeout;
globalThis.setTimeout = callback => {now += 1000; queueMicrotask(callback);};
const connection = {connected:true, socket:{}, sendMessagePromise:async message => {submitted = message;}};
const hass = {user:{is_admin:true}, connection};
try {
  const report = await measure(hass, 1000);
  assert.equal(report.frames, 1);
  assert.equal(report.blocking_ms, 30);
  assert.equal(report.scripts.length, 2);
  assert.equal(report.scripts[0].phase, "buffered");
  assert.equal(report.scripts[0].source, "/hacsfiles/card.js");
  assert.equal(submitted.type, "loona/browser_report");
  assert.equal(disconnected, 1);
  await assert.rejects(measure({...hass,user:{is_admin:false}},1000));
  globalThis.setTimeout = callback => {location.pathname = "/other/main";queueMicrotask(callback);};
  await assert.rejects(measure(hass,1000), /Dashboard changed/);
  assert.equal(disconnected, 2);
  location.pathname = "/wall-panel/main";
  globalThis.setTimeout = callback => {now += 1000; queueMicrotask(callback);};
  globalThis.PerformanceObserver = undefined;
  const fallback = await measure(hass,1000);
  assert.equal(fallback.loaf_supported, false);
  assert.equal(fallback.subscriptions[0].count, 1);
} finally {
  globalThis.setTimeout = nativeTimeout;
}
console.log("Bounded browser measurement, privacy, cleanup and unsupported-browser fallback pass");
