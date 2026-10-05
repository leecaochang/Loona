// Native HA exposes asynchronous icon paths separately from Lit's first render.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const source=readFileSync("custom_components/loona/frontend/benchmark-runner.js","utf8");
const rect={width:24,height:24,top:20,bottom:44,left:20,right:44};
const element=(tag,props={})=>({tagName:tag,children:[],isConnected:true,hidden:false,
  getBoundingClientRect:()=>rect,checkVisibility:()=>true,...props});
const root=(children)=>({children,querySelector:selector=>children.find(node=>node.tagName===selector.toUpperCase())});

async function fixture(extra=[]) {
  let now=100,callback,received;
  const commands=new Map();
  const card=element("HUI-CARD",{config:{type:"entity"},_element:element("HUI-ENTITY-CARD")});
  const socket={send(){},addEventListener(type,handler){if(type==="message") received=handler;},removeEventListener(){}};
  const context={benchmark:{index:0,dashboard:"wall-panel",view:"main"},
    config:{benchmark_key:"loona.benchmark",benchmark_limits:{requests:500,nodes:10000}},
    window:{dispatchEvent(){},addEventListener(){},removeEventListener(){}},
    document:{readyState:"complete",hidden:false,children:[card,...extra],fonts:{status:"loaded"},addEventListener(){},removeEventListener(){}},
    navigator:{userAgent:"Readiness fixture"},innerWidth:1000,innerHeight:800,TextEncoder,Event,URL,
    performance:{now:()=>now},setTimeout:fn=>{callback=fn;return 1;},clearTimeout(){},
    location:{pathname:"/wall-panel/main",href:"http://ha.test/wall-panel/main"},
    sessionStorage:{setItem(){},removeItem(){}}};
  vm.runInNewContext(source,context);
  const connection={connected:true,commands,socket,sendMessagePromise:async()=>({resource_urls:[],ready_ms:30000,seconds:30})};
  await context.window.loonaBenchmark.attach(connection);
  socket.send(JSON.stringify({id:2,type:"subscribe_entities"}));
  received({data:JSON.stringify({id:2,type:"event",event:{a:{"sensor.wall":{}}}})});
  return {context,commands,card,state:context.window.loonaBenchmark,step(time){now=time;callback();}};
}

const svg=element("HA-SVG-ICON",{path:undefined});
const icon=element("HA-ICON",{icon:"mdi:thermometer",shadowRoot:root([svg])});
const a=await fixture([icon]);
a.step(100);a.step(1100);a.step(3100);
assert.equal(a.state.status,"loading","An empty native icon must hold the entire pass, including warm-up");
svg.path="M0 0h24v24H0z";svg.isUpdatePending=true;
a.step(3200);a.step(3800);
assert.equal(a.state.status,"loading","A resolved icon still needs its SVG render");
svg.isUpdatePending=false;a.step(4000);a.step(4500);
assert.equal(a.state.status,"observing");assert.equal(a.state.sample.ready_ms,4000);

for (const [name,node,release] of [
  ["visible image",element("IMG",{complete:false}),node=>{node.complete=true;}],
  ["visible Lit render",element("HUI-ENTITY-CARD",{isUpdatePending:true}),node=>{node.isUpdatePending=false;}],
  ["visible spinner",element("HA-SPINNER"),node=>{node.hidden=true;}],
]) {
  const f=await fixture([node]);f.step(100);f.step(1000);
  assert.equal(f.state.status,"loading",name+" blocks readiness");
  release(node);f.step(1100);f.step(1600);assert.equal(f.state.status,"observing",name+" releases readiness");
}

const b=await fixture();b.context.document.fonts.status="loading";
b.step(100);b.step(1000);assert.equal(b.state.status,"loading","Fonts must settle");
b.context.document.fonts.status="loaded";
b.commands.set(3,{resolve(){}});b.step(1100);b.step(1700);
assert.equal(b.state.status,"loading","Pending native one-shot commands block readiness");
b.commands.delete(3);b.commands.set(4,{subscribe(){}});b.step(1800);b.step(2300);
assert.equal(b.state.status,"observing","Persistent subscriptions do not block readiness");

const c=await fixture([
  element("HA-ICON",{icon:"mdi:unavailable",checkVisibility:()=>false}),
  element("HA-ICON",{icon:"mdi:offscreen",getBoundingClientRect:()=>({...rect,top:900,bottom:924})}),
  element("HA-ICON",{icon:undefined}),
  element("LOONA-BENCHMARK-CARD",{shadowRoot:root([icon])}),
]);
c.step(100);c.step(600);assert.equal(c.state.status,"observing","Hidden/off-screen/empty icons and the benchmark's own content are excluded");

const d=await fixture([element("HA-ICON",{icon:"mdi:unavailable",shadowRoot:root([])})]);
d.step(100);d.step(29900);assert.equal(d.state.status,"loading");
d.step(30100);assert.equal(d.state.sample.ready_ms,null,"Never fabricate readiness for a missing icon");
assert.equal(d.state.status,"observing","Unresolved readiness remains bounded by the existing timeout");

const e=await fixture();e.step(100);e.context.document.children.push(element("HA-ICON",{icon:"mdi:late"}));
e.step(500);e.step(1000);assert.equal(e.state.status,"loading","An icon appearing during the quiet interval resets readiness");
console.log("Passed: delayed native icons/renders, images/fonts, one-shot commands, visibility and bounded readiness");
