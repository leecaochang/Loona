import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { Connection } from "home-assistant-js-websocket";

class Socket extends EventTarget {
  OPEN = 1;
  readyState = 1;
  haVersion = "2026.9.4";
  sent = [];
  removed = false;
  send(data) {
    const message = JSON.parse(data);
    assert.ok(message.id > (this.sent.at(-1)?.id || 0), "Command IDs must stay ordered");
    this.sent.push(message);
    queueMicrotask(() => this.dispatchEvent(new MessageEvent("message", {
      data: JSON.stringify(this.removed && message.type === "loona/panel"
        ? { id: message.id, type: "result", success: false, error: { code: "unknown_command" } }
        : { id: message.id, type: "result", success: true, result: null }),
    })));
  }
  close() { this.readyState = 3; }
}

const location = { pathname: "/wall-panel/main" };
let app;
const listeners = new Map();
const timers = [];
class App {
  hassConnected() {
    this.hass.connection.subscribeMessage(() => {}, { type: "subscribe_entities" });
    this.hass.connection.sendMessagePromise({ type: "config/entity_registry/list_for_display" });
  }
}
const window = {
  addEventListener: (kind, callback) => listeners.set(kind, callback),
  setInterval: (callback) => timers.push(callback),
};
const context = vm.createContext({
  window, location, URL, console,
  document: { querySelector: () => app },
  customElements: { get: () => App },
});
const source = readFileSync(new URL("../custom_components/loona/frontend/panel-context.js", import.meta.url), "utf8")
  .replace('import "./resource-loading.js?v=0.9.12";', readFileSync(new URL("../custom_components/loona/frontend/resource-loading.js", import.meta.url), "utf8"))
  .replaceAll("import.meta.url", JSON.stringify("http://test/loona/panel-context.js?poll=100"));
vm.runInContext(source, context);
const socket = new Socket();
const connection = new Connection(socket, { setupRetry: 0 });
app = new App();
app.hass = { connection };
app.hassConnected();
await new Promise(setImmediate);
assert.deepEqual(socket.sent.map((row) => row.type), [
  "loona/subscribe_panel", "subscribe_entities", "config/entity_registry/list_for_display",
]);
assert.equal(socket.sent[0].dashboard, "wall-panel");
assert.equal(socket.sent[0].view, "main");

await window.loonaAttachBootstrapPanel(connection, null);
await new Promise(setImmediate);
assert.equal(socket.sent.filter(row => row.type === "lovelace/config").length, 1);
await connection.sendMessagePromise({type:"lovelace/config", url_path:"wall-panel", force:false});
assert.equal(socket.sent.filter(row => row.type === "lovelace/config").length, 1, "The panel consumes the prefetched config once");
await connection.sendMessagePromise({type:"lovelace/config", url_path:"wall-panel", force:true});
assert.equal(socket.sent.filter(row => row.type === "lovelace/config").length, 2, "Forced refresh remains native");
await window.loonaAttachBootstrapPanel(connection, null);
assert.equal(socket.sent.filter(row => row.type === "lovelace/resources").length, 1);
const raw = await connection.subscribeMessage(() => {}, {type:"subscribe_events", event_type:"state_changed"});
await new Promise(setImmediate);
assert.ok(window.loonaSubscriptionReport(connection).some(row => row.type === "subscribe_events/state_changed" && row.count === 1));
await raw();
assert.ok(!window.loonaSubscriptionReport(connection).some(row => row.type === "subscribe_events/state_changed"));

location.pathname = "/config/ai_task";
listeners.get("location-changed")();
await connection.sendMessagePromise({ type: "config/entity_registry/list" });
assert.equal(socket.sent.at(-2).type, "loona/panel");
assert.equal(socket.sent.at(-2).dashboard, "config");
assert.equal(socket.sent.at(-1).type, "config/entity_registry/list");
const count = socket.sent.length;
timers[0]();
await new Promise(setImmediate);
assert.equal(socket.sent.length, count, "Unchanged routes must not send repeated reports");

// Requests catch route changes even when no navigation event was emitted.
location.pathname = "/wall-panel/other-view";
await connection.sendMessagePromise({ type: "config/entity_registry/list" });
assert.equal(socket.sent.at(-2).type, "loona/panel");
assert.equal(socket.sent.at(-2).dashboard, "wall-panel");
assert.equal(socket.sent.at(-2).view, "other-view");

location.pathname = "/wall-panel/1";
listeners.get("location-changed")();
await new Promise(setImmediate);
assert.equal(socket.sent.at(-1).view, "1", "Same-dashboard tab changes must report");
location.pathname = "/wall-panel/%E6%88%BF%E9%97%B4";
listeners.get("location-changed")();
await new Promise(setImmediate);
assert.equal(socket.sent.at(-1).view, "房间");
for (const path of ["/wall-panel", "/wall-panel/%E0%A4%A", "/wall-panel/a/extra"]) {
  location.pathname = path;
  listeners.get("location-changed")();
  await new Promise(setImmediate);
  assert.equal(socket.sent.at(-1).view, null, "Missing or unresolved view retains dashboard delivery");
}
location.pathname = "/wall-panel/hass-unused-entities";
listeners.get("location-changed")();
await new Promise(setImmediate);
assert.equal(socket.sent.at(-1).expanded, true, "Native unused-entities editor retains the union");
location.pathname = "/wall-panel/other-view";
listeners.get("location-changed")();
await new Promise(setImmediate);

