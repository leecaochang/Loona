/* Same-tab, administrator-only comparisons. Exported SVG contains aggregate data only. */
import {text, language, markHtml, markStyles, buttonStyles, makeButton, confirmAction, cancelConfirmation} from "./i18n.js?v=0.9.11";
const VERSION="0.9.11", KEY="loona.benchmark", RESULT=KEY+".result", ERROR=KEY+".error";
const ns="http://www.w3.org/2000/svg";
const finite=value=>typeof value==="number" && Number.isFinite(value) && value>=0;
const median=values=>{ const rows=values.filter(finite).sort((a,b)=>a-b); return rows.length ? (rows[Math.floor((rows.length-1)/2)]+rows[Math.floor(rows.length/2)])/2 : null; };
const route=()=>{ try { const parts=location.pathname.split("/").filter(Boolean).map(decodeURIComponent); return {dashboard:parts[0]||"lovelace",view:parts[1]||""}; } catch { return null; } };
const read=(storage,key)=>{ try { return JSON.parse(storage.getItem(key)); } catch { return null; } };
const stored=()=>read(sessionStorage,RESULT);
const matches=(a,b)=>a && b && a.dashboard===b.dashboard && a.view===b.view;
const svgNode=(tag,attrs={},value)=>{ const el=document.createElementNS(ns,tag); for (const [key,v] of Object.entries(attrs)) el.setAttribute(key,String(v)); if(value!==undefined) el.textContent=value; return el; };
const fmt=(hass,value,digits=1)=>finite(value) ? new Intl.NumberFormat(language(hass),{maximumFractionDigits:digits}).format(value) : text(hass,"Unavailable");
const version=value=>/^\d+\.\d+(?:\.\d+)?(?:[ab]\d+)?$/.test(value||"") ? value : "?";
const scored=report=>(report?.samples||[]).filter(row=>!row.warmup);
const bytes=rows=>rows.some(row=>!finite(row.bytes)) ? null : rows.reduce((sum,row)=>sum+row.bytes,0);
export function benchmarkMetrics(report) {
  const samples=scored(report), modes=["native","loona"].map(mode=>samples.filter(row=>row.mode===mode));
  return [
    {label:"Visible cards ready",unit:"s",values:modes.map(rows=>rows.map(row=>row.issues.length || !finite(row.ready_ms) ? null : row.ready_ms/1000)),timing:true},
    {label:"Initial dashboard data",unit:"KB",values:modes.map(rows=>rows.map(row=>(row.initial_bytes+row.registry_bytes)/1000)),extras:modes.map(rows=>median(rows.map(row=>row.initial_entities))),extra:"{count} entities"},
    {label:"Card files loaded",unit:"KB",values:modes.map(rows=>rows.map(row=>{const value=bytes(row.resources);return value===null ? null : value/1000;})),extras:modes.map(rows=>median(rows.map(row=>row.resources.length))),extra:"{count} card files"},
    {label:"Live updates",unit:"updates/s",values:modes.map(rows=>rows.map(row=>row.updates/(row.duration_ms/1000))),inactive:modes.every(rows=>rows.every(row=>row.updates===0))},
    {label:"Browser blocking",unit:"ms",values:modes.map(rows=>rows.map(row=>row.loaf_supported ? row.blocking_ms : null)),timing:true}
  ].map(metric=>{
    const values=metric.values.map(median), complete=metric.values.every(rows=>rows.length>=3 && rows.every(finite));
    let status="Comparison available";
    if(!complete) status="Incomplete measurement";
    else if(metric.inactive) status="No updates observed";
    else if(values[0]===values[1]) status="No measurable change";
    else if(metric.timing && Math.max(Math.min(...metric.values[0]),Math.min(...metric.values[1]))<=Math.min(Math.max(...metric.values[0]),Math.max(...metric.values[1]))) status="Inconclusive";
    return {...metric,medians:values,status};
  });
}
// All report strings are fixed messages or validated version numbers. Private details never enter this tree.
export function benchmarkSvg(report,hass,width=360,colors={}) {
  width=Math.max(280,Math.min(800,width));
  const c={background:colors.background||"#ffffff",text:colors.text||"#212121",secondary:colors.secondary||"#555555",accent:colors.accent||"#007da8",divider:colors.divider||"#dddddd"};
  const metrics=benchmarkMetrics(report), height=report.error ? 168 : 806;
  const root=svgNode("svg",{xmlns:ns,viewBox:`0 0 ${width} ${height}`,width,height,role:"img","aria-label":text(hass,"Benchmark Results")});
  root.append(svgNode("rect",{width,height,fill:c.background}));
  const label=(value,x,y,size=14,color=c.text,weight=400)=>{const node=svgNode("text",{x,y,fill:color,"font-size":size,"font-family":"Arial, sans-serif","font-weight":weight},value);root.append(node);return node;};
  label(text(hass,"Benchmark Results"),18,36,20,c.text,600).setAttribute("data-title", "");
  if(report.error) {
    label(text(hass,"Benchmark interrupted"),18,82,16,c.text,600);
    label(text(hass,"No valid comparison was completed."),18,108,12,c.secondary);
    label(text(hass,"See the detailed report for recovery steps."),18,140,12,c.secondary);
    return root;
  }
  const partial=metrics.some(metric=>["Incomplete measurement","Inconclusive"].includes(metric.status));
  label(text(hass,partial ? "Some results are inconclusive" : "Native HA and current Loona settings"),18,76,12,c.secondary);
  const legendY=104;
  root.append(svgNode("rect",{x:18,y:legendY-9,width:12,height:8,fill:c.secondary,rx:2})); label("Native HA",36,legendY,12,c.secondary);
  root.append(svgNode("rect",{x:width/2,y:legendY-9,width:12,height:8,fill:c.accent,rx:2})); label("Loona",width/2+18,legendY,12,c.secondary);
  metrics.forEach((metric,index)=>{
    const y=136+index*124, available=metric.medians, max=Math.max(...available.filter(finite),1), barWidth=width-36;
    label(text(hass,metric.label),18,y,15,c.text,600);
    available.forEach((value,mode)=>{
      const lineY=y+24+mode*32;
      let valueText=fmt(hass,value)+(finite(value) ? " "+text(hass,metric.unit) : "");
      if(metric.extras) valueText=text(hass,metric.extra,{count:fmt(hass,metric.extras[mode],0)})+" · "+valueText;
      label(valueText,18,lineY,12,c.secondary);
      root.append(svgNode("rect",{x:18,y:lineY+6,width:barWidth,height:6,fill:c.divider,rx:3}));
      if(finite(value) && value>0) root.append(svgNode("rect",{x:18,y:lineY+6,width:barWidth*value/max,height:6,fill:mode ? c.accent : c.secondary,rx:3}));
    });
    label(text(hass,metric.status),18,y+99,12,c.secondary);
  });
  root.append(svgNode("line",{x1:18,x2:width-18,y1:758,y2:758,stroke:c.divider}));
  label(`HA ${version(report.core_version)} · Loona ${version(report.version)}`,18,780,12,c.secondary);
  label(text(hass,"{pairs} pairs · {seconds}s observation · cached reloads",{pairs:Math.floor(scored(report).length/2),seconds:report.seconds}),18,799,11,c.secondary);
  return root;
}
const issueMessages={
  readiness_timeout:"Visible cards did not become ready in time. Put the benchmark card near the top, keep another card visible, fix loading cards and start over.",
  card_error:"A visible card reported an error. Fix that card and start over.",
  resource_error:"A card file failed to load. Check dashboard resources and the connection, then start over.",
  observer_limit:"The observer reached its limit. Try a smaller tab with fewer cards and start over."
};
function install() {
  // HA can replace its HTMLElement and registry during browser bootstrap.
  if(!document.querySelector("home-assistant")?.hass) { window.setTimeout(install,100);return; }
  if(customElements.get("loona-benchmark-card")) return;
  class BenchmarkCard extends HTMLElement {
  constructor() {
    super(); this._logoPromise=null; this.attachShadow({mode:"open"}); this._onProgress=()=>this._render();
    this.shadowRoot.innerHTML=`<style>${markStyles}${buttonStyles}
      :host { display:block; color:var(--primary-text-color); } [hidden] { display:none!important; }
      ha-card { padding:24px; overflow:hidden; user-select:text; -webkit-user-select:text; }
      h2 { margin:0; font-size:20px; line-height:1.35; font-weight:500; }
      p { line-height:1.5; margin:14px 0; } .muted,#version { color:var(--secondary-text-color); }
      .actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; } .secondary { margin-top:8px; }
      #status { margin:16px 0 8px; min-height:24px; } progress { width:100%; height:8px; accent-color:var(--primary-color); }
      details { border-top:1px solid var(--divider-color); margin-top:20px; padding-top:8px; }
      summary { cursor:pointer; min-height:44px; line-height:44px; font-weight:500; }
      summary:focus-visible { outline:2px solid var(--primary-color); outline-offset:3px; }
      #details p { font-size:14px; overflow-wrap:anywhere; } #details h3 { font-size:15px; margin:24px 0 8px; }
      #report svg { display:block; width:100%; height:auto; } #report { margin:-6px -6px 0; }
      #message { color:var(--primary-text-color); overflow-wrap:anywhere; } .error { font-weight:500; }
      @media(max-width:480px) { ha-card { padding:16px; } }
      </style><ha-card><header class="brand">${markHtml}<div class="heading"><h2></h2><p id="version"></p></div></header>
      <div id="intro"></div><p id="message" role="status" aria-live="polite" hidden></p>
      <div id="progress" hidden><p id="status" role="status" aria-live="polite"></p><progress max="100" value="0" aria-label="Benchmark progress"></progress></div>
      <div id="report"></div><div class="actions" id="actions"></div><div class="actions secondary" id="secondary"></div>
      <details id="disclosure"><summary></summary><div id="details"></div></details></ha-card>`;
  }
  setConfig(config) { this._config={...config,type:"custom:loona-benchmark-card"}; }
  getCardSize() { return this._report && !this._report.error ? 15 : 4; }
  getGridOptions() { return {columns:12,rows:this._report && !this._report.error ? 15 : 4,min_columns:6}; }
  set hass(value) {
    const themeChanged=this._hass?.themes!==value?.themes;
    const changed=this._hass?.user?.id!==value?.user?.id || this._hass?.user?.is_admin!==value?.user?.is_admin || language(this._hass)!==language(value);
    this._hass=value;
    if(changed) { this._restore(); this._render(); }
    else if(themeChanged && this._report) requestAnimationFrame(()=>this._draw());
  }
  connectedCallback() {
    window.addEventListener("loona-benchmark",this._onProgress); this._restore(); this._render();
    if(typeof ResizeObserver==="function") { this._resize=new ResizeObserver(()=>this._draw());this._resize.observe(this); }
  }
  disconnectedCallback() { window.removeEventListener("loona-benchmark",this._onProgress);this._resize?.disconnect();cancelConfirmation(this); }
  _restore() {
    if(this._dialogReport) return;
    const target=route(), latest=stored();
    this._report=matches(target,latest) && latest.owner===this._hass?.user?.id ? latest.report : null;
    const historyKey=this._historyKey();
    if(sessionStorage.getItem(ERROR)) {this._report={error:true,samples:[],controls:{}};return;}
    if(this._hass?.user?.is_admin && historyKey) {
      if(this._report) { try { const history=read(localStorage,`${RESULT}.history.${this._hass.user.id}`)||[];const keys=[historyKey,...history.filter(key=>key!==historyKey)].slice(0,this._report.history_limit||1);for(const key of history) if(!keys.includes(key)) localStorage.removeItem(key);localStorage.setItem(`${RESULT}.history.${this._hass.user.id}`,JSON.stringify(keys));localStorage.setItem(historyKey,JSON.stringify(this._report)); } catch { /* Session result remains available. */ } }
      else this._report=read(localStorage,historyKey);
    }
  }
  _historyKey() { const target=route();return this._hass?.user?.id && target ? `${RESULT}.${this._hass.user.id}.${target.dashboard}.${target.view}` : null; }
  _button(root,label,icon,kind,fn,disabled=false) { const button=makeButton(this._hass,label,icon,kind);button.disabled=disabled;button.addEventListener("click",fn);root.append(button);return button; }
  _message(value) { const node=this.shadowRoot.querySelector("#message");node.textContent=value||"";node.hidden=!value; }
  _render() {
    if(!this.isConnected || !this._hass) return;
    const root=this.shadowRoot, t=key=>text(this._hass,key), state=window.loonaBenchmark;
    const running=!this._dialogReport && state && ["authorizing","loading","observing","saving","paused"].includes(state.status);
    if(state?.status==="error" && !this._dialogReport) this._report={error:true,samples:[],controls:{}};
    root.querySelector("header").hidden=Boolean(this._report && !running);
    root.querySelector("h2").textContent=t("Benchmark this dashboard");root.querySelector("#version").textContent=t("Version: {version}").replace("{version}",VERSION);
    const intro=root.querySelector("#intro"),actions=root.querySelector("#actions"),secondary=root.querySelector("#secondary");
    intro.replaceChildren();if(!running || !this._wasRunning) actions.replaceChildren();secondary.replaceChildren();
    root.querySelector("#progress").hidden=!running;
    root.querySelector("#report").hidden=Boolean(running);
    const disclosure=root.querySelector("#disclosure");disclosure.hidden=Boolean(running);
    root.querySelector("summary").textContent=t(this._report ? "Detailed report (may contain private information)" : "What will be measured");
    if(running) {
      const current=state.report?.sequence?.[state.index];
      const phase=state.status==="paused" ? "Paused. Return to this page to repeat this pass." : state.status==="observing" ? "Observing" : state.status==="saving" ? "Saving pass" : "Loading dashboard";
      root.querySelector("#status").textContent=t(phase)+" · "+(current?.mode==="native" ? "Native HA" : "Loona")+" · "+text(this._hass,"Pass {pass} of {total}",{pass:state.index+1,total:state.report?.sequence.length||8})+(state.status==="observing" ? ` · ${state.remaining}s` : "");
      const total=state.report?.sequence.length||8, seconds=state.report?.seconds||30;
      root.querySelector("progress").value=100*(state.index+(state.status==="observing" ? 1-state.remaining/seconds : 0))/total;
      if(!this._wasRunning) this._button(actions,"Cancel benchmark","cancel","quiet",()=>window.loonaBenchmark.cancel());
      this._wasRunning=true;
      this._message("");return;
    }
    this._wasRunning=false;
    this._message(this._error || (state?.status==="error" ? state.reason : sessionStorage.getItem(ERROR)));
    if(!this._hass.user?.is_admin) {
      this._report=null;this._p(intro,"Sign in as an administrator to benchmark this dashboard.");disclosure.hidden=true;root.querySelector("#report").replaceChildren();return;
    }
    if(this._report) {
      this._draw();
      this._button(actions,"Copy","copy","",()=>this._copy(),!globalThis.ClipboardItem || !navigator.clipboard?.write);
      this._button(actions,"Save","download","primary",()=>this._save());
      if(!globalThis.ClipboardItem || !navigator.clipboard?.write) this._p(intro,"Clipboard copying needs a secure browser connection. Save the PNG instead.");
      if(!this._dialogReport) {
        this._button(secondary,"Start over","reset","quiet",()=>this._startOver());
        this._button(secondary,"Remove","trash","quiet",()=>this._remove());
      }
    } else {
      root.querySelector("#report").replaceChildren();
      this._p(intro,"Compare native Home Assistant with your saved Loona settings on this tab. About 4 minutes, with automatic page reloads.");
      this._p(intro,"Keep this page in the foreground without touching, scrolling or resizing it. Put this card near the top with another card visible.");
      this._button(actions,"Go","play","primary",()=>this._start(),this._busy || !route());
    }
    this._details();
  }
  _p(root,key,values) { const p=document.createElement("p");p.textContent=text(this._hass,key,values);root.append(p);return p; }
  _details() {
    const root=this.shadowRoot.querySelector("#details");root.replaceChildren();
    for(const key of ["Reloads use the browser cache. This is not a cold-cache or hard-refresh test.","Readiness means known visible cards have mounted and loading indicators have settled. Cameras, charts and custom content may still be loading.","JSON sizes are logical UTF-8 message sizes, before network compression. Card file sizes are decoded content sizes when the browser exposes them.","Browser blocking uses Long Animation Frames. It does not measure total CPU, GPU, memory, battery or all response delays.","Each mode gets a warm-up, then three alternating pairs. Live activity can differ between passes. Overlapping timing ranges are inconclusive.","Idle savings appear only if the configured idle threshold is reached. This test does not isolate the benefit of each setting."]) this._p(root,key);
    if(!this._report) return;
    const metrics=benchmarkMetrics(this._report);
    for(const metric of metrics) if(metric.status!=="Comparison available") {
      this._p(root,metric.label).style.fontWeight="600";
      this._p(root,metric.status);
      if(metric.status==="Incomplete measurement") this._p(root,"A required reading is unavailable. Check the per-pass issues below. For blocking measurements use a browser that supports Long Animation Frames; file sizes may be hidden by cross-origin servers.");
      if(metric.status==="Inconclusive") this._p(root,"Timing ranges overlap. Close other busy applications, keep the same viewport and repeat the test.");
      if(metric.status==="No updates observed") this._p(root,"No live updates were observed. Repeat while the dashboard entities are changing.");
    }
    const heading=document.createElement("h3");heading.textContent=text(this._hass,"Saved settings");root.append(heading);
    for(const [key,value] of Object.entries(this._report.controls||{})) this._p(root,"{key}: {value}",{key,value:text(this._hass,value ? "Enabled" : "Disabled")});
    const settings=document.createElement("p");settings.textContent=JSON.stringify(this._report.settings||{});root.append(settings);
    this._report.samples.forEach((row,index)=>{
      const h=document.createElement("h3");h.textContent=`${text(this._hass,"Pass {pass} of {total}",{pass:index+1,total:this._report.samples.length})} · ${row.mode==="native" ? "Native HA" : "Loona"}${row.warmup ? " · "+text(this._hass,"Warm-up (excluded)") : ""}`;root.append(h);
      this._p(root,"Ready: {ready}s; observation: {duration}s; initial entities: {entities}; initial JSON: {initial} KB; registry JSON: {registry} KB; live updates: {updates} ({bytes} KB).",{ready:fmt(this._hass,row.ready_ms===null ? null : row.ready_ms/1000),duration:fmt(this._hass,row.duration_ms/1000),entities:fmt(this._hass,row.initial_entities,0),initial:fmt(this._hass,row.initial_bytes/1000),registry:fmt(this._hass,row.registry_bytes/1000),updates:fmt(this._hass,row.updates,0),bytes:fmt(this._hass,row.update_bytes/1000)});
      this._p(root,"Startup blocking: {startup} ms; observation blocking: {live} ms; long frames: {frames}.",{startup:fmt(this._hass,row.loaf_supported ? row.startup_blocking_ms : null),live:fmt(this._hass,row.loaf_supported ? row.blocking_ms : null),frames:fmt(this._hass,row.startup_frames+row.frames,0)});
      for(const issue of row.issues) this._p(root,issueMessages[issue]||"Incomplete measurement");
      this._p(root,"Browser: {browser}; viewport: {width} x {height}",{browser:row.browser,width:row.viewport[0],height:row.viewport[1]});
      for(const file of row.resources) this._p(root,"{source}: {bytes} KB ({phase}, {cache})",{source:file.source,bytes:fmt(this._hass,file.bytes===null ? null : file.bytes/1000),phase:text(this._hass,file.before_ready ? "before measuring" : "while measuring"),cache:text(this._hass,file.cached ? "Cached" : "Downloaded")});
      for(const script of row.scripts) this._p(root,"{source} ({phase}): {ms} ms",{source:script.source,phase:text(this._hass,script.phase==="startup" ? "before measuring" : "while measuring"),ms:fmt(this._hass,script.duration_ms)});
    });
  }
  _draw() {
    if(!this._report || !this._hass?.user?.is_admin) return;
    const style=getComputedStyle(this), colors={};
    for(const [key,name,fallback] of [["background","--card-background-color","#fff"],["text","--primary-text-color","#212121"],["secondary","--secondary-text-color","#555"],["accent","--primary-color","#007da8"],["divider","--divider-color","#ddd"]]) colors[key]=style.getPropertyValue(name).trim()||fallback;
    const root=this.shadowRoot.querySelector("#report"),width=Math.max(280,root.getBoundingClientRect().width||360);
    this._svg=benchmarkSvg(this._report,this._hass,width,colors);root.replaceChildren(this._svg);this._png=null;
    const placeLogo=()=>{
      if(!this._logo || !this._svg || this._svg.querySelector("image")) return;
      this._svg.append(svgNode("image",{x:18,y:12,width:44,height:44,href:this._logo}));
      this._svg.querySelector("[data-title]").setAttribute("x",76);
      this._svg.querySelector("[data-title]").setAttribute("font-size",width<330 ? 18 : 20);this._png=null;
    };
    placeLogo();
    const mark=this.shadowRoot.querySelector(".mark");
    if(!this._logoPromise && mark?.src) {
      this._logoPromise=fetch(mark.src).then(response=>{if(!response.ok) throw new Error("Logo unavailable");return response.blob();})
        .then(blob=>new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.readAsDataURL(blob);}))
        .then(data=>{this._logo=data;placeLogo();}).catch(()=>{});
    }
  }
  async _start() {
    if(this._busy) return;this._busy=true;this._error=null;sessionStorage.removeItem(ERROR);this._render();
    const target=route();let result;
    try {
      if(!target || document.hidden) throw new Error(text(this._hass,"Keep the benchmark tab visible before starting."));
      result=await this._hass.callWS({type:"loona/benchmark",action:"start",...target});
      sessionStorage.setItem(KEY,JSON.stringify({...target,token:result.token,owner:this._hass.user.id,index:0,viewport:[innerWidth,innerHeight],expires:Date.now()+result.session_seconds*1000}));
      // The default HA route can be '/'. Use its explicit dashboard route for all passes.
      if(!location.pathname.split("/").filter(Boolean).length) location.replace("/lovelace"); else location.reload();
    } catch(err) {
      if(result?.token) await this._hass.callWS({type:"loona/benchmark",action:"cancel",token:result.token}).catch(()=>{});
      this._error=err.message||err.code||text(this._hass,"Benchmark could not start. Refresh and try again.");this._busy=false;this._render();
    }
  }
  _startOver() { this._report=null;this._error=null;sessionStorage.removeItem(RESULT);sessionStorage.removeItem(ERROR);const key=this._historyKey();if(key) localStorage.removeItem(key);this._render(); }
  async _remove() {
    if(!await confirmAction(this,"Remove benchmark card?","Remove this benchmark card from this tab? Saved PNGs are kept.","Remove")) return;
    try { await this._hass.callWS({type:"loona/benchmark",action:"remove",...route(),card:this._config}); }
    catch(err) { this._message(err.message||text(this._hass,"Remove this card manually in the dashboard editor or YAML source.")); }
  }
  async _blob() {
    await this._logoPromise;
    if(this._png) return this._png;
    const root=this._svg.cloneNode(true), image=new Image();
    const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(root)],{type:"image/svg+xml;charset=utf-8"}));
    try {
      image.src=url;await image.decode();const canvas=document.createElement("canvas");canvas.width=Number(root.getAttribute("width"))*2;canvas.height=Number(root.getAttribute("height"))*2;
      canvas.getContext("2d").drawImage(image,0,0,canvas.width,canvas.height);
      this._png=await new Promise((resolve,reject)=>canvas.toBlob(blob=>blob ? resolve(blob) : reject(new Error("PNG export failed")),"image/png"));return this._png;
    } finally { URL.revokeObjectURL(url); }
  }
  async _copy() { try { await navigator.clipboard.write([new ClipboardItem({"image/png":this._blob()})]);this._message(text(this._hass,"PNG copied.")); } catch {this._message(text(this._hass,"Could not copy the PNG. Save it instead."));} }
  async _save() { try {const url=URL.createObjectURL(await this._blob()),link=document.createElement("a");link.href=url;link.download="loona-benchmark.png";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);} catch {this._message(text(this._hass,"PNG export failed. Start over and try again."));} }
}
  customElements.define("loona-benchmark-card",BenchmarkCard);
  window.customCards=window.customCards||[];
  if(!window.customCards.some(card=>card.type==="loona-benchmark-card")) window.customCards.push({type:"loona-benchmark-card",name:"Loona benchmark",description:"Compare native HA and saved Loona settings on this tab."});
}
install();
// The module is also loaded when the card is hidden or unmounted.
function showResults(hass,result) {
  const active=[...document.querySelectorAll("home-assistant")];
  const visit=root=>{for(const element of root.children||[]) {if(element.tagName==="LOONA-BENCHMARK-CARD" && element.getBoundingClientRect().width>0 && element.getBoundingClientRect().height>0) {element.scrollIntoView({block:"start"});return true;}if(element.shadowRoot && visit(element.shadowRoot)) return true;if(visit(element)) return true;}return false;};
  if(matches(route(),result) && active.some(visit)) return;
  const dialog=document.createElement("dialog"),card=document.createElement("loona-benchmark-card");
  dialog.style.cssText="width: min(480px, calc(100vw - 32px)); max-height: calc(100vh - 32px); overflow: auto; padding: 0; border: 0; background: var(--card-background-color); color: var(--primary-text-color); border-radius: var(--ha-border-radius,12px)";
  card._dialogReport=true;card._report=result.report;card.hass=hass;dialog.append(card);document.body.append(dialog);
  const close=makeButton(hass,"Close","cancel","quiet");close.addEventListener("click",()=>dialog.close());card.shadowRoot.querySelector("#secondary").append(close);
  dialog.addEventListener("close",()=>dialog.remove(),{once:true});dialog.setAttribute("aria-label",text(hass,"Benchmark Results"));dialog.showModal();
}
const completed=stored();
if(completed && !completed.notified) {
  let attempts=0;
  const notify=()=>{
    const app=document.querySelector("home-assistant"),hass=app?.hass;
    if(!hass || !customElements.get("loona-benchmark-card")) {if(attempts++<120) setTimeout(notify,250);return;}
    if(!hass.user?.is_admin || completed.owner!==hass.user.id) return;
    completed.notified=true;try {sessionStorage.setItem(RESULT,JSON.stringify(completed));} catch { /* Result still available. */ }
    app.dispatchEvent(new CustomEvent("hass-notification",{bubbles:true,composed:true,detail:{message:text(hass,"Benchmark complete. Results are ready."),duration:10000,action:{text:text(hass,"Show results"),action:()=>showResults(hass,completed)}}}));
  };
  setTimeout(notify,250);
}
