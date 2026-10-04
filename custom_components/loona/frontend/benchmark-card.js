/* Same-tab, administrator-only comparisons. Exported SVG contains aggregate data only. */
import {text, language, markHtml, markStyles, buttonStyles, makeButton, confirmAction, cancelConfirmation, helpStyles} from "./i18n.js?v=0.9.13";
const VERSION="0.9.13", KEY="loona.benchmark", RESULT=KEY+".result", ERROR=KEY+".error";
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
    {label:"Initial dashboard data",unit:"KB",values:modes.map(rows=>rows.map(row=>(row.initial_bytes+row.registry_bytes)/1000)),extras:modes.map(rows=>median(rows.map(row=>row.initial_entities))),extra:"{count} entities",less:"{percent}% less data",more:"{percent}% more data"},
    {label:"Card files loaded",unit:"KB",values:modes.map(rows=>rows.map(row=>{const value=bytes(row.resources);return value===null ? null : value/1000;})),extras:modes.map(rows=>median(rows.map(row=>row.resources.length))),extra:"{count} card files",less:"{percent}% less file data",more:"{percent}% more file data"},
    {label:"Live updates",unit:"updates/s",values:modes.map(rows=>rows.map(row=>row.updates/(row.duration_ms/1000))),inactive:modes.every(rows=>rows.every(row=>row.updates===0)),less:"{percent}% fewer updates",more:"{percent}% more updates"},
    {label:"Browser blocking",unit:"ms",values:modes.map(rows=>rows.map(row=>row.loaf_supported ? row.blocking_ms : null)),timing:true,unsupported:samples.length>0 && samples.every(row=>!row.loaf_supported)}
  ].map(metric=>{
    const values=metric.values.map(median), complete=metric.values.every(rows=>rows.length>=3 && rows.every(finite));
    let status="No measurable change", percent=null;
    if(metric.unsupported) status="Not supported in this browser";
    else if(!complete) status="Incomplete measurement";
    else if(metric.inactive) status="No updates observed";
    else if(metric.timing && (values[0]!==values[1]) && Math.max(Math.min(...metric.values[0]),Math.min(...metric.values[1]))<=Math.min(Math.max(...metric.values[0]),Math.max(...metric.values[1]))) status="No clear timing difference";
    else if(values[0]!==values[1]) {
      percent=values[0]>0 ? Math.abs(100*(values[1]-values[0])/values[0]) : null;
      status=metric.timing ? (values[1]<values[0] ? "Less time observed" : "More time observed") : finite(percent) ? (values[1]<values[0] ? metric.less : metric.more) : "More observed with Loona";
    }
    return {...metric,medians:values,status,percent};
  });
}
const metricStatus=(metric,hass)=>text(hass,metric.status,{percent:fmt(hass,metric.percent,0)});
const valueLabel=(metric,hass,mode)=>{
  const value=metric.medians[mode];
  let result=fmt(hass,value)+(finite(value) ? " "+text(hass,metric.unit) : "");
  if(metric.extras) result=text(hass,metric.extra,{count:fmt(hass,metric.extras[mode],0)})+" · "+result;
  return result;
};
const settingsLabels={enabled:"Enabled",entity_filtering:"Entity filtering",current_dashboard_updates:"Live updates for current tab only",registry_filtering:"Device and area filtering",resource_filtering:"Skip unused card files",delay_card_resources:"Load current tab first",preload_card_resources:"Preload card files",visible_first_graphs:"Delay graph loading",pause_animations_during_loading:"Pause animations during loading",pause_offscreen_animations:"Pause off-screen animations",idle_updates:"Idle mode",dashboard_cards:"Loona dashboard cards",dashboards:"Dashboards",target_mode:"Apply filtering to",user_ids:"Accounts",extra_entities:"Entities",include_domains:"Entity types",include_globs:"Entities to include",exclude_globs:"Entities to exclude",always_forward_resources:"Extra card files to load",idle_after_minutes:"Idle after (minutes)",idle_refresh_seconds:"Idle refresh (seconds)"};
const cardLabels={benchmark:"Loona benchmark",settings:"Loona settings",statistics:"Loona statistics"};
const methods=["Reloads use the browser cache. This is not a cold-cache or hard-refresh test.","Readiness means known visible cards have mounted and loading indicators have settled. Cameras, charts and custom content may still be loading.","JSON sizes are logical UTF-8 message sizes, before network compression. Card file sizes are decoded content sizes when the browser exposes them.","Browser blocking uses Long Animation Frames. It does not measure total CPU, GPU, memory, battery or all response delays.","Each mode gets a warm-up, then three alternating pairs. Live activity can differ between passes. Overlapping timing ranges are inconclusive.","Idle savings appear only if the configured idle threshold is reached. This test does not isolate the benefit of each setting."];
export function benchmarkSections(report,hass) {
  const t=(key,values)=>text(hass,key,values), sections=[];
  if(!report) return [{title:"",lines:methods.map(key=>t(key))}];
  if(report.error) return [{title:t("Executive summary"),lines:[t("No valid comparison was completed."),t(report.reason||"Benchmark interrupted"),t("Start over to run a new comparison.")]}];
  const metrics=benchmarkMetrics(report);
  sections.push({title:t("Executive summary"),list:true,lines:metrics.map(metric=>`${t(metric.label)}: ${metricStatus(metric,hass)}.`)});
  sections.push({title:t("Measurements"),headers:[t("Measurement"),"Native HA","Loona"],rows:metrics.map(metric=>[t(metric.label),valueLabel(metric,hass,0),valueLabel(metric,hass,1)])});
  const names=report.names||{}, settings=report.settings||{};
  sections.push({title:t("Test details"),headers:[t("Setting"),t("Value")],rows:[
    [t("Dashboard"),report.dashboard_title||t("Unavailable")],[t("Tab"),report.view_title||t("Unavailable")],
    ["Loona",version(report.version)],["Home Assistant",version(report.core_version)],
    [t("Completed"),report.completed_at ? new Date(report.completed_at).toLocaleString(language(hass)) : t("Unavailable")],
    [t("Method"),t("{pairs} pairs · {seconds}s observation · cached reloads",{pairs:Math.floor(scored(report).length/2),seconds:report.seconds})]
  ]});
  const advice=[];
  for(const metric of metrics) {
    if(metric.status==="No clear timing difference" || metric.timing && metric.status==="No measurable change") advice.push(t("The loading or blocking times are similar or overlap across passes. This does not indicate an interrupted test. Data savings can still be measured without a proven speed improvement."));
    if(metric.unsupported) advice.push(t("This browser does not expose Long Animation Frames. Blocking is unavailable; the other comparisons remain valid. Use a browser supporting this API to measure blocking."));
    if(metric.status==="Incomplete measurement") advice.push(t(metric.label)+": "+t(metric.label==="Card files loaded" ? "Some servers hide file sizes. File counts are still available; use the browser Network panel to inspect sizes." : "Fewer than three valid readings are available. Resolve the issues below and repeat the test."));
    if(metric.inactive) advice.push(t("No live updates were observed. Repeat while the dashboard entities are changing."));
  }
  for(const issue of new Set((report.samples||[]).flatMap(row=>row.issues||[]))) advice.push(t(issueMessages[issue]||"Incomplete measurement"));
  sections.push({title:t("Interpretation and next steps"),lines:[...new Set(advice),t("To inspect individual card files, open Settings > Dashboards > Resources, or filter the browser Network panel to JavaScript and reload. The comparison above reports totals without repeating files for every pass.")]});
  const settingRows=Object.entries({...report.controls,...settings}).filter(([key])=>settingsLabels[key]).map(([key,value])=>{
    let display;
    if(typeof value==="boolean") display=t(value ? "Enabled" : "Disabled");
    else if(key==="target_mode") display=t(value==="all" ? "All accounts" : "Selected accounts");
    else if(key==="user_ids" && settings.target_mode==="all") display=t("All accounts");
    else if(Array.isArray(value)) display=value.map(item=>key==="dashboard_cards" ? t(cardLabels[item]||item) : names[key]?.[item]||hass?.states?.[item]?.attributes?.friendly_name||item).join(", ")||t("None");
    else display=String(value);
    return [t(settingsLabels[key]),display];
  });
  sections.push({title:t("Saved settings"),headers:[t("Setting"),t("Value")],rows:settingRows});
  sections.push({title:t("Individual passes"),headers:[t("Pass"),t("Mode"),t("Ready (s)"),t("Data (KB)"),t("Card files"),t("Updates"),t("Blocking (ms)")],rows:scored(report).map((row,index)=>[
    fmt(hass,index+1,0),row.mode==="native" ? "Native HA" : "Loona",fmt(hass,finite(row.ready_ms) ? row.ready_ms/1000 : null),
    fmt(hass,(row.initial_bytes+row.registry_bytes)/1000),fmt(hass,row.resources.length,0),fmt(hass,row.updates,0),fmt(hass,row.loaf_supported ? row.blocking_ms : null)
  ])});
  const first=scored(report)[0];
  sections.push({title:t("Measurement limits"),lines:[...methods.map(key=>t(key)),...(first ? [t("Browser: {browser}; viewport: {width} x {height}",{browser:first.browser,width:first.viewport[0],height:first.viewport[1]})] : [])]});
  return sections;
}
// Treat names and failure reasons as literal Markdown content, including inside table cells.
const markdownLiteral=value=>String(value).replace(/\\/g,"\\\\").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/([`*_{}\[\]#!|])/g,"\\$1").replace(/\r\n|\r|\n/g,"<br>");
export function benchmarkText(report,hass) {
  const sections=benchmarkSections(report,hass).map(section=>{
    const parts=section.title ? ["## "+markdownLiteral(section.title)] : [];
    if(section.lines?.length) parts.push(section.lines.map(line=>(section.list ? "- " : "")+markdownLiteral(line)).join(section.list ? "\n" : "\n\n"));
    if(section.headers) parts.push([
      "| "+section.headers.map(markdownLiteral).join(" | ")+" |",
      "| "+section.headers.map(()=>"---").join(" | ")+" |",
      ...section.rows.map(row=>"| "+row.map(markdownLiteral).join(" | ")+" |")
    ].join("\n"));
    return parts.join("\n\n");
  });
  return "# "+text(hass,"Benchmark Results")+"\n\n"+sections.join("\n\n")+"\n";
}
export function benchmarkFilename(report,extension) {
  const name=String(report.dashboard_title||route()?.dashboard||"dashboard").normalize("NFKC").replace(/[^\p{L}\p{N}_-]+/gu,"-").replace(/^-+|-+$/g,"").slice(0,80)||"dashboard";
  const date=new Date(report.completed_at||0), stamp=(Number.isFinite(date.getTime()) ? date : new Date(0)).toISOString().replace(/[-:]/g,"").replace(/\.\d{3}Z$/,"Z");
  return `loona-${version(report.version||VERSION)}-benchmark-${name}-${stamp}.${extension}`;
}
// All report strings are fixed messages or validated version numbers. Private details never enter this tree.
export function benchmarkSvg(report,hass,width=360,colors={}) {
  width=Math.max(280,Math.min(800,width));
  const c={background:colors.background||"#ffffff",text:colors.text||"#212121",secondary:colors.secondary||"#555555",accent:colors.accent||"#007da8",divider:colors.divider||"#dddddd"};
  const metrics=benchmarkMetrics(report), height=report.error ? 168 : 806;
  const root=svgNode("svg",{xmlns:ns,viewBox:`0 0 ${width} ${height}`,width,height,role:"img","aria-label":text(hass,"Benchmark Results")});
  root.append(svgNode("rect",{width,height,fill:c.background}));
  const label=(value,x,y,size=14,color=c.text,weight=400)=>{const node=svgNode("text",{x,y,fill:color,"font-size":size,"font-family":"Arial, sans-serif","font-weight":weight},value);root.append(node);return node;};
  label(text(hass,"Benchmark Results"),76,32,width<330 ? 18 : 20,c.text,600).setAttribute("data-title", "");
  label(`Loona ${version(report.version||VERSION)}`,76,53,12,c.secondary);
  if(report.error) {
    label(text(hass,"Benchmark interrupted"),18,82,16,c.text,600);
    label(text(hass,"No valid comparison was completed."),18,108,12,c.secondary);
    label(text(hass,"See the detailed report for recovery steps."),18,140,12,c.secondary);
    return root;
  }
  label(text(hass,"Native HA and current Loona settings"),18,80,12,c.secondary);
  const legendY=104;
  root.append(svgNode("rect",{x:18,y:legendY-9,width:12,height:8,fill:c.secondary,rx:2})); label("Native HA",36,legendY,12,c.secondary);
  root.append(svgNode("rect",{x:width/2,y:legendY-9,width:12,height:8,fill:c.accent,rx:2})); label("Loona",width/2+18,legendY,12,c.secondary);
  metrics.forEach((metric,index)=>{
    const y=136+index*124, available=metric.medians, max=Math.max(...available.filter(finite),1), barWidth=width-36;
    label(text(hass,metric.label),18,y,15,c.text,600);
    available.forEach((value,mode)=>{
      const lineY=y+24+mode*32;
      const valueText=valueLabel(metric,hass,mode);
      label(valueText,18,lineY,12,c.secondary);
      root.append(svgNode("rect",{x:18,y:lineY+6,width:barWidth,height:6,fill:c.divider,rx:3}));
      if(finite(value) && value>0) root.append(svgNode("rect",{x:18,y:lineY+6,width:barWidth*value/max,height:6,fill:mode ? c.accent : c.secondary,rx:3}));
    });
    label(metricStatus(metric,hass),18,y+99,12,c.secondary);
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
    this.shadowRoot.innerHTML=`<style>${markStyles}${buttonStyles}${helpStyles}
      :host { display:block; color:var(--primary-text-color); } [hidden] { display:none!important; }
      ha-card { padding:24px; overflow:hidden; user-select:text; -webkit-user-select:text; }
      h2 { margin:0; font-size:20px; line-height:1.35; font-weight:500; }
      p { line-height:1.5; margin:14px 0; } .muted,#version { color:var(--secondary-text-color); }
      .actions { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; margin-top:16px; } .secondary { margin-top:8px; } .actions button { width:100%; justify-content:center; } .actions button:only-child { grid-column:1 / -1; }
      #status { margin:16px 0 8px; min-height:24px; } progress { width:100%; height:8px; accent-color:var(--primary-color); }
      details { border-top:1px solid var(--divider-color); margin-top:20px; padding-top:8px; }
      summary { cursor:pointer; min-height:44px; line-height:1.5; padding:10px 0; box-sizing:border-box; font-weight:500; }
      summary:focus-visible { outline:2px solid var(--primary-color); outline-offset:3px; }
      #details { max-height:min(360px,50vh); overflow-y:auto; overscroll-behavior:contain; scrollbar-color:var(--secondary-text-color) var(--card-background-color); } #details:focus-visible { outline:2px solid var(--primary-color); outline-offset:-2px; } #details p,#details li { font-size:14px; overflow-wrap:anywhere; } #details h3 { font-size:15px; margin:24px 0 8px; } #details h3:first-child { margin-top:8px; } #details ul { padding-inline-start:20px; margin:12px 0; line-height:1.5; } #details li { margin:8px 0; } .table-scroll { overflow-x:auto; scrollbar-color:var(--secondary-text-color) var(--card-background-color); } .table-scroll:focus-visible { outline:2px solid var(--primary-color); outline-offset:-2px; } table { width:100%; border-collapse:collapse; font-size:14px; line-height:1.5; } table.wide { min-width:500px; } th,td { padding:8px; text-align:start; vertical-align:top; border-bottom:1px solid var(--divider-color); overflow-wrap:anywhere; font-variant-numeric:tabular-nums; } th { font-weight:600; } #text-actions { margin-top:12px; } details:not([open]) #text-actions { display:none; }
      #report svg,#report img { display:block; width:100%; height:auto; } #report { margin:-6px -6px 0; }
      #message { color:var(--primary-text-color); overflow-wrap:anywhere; } .error { font-weight:500; }
      @media(max-width:480px) { ha-card { padding:16px; } }
      </style><ha-card><header class="brand">${markHtml}<div class="heading"><h2></h2><p id="version"></p></div></header>
      <div id="intro"></div><p id="message" role="status" aria-live="polite" hidden></p>
      <div id="progress" hidden><p id="status" role="status" aria-live="polite"></p><progress max="100" value="0" aria-label="Benchmark progress"></progress></div>
      <div id="report"></div><span id="copy-tip" class="help-text" role="tooltip" hidden></span><div class="actions" id="actions"></div><div class="actions secondary" id="secondary"></div>
      <details id="disclosure"><summary></summary><div id="details" tabindex="0" role="region" aria-label="Detailed report"></div><div class="actions" id="text-actions"></div></details></ha-card>`;
  }
  setConfig(config) { this._config={...config,type:"custom:loona-benchmark-card"}; }
  getCardSize() { return this._report && !this._report.error ? 15 : 4; }
  getGridOptions() { return {columns:12,rows:this._report && !this._report.error ? 15 : 4,min_columns:6}; }
  set hass(value) {
    const changed=this._hass?.user?.id!==value?.user?.id || this._hass?.user?.is_admin!==value?.user?.is_admin || language(this._hass)!==language(value);
    this._hass=value;
    if(changed) { this._restore(); this._render(); }
  }
  connectedCallback() {
    window.addEventListener("loona-benchmark",this._onProgress); this._restore(); this._render();
    if(typeof ResizeObserver==="function") {this._resize=new ResizeObserver(()=>this._draw());this._resize.observe(this);}
  }
  disconnectedCallback() { window.removeEventListener("loona-benchmark",this._onProgress);this._resize?.disconnect();this._clearPreview();this._closeCopyTip();cancelConfirmation(this); }
  _restore() {
    if(this._dialogReport) return;
    const target=route(), latest=stored();
    this._report=matches(target,latest) && latest.owner===this._hass?.user?.id ? latest.report : null;
    const historyKey=this._historyKey();
    if(sessionStorage.getItem(ERROR)) {this._report=this._errorReport(sessionStorage.getItem(ERROR));return;}
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
    this._closeCopyTip();
    const root=this.shadowRoot, t=key=>text(this._hass,key), state=window.loonaBenchmark;
    const running=!this._dialogReport && state && ["authorizing","loading","observing","saving","paused"].includes(state.status);
    if(state?.status==="error" && !this._dialogReport) this._report=this._errorReport(state.reason);
    root.querySelector("header").hidden=Boolean(this._report && !running);
    root.querySelector("h2").textContent=t("Benchmark this dashboard");root.querySelector("#version").textContent=text(this._hass,"Version: {version}",{version:VERSION});
    const intro=root.querySelector("#intro"),actions=root.querySelector("#actions"),secondary=root.querySelector("#secondary");
    intro.replaceChildren();if(!running || !this._wasRunning) actions.replaceChildren();secondary.replaceChildren();
    root.querySelector("#progress").hidden=!running;
    root.querySelector("#report").hidden=Boolean(running);
    const disclosure=root.querySelector("#disclosure");disclosure.hidden=Boolean(running);
    root.querySelector("summary").textContent=t(this._report ? "Detailed report" : "What will be measured");
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
    this._message(this._report ? "" : this._error);
    if(!this._hass.user?.is_admin) {
      this._clearPreview();this._report=null;this._p(intro,"Sign in as an administrator to benchmark this dashboard.");disclosure.hidden=true;root.querySelector("#report").replaceChildren();return;
    }
    if(this._report) {
      this._draw();
      this._copyButton=this._button(actions,"Copy","copy","",()=>this._copy(),!navigator.clipboard?.write && !root.querySelector("#report img"));
      this._button(actions,"Save","download","primary",()=>this._save());
      if(!this._dialogReport) {
        this._button(secondary,"Start over","reset","quiet",()=>this._startOver());
        this._button(secondary,"Remove","trash","quiet",()=>this._remove());
      }
    } else {
      this._clearPreview();root.querySelector("#report").replaceChildren();
      this._p(intro,"Compare native Home Assistant with your saved Loona settings on this tab. About 4 minutes, with automatic page reloads.");
      this._p(intro,"Keep this page in the foreground without touching, scrolling or resizing it. Put this card near the top with another card visible.");
      this._button(actions,"Go","play","primary",()=>this._start(),this._busy || !route());
    }
    this._details();
  }
  _p(root,key,values) { const p=document.createElement("p");p.textContent=text(this._hass,key,values);root.append(p);return p; }
  _errorReport(reason) { return {error:true,reason,version:VERSION,completed_at:new Date().toISOString(),samples:[],controls:{}}; }
  _details() {
    const root=this.shadowRoot.querySelector("#details"),actions=this.shadowRoot.querySelector("#text-actions");root.replaceChildren();actions.replaceChildren();
    root.setAttribute("aria-label",text(this._hass,"Detailed report"));
    for(const section of benchmarkSections(this._report,this._hass)) {
      if(section.title) {const h=document.createElement("h3");h.textContent=section.title;root.append(h);}
      const lines=section.list ? document.createElement("ul") : root;
      for(const line of section.lines||[]) {const node=document.createElement(section.list ? "li" : "p");node.textContent=line;lines.append(node);}
      if(section.list) root.append(lines);
      if(section.headers) {
        const container=document.createElement("div"),table=document.createElement("table"),head=document.createElement("thead"),heading=document.createElement("tr"),body=document.createElement("tbody");
        container.className="table-scroll";container.tabIndex=0;container.setAttribute("role","region");container.setAttribute("aria-label",section.title);table.classList.toggle("wide",section.headers.length>2);
        for(const label of section.headers) {const cell=document.createElement("th");cell.scope="col";cell.textContent=label;heading.append(cell);}
        head.append(heading);table.append(head,body);
        for(const row of section.rows) {const line=document.createElement("tr");for(const value of row) {const cell=document.createElement("td");cell.textContent=value;line.append(cell);}body.append(line);}
        container.append(table);root.append(container);
      }
    }
    if(this._report) {
      this._button(actions,"Copy text","copy","quiet",()=>this._copyText());
      this._button(actions,"Save text","download","quiet",()=>this._saveText());
    }
  }
  _exportSvg(width=420) {
    const root=benchmarkSvg(this._report,this._hass,width,this._report.export_colors||{background:"#1c1c1c",text:"#e1e1e1",secondary:"#aaaaaa",accent:"#009ac7",divider:"#333333"});
    if(this._logo) root.append(svgNode("image",{x:18,y:12,width:44,height:44,href:this._logo}));
    return root;
  }
  _clearPreview() { this._drawSequence=(this._drawSequence||0)+1;if(this._previewUrl) URL.revokeObjectURL(this._previewUrl);this._previewUrl=null;this._previewReport=null; }
  _draw() {
    if(!this._report || !this._hass?.user?.is_admin) return;
    const root=this.shadowRoot.querySelector("#report"),width=Math.max(280,root.getBoundingClientRect().width||360);
    if(this._previewReport===this._report && this._previewLanguage===language(this._hass) && this._previewWidth===width) return;
    const report=this._report,sequence=(this._drawSequence||0)+1;this._drawSequence=sequence;
    const svg=this._exportSvg(width);this._svg=svg;root.replaceChildren(svg);
    const mark=this.shadowRoot.querySelector(".mark");
    if(!this._logoPromise && mark?.src) {
      this._logoPromise=fetch(mark.src).then(response=>{if(!response.ok) throw new Error("Logo unavailable");return response.blob();})
        .then(blob=>new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.readAsDataURL(blob);}))
        .then(data=>{this._logo=data;}).catch(()=>{});
    }
    Promise.resolve(this._logoPromise).then(()=>{
      if(this._logo && !svg.querySelector("image")) svg.append(svgNode("image",{x:18,y:12,width:44,height:44,href:this._logo}));
      return this._rasterize(svg);
    }).then(async blob=>{
      const url=URL.createObjectURL(blob),image=new Image();
      image.alt=[...svg.querySelectorAll("text")].map(node=>node.textContent).join(". ");image.src=url;
      try {await image.decode();} catch(err) {URL.revokeObjectURL(url);throw err;}
      if(sequence!==this._drawSequence || this._report!==report || !this.isConnected) {URL.revokeObjectURL(url);return;}
      if(this._previewUrl) URL.revokeObjectURL(this._previewUrl);
      this._previewUrl=url;this._previewReport=report;this._previewLanguage=language(this._hass);this._previewWidth=width;root.replaceChildren(image);
      if(this._copyButton) this._copyButton.disabled=false;
    }).catch(()=>{if(sequence===this._drawSequence) this._message(text(this._hass,"PNG export failed. Start over and try again."));});
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
  _startOver() { this._clearPreview();this._closeCopyTip();if(window.loonaBenchmark && ["error","cancelled","complete"].includes(window.loonaBenchmark.status)) delete window.loonaBenchmark;this._report=null;this._error=null;this._busy=false;this._png=null;this._pngReport=null;this.shadowRoot.querySelector("#disclosure").open=false;this.shadowRoot.querySelector("#details").scrollTop=0;sessionStorage.removeItem(RESULT);sessionStorage.removeItem(ERROR);const key=this._historyKey();if(key) localStorage.removeItem(key);this._render(); }
  async _remove() {
    if(!await confirmAction(this,"Remove benchmark card?","Remove this benchmark card from this tab? Saved PNGs are kept.","Remove")) return;
    try { await this._hass.callWS({type:"loona/benchmark",action:"remove",...route(),card:this._config}); }
    catch(err) { this._message(err.message||text(this._hass,"Remove this card manually in the dashboard editor or YAML source.")); }
  }
  async _blob() {
    await this._logoPromise;
    if(this._png && this._pngReport===this._report && this._pngLanguage===language(this._hass)) return this._png;
    const report=this._report;
    // Export dimensions and paint belong to the result, never to its card or dialog container.
    const blob=await this._rasterize(this._exportSvg());
    this._png=blob;this._pngReport=report;this._pngLanguage=language(this._hass);return blob;
  }
  async _rasterize(root) {
    const image=new Image(),url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(root)],{type:"image/svg+xml;charset=utf-8"}));
    try {
      image.src=url;await image.decode();const canvas=document.createElement("canvas");canvas.width=Number(root.getAttribute("width"))*2;canvas.height=Number(root.getAttribute("height"))*2;
      canvas.getContext("2d").drawImage(image,0,0,canvas.width,canvas.height);
      return await new Promise((resolve,reject)=>canvas.toBlob(value=>value ? resolve(value) : reject(new Error("PNG export failed")),"image/png"));
    } finally { URL.revokeObjectURL(url); }
  }
  async _copy() {
    if(globalThis.ClipboardItem && navigator.clipboard?.write) {
      try { await navigator.clipboard.write([new ClipboardItem({"image/png":this._blob()})]);this._message(text(this._hass,"PNG copied."));return; } catch { /* Native image copying remains available. */ }
    }
    this._showCopyTip();
  }
  _closeCopyTip() {
    const tip=this.shadowRoot.querySelector("#copy-tip");if(tip) tip.hidden=true;this._copyButton?.removeAttribute("aria-describedby");
    document.removeEventListener("pointerdown",this._tipOutside);document.removeEventListener("keydown",this._tipEscape);
    window.removeEventListener("resize",this._tipDismiss);window.removeEventListener("scroll",this._tipDismiss,true);
  }
  _showCopyTip() {
    const tip=this.shadowRoot.querySelector("#copy-tip"),button=this._copyButton;
    if(!tip || !button) return;
    if(!tip.hidden) {this._closeCopyTip();return;}
    tip.textContent=text(this._hass,"Right-click the image above and choose Copy Image. On a touch screen, touch and hold it.");tip.hidden=false;button.setAttribute("aria-describedby",tip.id);
    const bounds=button.getBoundingClientRect(),width=Math.min(320,window.innerWidth-32);tip.style.left=Math.max(16,Math.min(bounds.right-width,window.innerWidth-width-16))+"px";tip.style.top="16px";
    const height=tip.getBoundingClientRect().height;tip.style.top=Math.max(16,bounds.bottom+height+8<=window.innerHeight-16 ? bounds.bottom+8 : bounds.top-height-8)+"px";
    this._tipOutside=event=>{if(!event.composedPath().includes(button) && !event.composedPath().includes(tip)) this._closeCopyTip();};
    this._tipEscape=event=>{if(event.key==="Escape") {event.preventDefault();event.stopPropagation();this._closeCopyTip();}};
    this._tipDismiss=()=>this._closeCopyTip();
    document.addEventListener("pointerdown",this._tipOutside);document.addEventListener("keydown",this._tipEscape);window.addEventListener("resize",this._tipDismiss);window.addEventListener("scroll",this._tipDismiss,true);
  }
  _download(blob,extension) {const url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=benchmarkFilename(this._report,extension);link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  async _save() { try {this._download(await this._blob(),"png");} catch {this._message(text(this._hass,"PNG export failed. Start over and try again."));} }
  async _copyText() {
    const value=benchmarkText(this._report,this._hass);
    try {
      if(navigator.clipboard?.writeText) await navigator.clipboard.writeText(value);
      else {
        const input=document.createElement("textarea"),focus=document.activeElement;input.value=value;input.style.cssText="position:fixed;top:0;left:0;opacity:0";this.shadowRoot.append(input);input.select();
        try {if(!document.execCommand("copy")) throw new Error("Copy unavailable");} finally {input.remove();focus?.focus();}
      }
      this._message(text(this._hass,"Text copied."));
    } catch {this._message(text(this._hass,"Could not copy the text. Save the text instead."));}
  }
  _saveText() {this._download(new Blob([benchmarkText(this._report,this._hass)],{type:"text/markdown;charset=utf-8"}),"md");}

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
