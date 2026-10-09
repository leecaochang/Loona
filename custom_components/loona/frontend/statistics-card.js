/* Native-themed live filtering statistics. */
import { language, text, translate, renderNotices, renderVersion, markHtml, markStyles, hideBrokenMark, icon, buttonStyles, cardPreferences, saveCardPreferences, setText, formatNumber, formatDateTime, confirmAction, cancelConfirmation, createHelp, closeHelp, helpStyles } from "./i18n.js?v=1.0.1";

const cardVersion = "1.0.1";
const command = "loona/statistics";
const elementName = "loona-statistics-card";

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function svg(tag, attributes = {}) {
  const element=document.createElementNS("http://www.w3.org/2000/svg",tag);
  for (const [key,value] of Object.entries(attributes)) element.setAttribute(key,String(value));
  return element;
}
function chartText(x,y,size,attributes={}) { return svg("text",{x,y,"font-size":size,fill:"var(--primary-text-color)",...attributes}); }

// Charts stay bound to the active theme: solid primary is "sent", dashed secondary text is "filtered".
const SENT="var(--primary-color)", FILTERED="var(--secondary-text-color)";
let chartSequence=0;
const reducedMotion=()=>window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches===true;
// One authored moment: values ease out exponentially from their previous reading.
function tween(owner,from,to,apply,duration=800) {
  window.cancelAnimationFrame?.(owner.__frame); window.clearTimeout(owner.__settle);
  if (!window.requestAnimationFrame || reducedMotion() || from===to) { apply(to); return; }
  // Frames pause in hidden documents; the timer still lands the exact value.
  owner.__settle=window.setTimeout(()=>{ window.cancelAnimationFrame?.(owner.__frame); apply(to); },duration+250);
  let start;
  const step=now=>{
    start??=now;
    const t=Math.min(1,Math.max(0,(now-start)/duration));
    apply(from+(to-from)*(t===1 ? 1 : 1-2**(-10*t)));
    if (t<1) owner.__frame=window.requestAnimationFrame(step);
  };
  owner.__frame=window.requestAnimationFrame(step);
}
const fixed=value=>Number(value.toFixed(2));
// Charts draw 1:1 in CSS pixels so labels keep their real size at any card width.
function chartWidth(root) {
  const width=Math.max(120,Math.round(root.clientWidth||320));
  if (root.firstElementChild && root.firstElementChild.__width!==width) root.replaceChildren();
  return width;
}

// Lit area equals fraction f of the disc: a left half-disc, widened or narrowed by a half-ellipse terminator.
function phasePath(cx,cy,r,f) {
  if (!(f>0.0005)) return "";
  const k=r*Math.abs(1-2*Math.min(1,f)), top=`${cx} ${cy-r}`, bottom=`${cx} ${cy+r}`;
  return `M${top}A${r} ${r} 0 0 0 ${bottom}A${fixed(k)} ${r} 0 0 ${f>0.5 ? 0 : 1} ${top}Z`;
}
// Labels sit under the chart; wrap onto a second line when the estimated text width exceeds the chart.
function setLabel(chart,value,width) {
  const wide=[...value].reduce((sum,character)=>sum+(character.charCodeAt(0)>0x2e7f ? 12.5 : 6.6),0);
  let lines=[value];
  if (wide>width-8) {
    const spaces=[...value].flatMap((character,index)=>character===" " ? [index] : []), middle=value.length/2;
    const at=spaces.length ? spaces.reduce((best,index)=>Math.abs(index-middle)<Math.abs(best-middle) ? index : best) : Math.ceil(middle);
    lines=[value.slice(0,at),value.slice(spaces.length ? at+1 : at)];
  }
  const label=chart.querySelector('[data-part="label"]'), x=label.getAttribute("x");
  label.replaceChildren(...lines.map((line,index)=>{ const row=svg("tspan",{x,dy:index ? 14 : 0}); row.textContent=line; return row; }));
}
// The lit side of the moon is the percentage; the dark side is the remainder.
function moonChart(root,hass,label,percent,hasUpdates) {
  if (!root.firstElementChild) {
    const id=++chartSequence, r=46, cx=60, cy=56;
    const chart=svg("svg",{viewBox:"0 0 120 170",role:"img","data-chart":"moon"});
    const defs=svg("defs"), gradient=svg("radialGradient",{id:`loona-moon-${id}`,cx:"38%",cy:"34%",r:"75%"}), halo=svg("radialGradient",{id:`loona-halo-${id}`});
    halo.append(svg("stop",{offset:0,style:"stop-color:var(--primary-color);stop-opacity:.2"}),svg("stop",{offset:1,style:"stop-color:var(--primary-color);stop-opacity:0"})); defs.append(halo);
    gradient.append(svg("stop",{offset:0,style:"stop-color:color-mix(in srgb,var(--primary-color) 62%,#fff)"}),svg("stop",{offset:1,style:"stop-color:var(--primary-color)"}));
    defs.append(gradient); chart.append(defs);
    chart.append(svg("circle",{cx,cy,r:r*1.45,fill:`url(#loona-halo-${id})`}));
    chart.append(svg("circle",{cx,cy,r,"data-part":"shadow",style:"fill:color-mix(in srgb,var(--primary-color) 9%,var(--secondary-background-color));stroke:var(--divider-color);stroke-width:1.25"}));
    chart.append(svg("path",{"data-part":"lit",fill:`url(#loona-moon-${id})`}));
    for (const [dx,dy,size] of [[-.34,-.26,.2],[.22,.3,.15],[.3,-.4,.1],[-.2,.42,.09]]) {
      chart.append(svg("circle",{cx:fixed(cx+dx*r),cy:fixed(cy+dy*r),r:fixed(size*r),style:"fill:var(--primary-text-color);opacity:.07"}));
    }
    chart.append(chartText(60,130,22,{"text-anchor":"middle","data-part":"value","font-weight":600}),chartText(60,150,12.5,{"text-anchor":"middle","data-part":"label",fill:"var(--secondary-text-color)"}));
    chart.__geometry={cx,cy,r}; root.append(chart);
  }
  const chart=root.firstElementChild, {cx,cy,r}=chart.__geometry, value=Math.min(100,Math.max(0,Number(percent)||0));
  const formatted=formatNumber(hass,value/100,{style:"percent",maximumFractionDigits:1});
  const lit=hasUpdates ? value/100 : 0, lightPath=chart.querySelector('[data-part="lit"]');
  chart.setAttribute("data-lit",String(fixed(lit)));
  tween(chart,chart.__lit ?? 0,lit,fraction=>{ chart.__lit=fraction; lightPath.setAttribute("d",phasePath(cx,cy,r,fraction)); });
  const number=chart.querySelector('[data-part="value"]'); number.textContent=formatted;
  number.setAttribute("font-size",String(Math.min(22,108/(Math.max(1,formatted.length)*.62))));
  setLabel(chart,hasUpdates ? text(hass,label) : text(hass,"No updates"),120);
  chart.setAttribute("aria-label",text(hass,label)+": "+formatted+(!hasUpdates ? ". "+text(hass,"No updates") : ""));
}

