// Public SVG privacy, partial results and the shipped card's admin boundary.
import assert from "node:assert/strict";
import {build} from "esbuild";
import {Window} from "happy-dom";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const window=new Window({url:"http://ha.test/wall-panel/main"});
for(const key of ["document","customElements","HTMLElement","Element","Node","MutationObserver","CustomEvent","Event","location","sessionStorage","localStorage","getComputedStyle"]) globalThis[key]=window[key];
globalThis.window=window;
const source=(await build({entryPoints:["custom_components/loona/frontend/benchmark-card.js"],bundle:true,write:false,format:"esm"})).outputFiles[0].text;
const {benchmarkSvg,benchmarkMetrics}=await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
const row={warmup:false,ready_ms:1000,duration_ms:30000,initial_entities:5,initial_bytes:1000,registry_bytes:500,updates:0,update_bytes:0,loaf_supported:false,startup_blocking_ms:0,blocking_ms:0,startup_frames:0,frames:0,resources:[{source:"https://private-host/local/private-card.js",bytes:null,cached:false,before_ready:false}],scripts:[],issues:[],browser:"private-device",viewport:[1000,800]};
const report={version:"0.9.10",core_version:"2026.9.4",seconds:30,controls:{enabled:true},samples:["native","loona","loona","native","native","loona"].map(mode=>({...row,mode}))};
for(const language of ["en","zh-Hans"]) {
 const root=benchmarkSvg(report,{language},320);
 assert.ok(!root.outerHTML.includes("private"));
 assert.ok(!root.outerHTML.includes("wall-panel"));
 assert.ok(root.querySelectorAll("text").length>25);
 assert.equal(benchmarkMetrics(report)[2].status,"Incomplete measurement");
 assert.equal(benchmarkMetrics(report)[3].status,"No updates observed");
 assert.equal(benchmarkMetrics(report)[4].medians[0],null,"Unsupported blocking is never zero");
}
const card=document.createElement("loona-benchmark-card");card.setConfig({type:"custom:loona-benchmark-card"});document.body.append(card);
card.hass={user:{id:"admin",is_admin:true},language:"en"};card._report=report;card._render();
assert.equal(card.shadowRoot.querySelector("header").hidden,true);
assert.ok(card.shadowRoot.querySelector("#details").textContent.includes("private-card.js"));
assert.ok(!card.shadowRoot.querySelector("#report").textContent.includes("private-card.js"));
assert.equal(card.shadowRoot.querySelector("details").open,false);
card.hass={user:{id:"guest",is_admin:false},language:"en"};
assert.equal(card.shadowRoot.querySelector("#report").children.length,0);
assert.ok(card.shadowRoot.textContent.includes("Sign in as an administrator"));
card.remove();
// The early hook sees the mobile default viewport before HA's meta tag applies.
const callbacks=[], documentState={readyState:"loading",hidden:false,addEventListener(){},removeEventListener(){},children:[]};
const context={benchmark:{index:0,viewport:[390,844]},config:{benchmark_key:"loona.benchmark",benchmark_limits:{requests:500}},
  window:{dispatchEvent(){},addEventListener(){},removeEventListener(){}},document:documentState,
  navigator:{userAgent:"Test"},innerWidth:980,innerHeight:2121,TextEncoder,Event,
  performance:{now:()=>100},setTimeout:fn=>{callbacks.push(fn);return callbacks.length;},clearTimeout(){},
  sessionStorage:{setItem(){},removeItem(){}}};
vm.runInNewContext(readFileSync("custom_components/loona/frontend/benchmark-runner.js","utf8"),context);
await context.window.loonaBenchmark.attach({socket:{send(){},addEventListener(){},removeEventListener(){}},sendMessagePromise:async()=>({resource_urls:[],ready_ms:30000})});
callbacks.shift()();assert.equal(context.window.loonaBenchmark.status,"loading");
documentState.readyState="complete";context.innerWidth=390;context.innerHeight=844;
callbacks.shift()();assert.equal(context.window.loonaBenchmark.status,"loading");
assert.deepEqual(Array.from(context.window.loonaBenchmark.sample.viewport),[390,844]);
context.innerWidth=844;context.innerHeight=390;
callbacks.shift()();assert.equal(context.window.loonaBenchmark.status,"error");
console.log("Passed: benchmark SVG privacy, honest partial metrics, disclosure and admin boundary");
