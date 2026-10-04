import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
import {Window} from "happy-dom";

const window=new Window({url:"http://ha.test/wall-panel/main"}), document=window.document;
let now=0, next=0;
const timers=new Map(), sent=[];
window.setTimeout=(fn,ms)=>{timers.set(++next,{fn,at:now+ms});return next;};
window.clearTimeout=id=>timers.delete(id);
function advance(ms) {
  const end=now+ms;
  while (true) {
    const row=[...timers].filter(([,timer])=>timer.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];
    if (!row) break;
    now=row[1].at;timers.delete(row[0]);row[1].fn();
  }
  now=end;
}
let publish;
const policy={version:"0.9.10",enabled:true,after_ms:60000,refresh_seconds:60};
const connection={connected:true,socket:{},
  subscribeMessage(callback,message) { sent.push(message);publish=callback;callback({idle:policy});return Promise.resolve(()=>{}); },
  sendMessagePromise(message) {sent.push(message);return Promise.resolve(null);},
};
const app=document.createElement("home-assistant");app.hass={connection};document.body.append(app);
const source=readFileSync(new URL("../custom_components/loona/frontend/panel-context.js",import.meta.url),"utf8")
  .replace('import "./resource-loading.js?v=0.9.10";',readFileSync(new URL("../custom_components/loona/frontend/resource-loading.js",import.meta.url),"utf8"))
  .replaceAll("import.meta.url",JSON.stringify("http://ha.test/loona/panel-context.js?poll=0"));
vm.runInContext(source,vm.createContext({window,document,location:window.location,URL,Date:{now:()=>now},customElements:window.customElements,console}));
await new Promise(setImmediate);
assert.equal(sent[0].type,"loona/subscribe_panel");
assert.ok(!("idle" in sent[0]),"Old backends must accept the initial report");
const before=sent.length;
for (let i=0;i<90;i++) { advance(1000);document.dispatchEvent(new window.Event("pointermove")); }
assert.equal(sent.length,before,"Mouse activity should not create report traffic while already live");
advance(59999);assert.equal(sent.length,before);
advance(1);assert.equal(sent.at(-1).idle,true);
document.dispatchEvent(new window.Event("pointerdown"));
assert.equal(sent.at(-1).type,"loona/panel");assert.ok(!("idle" in sent.at(-1)),"Interaction wakes immediately");
advance(60000);assert.equal(sent.at(-1).idle,true);
window.history.pushState(null,"","/wall-panel/energy");window.dispatchEvent(new window.Event("location-changed"));
assert.equal(sent.at(-1).view,"energy");assert.ok(!("idle" in sent.at(-1)),"Navigation wakes immediately");
advance(60000);assert.equal(sent.at(-1).idle,true);
window.dispatchEvent(new window.CustomEvent("show-dialog",{detail:{dialogTag:"test-dialog"}}));
assert.equal(sent.at(-1).expanded,true);assert.ok(!("idle" in sent.at(-1)));
const expanded=sent.length;advance(120000);assert.equal(sent.length,expanded,"Open dialogs remain live");
window.dispatchEvent(new window.CustomEvent("dialog-closed",{detail:{dialog:"test-dialog"}}));
advance(60000);assert.equal(sent.at(-1).idle,true);
publish({idle:{...policy,enabled:false}});
assert.ok(!("idle" in sent.at(-1)));assert.equal(timers.size,0,"Disabled idle mode owns no timer");
publish({idle:{...policy,refresh_seconds:0}});advance(60000);
assert.equal(sent.at(-1).idle,true,"Zero refresh can still enter idle mode");
document.dispatchEvent(new window.Event("keydown"));assert.ok(!("idle" in sent.at(-1)));
advance(60000);assert.equal(sent.at(-1).idle,true);
connection.socket={};window.dispatchEvent(new window.Event("location-changed"));
await new Promise(setImmediate);
assert.equal(sent.at(-1).type,"loona/subscribe_panel");
assert.ok(!("idle" in sent.at(-1)),"A fresh socket starts with fresh live context");
publish({idle:{...policy,enabled:false}});
window.happyDOM.abort();
console.log("Idle reporting passes inactivity, mouse/keyboard wake, navigation, dialogs, disable and zero refresh");
