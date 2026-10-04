/* Included in the early bootstrap only for an explicitly started browser run. */
(() => {
  if (!benchmark) return;
  const key = config.benchmark_key;
  const marker = benchmark;
  const enc = new TextEncoder();
  const requests = new Map(), initialFeeds = new Set(), registered = new Set();
  const resources = new Map(), scripts = new Map(), issues = new Set();
  let connection, socket, report, stopped = false, observing = false, observationStart;
  let loafObserver, resourceObserver, timer, initialSend, entryCount = 0;
  const sample = {ready_ms:null, duration_ms:0, initial_entities:0, initial_bytes:0,
    registry_bytes:0, updates:0, update_bytes:0, loaf_supported:false,
    startup_blocking_ms:0, blocking_ms:0, startup_frames:0, frames:0,
    resources:[], scripts:[], issues:[], browser:navigator.userAgent.slice(0,256),
    viewport:[innerWidth,innerHeight]};
  const state = window.loonaBenchmark = {status:"authorizing", index:marker.index, sample,
    attach, cancel, fail, remaining:0};
  const publish = () => window.dispatchEvent(new Event("loona-benchmark"));
  const write = () => sessionStorage.setItem(key, JSON.stringify(marker));
  const jsonBytes = value => enc.encode(JSON.stringify(value)).length;
  const source = value => {
    try { const url=new URL(value,location.href); return ((url.origin===location.origin ? "" : url.origin)+url.pathname).slice(0,512); }
    catch { return "Unknown source"; }
  };
  const keepIssue = issue => { issues.add(issue); };
  const resourceEntry = entry => {
    if (!registered.has(entry.name)) return;
    const old=resources.get(entry.name);
    const value={source:source(entry.name),bytes:entry.decodedBodySize>0 ? entry.decodedBodySize : null,
      before_ready:sample.ready_ms!==null && entry.responseEnd<=sample.ready_ms,
      cached:entry.transferSize===0 && entry.decodedBodySize>0, end:entry.responseEnd};
    if (!old || old.end>value.end) {
      if (resources.size<config.benchmark_limits.resources) resources.set(entry.name,value);
      else keepIssue("observer_limit");
    }
  };
  const collectFrames = entries => {
    for (const frame of entries) {
      if (++entryCount>config.benchmark_limits.frames) { keepIssue("observer_limit"); break; }
      const steady=observationStart!==undefined && frame.startTime>=observationStart;
      sample[steady ? "frames" : "startup_frames"]++;
      sample[steady ? "blocking_ms" : "startup_blocking_ms"]+=frame.blockingDuration||0;
      for (const script of frame.scripts||[]) {
        if (!script.sourceURL) continue;
        const name=source(script.sourceURL), phase=steady ? "observation" : "startup", id=phase+name;
        if (!scripts.has(id) && scripts.size<config.benchmark_limits.scripts) scripts.set(id,{source:name,phase,duration_ms:0});
        const value=scripts.get(id); if (value) value.duration_ms+=script.duration||0;
      }
    }
  };
  if (typeof PerformanceObserver==="function") {
    sample.loaf_supported=PerformanceObserver.supportedEntryTypes?.includes("long-animation-frame")===true;
    if (sample.loaf_supported) {
      loafObserver=new PerformanceObserver(list=>collectFrames(list.getEntries()));
      loafObserver.observe({type:"long-animation-frame",buffered:true});
    }
    if (PerformanceObserver.supportedEntryTypes?.includes("resource")) {
      resourceObserver=new PerformanceObserver(list=>list.getEntries().forEach(resourceEntry));
      resourceObserver.observe({type:"resource",buffered:true});
    }
  }
  function received(event) {
    if (stopped || typeof event.data!=="string") return;
    let parsed; try { parsed=JSON.parse(event.data); } catch { return; }
    for (const value of Array.isArray(parsed) ? parsed : [parsed]) {
      const request=requests.get(value.id);
      if (!request) continue;
      if (value.type==="result" && value.success) {
        if (request.type.startsWith("config/") && request.type.includes("registry/list")) sample.registry_bytes+=jsonBytes(value);
        if (["lovelace/resources","lovelace/resources/list"].includes(request.type)) {
          for (const row of value.result||[]) {
            try { registered.add(new URL(row.url,location.href).href); } catch { /* Ignore malformed native rows. */ }
          }
        }
      }
      if (value.type!=="event") continue;
      if (request.type==="subscribe_entities") {
        const payload=value.event||{};
        if (!initialFeeds.has(value.id)) {
          if (!payload.a) continue;
          initialFeeds.add(value.id);
          sample.initial_entities+=Object.keys(payload.a).length;
          sample.initial_bytes+=jsonBytes(value);
        } else if (observing) {
          sample.updates+=Object.keys(payload.c||{}).length+Object.keys(payload.a||{}).length+(payload.r||[]).length;
          sample.update_bytes+=jsonBytes(value);
        }
      } else if (observing && request.type==="subscribe_events" && value.event?.event_type==="state_changed") {
        sample.updates++; sample.update_bytes+=jsonBytes(value);
      }
    }
  }
  function stop() {
    stopped=true; clearTimeout(timer);
    if (loafObserver) collectFrames(loafObserver.takeRecords());
    if (resourceObserver) resourceObserver.takeRecords().forEach(resourceEntry);
    loafObserver?.disconnect(); resourceObserver?.disconnect();
    socket?.removeEventListener("message",received);
    if (socket && socket.send===wrappedSend) socket.send=initialSend;
    document.removeEventListener("visibilitychange",visibility);
    window.removeEventListener("error",error,true);
    for (const type of ["pointerdown","keydown","scroll"]) document.removeEventListener(type,interaction,true);
  }
  function wrappedSend(raw) {
    if (typeof raw==="string") {
      try { const msg=JSON.parse(raw); if (requests.size<config.benchmark_limits.requests && msg.id) requests.set(msg.id,msg); }
      catch { /* Native websocket validation retains ownership. */ }
    }
    return initialSend.call(socket,raw);
  }
  async function attach(value) {
    if (!value || stopped) throw new Error("Benchmark connection is unavailable");
    connection=value; socket=value.socket; initialSend=socket.send; socket.send=wrappedSend;
    socket.addEventListener("message",received);
    try {
      report=await connection.sendMessagePromise({type:"loona/benchmark",action:"attach",token:marker.token,
        dashboard:marker.dashboard,view:marker.view,index:marker.index});
      state.report=report;
      for (const url of report.resource_urls||[]) { try { registered.add(new URL(url,location.href).href); } catch { /* Invalid rows remain native. */ } }
      state.status="loading"; publish();
      document.addEventListener("visibilitychange",visibility);
      window.addEventListener("error",error,true);
      for (const type of ["pointerdown","keydown","scroll"]) document.addEventListener(type,interaction,{capture:true,passive:true});
      timer=setTimeout(checkReady,100);
    } catch (err) { fail(err.message||err.code||"Startup authorization failed. Start over."); throw err; }
  }
  function error(event) {
    if (event.target?.tagName==="SCRIPT" || event.target?.tagName==="LINK") keepIssue("resource_error");
  }
  function interaction(event) {
    if (event.composedPath().some(node=>node?.tagName==="LOONA-BENCHMARK-CARD")) return;
    // HA's initial layout and restored scroll position are part of startup.
    if (observing && event.type==="scroll") fail("The viewport changed during measurement. Keep the page still and start over.");
    else if (event.type!=="scroll") fail("Interaction interrupted measurement. Keep the page still and start over.");
  }
  function visibility() {
    if (document.hidden && !stopped) {
      state.status="paused"; state.reason="Page hidden. Return to repeat this pass."; publish();
      stop();
      connection?.sendMessagePromise({type:"loona/benchmark",action:"retry",token:marker.token,index:marker.index})
        .then(()=>{
          const resume=()=>{ if (!document.hidden) { document.removeEventListener("visibilitychange",resume); location.reload(); } };
          document.addEventListener("visibilitychange",resume); resume();
        }).catch(err=>fail(err.message||"Could not repeat the interrupted pass. Start over."));
    }
  }
  function visibleCards() {
    const cards=[], loading=[]; let nodes=0;
    const visit=root=>{
      for (const element of root.children||[]) {
        if (++nodes>config.benchmark_limits.nodes) { keepIssue("observer_limit"); return; }
        if (element.tagName==="LOONA-BENCHMARK-CARD") continue;
        let visible=false;
        if (["HUI-CARD","HUI-ERROR-CARD","HA-SPINNER","HA-CIRCULAR-PROGRESS","MD-CIRCULAR-PROGRESS","LOONA-GRAPH-PLACEHOLDER"].includes(element.tagName)) {
          const rect=element.getBoundingClientRect();
          visible=rect.width>0 && rect.height>0 && rect.bottom>0 && rect.top<innerHeight && rect.right>0 && rect.left<innerWidth;
        }
        if (visible && element.tagName==="HUI-ERROR-CARD") keepIssue("card_error");
        if (visible && element.tagName==="HUI-CARD" && element.config?.type!=="custom:loona-benchmark-card") {
          cards.push(element); if (!element._element || !element._element.isConnected || element._element.hidden) loading.push(element);
        }
        if (visible && ["HA-SPINNER","HA-CIRCULAR-PROGRESS","MD-CIRCULAR-PROGRESS","LOONA-GRAPH-PLACEHOLDER"].includes(element.tagName)) loading.push(element);
        if (element.shadowRoot) visit(element.shadowRoot);
        visit(element);
      }
    };
    visit(document);
    return cards.length>0 && loading.length===0 && !issues.has("card_error");
  }
  let readySince, viewportReady=false;
  function checkReady() {
    if (stopped) return;
    if (document.hidden) { visibility(); return; }
    // Mobile browsers apply HA's viewport metadata after the parser-time hook.
    if (!viewportReady) {
      if (document.readyState==="loading") { timer=setTimeout(checkReady,100); return; }
      sample.viewport=marker.viewport||[innerWidth,innerHeight]; viewportReady=true;
    }
    if (sample.viewport[0]!==innerWidth || sample.viewport[1]!==innerHeight) {
      fail("Viewport size changed during testing. Keep the same orientation and start over."); return;
    }
    if (performance.now()>report.ready_ms) { keepIssue("readiness_timeout"); observe(); return; }
    if (initialFeeds.size && visibleCards()) {
      readySince??=performance.now();
      if (performance.now()-readySince>=500) { sample.ready_ms=readySince; observe(); return; }
    } else readySince=undefined;
    timer=setTimeout(checkReady,250);
  }
  function observe() {
    observing=true; observationStart=performance.now(); state.status="observing";
    tick();
  }
  function tick() {
    if (stopped) return;
    if (!connection.connected || connection.socket!==socket) { fail("Connection changed during testing. Check the connection and start over."); return; }
    const parts=location.pathname.split("/").filter(Boolean).map(part=>decodeURIComponent(part));
    if (parts[0]!==marker.dashboard || (parts[1]||"")!==marker.view) { fail("Tab changed during testing. Return to the benchmark tab and start over."); return; }
    if (sample.viewport[0]!==innerWidth || sample.viewport[1]!==innerHeight) { fail("Viewport size changed during testing. Start over."); return; }
    state.remaining=Math.max(0,Math.ceil(report.seconds-(performance.now()-observationStart)/1000)); publish();
    if (state.remaining===0) finish(); else timer=setTimeout(tick,1000);
  }
  async function finish() {
    if (stopped) return;
    sample.duration_ms=performance.now()-observationStart;
    observing=false; stop(); state.status="saving"; publish();
    performance.getEntriesByType("resource").forEach(resourceEntry);
    sample.resources=[...resources.values()].map(({end,...row})=>({...row,before_ready:sample.ready_ms!==null && end<=sample.ready_ms}));
    sample.scripts=[...scripts.values()]; sample.issues=[...issues];
    try {
      const result=await connection.sendMessagePromise({type:"loona/benchmark",action:"pass",token:marker.token,index:marker.index,sample});
      if (result.status==="complete") {
        const style=getComputedStyle(document.querySelector("home-assistant")||document.documentElement);
        result.export_colors={};
        for(const [name,property] of [["background","--card-background-color"],["text","--primary-text-color"],["secondary","--secondary-text-color"],["accent","--primary-color"],["divider","--divider-color"]]) {
          const color=style.getPropertyValue(property).trim();
          if(/^(#[0-9a-f]{3,8}|rgba?\([\d.,% ]+\))$/i.test(color)) result.export_colors[name]=color;
        }
        sessionStorage.setItem("loona.benchmark.result",JSON.stringify({owner:marker.owner,dashboard:marker.dashboard,view:marker.view,report:result}));
        sessionStorage.removeItem(key);
      } else { marker.index=result.index; write(); }
      location.reload();
    } catch (err) { fail(err.message||err.code||"Could not save the pass. Check the connection and start over."); }
  }
  async function cancel() {
    stop(); state.status="cancelled"; publish();
    sessionStorage.removeItem(key);
    try { await connection?.sendMessagePromise({type:"loona/benchmark",action:"cancel",token:marker.token}); }
    finally { location.reload(); }
  }
  function fail(reason) {
    stop(); state.status="error"; state.reason=String(reason).slice(0,300); publish();
    sessionStorage.removeItem(key);
    sessionStorage.setItem("loona.benchmark.error",state.reason);
    connection?.sendMessagePromise({type:"loona/benchmark",action:"cancel",token:marker.token}).catch(()=>{});
  }
})();
