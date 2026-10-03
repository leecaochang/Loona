import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
import {Window} from "happy-dom";

const source = readFileSync(new URL("../custom_components/loona/frontend/resource-loading.js", import.meta.url), "utf8");
const heavy = {id:"heavy", url:"/local/apexcharts-card.js?v=42", type:"module"};
const second = {id:"second", url:"/local/button-card.js?tag=2", type:"module"};
const plan = {enabled:true, defer:[heavy.url,second.url], quiet_ms:750, max_ms:10000, load_ms:10000, idle_ms:1000};
const settle = async () => { for(let i=0;i<12;i++) await Promise.resolve(); };
function fixture() {
  const window = new Window({url:"http://test/wall-panel/main"});
  const {document, location} = window;
  let now = 0, id = 0;
  const timers = new Map(), scripts = [];
  window.setTimeout = (fn,ms) => { timers.set(++id,{fn,at:now+ms});return id; };
  window.clearTimeout = timer => timers.delete(timer);
  document.head.append = element => scripts.push(element);
  const advance = ms => {
    const end = now+ms;
    while(true) {
      const next = [...timers.entries()].filter(([,row])=>row.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];
      if (!next) break;
      now=next[1].at;timers.delete(next[0]);next[1].fn();
    }
    now=end;
  };
  vm.runInContext(source,vm.createContext({window,document,location,URL,console}));
  const loader = window.loonaCreateResourceLoader();
  return {window,loader,scripts,timers,advance,ready:()=>window.dispatchEvent(new window.Event("hass-panel-ready"))};
}

// Lists remain native without an early hook, a valid plan or a complete scan.
for (const value of [undefined,{...plan,enabled:false},{...plan,load_ms:0}]) {
  const f=fixture();f.loader.policy(value);
  const rows=[heavy,second];assert.equal(f.loader.select(rows),rows);
  assert.equal(f.scripts.length,0);assert.equal(f.timers.size,0);
}
{
  const f=fixture(), rows=[heavy];
  const late=f.window.loonaCreateResourceLoader(false);late.policy(plan);
  assert.equal(late.select(rows),rows);
}

// Preserve classic scripts, styles, unknown modules and newly versioned URLs.
{
  const f=fixture();f.loader.policy(plan);
  const immediate=[{...heavy,type:"js"},{url:"/local/theme.css",type:"css"},
    {url:"/local/unknown.js",type:"module"},{...heavy,url:heavy.url+"-new"}];
  const rows=[heavy,...immediate,second];
  assert.deepEqual([...f.loader.select(rows)],immediate);
  assert.equal(f.scripts.length,0);f.ready();f.advance(749);assert.equal(f.scripts.length,0);
  f.advance(1);assert.equal(f.scripts.length,1);assert.equal(f.scripts[0].src,"http://test"+heavy.url);
  assert.equal(f.scripts[0].type,"module");f.scripts[0].onload();await settle();f.advance(0);
  assert.equal(f.scripts.length,2,"Idle loading is sequential");f.scripts[1].onload();await settle();
  assert.equal(f.window.__loonaResourceLoading.status,"complete");assert.equal(f.timers.size,0);
  assert.equal(f.loader.select(rows),rows,"Later editor/list requests remain intact");
}

// Navigation includes view and editing-query changes, even during an in-flight load.
for (const path of ["/wall-panel/other","/config","/wall-panel/main?edit=1"]) {
  const f=fixture();f.loader.policy(plan);f.loader.select([heavy,second]);f.ready();f.advance(750);
  f.window.history.pushState(null,"",path);f.loader.route();
  assert.equal(f.scripts.length,2,"Navigation immediately starts all remaining modules");
  f.scripts[1].onload();await settle();assert.notEqual(f.window.__loonaResourceLoading.status,"complete");
  f.scripts[0].onload();await settle();assert.equal(f.window.__loonaResourceLoading.status,"complete");
  assert.equal(f.timers.size,0);
}

// Disabling and unloading flush without waiting for readiness or idle callbacks.
for (const action of [f=>f.loader.policy({...plan,enabled:false}),f=>f.loader.stop()]) {
  const f=fixture();f.loader.policy(plan);f.loader.select([heavy,second]);action(f);
  assert.equal(f.scripts.length,2);
  for(const script of f.scripts)script.onload();await settle();assert.equal(f.timers.size,0);
}

// Missing native readiness has a deadline; network failures release the rest.
{
  const f=fixture();f.loader.policy(plan);f.loader.select([heavy,second]);f.advance(10000);
  assert.equal(f.scripts.length,2);
  f.scripts[0].onerror();await settle();assert.equal(f.scripts.length,3,"Retry uses the same module URL once");
  assert.equal(f.scripts[2].src,f.scripts[0].src);f.scripts[2].onerror();f.scripts[1].onload();await settle();
  assert.equal(f.scripts.length,3);assert.equal(f.window.__loonaResourceLoading.status,"fallback");
  assert.equal(f.timers.size,0);
}
{
  const f=fixture();f.loader.policy(plan);f.loader.select([heavy,second]);f.ready();f.advance(750);
  f.advance(10000);assert.equal(f.scripts.length,2,"Timeout must not duplicate the in-flight module");
  f.scripts[1].onload();await settle();assert.equal(f.window.__loonaResourceLoading.status,"fallback");
}
console.log("Resource deferral preserves native lists and passes idle, navigation, editing, unload and failure checks");

// Prefetch only authenticated same-origin asset URLs without module execution.
{
  const f=fixture(),rows=[heavy,second];
  const preload=[heavy.url,heavy.url,"https://elsewhere/local/x.js","/local/../../api/x","/hacsfiles/card/x.js?42","/uix/uix.js","/api/x"];
  f.loader.policy({...plan,enabled:false,preload});
  assert.equal(f.loader.select(rows),rows);
  assert.deepEqual(f.scripts.map(n=>n.rel),["modulepreload","modulepreload","modulepreload"]);
  assert.equal(f.scripts[0].href,"http://test"+heavy.url);
  f.loader.policy({...plan,enabled:false,preload});assert.equal(f.scripts.length,3);
  f.loader.stop();f.loader.policy({...plan,preload:[second.url]});assert.equal(f.scripts.length,3);
}