// Native dialogs and editor queries temporarily restore fresh union delivery.
assert.equal(socket.sent[0].live_dashboard, true);
listeners.get("hass-more-info")({detail:{entityId:"sensor.other"}});
await new Promise(setImmediate);
assert.equal(socket.sent.at(-1).expanded, true);
const opened = socket.sent.length;
listeners.get("show-dialog")({detail:{dialogTag:"ha-dialog-quick-bar"}});
listeners.get("dialog-closed")({detail:{dialog:"ha-more-info-dialog"}});
assert.equal(socket.sent.length, opened, "Another open native dialog keeps union delivery");
window.history = {state:{opensDialog:true}};
listeners.get("dialog-closed")({detail:{dialog:"ha-dialog-quick-bar"}});
await new Promise(setImmediate);
assert.equal(socket.sent.at(-1).expanded, false, "Native back-navigation markers do not mean a dialog is open");
location.search = "?edit=1";
listeners.get("location-changed")();
await new Promise(setImmediate);
assert.equal(socket.sent.at(-1).expanded, true);
location.search = "";
listeners.get("location-changed")();
await new Promise(setImmediate);
assert.equal(socket.sent.at(-1).expanded, false);

// Native reconnect replays the original context message after offline navigation.
let rawCalls = 0;
const replayRaw = await connection.subscribeMessage(() => { rawCalls++; }, {type:"subscribe_events", event_type:"example.custom:event"});
await new Promise(setImmediate);
connection.oldSubscriptions = connection.commands;
connection.commands = new Map();
connection.commandId = 1;
location.pathname = "/developer-tools/state";
const replacement = new Socket();
connection._setSocket(replacement);
await new Promise(setImmediate);
assert.equal(replacement.sent[0].type, "loona/subscribe_panel");
assert.equal(replacement.sent[0].dashboard, "developer-tools");
const replayId = replacement.sent.find(row => row.type === "subscribe_events" && row.event_type === "example.custom:event").id;
replacement.dispatchEvent(new MessageEvent("message", {data:JSON.stringify({id:replayId,type:"event",event:{}})}));
await new Promise(setImmediate);
assert.equal(rawCalls, 1, "Raw callbacks still receive their native event after reconnect");
assert.ok(window.loonaSubscriptionReport(connection).some(row => row.type === "subscribe_events/example.custom:event" && row.count === 1));
await replayRaw();

// Registry replacement and a different authenticated connection are rediscovered.
const nextSocket = new Socket();
const next = new Connection(nextSocket, { setupRetry: 0 });
app.hass = { connection: next };
timers[0]();
await new Promise(setImmediate);
assert.equal(nextSocket.sent[0].dashboard, "developer-tools");
location.pathname = "/%E0%A4%A";
listeners.get("popstate")();
await new Promise(setImmediate);
assert.equal(nextSocket.sent.at(-1).dashboard, null);
vm.runInContext(source, context);
assert.equal(timers.length, 1, "Duplicate module loads must not install another timer");
nextSocket.removed = true;
location.pathname = "/config/ai_task";
listeners.get("location-changed")();
await new Promise(setImmediate);
const afterRemoval = nextSocket.sent.length;
timers[0]();
await next.sendMessagePromise({ type: "get_config" });
assert.equal(nextSocket.sent.length, afterRemoval + 1, "Removed integrations must stop panel reports");
const finalSocket = new Socket();
const finalConnection = new Connection(finalSocket, { setupRetry: 0 });
app.hass = { connection: finalConnection };
timers[0]();
await new Promise(setImmediate);
const panelId = finalSocket.sent[0].id;
finalSocket.dispatchEvent(new MessageEvent("message", { data: JSON.stringify({
  id: panelId, type: "event", event: { enabled: false },
}) }));
await new Promise(setImmediate);
assert.equal(finalSocket.sent.at(-1).type, "unsubscribe_events");
assert.equal(finalConnection.commands.has(panelId), false, "Unload releases the stock client's persistent subscription");
const finalCount = finalSocket.sent.length;
timers[0]();
assert.equal(finalSocket.sent.length, finalCount + 1, "Unload probes for a reload through native methods");
assert.equal(finalConnection.sendMessagePromise,Connection.prototype.sendMessagePromise);
for(let i=0;i<35;i++) { await new Promise(setImmediate); timers[0](); }
await new Promise(setImmediate);
assert.equal(finalSocket.sent.length, finalCount + 30, "Reload probes stop after a bounded retry window");
console.log("Panel context passes native-client bootstrap, navigation, ordering, reconnect and account replacement");