// Constellation of update feeds: a lit four-point star per filtered feed, joined in a line; hollow dots are unfiltered.
const jitter=(index,seed)=>{ const value=Math.sin(index*127.1+seed*311.7)*43758.5453; return value-Math.floor(value)-.5; };
function starPath(cx,cy,r) {
  const k=r*.17;
  return `M${fixed(cx)} ${fixed(cy-r)}Q${fixed(cx+k)} ${fixed(cy-k)} ${fixed(cx+r)} ${fixed(cy)}Q${fixed(cx+k)} ${fixed(cy+k)} ${fixed(cx)} ${fixed(cy+r)}Q${fixed(cx-k)} ${fixed(cy+k)} ${fixed(cx-r)} ${fixed(cy)}Q${fixed(cx-k)} ${fixed(cy-k)} ${fixed(cx)} ${fixed(cy-r)}Z`;
}
function feedChart(root,hass,filtered,total,feeds) {
  const width=chartWidth(root);
  if (!root.firstElementChild) {
    const chart=svg("svg",{viewBox:`0 0 ${width} 170`,role:"img","data-chart":"feeds"});
    chart.append(svg("path",{"data-part":"links",fill:"none",style:"stroke:var(--primary-color);stroke-opacity:.45;stroke-width:1.25;stroke-linecap:round;stroke-linejoin:round"}),svg("g",{"data-part":"stars"}),
      chartText(width/2,130,22,{"data-part":"value","text-anchor":"middle","font-weight":600}),chartText(width/2,150,12.5,{"data-part":"label","text-anchor":"middle",fill:"var(--secondary-text-color)"}));
    chart.__width=width; root.append(chart);
  }
  const chart=root.firstElementChild, all=Math.max(0,Math.floor(Number(total)||0)), count=Math.min(all,Math.max(0,Math.floor(Number(filtered)||0)));
  setLabel(chart,text(hass,"Filtered connections"),width);
  chart.querySelector('[data-part="value"]').textContent=formatNumber(hass,count)+" / "+formatNumber(hass,all);
  // Beyond 48 stars the sky samples proportionally; the exact counts stay in the text.
  const shown=Math.min(all,48), lit=all>48 ? (count>0 ? Math.max(1,Math.round(48*count/all)) : 0) : count;
  // Names apply star by star only while every tracked feed is drawn and the list matches the counts.
  const named=Array.isArray(feeds) && feeds.length===all && all<=48 && feeds.filter(feed=>feed.filtered).length===count ? feeds : null;
  const area={x:10,y:6,w:width-20,h:98};
  let columns=1, size=0;
  for (let candidate=1;candidate<=Math.max(1,shown);candidate++) {
    const fit=Math.min(area.w/candidate,area.h/Math.ceil(shown/candidate));
    if (fit>size+.01) { size=fit; columns=candidate; }
  }
  size=Math.min(size,40);
  const rows=Math.ceil(shown/columns), top=area.y+(area.h-rows*size)/2, stars=[], centers=[];
  for (let index=0;index<shown;index++) {
    const row=Math.floor(index/columns), inRow=Math.min(columns,shown-row*columns), column=row%2 ? inRow-1-index%columns : index%columns;
    const cx=(width-columns*size)/2+((columns-inRow)/2+column+.5)*size+jitter(index,1)*size*.3, cy=top+(row+.5)*size+jitter(index,2)*size*.3;
    const isLit=index<lit;
    let mark;
    if (isLit) {
      mark=svg("path",{d:starPath(cx,cy,Math.min(13,Math.max(5,size*.32))),style:"fill:var(--primary-color);transform-box:fill-box;transform-origin:center"});
      centers.push([cx,cy]);
    } else {
      mark=svg("circle",{cx:fixed(cx),cy:fixed(cy),r:fixed(Math.min(5,Math.max(2.5,size*.1))),fill:"none",style:"stroke:var(--secondary-text-color);stroke-opacity:.6;stroke-width:1.25;pointer-events:all"});
    }
    const feed=named?.[index];
    if (feed?.dashboard) {
      const tip=svg("title",{});
      tip.textContent=feed.filtered ? feed.dashboard : text(hass,"{name} (not filtered)",{name:feed.dashboard});
      mark.append(tip);
    }
    mark.setAttribute("data-feed",""); mark.setAttribute("data-lit",String(isLit)); stars.push(mark);
  }
  chart.querySelector('[data-part="stars"]').replaceChildren(...stars);
  const links=chart.querySelector('[data-part="links"]');
  links.setAttribute("d",centers.length>1 ? "M"+centers.map(([x,y])=>`${fixed(x)} ${fixed(y)}`).join("L") : "");
  if (!root.__shown && lit>0 && !reducedMotion()) {
    root.__shown=true;
    stars.filter(mark=>mark.dataset.lit==="true").forEach((mark,index)=>mark.animate?.([{opacity:0,transform:"scale(.2)"},{opacity:1,transform:"scale(1)"}],{duration:650,delay:150+index*80,easing:"cubic-bezier(.16,1,.3,1)",fill:"backwards"}));
    links.animate?.([{opacity:0},{opacity:1}],{duration:700,delay:300,easing:"cubic-bezier(.16,1,.3,1)",fill:"backwards"});
  }
  chart.setAttribute("aria-label",text(hass,"{filtered} of {total} live connections filtered",{filtered:formatNumber(hass,count),total:formatNumber(hass,all)}));
}

