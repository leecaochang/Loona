// Exercise the shipped hook with stock Connection and Core's startup reactions.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import { Connection, subscribeEntities } from "home-assistant-js-websocket";

const reporter = readFileSync(new URL("../custom_components/loona/frontend/panel-context.js", import.meta.url), "utf8")
  .replace('import "./resource-loading.js?v=0.9.9";', readFileSync(new URL("../custom_components/loona/frontend/resource-loading.js", import.meta.url), "utf8"))
  .replaceAll("import.meta.url", JSON.stringify("http://test/loona/panel-context.js?poll=100"));
const hook = readFileSync(new URL("../custom_components/loona/frontend/pre-bootstrap.js", import.meta.url), "utf8");
const routeKey = path => { let value=2166136261; for(const byte of new TextEncoder().encode(path)) value=Math.imul(value^byte,16777619)>>>0; return value.toString(16).padStart(8,"0"); };
const tick = () => new Promise(setImmediate);
const unhandled = [];
process.on("unhandledRejection", error => unhandled.push(error));

async function run({path="/lovelace/0", delay=0, missing=false, absent=false, root=null, preference=null, system=null, legacy=null, foreign=false, enabled=true, withheld=false, hangRoot=false} = {}) {
  let selected = false;
  const sent = [];
  const acknowledgements = [];
  class Socket extends EventTarget {
    OPEN = 1; readyState = 1; haVersion = "2026.9.4";
    send(data) {
      const message = JSON.parse(data); sent.push({...message, selected});
      let result = null;
      if (message.type === "get_panels") result = {lovelace:{config:{mode:"storage"}},home:{},"wall-panel":{},config:{}};
      if (message.type === "frontend/get_user_data") result = {value:preference ? {default_panel:preference} : null};
      if (message.type === "frontend/get_system_data") result = {value:system ? {default_panel:system} : null};
      if (!absent && message.type === "loona/subscribe_panel") selected = ["lovelace", "wall-panel"].includes(message.dashboard);
      const reply = absent && message.type.startsWith("loona/")
        ? {id:message.id,type:"result",success:false,error:{code:"unknown_command",message:"Unknown command"}}
        : {id:message.id,type:"result",success:true,result};
      if (hangRoot && message.type === "get_panels") return;
      if (withheld && message.type === "loona/subscribe_panel") {
        acknowledgements.push(() => this.dispatchEvent(new MessageEvent("message", {data:JSON.stringify(reply)})));
        return;
      }
      queueMicrotask(() => {
        this.dispatchEvent(new MessageEvent("message", {data:JSON.stringify(reply)}));
        if (message.type === "subscribe_entities") this.dispatchEvent(new MessageEvent("message", {data:JSON.stringify({
          id:message.id,type:"event",event:{a:selected?{"sensor.wall":{s:"1",a:{},c:"context",lc:1700000000}}:{"sensor.wall":{s:"1",a:{},c:"context",lc:1700000000},"sensor.other":{s:"2",a:{},c:"context",lc:1700000000}}}
        })}));
      });
    }
    close() { this.readyState = 3; }
  }
  const conn = new Connection(new Socket(), {setupRetry:0});
  const value = {auth:{},conn};
  const window = {setTimeout,clearTimeout,addEventListener(){},setInterval(){},localStorage:{getItem:()=>legacy ? JSON.stringify(legacy) : null}};
  if (foreign) window.hassConnection = Promise.resolve(value);
  const context = vm.createContext({window,location:{pathname:path},URL,console,document:{querySelector:()=>null},customElements:{get:()=>undefined},TextEncoder});
  vm.runInContext(hook.replace("/* LOONA_CONFIG */ {}", JSON.stringify({timeout:30,routing:root,enabled,routes:["lovelace","wall-panel"].map(routeKey)})).replace("/* LOONA_REPORTER */",reporter), context);
  if (!missing && !delay) vm.runInContext(reporter, context);
  window.hassConnection = Promise.resolve(value);
  let states;
  const preload = window.hassConnection.then(({conn}) => {
    subscribeEntities(conn, next => { states = next; });
    conn.sendMessagePromise({type:"config/entity_registry/list_for_display"});
    conn.sendMessagePromise({type:"get_config"});
    if (path === "/" || path.startsWith("/lovelace/")) {
      conn.sendMessagePromise({type:"lovelace/config",url_path:null,force:false});
      conn.sendMessagePromise({type:"lovelace/resources"});
    }
  });
  if (delay) { await new Promise(resolve=>setTimeout(resolve,delay)); vm.runInContext(reporter, context); }
  assert.equal(await window.hassConnection, value); // Preserve the auth/connection result identity.
  await preload; await tick(); await tick();
  const stateCount = Object.keys(states).length;
  for (const acknowledge of acknowledgements) acknowledge();
  await tick();
  conn.close();
  return {sent,stateCount,status:window.__loonaBootstrap?.status};
}

for (const delay of [0,5]) {
  const result = await run({delay});
  assert.equal(result.status,"ready");
  assert.equal(result.stateCount,1);
  assert.ok(result.sent.filter(row=>!row.type.startsWith("loona/")).every(row=>row.selected));
  assert.equal(result.sent.filter(row=>row.type==="loona/subscribe_panel").length,1);
  assert.equal(result.sent.filter(row=>row.type==="subscribe_entities").length,1);
  assert.ok(result.sent.find(row=>row.type==="lovelace/resources").selected);
  assert.equal(new Set(result.sent.map(row=>row.id)).size,result.sent.length);
}
for (const options of [
  {root:{default:"lovelace",preferences:false}},
  {root:{default:"lovelace",preferences:false},legacy:"wall-panel"},
  {root:{default:"home",preferences:true},preference:"wall-panel",system:"config",legacy:"config"},
  {root:{default:"home",preferences:true},system:"wall-panel",legacy:"config"}
]) {
  const result = await run({path:"/",...options});
  assert.equal(result.stateCount,1); assert.equal(result.status,"ready");
}
for (const options of [
  {path:"/",root:{default:"home",preferences:true}},
  {path:"/",root:{default:"home",preferences:true},preference:"config"},
  {path:"/config/dashboard"}, {path:"/",root:null}, {absent:true}, {missing:true,foreign:true}, {enabled:false}, {path:"/unselected/0"}, {path:"/",root:{default:"lovelace",preferences:false},hangRoot:true}
]) {
  const result = await run(options);
  assert.equal(result.stateCount,2);
}
assert.equal((await run({missing:true})).stateCount,1,"Inline reporter does not depend on extra module loading");
assert.equal((await run({withheld:true})).stateCount,1,"Preload completes before the context acknowledgement");
assert.equal((await run({enabled:false})).status,undefined);
assert.equal((await run({path:"/config/dashboard"})).status,undefined);

// Native auth failure must still reject; the hook must never replace it with success.
const window = {setTimeout,clearTimeout};
const context = vm.createContext({window,location:{pathname:"/lovelace/0"},TextEncoder});
vm.runInContext(hook.replace("/* LOONA_CONFIG */ {}", "{timeout:30,routing:null,enabled:true,routes:null}"),context);
const failure = new Error("native auth failure");
window.hassConnection = Promise.reject(failure);
await assert.rejects(window.hassConnection,error=>error===failure);
await tick(); assert.deepEqual(unhandled,[]);
console.log("Passed pre-bootstrap context, delayed module, root routing and native fallbacks");
