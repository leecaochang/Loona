// Public SVG privacy, partial results and the shipped card's admin boundary.
import assert from "node:assert/strict";
import {build} from "esbuild";
import {Window} from "happy-dom";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const earlyWindow=new Window({url:"http://ha.test/wall-panel/main"});
const globals=["document","customElements","HTMLElement","Element","Node","MutationObserver","CustomEvent","Event","location","sessionStorage","localStorage","getComputedStyle"];
for(const key of globals) globalThis[key]=earlyWindow[key];
globalThis.window=earlyWindow;
const registrationTimers=[];
earlyWindow.setTimeout=fn=>{registrationTimers.push(fn);return registrationTimers.length;};
const source=(await build({entryPoints:["custom_components/loona/frontend/benchmark-card.js"],bundle:true,write:false,format:"esm"})).outputFiles[0].text;
const {benchmarkSvg,benchmarkMetrics,benchmarkText,benchmarkFilename}=await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
assert.equal(earlyWindow.customElements.get("loona-benchmark-card"),undefined,"Do not register against HA's pre-bootstrap registry");
const window=new Window({url:"http://ha.test/wall-panel/main"});
for(const key of globals) globalThis[key]=window[key];
globalThis.window=window;
const app=document.createElement("home-assistant");app.hass={user:{id:"admin",is_admin:true}};document.body.append(app);
registrationTimers.shift()();
assert.ok(customElements.get("loona-benchmark-card"),"Register against HA's replacement registry");
assert.ok(window.customCards.some(row=>row.type==="loona-benchmark-card"),"Expose the card to the native picker after bootstrap");
const row={warmup:false,ready_ms:1000,duration_ms:30000,initial_entities:5,initial_bytes:1000,registry_bytes:500,updates:0,update_bytes:0,loaf_supported:false,startup_blocking_ms:0,blocking_ms:0,startup_frames:0,frames:0,resources:[{source:"https://private-host/local/private-card.js",bytes:null,cached:false,before_ready:false}],scripts:[],issues:[],browser:"private-device",viewport:[1000,800]};
const report={version:"1.0.0",core_version:"2026.9.4",seconds:30,completed_at:"2026-10-04T10:15:23Z",dashboard_title:"Private dashboard / display",view_title:"Private tab",names:{dashboards:{"wall-panel":"Wall display"}},settings:{dashboards:["wall-panel"],dashboard_cards:["benchmark"],target_mode:"all",user_ids:[]},controls:{enabled:true,entity_filtering:true},samples:["native","loona","loona","native","native","loona"].map(mode=>({...row,mode}))};
for(const language of ["en","zh-Hans"]) {
 const root=benchmarkSvg(report,{language},320);
 assert.ok(!root.outerHTML.includes("private"));
 assert.ok(!root.outerHTML.includes("wall-panel"));
 assert.ok(root.querySelectorAll("text").length>25);
 assert.equal(benchmarkMetrics(report)[2].countOnly,true);
 assert.equal(benchmarkMetrics(report)[2].status,"No measurable change");
 assert.equal(benchmarkMetrics(report)[3].status,"No updates observed");
 assert.equal(benchmarkMetrics(report).length,4,"Unsupported blocking is omitted");
 assert.ok(!root.textContent.includes(language==="en" ? "Browser blocking" : "浏览器阻塞"));
 assert.ok(root.textContent.includes("Loona 1.0.0"));
 assert.ok(!root.textContent.includes("Some results are inconclusive"));
}
const changed=structuredClone(report);
changed.samples.forEach((sample,index)=>{sample.ready_ms=sample.mode==="native" ? 600+index*10 : 630+index*10;sample.initial_bytes=sample.mode==="native" ? 9500 : 500;sample.resources=sample.resources.map(resource=>({...resource,bytes:sample.mode==="native" ? 1000 : 500}));sample.updates=sample.mode==="native" ? 300 : 30;});
assert.equal(benchmarkMetrics(changed)[0].status,"No clear timing difference");
assert.equal(benchmarkMetrics(changed)[1].percent,90);
assert.equal(benchmarkMetrics(changed)[3].percent,90);
assert.equal(benchmarkMetrics(changed)[2].countOnly,false);
assert.equal(benchmarkMetrics(changed)[2].status,"{percent}% less file data");
// The image always uses the compact name at any width; the report text spells it out.
for(const width of [280,420]) {
  assert.ok(benchmarkSvg(changed,{language:"en"},width).textContent.includes("Native HA and your saved Loona settings"));
  assert.ok(!benchmarkSvg(changed,{language:"en"},width).textContent.includes("Native Home Assistant"));
}
assert.ok(benchmarkSvg(changed,{language:"zh-Hans"},420).textContent.includes("原生 HA"));
const missingSizes=structuredClone(changed);
missingSizes.samples.forEach(sample=>{sample.resources=Array.from({length:sample.mode==="native" ? 27 : 15},()=>({...row.resources[0],bytes:1000}));});
missingSizes.samples[0].resources[0].bytes=null;
const fileCountMetric=benchmarkMetrics(missingSizes)[2];
assert.equal(fileCountMetric.countOnly,true,"One missing size switches both modes to counts");
assert.deepEqual(fileCountMetric.medians,[27,15]);
assert.equal(fileCountMetric.status,"{percent}% fewer files");
assert.equal(Math.round(fileCountMetric.percent),44);
assert.ok(benchmarkSvg(missingSizes,{language:"en"},420).textContent.includes("44% fewer files"));
assert.ok(benchmarkSvg(missingSizes,{language:"zh-Hans"},420).textContent.includes("文件数量减少 44%"));
assert.ok(benchmarkText(missingSizes,{language:"en"}).includes("| Card files loaded | 27 card files | 15 card files |"));
const tooFew=structuredClone(missingSizes);tooFew.samples=tooFew.samples.slice(0,4);
assert.equal(benchmarkMetrics(tooFew)[2].status,"Incomplete measurement","Counts still require three readings per mode");
const supported=structuredClone(changed);
supported.samples.forEach(sample=>{sample.loaf_supported=true;sample.blocking_ms=sample.mode==="native" ? 100 : 20;});
assert.equal(benchmarkMetrics(supported).length,5);
assert.equal(benchmarkMetrics(supported)[4].percent,80);
assert.ok(benchmarkText(supported,{language:"en"}).includes("Blocking (ms)"));
assert.equal(Number(benchmarkSvg(supported,{language:"en"}).getAttribute("height"))-Number(benchmarkSvg(changed,{language:"en"}).getAttribute("height")),164,"Unsupported blocking removes one full panel");
const mixedSupport=structuredClone(supported);mixedSupport.samples[0].loaf_supported=false;
assert.equal(benchmarkMetrics(mixedSupport)[4].status,"Incomplete measurement","Missing supported-browser readings are never interpreted as zero");
const reportText=benchmarkText(report,{language:"en"});
assert.ok(reportText.startsWith("# Benchmark Results\n\n## Executive summary\n"));
assert.ok(reportText.includes("| Entity filtering | Enabled |"));
assert.ok(reportText.includes("| Dashboards | Wall display |"));
assert.ok(!reportText.includes("entity_filtering"));
assert.ok(!reportText.includes("private-card.js"));
assert.ok(reportText.includes("Settings &gt; Dashboards &gt; Resources"));
assert.ok(reportText.includes("| Measurement | Native Home Assistant | Loona |\n| --- | --- | --- |"));
assert.ok(reportText.includes("## Individual passes\n\n| Pass | Mode |"));
assert.ok(!reportText.includes("Browser blocking:") && !reportText.includes("Blocking (ms)"));
assert.ok(reportText.includes("use WebKit") && reportText.includes("file counts for both modes"));
assert.ok(reportText.includes("## Caveats\n") && !reportText.includes("Measurement limits"));
assert.ok(reportText.includes("## Saved settings\n\nThis report can include dashboard and account names, entity names, card file addresses and browser details. Review it before posting.\n\n| Setting | Value |"));
assert.ok(reportText.includes("Blocking was skipped") && reportText.includes("Chrome and Edge 123+") && reportText.includes("does not shorten the run"));
const hostile=structuredClone(report);hostile.dashboard_title='Room | <img src=x onerror=alert(1)> **bold** [link](https://private)\n# heading';
const escaped=benchmarkText(hostile,{language:"en"});
assert.ok(escaped.includes('Room \\| &lt;img'));
assert.ok(!escaped.includes('<img'));
assert.ok(escaped.includes('\\*\\*bold\\*\\* \\[link\\]'));
assert.ok(escaped.includes('<br>\\# heading'));
assert.equal(benchmarkFilename(report,"png"),"loona-1.0.0-benchmark-Private-dashboard-display-20261004T101523Z.png");
const card=document.createElement("loona-benchmark-card");card.setConfig({type:"custom:loona-benchmark-card"});document.body.append(card);
card.hass={user:{id:"admin",is_admin:true},language:"en"};card._report=report;card._render();
assert.equal(card.shadowRoot.querySelector("header").hidden,true);
assert.ok(card.shadowRoot.querySelector("#details").textContent.startsWith("Executive summary"));
assert.ok(!card.shadowRoot.querySelector("#report").textContent.includes("private-card.js"));
assert.equal(card.shadowRoot.querySelector("details").open,false);
assert.equal(card.shadowRoot.querySelector("summary").textContent,"Detailed report");
assert.equal(card.shadowRoot.querySelectorAll("#details table").length,4);
assert.equal(card.shadowRoot.querySelector("#details table th").scope,"col");
assert.ok(card.shadowRoot.querySelector("#details .table-scroll").hasAttribute("tabindex"));
assert.deepEqual([...card.shadowRoot.querySelectorAll("#text-actions button")].map(node=>node.textContent.trim()),["Copy text","Save text"]);
window.loonaBenchmark={status:"error",reason:"Interaction interrupted measurement. Keep the page still and start over."};
sessionStorage.setItem("loona.benchmark.error",window.loonaBenchmark.reason);
card._render();card.shadowRoot.querySelector("details").open=true;
assert.equal(card.shadowRoot.querySelector("#message").hidden,true,"Failure reason belongs only in the detailed report");
assert.equal(card.shadowRoot.querySelector("#details").textContent.match(/Interaction interrupted/g).length,1);
assert.ok(card.shadowRoot.querySelector("#report").textContent.includes("Loona 1.0.0"),"Errors also carry the version");
card._startOver();
assert.equal(window.loonaBenchmark,undefined);
assert.equal(card._report,null);
assert.equal(card.shadowRoot.querySelector("details").open,false);
assert.equal(card.shadowRoot.querySelector("#actions button").textContent.trim(),"Go");
assert.equal(card.shadowRoot.querySelector("#version").textContent,"Version: 1.0.0");
card._report=report;card._render();card._showCopyTip();
assert.equal(card.shadowRoot.querySelector("#copy-tip").hidden,false);
assert.ok(card.shadowRoot.querySelector("#copy-tip").textContent.includes("image above"));
document.dispatchEvent(new window.KeyboardEvent("keydown",{key:"Escape"}));
assert.equal(card.shadowRoot.querySelector("#copy-tip").hidden,true);
card.hass={user:{id:"guest",is_admin:false},language:"en"};
assert.equal(card.shadowRoot.querySelector("#report").children.length,0);
assert.ok(card.shadowRoot.textContent.includes("Sign in as an administrator"));
card.remove();
// Blocked site data leaves the card usable and stops a run before the server opens it.
const browserStorage={sessionStorage:globalThis.sessionStorage,localStorage:globalThis.localStorage};
for(const name of Object.keys(browserStorage)) Object.defineProperty(globalThis,name,{configurable:true,get(){throw new Error("SecurityError");}});
const started=[];
const blocked=document.createElement("loona-benchmark-card");blocked.setConfig({type:"custom:loona-benchmark-card"});document.body.append(blocked);
blocked.hass={user:{id:"admin",is_admin:true},language:"en",callWS:async request=>{started.push(request);return {token:"t",session_seconds:60};}};
await blocked._start();
assert.equal(started.length,0,"No server run without session storage");
assert.equal(blocked.shadowRoot.querySelector("#message").textContent,"The benchmark needs browser storage. Allow this site to store data, then try again.");
blocked._startOver();blocked.remove();
for(const [name,value] of Object.entries(browserStorage)) Object.defineProperty(globalThis,name,{configurable:true,writable:true,value});
// Storage failing mid-run never skips the server cancellation.
const runnerMessages=[];let reloads=0;
const failingStorage={setItem(){throw new Error("QuotaExceededError");},removeItem(){throw new Error("SecurityError");},getItem(){throw new Error("SecurityError");}};
const failing={benchmark:{index:0,token:"run",viewport:[980,2121]},config:{benchmark_key:"loona.benchmark",benchmark_limits:{requests:500}},
  window:{dispatchEvent(){},addEventListener(){},removeEventListener(){}},document:{readyState:"loading",hidden:false,addEventListener(){},removeEventListener(){},children:[]},
  navigator:{userAgent:"Test"},innerWidth:980,innerHeight:2121,TextEncoder,Event,URL,location:{href:"http://ha.test/wall-panel/main",reload(){reloads++;}},
  performance:{now:()=>100},setTimeout:()=>0,clearTimeout(){},sessionStorage:failingStorage};
vm.runInNewContext(readFileSync("custom_components/loona/frontend/benchmark-runner.js","utf8"),failing);
await failing.window.loonaBenchmark.attach({socket:{send(){},addEventListener(){},removeEventListener(){}},sendMessagePromise:async message=>{runnerMessages.push(message);return {resource_urls:[],ready_ms:30000};}});
failing.window.loonaBenchmark.fail("Interrupted");
assert.equal(failing.window.loonaBenchmark.status,"error");
await failing.window.loonaBenchmark.cancel();
assert.deepEqual(runnerMessages.filter(message=>message.action==="cancel").map(message=>message.token),["run","run"]);
assert.equal(reloads,1);
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