// Smooth monotone-ish curve; control points are clamped so the line never dips below the baseline.
function curve(points) {
  if (points.length<2) return "";
  let d=`M${fixed(points[0][0])} ${fixed(points[0][1])}`;
  for (let index=0;index<points.length-1;index++) {
    const [p0,p1,p2,p3]=[points[Math.max(0,index-1)],points[index],points[index+1],points[Math.min(points.length-1,index+2)]];
    const low=Math.min(p1[1],p2[1]), high=Math.max(p1[1],p2[1]);
    const y1=Math.min(high,Math.max(low,p1[1]+(p2[1]-p0[1])/6)), y2=Math.min(high,Math.max(low,p2[1]-(p3[1]-p1[1])/6));
    d+=`C${fixed(p1[0]+(p2[0]-p0[0])/6)} ${fixed(y1)} ${fixed(p2[0]-(p3[0]-p1[0])/6)} ${fixed(y2)} ${fixed(p2[0])} ${fixed(p2[1])}`;
  }
  return d;
}
const STREAM={left:8,top:30,base:108};
function streamChart(root,hass,history,metrics,max) {
  const width=chartWidth(root), right=width-8, plotRight=width-52;
  if (!root.firstElementChild) {
    const id=++chartSequence, plot=svg("svg",{viewBox:`0 0 ${width} 148`,role:"slider",tabindex:0,"aria-valuemin":0,"data-chart":"stream"}); plot.__width=width;
    const defs=svg("defs"), area=svg("linearGradient",{id:`loona-area-${id}`,x1:0,y1:0,x2:0,y2:1});
    area.append(svg("stop",{offset:0,style:"stop-color:var(--primary-color);stop-opacity:.38"}),svg("stop",{offset:1,style:"stop-color:var(--primary-color);stop-opacity:0"}));
    const clip=svg("clipPath",{id:`loona-reveal-${id}`}); clip.append(svg("rect",{x:0,y:0,width,height:148,"data-part":"reveal"}));
    defs.append(area,clip); plot.append(defs);
    for (const [fraction,part] of [[1,"max"],[.5,"half"],[0,"zero"]]) {
      const y=STREAM.base-(STREAM.base-STREAM.top)*fraction;
      plot.append(svg("line",{x1:STREAM.left,x2:plotRight,y1:y,y2:y,style:`stroke:var(--divider-color);stroke-width:1;${fraction ? "stroke-dasharray:2 4" : ""}`}));
      if (fraction) plot.append(chartText(right,y+4,11,{"data-part":part,"text-anchor":"end",fill:"var(--secondary-text-color)"}));
    }
    const series=svg("g",{"clip-path":`url(#loona-reveal-${id})`});
    series.append(svg("path",{"data-part":"sent-area",style:`fill:url(#loona-area-${id})`}),svg("path",{"data-part":"filtered-area",style:`fill:${FILTERED};opacity:.1`}),
      svg("path",{"data-part":"filtered-line",fill:"none",style:`stroke:${FILTERED};stroke-width:2;stroke-dasharray:5 4;stroke-linecap:round;stroke-linejoin:round`}),
      svg("path",{"data-part":"sent-line",fill:"none",style:`stroke:${SENT};stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round`}),
      svg("circle",{r:3.2,"data-part":"sent-latest",style:`fill:${SENT};stroke:var(--card-background-color);stroke-width:1.5`}),
      svg("circle",{r:3.2,"data-part":"filtered-latest",style:`fill:${FILTERED};stroke:var(--card-background-color);stroke-width:1.5`}));
    plot.append(series);
    plot.append(chartText(STREAM.left,138,12,{"data-part":"history",fill:"var(--secondary-text-color)"}),chartText(plotRight,138,12,{"data-part":"now","text-anchor":"end",fill:"var(--secondary-text-color)"}));
    const scrub=svg("g",{"data-part":"scrub",style:"display:none;pointer-events:none"});
    scrub.append(svg("line",{y1:STREAM.top-6,y2:STREAM.base,"data-part":"rule",style:"stroke:var(--primary-text-color);stroke-opacity:.35;stroke-width:1"}),
      svg("circle",{r:4,"data-part":"scrub-sent",style:`fill:${SENT};stroke:var(--card-background-color);stroke-width:1.5`}),
      svg("circle",{r:4,"data-part":"scrub-filtered",style:`fill:${FILTERED};stroke:var(--card-background-color);stroke-width:1.5`}),
      chartText(STREAM.left,13,12.5,{"data-part":"readout","font-weight":600}));
    plot.append(scrub,svg("rect",{x:0,y:0,width,height:148,fill:"transparent","data-part":"hit"}));
    // Rows carry readouts in the current language, so a reused plot never shows an old one.
    const select=index=>{
      const rows=plot.__rows; if (!rows?.length) return;
      plot.__index=Math.max(0,Math.min(rows.length-1,index)); const best=rows[plot.__index];
      const readout=plot.querySelector('[data-part="readout"]'), place=(part,y)=>{ const dot=plot.querySelector(`[data-part="${part}"]`); dot.setAttribute("cx",String(fixed(best.x))); dot.setAttribute("cy",String(fixed(y))); };
      const rule=plot.querySelector('[data-part="rule"]'); rule.setAttribute("x1",String(fixed(best.x))); rule.setAttribute("x2",String(fixed(best.x)));
      place("scrub-sent",best.sentY); place("scrub-filtered",best.filteredY);
      readout.textContent=best.readout;
      readout.setAttribute("text-anchor",best.x>width/2 ? "end" : "start"); readout.setAttribute("x",String(best.x>width/2 ? right : STREAM.left));
      plot.setAttribute("aria-valuenow",String(plot.__index)); plot.setAttribute("aria-valuetext",best.readout);
      plot.querySelector('[data-part="scrub"]').style.display="";
    };
    const show=event=>{
      const rows=plot.__rows; if (!rows?.length) return;
      const box=plot.getBoundingClientRect(), x=(event.clientX-box.left)/Math.max(1,box.width)*width;
      let best=0; rows.forEach((row,index)=>{ if (Math.abs(row.x-x)<Math.abs(rows[best].x-x)) best=index; });
      select(best);
    };
    // Without a selection the slider reads the latest sample, which is where the keys start.
    const release=()=>{
      plot.__index=undefined; plot.querySelector('[data-part="scrub"]').style.display="none";
      const rows=plot.__rows || [];
      plot.setAttribute("aria-valuenow",String(Math.max(0,rows.length-1))); plot.setAttribute("aria-valuetext",rows.at(-1)?.readout || plot.__caption || "");
    };
    plot.__select=select; plot.__release=release;
    plot.style.touchAction="pan-y";
    for (const name of ["pointerdown","pointermove"]) plot.addEventListener(name,show);
    // A pointer leaving keeps the focused slider's selection; Escape and blur release it.
    for (const name of ["pointerleave","pointercancel"]) plot.addEventListener(name,()=>{ if (!plot.__focused) release(); });
    plot.addEventListener("blur",()=>{ plot.__focused=false; release(); });
    // Arrow keys step through the same samples as pointer scrubbing, starting from the latest.
    plot.addEventListener("focus",()=>{ plot.__focused=true; if (plot.__index===undefined) select(Infinity); });
    plot.addEventListener("keydown",event=>{
      const rows=plot.__rows; if (!rows?.length) return;
      const index=plot.__index ?? rows.length-1;
      const next={ArrowLeft:index-1,ArrowDown:index-1,ArrowRight:index+1,ArrowUp:index+1,Home:0,End:rows.length-1}[event.key];
      if (event.key==="Escape") release();
      else if (next!==undefined) { event.preventDefault(); select(next); }
    });
    root.append(plot);
  }
  const plot=root.firstElementChild, part=name=>plot.querySelector(`[data-part="${name}"]`);
  const start=history.length ? Date.parse(history[0].at)-1000*history[0].seconds : 0, end=history.length ? Date.parse(history[history.length-1].at) : 0, span=Math.max(1,end-start);
  const x=row=>STREAM.left+(plotRight-STREAM.left-6)*(Date.parse(row.at)-start)/span;
  const y=value=>STREAM.base-(STREAM.base-STREAM.top)*Math.max(0,value)/max;
  const sent=history.map(row=>[x(row),y(row.sent)]), filtered=history.map(row=>[x(row),y(row.filtered)]);
  const area=points=>points.length>1 ? `${curve(points)}L${fixed(points.at(-1)[0])} ${STREAM.base}L${fixed(points[0][0])} ${STREAM.base}Z` : "";
  part("sent-line").setAttribute("d",curve(sent)); part("filtered-line").setAttribute("d",curve(filtered));
  part("sent-area").setAttribute("d",area(sent)); part("filtered-area").setAttribute("d",area(filtered));
  for (const [name,points,key] of [["sent-latest",sent,"sent"],["filtered-latest",filtered,"filtered"]]) {
    const dot=part(name); dot.style.display=points.length ? "" : "none";
    if (points.length) { dot.setAttribute("cx",String(fixed(points.at(-1)[0]))); dot.setAttribute("cy",String(fixed(points.at(-1)[1]))); }
  }
  const number=value=>formatNumber(hass,value,{minimumFractionDigits:1,maximumFractionDigits:1});
  part("max").textContent=number(max); part("half").textContent=number(max/2);
  plot.__rows=history.map((row,index)=>{
    const minutes=Math.round((end-Date.parse(row.at))/60000);
    const when=minutes<1 ? text(hass,"Now") : text(hass,"{minutes} min ago",{minutes:formatNumber(hass,minutes)});
    return {x:sent[index][0],sentY:sent[index][1],filteredY:filtered[index][1],
      readout:`${when} · ${text(hass,"Sent")} ${number(row.sent)} · ${text(hass,"Filtered out")} ${number(row.filtered)}`};
  });
  const caption=history.length ? text(hass,"{minutes} min history",{minutes:formatNumber(hass,span/60000,{maximumFractionDigits:1})}) : text(hass,"No history yet");
  part("history").textContent=caption; part("now").textContent=history.length ? text(hass,"Now") : "";
  const rates={sent:number(metrics.forwarded_rate),filtered:number(metrics.avoided_rate)}, unit=text(hass,"updates/s");
  plot.setAttribute("aria-label",`${text(hass,"Sent")}: ${rates.sent} ${unit}. ${text(hass,"Filtered out")}: ${rates.filtered} ${unit}. ${caption}`);
  plot.setAttribute("aria-valuemax",String(Math.max(0,history.length-1))); plot.__caption=caption;
  if (plot.__index!==undefined && history.length) plot.__select(plot.__index); else plot.__release();
  if (!root.__revealed && history.length>1) {
    root.__revealed=true; const reveal=part("reveal");
    tween(plot,0,width,value=>reveal.setAttribute("width",String(fixed(value))),1100);
  }
}

