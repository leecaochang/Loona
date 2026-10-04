// Reconnect while Loona is absent, then recover using the real stock client.
// HA restart where the tab reconnects before Loona registers its commands.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { Connection, subscribeEntities } from "home-assistant-js-websocket";

let loonaLoaded = true;
const subscribedOnBackend = new Set();
class Socket extends EventTarget {
  OPEN = 1; readyState = 1; haVersion = "2026.9.4"; sent = [];
  send(data) {
    const m = JSON.parse(data); this.sent.push(m);
    let reply;
    if (m.type.startsWith("loona/") && !loonaLoaded) reply = { id: m.id, type: "result", success: false, error: { code: "unknown_command", message: "Unknown command." } };
    else if (m.type === "loona/subscribe_panel") { subscribedOnBackend.add(this); reply = { id: m.id, type: "result", success: true, result: null }; }
    else if (m.type === "loona/panel" && !subscribedOnBackend.has(this)) reply = { id: m.id, type: "result", success: false, error: { code: "not_subscribed", message: "Subscribe to panel context first" } };
    else reply = { id: m.id, type: "result", success: true, result: null };
    queueMicrotask(() => this.dispatchEvent(new MessageEvent("message", { data: JSON.stringify(reply) })));
  }
  close() { this.readyState = 3; }
}
const location = { pathname: "/wall-panel/main" };
let app; const listeners = new Map(); const timers = [];
class App { hassConnected() {} }
const window = { addEventListener: (k, cb) => listeners.set(k, cb), setInterval: (cb) => timers.push(cb) };
const context = vm.createContext({ window, location, URL, console, document: { querySelector: () => app }, customElements: { get: () => App } });
const source = readFileSync(new URL("../custom_components/loona/frontend/panel-context.js", import.meta.url), "utf8")
  .replace('import "./resource-loading.js?v=0.9.12";', readFileSync(new URL("../custom_components/loona/frontend/resource-loading.js", import.meta.url), "utf8"))
  .replaceAll("import.meta.url", JSON.stringify("http://test/loona/panel-context.js?poll=100"));
const unhandled = [];
process.on("unhandledRejection", (reason) => unhandled.push(reason?.code ?? String(reason)));
vm.runInContext(source, context);
const socket = new Socket();
const connection = new Connection(socket, { setupRetry: 0 });
app = new App(); app.hass = { connection }; app.hassConnected(); timers[0]();
await new Promise(setImmediate);
loonaLoaded = false;                                                 // HA restarted; Loona not set up yet
connection.oldSubscriptions = connection.commands; connection.commands = new Map(); connection.commandId = 1;
const replacement = new Socket();
connection._setSocket(replacement);
await new Promise(setImmediate); await new Promise(setImmediate);
console.log("replayed while Loona not loaded:", replacement.sent.map(r => r.type), "unhandled:", unhandled);
loonaLoaded = true;                                                  // Loona finishes loading
location.pathname = "/config/dashboard"; listeners.get("location-changed")();
await new Promise(setImmediate); await new Promise(setImmediate);
location.pathname = "/wall-panel/main"; listeners.get("location-changed")(); timers[0]();
await new Promise(setImmediate); await new Promise(setImmediate);
console.log("after Loona loads + navigation:", replacement.sent.map(r => r.type), "backend context:", subscribedOnBackend.has(replacement));
const before = replacement.sent.length; location.pathname = "/other-dash/x"; listeners.get("location-changed")(); timers[0]();
await new Promise(setImmediate);
console.log("further navigation sends reports:", replacement.sent.length > before);

assert.deepEqual(unhandled, []);
assert.ok(subscribedOnBackend.has(replacement));
assert.ok(replacement.sent.length > before);

