// Exercise cache recovery through the runner's complete observation and save flow.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const urls=["/known.js","/cached.js","/missing.js","/timeout.js","/empty.js","https://other.test/card.js"];
const origin="http://ha.test", entries=urls.map((url,index)=>({name:new URL(url,origin).href,decodedBodySize:index===0 ? 123 : 0,transferSize:0,responseEnd:10}));
const fetched=[],observers=[],events=[];
let submitted,resolveDone;
const done=new Promise(resolve=>{resolveDone=resolve;});
class Observer {
  static supportedEntryTypes=["resource"];
  constructor() {this.disconnected=false;observers.push(this);}
  observe() {}
  takeRecords() {return [];}
  disconnect() {this.disconnected=true;}
}
const socket={send(){},addEventListener(){},removeEventListener(){}};
const context={benchmark:{index:0,dashboard:"wall-panel",view:"main"},
  config:{benchmark_key:"loona.benchmark",benchmark_limits:{requests:500,resources:200}},
  window:{dispatchEvent(){},addEventListener(){},removeEventListener(){}},
  document:{readyState:"complete",hidden:false,children:[],addEventListener(){},removeEventListener(){}},
  navigator:{userAgent:"WebKit fixture"},innerWidth:1000,innerHeight:800,TextEncoder,Event,URL,AbortController,PerformanceObserver:Observer,
  location:{origin,href:origin+"/wall-panel/main",pathname:"/wall-panel/main",reload(){resolveDone();}},
  performance:{now:()=>100,getEntriesByType:()=>entries},setTimeout,clearTimeout,
  sessionStorage:{setItem(){},removeItem(){}},
  fetch:async (url,options)=>{
    assert.equal(context.window.loonaBenchmark.status,"saving","Read cache only after observation stops");
    assert.ok(observers.every(observer=>observer.disconnected));
    assert.equal(options.cache,"only-if-cached");
    assert.equal(options.mode,"same-origin");
    assert.equal(options.credentials,"same-origin");
    fetched.push(url);
    if(url.endsWith("missing.js")) return {ok:false,status:504};
    if(url.endsWith("timeout.js")) return new Promise((resolve,reject)=>options.signal.addEventListener("abort",()=>{events.push("aborted");reject(new Error("Aborted"));}));
    return {ok:true,blob:async()=>new Blob(url.endsWith("empty.js") ? [] : ["缓存脚本"])};
  }};
vm.runInNewContext(readFileSync("custom_components/loona/frontend/benchmark-runner.js","utf8"),context);
await context.window.loonaBenchmark.attach({connected:true,socket,sendMessagePromise:async message=>{
  if(message.action==="attach") return {resource_urls:urls,ready_ms:1,seconds:0,cache_read_ms:10};
  assert.equal(message.action,"pass");submitted=message.sample;
  return {status:"running",index:1};
}});
await done;
assert.equal(submitted.loaf_supported,false,"Unsupported blocking never starts an observer");
assert.equal(observers.length,1);
assert.equal(submitted.resources.length,6,"Recovery adds no files to the measured list");
assert.equal(submitted.resources[0].bytes,123,"Keep measured sizes");
assert.equal(submitted.resources[1].bytes,new Blob(["缓存脚本"]).size,"Recover decoded byte size, not character count or compressed size");
assert.ok(submitted.resources.slice(2).every(row=>row.bytes===null),"Cache miss, timeout, empty body and cross-origin files stay unknown");
assert.equal(fetched.length,4);
assert.ok(fetched.every(url=>url.startsWith(origin)),"Never probe cross-origin files");
assert.deepEqual(events,["aborted"]);
console.log("Passed: post-observation cache-only size recovery, misses, bounded timeout and unchanged file counts");