function install() {
  // Wait for HA bootstrap to install its current HTMLElement/registry pair.
  const app = document.querySelector("home-assistant");
  if (!app?.hass) {
    window.setTimeout(install, 1000);
    return;
  }
  if (customElements.get(elementName)) return;

  class LoonaStatisticsCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._sequence = 0;
      this._visible = true;
      this._lastRequest = 0;
      this.shadowRoot.innerHTML = `
        <style>${helpStyles}${markStyles}${buttonStyles}
          :host { user-select:text; -webkit-user-select:text; display:block; color:var(--primary-text-color); }
          ha-card { user-select:text; -webkit-user-select:text; padding:24px; overflow:hidden; }
          header { display:flex; justify-content:space-between; align-items:start; gap:16px; }
          header>div { flex:1; min-width:0; }
          header>button { flex-shrink:0; white-space:nowrap; }
          h2 { margin:0; font-size:20px; line-height:1.4; font-weight:500; }
          p { margin:8px 0 0; font-size:14px; line-height:1.5; color:var(--secondary-text-color); }
          .state { display:flex; align-items:flex-start; gap:8px; margin:6px 0 0; color:var(--primary-text-color); font-size:14px; line-height:1.5; }
          .state::before { content:""; flex-shrink:0; width:9px; height:9px; margin-top:7px; border-radius:50%; background:var(--disabled-text-color); }
          .state[data-tone="active"]::before { background:var(--primary-color); }
          .state[data-tone="waiting"]::before { background:transparent; box-shadow:inset 0 0 0 2px var(--primary-color); }
          .state[data-tone="problem"]::before { background:var(--error-color); }
          button { font:inherit; color:var(--primary-text-color); }
          button { border:0; border-radius:var(--ha-border-radius,8px); min-height:44px;
            padding:8px 12px; background:transparent; color:var(--primary-color); cursor:pointer; transition:background-color .15s; }
          button:hover { background:var(--secondary-background-color); }
          button:disabled { color:var(--disabled-text-color); cursor:default; }
          button:focus-visible,summary:focus-visible,#stream-chart svg:focus-visible {
            outline:2px solid var(--primary-color); outline-offset:2px; }
          ::selection { background:var(--primary-color); color:var(--text-primary-color,#fff); }
          /* One continuous wash: the hero holds the deepest tint, Totals carries it on and fades into the card. */
          ha-card { --loona-wash-deep:color-mix(in srgb,var(--primary-color) 8%,color-mix(in srgb,var(--secondary-background-color) 60%,var(--card-background-color)));
            --loona-wash-mid:color-mix(in srgb,var(--primary-color) 5%,color-mix(in srgb,var(--secondary-background-color) 35%,var(--card-background-color))); }
          .hero { position:relative; margin:20px -24px 0; padding:20px 24px 12px; font-variant-numeric:tabular-nums;
            background:linear-gradient(180deg,var(--loona-wash-deep),var(--loona-wash-mid)); }
          .totals { margin:0 -24px; padding:4px 24px 18px; border-top:1px solid color-mix(in srgb,var(--primary-color) 12%,transparent);
            background:linear-gradient(180deg,var(--loona-wash-mid),var(--card-background-color)); }
          .hero-top,.totals-visual { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); align-items:start; gap:8px 0; }
          .hero-top { align-items:center; }
          .totals-visual { margin:12px 0 0; }
          .gauge { min-width:0; }
          .gauge-text .big { margin:0; font-size:40px; line-height:1.1; font-weight:500; color:var(--primary-text-color); }
          .gauge-text .big span:last-child { font-size:.55em; margin-inline-start:2px; }
          .gauge-text p { margin:4px 0 0; font-size:13px; line-height:1.4; }
          .rates { display:grid; gap:14px; margin:0; }
          .rate dt { display:flex; align-items:center; gap:8px; font-size:13px; line-height:1.5; color:var(--secondary-text-color); }
          .rate dd { display:flex; align-items:baseline; gap:8px; margin:2px 0 0; font-size:30px; font-weight:500; line-height:1.15; }
          .rate dd small { font-size:12px; font-weight:400; color:var(--secondary-text-color); }
          .key { flex-shrink:0; width:22px; height:0; border-top:3px solid var(--primary-color); border-radius:2px; }
          .rate.filtered .key { border-top:2px dashed var(--secondary-text-color); }
          .metric-tools { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-top:8px; }
          .chart-choice { display:flex; align-items:center; gap:12px; min-height:44px; font-size:14px; cursor:pointer; }
          .chart-choice input { width:18px; height:18px; accent-color:var(--primary-color); }
          .chart-choice input:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }
          #interval-note { margin:0; }
          .metric-chart { min-width:0; }
          .metric-chart svg { display:block; width:100%; height:auto; font-family:inherit; overflow:visible; }
          #stream-chart { grid-column:1/-1; margin-top:4px; }
          #reduction-chart svg,#estimate-chart svg { width:128px; max-width:100%; }
          .ledger { margin:12px 0 0; font-variant-numeric:tabular-nums; }
          .row { display:flex; align-items:baseline; gap:8px; padding:5px 0; font-size:14px; line-height:1.5; }
          .row dt { flex:0 1 auto; min-width:0; color:var(--primary-text-color); }
          .row .leader { flex:1 1 16px; min-width:16px; align-self:end; margin-bottom:5px; border-bottom:1px dotted var(--secondary-text-color); opacity:.5; }
          .row dd { flex:none; margin:0; text-align:end; font-weight:500; }
          .fact-heading { margin:16px 0 0; }
          .fact-heading h3 { margin:0; font-size:15px; font-weight:500; }
          .actions { display:flex; justify-content:space-between; align-items:center; gap:12px;
            border-top:1px solid var(--divider-color); padding-top:12px; margin-top:16px; }
          .actions p { flex:1; min-width:0; margin:0; font-size:12px; }
          details { margin-top:20px; border-top:1px solid var(--divider-color); padding-top:16px; }
          summary { cursor:pointer; min-height:36px; font-size:15px; line-height:1.5; }
          .rows { margin:0; padding:0; list-style:none; overflow-wrap:anywhere; }
          .rows>li { border-top:1px solid var(--divider-color); padding:12px 0; }
          .section-summary { min-height:44px; }
          .section-summary .help { margin-inline-start:auto; }
          .rows small,.notice-items small { display:block; font-size:12px; color:var(--secondary-text-color); overflow-wrap:anywhere; }
          .loona-notices ul { list-style:none; padding:0; margin:0; }
          .loona-notices li { padding:16px 0; border-top:1px solid var(--divider-color); }
          .loona-notices li:first-child { border-top:0; }
          .loona-notices h3 { margin:0; font-size:14px; line-height:1.5; }
          .loona-notices .notice-items { max-height:160px; overflow:auto; overflow-wrap:anywhere; font-size:12px; scrollbar-color:var(--divider-color) transparent; }
          #error { color:var(--error-color); overflow-wrap:anywhere; }
          [hidden] { display:none !important; }
          @media(max-width:480px) { ha-card { padding:16px; } .hero,.totals { margin-inline:-16px; padding-inline:16px; }
            .rate dd { font-size:26px; } .gauge-text .big { font-size:34px; }
            .actions { align-items:center; } }
        </style>
        <ha-card>
          <header><div class="brand">${markHtml}<div class="heading"><h2 data-i18n="Loona statistics">Loona statistics</h2><p id="version"></p><p class="state" id="state" role="status" data-tone="idle" data-i18n="Loading statistics...">Loading statistics...</p></div></div>
            <button id="refresh" class="btn icon-only" type="button" aria-label="Refresh" title="Refresh">${icon("refresh")}</button></header>
          <p id="error" role="alert" hidden></p>
          <div id="content" hidden>
            <div class="hero">
              <div class="hero-top">
                <div class="gauge">
                  <div class="gauge-text metric-text"><p class="big"><span id="reduction">0</span><span>%</span></p><p data-i18n="Updates filtered out">Updates filtered out</p><p><small data-i18n="of all updates">of all updates</small></p></div>
                  <div id="reduction-chart" class="metric-chart" hidden></div>
                </div>
                <dl class="rates">
                  <div class="rate sent"><dt><i class="key"></i><span data-i18n="Sent">Sent</span></dt><dd><span id="forwarded">0</span><small data-i18n="updates/s">updates/s</small></dd></div>
                  <div class="rate filtered"><dt><i class="key"></i><span data-i18n="Filtered out">Filtered out</span></dt><dd><span id="avoided">0</span><small data-i18n="updates/s">updates/s</small></dd></div>
                </dl>
                <div id="stream-chart" class="metric-chart" hidden></div>
              </div>
            </div>
            <section class="totals"><div class="section-heading fact-heading"><h3 data-i18n="Totals and entities">Totals and entities</h3><span id="scope-help"></span></div>
            <div id="totals-visual" class="totals-visual" hidden><div id="estimate-chart" class="metric-chart"></div><div id="feeds-chart" class="metric-chart"></div></div>
            <div class="metric-tools"><label class="chart-choice"><input id="show-charts" type="checkbox"><span data-i18n="Show statistics charts">Show statistics charts</span></label><span id="rates-help"></span></div>
            <dl class="ledger">
              <div class="row"><dt data-i18n="Updates sent since reset">Updates sent since reset</dt><i class="leader"></i><dd id="forwarded-total"></dd></div>
              <div class="row"><dt data-i18n="Updates filtered out since reset">Updates filtered out since reset</dt><i class="leader"></i><dd id="avoided-total"></dd></div>
              <div class="row" id="subscriptions-row"><dt id="subscriptions-label" data-i18n="Connections filtered / total">Connections filtered / total</dt><i class="leader"></i><dd id="subscriptions"></dd></div>
              <div class="row"><dt data-i18n="Entities currently included">Entities currently included</dt><i class="leader"></i><dd id="scope"></dd></div>
              <div class="row" id="estimate-row"><dt data-i18n="Estimated entities trimmed">Estimated entities trimmed</dt><i class="leader"></i><dd id="estimate"></dd></div>
            </dl></section>
            <div class="actions"><p id="reset-time"></p><span class="action-help"><button id="reset" class="btn small" type="button">${icon("reset")}<span data-i18n="Reset live statistics">Reset live statistics</span></button><span id="reset-help"></span></span></div>
            <div id="notices"></div>
            <details id="loads"><summary class="section-summary"><span data-i18n="Recent page loads">Recent page loads</span> <span id="load-count"></span><span id="loads-help"></span></summary>
              <ul id="load-rows" class="rows"></ul>
            </details>
            <details><summary class="section-summary"><span data-i18n="Browser performance">Browser performance</span><span id="performance-help"></span></summary>
              <ul id="performance-rows" class="rows"></ul>
              <p data-i18n="Entities sending the most updates since reset">Entities sending the most updates since reset</p>
              <ul id="noisy-rows" class="rows"></ul>
            </details>
          </div>
        </ha-card>`;
      hideBrokenMark(this.shadowRoot);
      this._get("rates-help").append(createHelp(this._hass,"Live updates","","interval"));
      this._get("scope-help").append(createHelp(this._hass,"Totals and entities","A live connection is the link a dashboard tab keeps open to Home Assistant. Each open tab usually has one connection, sometimes more. 'Connections filtered / total' shows how many of them Loona is filtering. 'Estimated entities trimmed' is the percentage of Home Assistant's entities outside Loona's configured inclusion set. It describes potential entity reduction, not measured update reduction, and remains visible when filtering is off."));
      this._get("loads-help").append(createHelp(this._hass,"Recent page loads","Shows how many entities and card files were filtered out of those available for each dashboard's latest recorded page load. It does not measure loading time."));
      this._get("performance-help").append(createHelp(this._hass,"Browser performance","Lists the 20 entities with the most updates sent since reset, alongside browser reports of slow frames, script work and event subscriptions that may bypass filtering. These reports cover only part of the browser's work. Items marked 'before measuring' happened before Loona started watching."));
      this._get("reset-help").append(createHelp(this._hass,"Reset live statistics","Clears the live counters, recent page-load records and browser readings. Your Loona settings and Home Assistant's recorded history are untouched."));
      this._get("refresh").addEventListener("click", () => this._fetch());
      this._get("reset").addEventListener("click", () => this._reset());
      this._get("show-charts").addEventListener("change", () => {
        if (this._hass?.user?.is_admin) saveCardPreferences(this._hass, {charts:this._get("show-charts").checked});
      });
    }

    static getStubConfig() { return { type: "custom:loona-statistics-card" }; }
    setConfig(config) {
      if (config.title !== undefined && typeof config.title !== "string") throw new Error(text(this._hass, "Loona card title must be text"));
      if (config.show_charts !== undefined && typeof config.show_charts !== "boolean") throw new Error(text(this._hass, "show_charts must be a boolean"));
      this._defaultCharts = config.show_charts !== false;
      this._customTitle = config.title;
      this._localize();
    }
    _localize() {
      translate(this.shadowRoot, this._hass);
      this.shadowRoot.querySelector("h2").textContent = this._customTitle || text(this._hass, "Loona statistics");
      this._get("refresh").setAttribute("aria-label", text(this._hass, "Refresh")); this._get("refresh").title = text(this._hass, "Refresh");
      if (this._data) this._render(this._data);
      if (this._errorKey) {
        this._get("error").textContent = text(this._hass, this._errorKey);
        if (!this._data) this._get("state").textContent = text(this._hass, "Unable to load statistics");
      }
      const metadata = window.customCards?.find(card => card.type === elementName);
      if (metadata) { metadata.name = text(this._hass, "Loona statistics"); metadata.description = text(this._hass, "Live filtering statistics and recent page loads"); }
    }
    getCardSize() { return 7; }
    getGridOptions() { return { columns: 12, min_columns: 6 }; }
    _get(id) { return this.shadowRoot.getElementById(id); }
    set hass(value) {
      const changedUser = this._hass?.user?.id !== value?.user?.id;
      const changedLanguage = language(this._hass) !== language(value);
      this._hass = value;
      if (changedLanguage) this._localize();
      if (changedUser || !value?.user?.is_admin) {
        cancelConfirmation(this); closeHelp(this.shadowRoot);
        this._sequence++;
        this._data = undefined;
        this._errorKey = undefined; this._get("error").hidden = true;
        this._loading = false;
        this._get("content").hidden = true;
        this._get("load-rows").replaceChildren();
        this._get("notices").replaceChildren();
        this._get("noisy-rows").replaceChildren();
        this._get("performance-rows").replaceChildren();
        this._get("version").textContent = "";
        this.shadowRoot.querySelectorAll(".metric-chart").forEach(root=>{ root.replaceChildren(); root.hidden=true; });
        this._get("show-charts").checked = false;
      }
      if (!value?.user?.is_admin) {
        this._get("content").hidden = true;
        this._get("state").textContent = text(this._hass, 'Sign in as an administrator to view Loona statistics.');
        this._get("refresh").disabled = true;
        return;
      }
      this._get("refresh").disabled = false;
      if (changedUser || !this._data && !this._loading) this._fetch();
    }
    connectedCallback() {
      this._observer = new IntersectionObserver(([entry]) => { this._visible = entry.isIntersecting; });
      this._observer.observe(this);
      if (typeof ResizeObserver==="function") {
        this._resize = new ResizeObserver(() => { if (this._data && this._chartsEnabled()) this._renderCharts(this._data); });
        this.shadowRoot.querySelectorAll(".metric-chart").forEach(root=>this._resize.observe(root));
      }
      this._timer = window.setInterval(() => {
        const interval = (this._data?.interval_seconds || 30) * 1000;
        if (!document.hidden && this._visible && Date.now() - this._lastRequest >= interval && !this._loading) this._fetch();
      }, 1000);
      this._capabilityListener = () => { if (this._data) renderNotices(this._get("notices"), this._hass, this._data.notices || [], this._data.notice_labels); };
      window.addEventListener("loona-capabilities", this._capabilityListener);
      this._preferenceListener = () => { if (this._data && this._hass?.user?.is_admin) { this._renderCharts(this._data); this._capabilityListener(); if (this._chartsEnabled() && !this._historyRequested && !this._loading) this._fetch(); } };
      window.addEventListener("loona-card-preferences", this._preferenceListener);
      this._resetListener = () => this._fetch(); window.addEventListener("loona-statistics-reset", this._resetListener);
      if (this._hass) this._fetch();
    }
    disconnectedCallback() {
      cancelConfirmation(this); closeHelp(this.shadowRoot);
      window.removeEventListener("loona-capabilities", this._capabilityListener);
      window.removeEventListener("loona-card-preferences", this._preferenceListener);
      window.removeEventListener("loona-statistics-reset", this._resetListener);
      window.clearInterval(this._timer);
      this._observer?.disconnect(); this._resize?.disconnect();
      this._sequence++;
      this._loading = false;
    }
    async _fetch() {
      if (!this.isConnected || !this._hass?.user?.is_admin || !this._hass.connection?.connected) return;
      const sequence = ++this._sequence;
      this._loading = true;
      this._lastRequest = Date.now();
      this._get("refresh").disabled = true; this._get("refresh").toggleAttribute("data-busy", true);
      try {
        const withHistory=this._chartsEnabled() && (!this._data || this._data.version===cardVersion);
        let data;
        try { data=await this._hass.callWS({type:command,...(withHistory ? {include_rate_history:true} : {})}); }
        catch (error) {
          if (!withHistory || error.code!=="invalid_format") throw error;
          data=await this._hass.callWS({type:command});
        }
        if (sequence !== this._sequence || !this._hass?.user?.is_admin) return;
        this._data = data; this._historyRequested=withHistory || (this._chartsEnabled() && data.version!==cardVersion);
        this._errorKey = undefined;
        this._get("error").hidden = true;
        this._render(data);
      } catch (error) {
        if (sequence !== this._sequence) return;
        this._errorKey = "Could not load statistics. Check that Loona is running, then press Refresh.";
        this._get("error").textContent = text(this._hass, this._errorKey);
        this._get("error").hidden = false;
        if (!this._data) { this._get("state").textContent = text(this._hass, 'Unable to load statistics'); this._get("state").dataset.tone = "problem"; }
      } finally {
        if (sequence === this._sequence) {
          this._loading = false;
          this._get("refresh").disabled = false; this._get("refresh").toggleAttribute("data-busy", false);
          if (!this._errorKey && this._data?.version===cardVersion && this._chartsEnabled() && !this._historyRequested) this._fetch();
        }
      }
    }
    async _reset() {
      if (!this._data?.reset_entity || this._resetting || !this._hass?.user?.is_admin) return;
      const account = this._hass.user.id;
      if (!await confirmAction(this, "Reset live statistics?",
          "Clear the live counters, recent page-load records and browser readings? Your Loona settings and Home Assistant's recorded history are untouched.", "Reset live statistics")) return;
      if (this._hass?.user?.id !== account || !this._hass.user.is_admin || !this.isConnected || this._resetting) return;
      this._resetting = true;
      this._get("reset").disabled = true;
      try {
        await this._hass.callService("button", "press", { entity_id: this._data.reset_entity });
        await this._fetch();
      } catch {
        this._errorKey = "Could not reset statistics. Try Reset live statistics on the Loona device page.";
        this._get("error").textContent = text(this._hass, this._errorKey);
        this._get("error").hidden = false;
      } finally {
        this._resetting = false;
        this._get("reset").disabled = !this._data?.reset_entity;
      }
    }
    _chartsEnabled() {
      const preference=cardPreferences(this._hass).charts;
      return typeof preference==="boolean" ? preference : this._defaultCharts!==false;
    }
    _renderCharts(data) {
      const enabled=this._chartsEnabled();
      this._get("show-charts").checked=enabled;
      this.shadowRoot.querySelectorAll(".metric-text").forEach(root=>root.hidden=enabled);
      for (const id of ["subscriptions-row","estimate-row"]) this._get(id).hidden=enabled;
      this._get("totals-visual").hidden=!enabled;
      this.shadowRoot.querySelectorAll(".metric-chart").forEach(root=>{ root.hidden=!enabled; if (!enabled) { root.replaceChildren(); root.__revealed=false; root.__shown=false; } });
      if (!enabled) return;
      const metrics=data.metrics;
      const history=(data.rate_history || []).filter(row=>Number.isFinite(Date.parse(row.at)) && Number.isFinite(row.sent) && Number.isFinite(row.filtered));
      const max=Math.max(1,metrics.forwarded_rate,metrics.avoided_rate,...history.flatMap(row=>[row.sent,row.filtered]));
      streamChart(this._get("stream-chart"),this._hass,history,metrics,max);
      moonChart(this._get("reduction-chart"),this._hass,"Updates filtered out",metrics.update_reduction,metrics.forwarded_rate+metrics.avoided_rate>0);
      moonChart(this._get("estimate-chart"),this._hass,"Estimated entities trimmed",metrics.reduction_estimate,true);
      feedChart(this._get("feeds-chart"),this._hass,metrics.filtered_subscriptions,metrics.managed_subscriptions,data.feeds);
    }
    _render(data) {
      const metrics = data.metrics;
      renderVersion(this._get("version"), this._hass, data.version, cardVersion);
      renderNotices(this._get("notices"), this._hass, data.notices || [], data.notice_labels);
      this._get("content").hidden = false;
      this._renderCharts(data);
      const format = (value) => formatNumber(this._hass, value, { maximumFractionDigits: 1 });
      const problem = data.compatibility_problem || !data.complete;
      const on = !problem && data.controls.enabled && data.controls.entity_filtering;
      // A hollow dot means filtering is on but no open dashboard is filtered at this moment.
      this._get("state").dataset.tone = problem ? "problem" : !on ? "idle" : metrics.filtered_subscriptions > 0 ? "active" : "waiting";
      setText(this._get("state"), data.compatibility_problem ? text(this._hass, "Some features are unavailable. See Loona's diagnostics.")
        : !data.complete ? text(this._hass, "Dashboard scan incomplete. All entities are being sent.")
        : !data.controls.enabled || !data.controls.entity_filtering ? text(this._hass, "Entity filtering is disabled")
        : metrics.filtered_subscriptions ? text(this._hass, "Entity filtering is active")
        // This card usually sits on an unselected dashboard, so earlier filtering must not read as none.
        : metrics.avoided_updates ? text(this._hass, "Entity filtering is on, but no open dashboard is being filtered right now. The totals include earlier filtering.")
        : text(this._hass, "Entity filtering is on, but no open dashboard is being filtered right now. Open a selected dashboard with a selected account."));
      for (const [id, key] of [["forwarded", "forwarded_rate"], ["avoided", "avoided_rate"], ["reduction", "update_reduction"],
        ["forwarded-total", "forwarded_updates"], ["avoided-total", "avoided_updates"]]) this._get(id).textContent = key.endsWith("_rate") ? formatNumber(this._hass, metrics[key], {minimumFractionDigits:1, maximumFractionDigits:1}) : format(metrics[key]);
      this._get("interval").textContent = (data.sample_seconds
        ? text(this._hass, "Measured over the last {seconds} seconds.", { seconds: format(data.sample_seconds) })
        : text(this._hass, "Rates update within {seconds} seconds.", { seconds: format(data.interval_seconds) }))
        + " " + text(this._hass, "Each update counts once per connection, so opening more tabs increases the totals. These figures measure entity updates, not data size, bandwidth, CPU usage or loading speed.")
        + " " + text(this._hass,"Charts show up to 15 minutes of history and refresh along with the statistics. Chart history is kept only in memory and clears on reset or restart. Sent and filtered out share one scale.")
        + " " + text(this._hass,"On the moons, the lit part shows the percentage and the dark part is the rest.");
      this._get("subscriptions").textContent = format(metrics.filtered_subscriptions) + " / " + format(metrics.managed_subscriptions);
      this._get("scope").textContent = text(this._hass, metrics.current_scope === 1 ? "1 entity" : "{count} entities", { count: format(metrics.current_scope) });
      this._get("estimate").textContent = formatNumber(this._hass, metrics.reduction_estimate / 100, {style:"percent",maximumFractionDigits:1});
      this._get("reset-time").textContent = text(this._hass, "Since {time}", { time: formatDateTime(this._hass, data.reset_at) });
      this._get("reset").disabled = !data.reset_entity || this._resetting;
      this._get("load-count").textContent = "(" + data.page_loads.length + ")";
      this._get("load-rows").replaceChildren(...(data.page_loads.length ? data.page_loads.map(row => {
        const item = node("li"); item.append(node("strong", row.title));
        item.append(node("p", formatDateTime(this._hass, row.at)));
        const filteredOf = counts => ({filtered: Math.max(0, counts.available - counts.sent), available: counts.available});
        item.append(node("p", text(this._hass, "Entities filtered: {filtered} out of {available}", filteredOf(row.entities))));
        item.append(node("p", row.resources ? text(this._hass, "Card files filtered: {filtered} out of {available}", filteredOf(row.resources)) : text(this._hass, "No card file count was recorded for this load.")));
        return item;
      }) : [node("li", text(this._hass, "No page loads recorded yet. Reload one of your dashboards."))]));
      this._get("noisy-rows").replaceChildren(...(data.noisy_entities?.entities || []).map(row => {
        const item=node("li"); const label=row.label || this._hass?.states?.[row.entity_id]?.attributes?.friendly_name || row.entity_id;
        item.append(node("span",label)); if (label!==row.entity_id) item.append(node("small",row.entity_id));
        item.append(node("p",text(this._hass,"{count} updates sent",{count:format(row.updates)}))); return item;
      }));
      if (data.noisy_entities?.untracked_updates) this._get("noisy-rows").append(node("li",
        text(this._hass, "Only the busiest entities are listed. {count} more updates came from entities not shown.", {count:format(data.noisy_entities.untracked_updates)})));
      this._get("performance-rows").replaceChildren(...(data.browser_reports || []).map(row => {
        const item = node("li");
        item.append(node("strong", row.dashboard));
        item.append(node("p", formatDateTime(this._hass, row.at)));
        item.append(node("p", row.loaf_supported ? text(this._hass, "Slow frames: {count}, adding up to {ms} ms of delay", {count:format(row.frames), ms:format(row.blocking_ms)})
          : text(this._hass, "This browser cannot report slow frames.")));
        for (const script of row.scripts) {
          const label=data.resource_labels?.[script.source];
          if (label && label!==script.source) item.append(node("p",label));
          item.append(node("p", text(this._hass,
          "{source} ({phase}): {ms} ms, including {layout} ms re-measuring the page", {source:script.source,
            phase:text(this._hass, script.phase === "buffered" ? "before measuring" : "while measuring"),
            ms:format(script.duration_ms), layout:format(script.forced_layout_ms)})));
        }
        for (const subscription of row.subscriptions) item.append(node("p", `${subscription.type}: ${format(subscription.count)}`));
        if (row.subscriptions.some(value => value.type === "subscribe_events/state_changed" || value.type === "subscribe_events/*")) {
          item.append(node("p", text(this._hass, "This dashboard listens to all Home Assistant events, which can bypass entity filtering.")));
        }
        return item;
      }));
    }
  }

  customElements.define(elementName, LoonaStatisticsCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: elementName, name: text(app.hass, "Loona statistics"), description: text(app.hass, "Live filtering statistics and recent page loads"), preview: true });
  // One report per full page load; SPA navigation does not create a new snapshot.
  const dashboard = location.pathname.split("/")[1] || "lovelace";
  let attempts = 0;
  const reportLoad = () => {
    const hass = document.querySelector("home-assistant")?.hass;
    if (hass?.connection?.connected && Object.keys(hass.states || {}).length) {
      hass.callWS({ type: "loona/page_load", dashboard }).catch(() => {});
    } else if (++attempts < 120) window.setTimeout(reportLoad, 250);
  };
  reportLoad();
}
install();