const stopStates = subscribeEntities(connection, states => { app.hass.states = states; });
await new Promise(setImmediate);
const snapshot = (socket, ids, explicit = false) => {
  const command = socket.sent.filter(row => row.type === "subscribe_entities" && !row.include && ("entity_ids" in row) === explicit).at(-1);
  const a = Object.fromEntries(ids.map(id => [id,{s:"1",a:{},c:"context",lc:1}]));
  socket.dispatchEvent(new MessageEvent("message", {data:JSON.stringify({id:command.id,type:"event",event:{a}})}));
};
snapshot(replacement, ["sensor.wall", "sensor.other"]);
assert.deepEqual(Object.keys(app.hass.states).sort(), ["sensor.other", "sensor.wall"]);
const includedEvents = [];
await connection.subscribeMessage(event => includedEvents.push(event), {type:"subscribe_entities",include:{domains:["sensor"]}});
const included = replacement.sent.findLast(row => row.type === "subscribe_entities" && row.include);
replacement.dispatchEvent(new MessageEvent("message", {data:JSON.stringify({id:included.id,type:"event",event:{a:{"sensor.wall":{s:"1",a:{},c:"context",lc:1}}}})}));
assert.equal(includedEvents.at(-1).r, undefined, "Native include filters retain their original events");

// Recovery uses one native reconnect, preserving the original explicit request.
let recoveries = 0;
let recoveredSocket;
connection.reconnect = () => {
  recoveries++;
  connection.oldSubscriptions = connection.commands;
  connection.commands = new Map(); connection.commandId = 1;
  recoveredSocket = new Socket(); connection._setSocket(recoveredSocket);
};
const explicitEvents = [];
await connection.subscribeMessage(event => explicitEvents.push(event), {type:"subscribe_entities",entity_ids:[]});
const panelCommand = replacement.sent.filter(row => row.type === "loona/subscribe_panel").at(-1);
replacement.dispatchEvent(new MessageEvent("message", {data:JSON.stringify({id:panelCommand.id,type:"event",event:{resubscribe:true}})}));
await new Promise(setImmediate); await new Promise(setImmediate);
assert.equal(recoveries,1);
assert.deepEqual(recoveredSocket.sent.find(row=>row.type==="subscribe_entities" && "entity_ids" in row).entity_ids,[]);
assert.ok(subscribedOnBackend.has(recoveredSocket));
snapshot(recoveredSocket, ["sensor.wall"]);
assert.deepEqual(Object.keys(app.hass.states), ["sensor.wall"], "Replayed snapshot must remove full cached states");
snapshot(recoveredSocket, ["sensor.other"], true);
assert.equal(explicitEvents.at(-1).r, undefined, "Explicit feeds retain their original events");
// Unload restores native methods; a later poll detects a newly loaded runtime.
snapshot(recoveredSocket, ["sensor.wall", "sensor.other"]);
assert.equal(Object.keys(app.hass.states).length, 2);
const lastPanel = recoveredSocket.sent.filter(row => row.type === "loona/subscribe_panel").at(-1);
loonaLoaded = false; subscribedOnBackend.delete(recoveredSocket);
recoveredSocket.dispatchEvent(new MessageEvent("message", {data:JSON.stringify({id:lastPanel.id,type:"event",event:{enabled:false}})}));
await new Promise(setImmediate);
assert.equal(connection.sendMessagePromise,Connection.prototype.sendMessagePromise);
assert.equal(connection.subscribeMessage,Connection.prototype.subscribeMessage);
const beforeReload = recoveredSocket.sent.length;
timers[0](); await new Promise(setImmediate);
assert.ok(recoveredSocket.sent.slice(beforeReload).some(row=>row.type==="loona/panel"));
loonaLoaded = true;
timers[0](); await new Promise(setImmediate); await new Promise(setImmediate);
assert.ok(subscribedOnBackend.has(recoveredSocket));
const reloadedPanel = recoveredSocket.sent.filter(row => row.type === "loona/subscribe_panel").at(-1);
recoveredSocket.dispatchEvent(new MessageEvent("message", {data:JSON.stringify({id:reloadedPanel.id,type:"event",event:{resubscribe:true}})}));
await new Promise(setImmediate); await new Promise(setImmediate);
assert.equal(recoveries,2);
assert.deepEqual(recoveredSocket.sent.find(row=>row.type==="subscribe_entities" && "entity_ids" in row).entity_ids,[]);
snapshot(recoveredSocket, ["sensor.wall"]);
assert.deepEqual(Object.keys(app.hass.states), ["sensor.wall"], "Reload must retire the full unload snapshot");
stopStates();
connection.fireEvent("disconnected");
connection.close();
