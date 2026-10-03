/* Native-themed live filtering statistics. */
import { language, text, translate, renderNotices, renderVersion, cardPreferences, saveCardPreferences, setText, formatNumber, formatDateTime, confirmAction, cancelConfirmation, createHelp, closeHelp, helpStyles } from "./i18n.js?v=0.9.9";

const cardVersion = "0.9.9";
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
function rateChart(root,hass,label,value,history,key,max) {
  if (!root.firstElementChild) {
    const plot=svg("svg",{viewBox:"0 0 120 160",role:"img","data-chart":key});
    plot.append(chartText(6,18,14,{"data-part":"label"}),chartText(6,50,26,{"data-part":"value"}),chartText(6,72,14,{"data-part":"unit"}));
    plot.append(svg("line",{x1:6,x2:114,y1:128,y2:128,stroke:"var(--divider-color)"}));
    plot.append(svg("polyline",{fill:"none",stroke:"var(--primary-color)","stroke-width":2,"data-part":"line"}));
    plot.append(svg("circle",{r:2.5,fill:"var(--primary-color)","data-part":"latest"}));
    plot.append(chartText(6,150,13.5,{"data-part":"history",fill:"var(--secondary-text-color)"})); root.append(plot);
  }
  const plot=root.firstElementChild;
  const formatted=formatNumber(hass,value,{minimumFractionDigits:1,maximumFractionDigits:1});
  plot.querySelector('[data-part="label"]').textContent=text(hass,label);
  const number=plot.querySelector('[data-part="value"]'); number.textContent=formatted;
  number.setAttribute("font-size",String(Math.min(26,104/(Math.max(1,formatted.length)*.62))));
  plot.querySelector('[data-part="unit"]').textContent=text(hass,"updates/s");
  const start=history.length ? Date.parse(history[0].at)-1000*history[0].seconds : 0;
  const end=history.length ? Date.parse(history[history.length-1].at) : 0;
  const span=Math.max(1,end-start);
  const points=history.map(row=>[6+108*(Date.parse(row.at)-start)/span,128-44*Math.max(0,row[key])/max]);
  plot.querySelector('[data-part="line"]').setAttribute("points",points.map(([x,y])=>`${x.toFixed(2)},${y.toFixed(2)}`).join(" "));
  const dot=plot.querySelector('[data-part="latest"]'); dot.hidden=!points.length; dot.style.display=points.length ? "" : "none";
  if (points.length) { dot.setAttribute("cx",String(points[points.length-1][0])); dot.setAttribute("cy",String(points[points.length-1][1])); }
  const caption=history.length ? text(hass,"{minutes} min history",{minutes:formatNumber(hass,span/60000,{maximumFractionDigits:1})}) : text(hass,"No history yet");
  plot.querySelector('[data-part="history"]').textContent=caption;
  plot.setAttribute("aria-label",text(hass,"{label}: {rate} updates/s. {history}",{label:text(hass,label),rate:formatted,history:caption}));
}
function ringChart(root,hass,label,value,full,hasUpdates) {
  if (!root.firstElementChild) {
    const chart=svg("svg",{viewBox:full ? "0 0 120 160" : "0 0 100 100",role:"img","data-chart":"ring"});
    if (full) chart.append(chartText(60,18,14,{"text-anchor":"middle","data-part":"label"}));
    const cx=full ? 60 : 50, cy=full ? 88 : 50;
    chart.append(svg("circle",{cx,cy,r:34,fill:"none",stroke:"var(--divider-color)","stroke-width":12}));
    chart.append(svg("circle",{cx,cy,r:34,fill:"none",stroke:"var(--primary-color)","stroke-width":12,pathLength:100,transform:`rotate(-90 ${cx} ${cy})`,"data-part":"ring"}));
    chart.append(chartText(cx,cy+7,22,{"text-anchor":"middle","data-part":"value"}));
    if (full) chart.append(chartText(60,150,13.5,{"text-anchor":"middle","data-part":"empty",fill:"var(--secondary-text-color)"})); root.append(chart);
  }
  const chart=root.firstElementChild, percentage=Math.min(100,Math.max(0,Number(value)||0));
  const formatted=formatNumber(hass,percentage/100,{style:"percent",maximumFractionDigits:1});
  chart.querySelector('[data-part="ring"]').setAttribute("stroke-dasharray",`${percentage} ${100-percentage}`);
  const number=chart.querySelector('[data-part="value"]'); number.textContent=formatted;
  number.setAttribute("font-size",String(Math.min(22,58/(Math.max(1,formatted.length)*.62))));
  if (full) {
    chart.querySelector('[data-part="label"]').textContent=text(hass,label);
    chart.querySelector('[data-part="empty"]').textContent=hasUpdates ? "" : text(hass,"No updates");
  }
  chart.setAttribute("aria-label",text(hass,label)+": "+formatted+(!hasUpdates ? ". "+text(hass,"No updates") : ""));
}
function feedChart(root,hass,filtered,total) {
  if (!root.firstElementChild) {
    const chart=svg("svg",{viewBox:"0 0 320 78",role:"img","data-chart":"feeds"});
    chart.append(chartText(0,18,14,{"data-part":"label"}));
    chart.append(svg("rect",{x:0,y:30,width:320,height:40,fill:"var(--secondary-background-color)"}));
    chart.append(svg("rect",{x:0,y:30,height:40,fill:"var(--primary-color)","data-part":"bar"}));
    chart.append(svg("rect",{x:123,y:37,width:74,height:26,fill:"var(--card-background-color)"}));
    chart.append(chartText(160,56,18,{"text-anchor":"middle","data-part":"value"})); root.append(chart);
  }
  const chart=root.firstElementChild, count=Math.min(Math.max(0,Number(total)||0),Math.max(0,Number(filtered)||0));
  chart.querySelector('[data-part="label"]').textContent=text(hass,"Filtered update feeds");
  chart.querySelector('[data-part="bar"]').setAttribute("width",String(total ? 320*count/total : 0));
  const formatted=formatNumber(hass,count)+" / "+formatNumber(hass,total);
  const number=chart.querySelector('[data-part="value"]'); number.textContent=formatted;
  number.setAttribute("font-size",String(Math.min(18,66/(Math.max(1,formatted.length)*.62))));
  chart.setAttribute("aria-label",text(hass,"{filtered} of {total} update feeds filtered",{filtered:formatNumber(hass,count),total:formatNumber(hass,total)}));
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
        <style>${helpStyles}
          :host { user-select:text; -webkit-user-select:text; display:block; color:var(--primary-text-color); }
          ha-card { user-select:text; -webkit-user-select:text; padding:24px; overflow:hidden; }
          header { display:flex; justify-content:space-between; align-items:start; gap:16px; }
          header>div { flex:1; min-width:0; }
          header>button { flex-shrink:0; white-space:nowrap; }
          h2 { margin:0; font-size:20px; line-height:1.4; font-weight:500; }
          p { margin:8px 0 0; font-size:14px; line-height:1.5; color:var(--secondary-text-color); }
          .state { color:var(--primary-text-color); }
          button { font:inherit; color:var(--primary-text-color); }
          button { border:0; border-radius:var(--ha-border-radius,8px); min-height:44px;
            padding:8px 12px; background:transparent; color:var(--primary-color); cursor:pointer; }
          button:hover { background:var(--secondary-background-color); }
          button:disabled { color:var(--disabled-text-color); cursor:default; }
          button:focus-visible,summary:focus-visible {
            outline:2px solid var(--primary-color); outline-offset:2px; }
          ::selection { background:var(--primary-color); color:var(--text-primary-color,#fff); }
          .rates { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:20px 16px;
            margin:24px 0 0; font-variant-numeric:tabular-nums; }
          dt { font-size:14px; color:var(--secondary-text-color); line-height:1.5; }
          dd { margin:6px 0 0; font-size:26px; font-weight:500; line-height:1.2; }
          dd small { display:block; font-size:12px; margin-top:4px; font-weight:400; color:var(--secondary-text-color); }
          .facts { display:grid; grid-template-columns:1fr auto; gap:8px 16px; margin:20px 0;
            font-size:14px; font-variant-numeric:tabular-nums; }
          .facts dd { margin:0; font-size:14px; text-align:end; }
          .facts dt { color:var(--primary-text-color); }
          .actions { display:flex; justify-content:space-between; align-items:center; gap:12px;
            border-top:1px solid var(--divider-color); padding-top:12px; }
          .actions p { margin:0; font-size:12px; }
          details { margin-top:20px; border-top:1px solid var(--divider-color); padding-top:16px; }
          summary { cursor:pointer; min-height:36px; font-size:15px; line-height:1.5; }
          .rows { margin:0; padding:0; list-style:none; overflow-wrap:anywhere; }
          .rows>li { border-top:1px solid var(--divider-color); padding:12px 0; }
          .chart-choice { display:flex; align-items:center; gap:12px; min-height:44px; font-size:14px; margin-top:16px; cursor:pointer; }
          .chart-choice input { width:18px; height:18px; accent-color:var(--primary-color); }
          .chart-choice input:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }
          .metric-tools { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-top:12px; }
          .metric-tools .chart-choice { margin:0; }
          .rates { margin-top:12px; }
          .metric-chart svg { display:block; width:100%; height:auto; font-family:inherit; }
          .metric-chart { min-width:0; }
          #feeds-chart { grid-column:1/-1; min-width:0; margin:8px 0; }
          #feeds-chart svg { display:block; width:100%; height:auto; }
          #estimate-chart { width:88px; }
          #estimate-chart svg { display:block; width:100%; }
          .facts { align-items:center; }
          .fact-heading { margin:20px 0 0; }
          .fact-heading h3 { margin:0; font-size:15px; font-weight:500; }
          .section-summary { min-height:44px; }
          .section-summary .help { margin-inline-start:auto; }
          .rows small,.notice-items small { display:block; font-size:12px; color:var(--secondary-text-color); overflow-wrap:anywhere; }
          #version { font-size:12px; }
          .loona-notices ul { list-style:none; padding:0; margin:0; }
          .loona-notices li { padding:16px 0; border-top:1px solid var(--divider-color); }
          .loona-notices li:first-child { border-top:0; }
          .loona-notices h3 { margin:0; font-size:14px; line-height:1.5; }
          .loona-notices .notice-items { max-height:160px; overflow:auto; overflow-wrap:anywhere; font-size:12px; }
          #error { color:var(--error-color); overflow-wrap:anywhere; }
          [hidden] { display:none !important; }
          @media(max-width:480px) { ha-card { padding:16px; } .rates { gap:16px 10px; }
            dd { font-size:23px; } .actions { align-items:start; }
            .actions p { max-width:55%; } }
        </style>
        <ha-card>
          <header><div><h2 data-i18n="Loona statistics">Loona statistics</h2><p class="state" id="state" role="status" data-i18n="Loading statistics...">Loading statistics...</p></div>
            <button id="refresh" aria-label="Refresh Loona statistics" data-i18n="Refresh">Refresh</button></header>
          <p id="error" role="alert" hidden></p>
          <div id="content" hidden>
            <p id="version"></p><div id="notices"></div>
            <div class="metric-tools"><label class="chart-choice"><input id="show-charts" type="checkbox"><span data-i18n="Show statistics charts">Show statistics charts</span></label><span id="rates-help"></span></div>
            <dl class="rates">
              <div><dt class="metric-text" data-i18n="Sent">Sent</dt><dd class="metric-text"><span id="forwarded">0</span><small data-i18n="updates/s">updates/s</small></dd><div id="sent-chart" class="metric-chart" hidden></div></div>
              <div><dt class="metric-text" data-i18n="Filtered out">Filtered out</dt><dd class="metric-text"><span id="avoided">0</span><small data-i18n="updates/s">updates/s</small></dd><div id="filtered-chart" class="metric-chart" hidden></div></div>
              <div><dt class="metric-text" data-i18n="Updates filtered">Updates filtered</dt><dd class="metric-text"><span id="reduction">0</span>%<small data-i18n="of counted updates">of counted updates</small></dd><div id="reduction-chart" class="metric-chart" hidden></div></div>
            </dl>
            <div class="section-heading fact-heading"><h3 data-i18n="Totals and entity scope">Totals and entity scope</h3><span id="scope-help"></span></div>
            <dl class="facts">
              <dt data-i18n="Updates sent since reset">Updates sent since reset</dt><dd id="forwarded-total"></dd>
              <dt data-i18n="Updates filtered since reset">Updates filtered since reset</dt><dd id="avoided-total"></dd>
              <dt id="subscriptions-label" data-i18n="Filtered / tracked update feeds">Filtered / tracked update feeds</dt><dd id="subscriptions"></dd>
              <div id="feeds-chart" class="metric-chart" hidden></div>
              <dt data-i18n="Entities currently included">Entities currently included</dt><dd id="scope"></dd>
              <dt data-i18n="Estimated entity reduction">Estimated entity reduction</dt><dd><span id="estimate"></span><div id="estimate-chart" class="metric-chart" hidden></div></dd>
            </dl>
            <div class="actions"><p id="reset-time"></p><button id="reset" data-i18n="Reset live statistics">Reset live statistics</button></div>
            <details id="loads"><summary class="section-summary"><span data-i18n="Latest page loads">Latest page loads</span> <span id="load-count"></span><span id="loads-help"></span></summary>
              <ul id="load-rows" class="rows"></ul>
            </details>
            <details><summary class="section-summary"><span data-i18n="Performance diagnostics">Performance diagnostics</span><span id="performance-help"></span></summary>
              <ul id="performance-rows" class="rows"></ul>
              <p data-i18n="Busiest tracked entities since reset">Busiest tracked entities since reset</p>
              <ul id="noisy-rows" class="rows"></ul>
            </details>
          </div>
        </ha-card>`;
      this._get("rates-help").append(createHelp(this._hass,"Live updates","","interval"));
      this._get("scope-help").append(createHelp(this._hass,"Totals and entity scope","An update feed receives live entity changes; one tab can have more than one. The entity reduction estimate compares included entities with all current entities, even when filtering is off."));
      this._get("loads-help").append(createHelp(this._hass,"Latest page loads","Initial snapshots are filtered when startup dashboard detection succeeds. Startup fallback retains full data. File counts cover registered Lovelace files for the whole page session."));
      this._get("performance-help").append(createHelp(this._hass,"Performance diagnostics","Measurements belong to this browser and dashboard. Long frames show only part of CPU work; buffered entries precede the measurement window."));
      this._get("refresh").addEventListener("click", () => this._fetch());
      this._get("reset").addEventListener("click", () => this._reset());
      this._get("show-charts").addEventListener("change", () => {
        if (this._hass?.user?.is_admin) saveCardPreferences(this._hass, {charts:this._get("show-charts").checked});
      });
    }

    static getStubConfig() { return { type: "custom:loona-statistics-card" }; }
    setConfig(config) {
      if (config.title !== undefined && typeof config.title !== "string") throw new Error(text(this._hass, "Loona card title must be text"));
      if (config.show_charts !== undefined && typeof config.show_charts !== "boolean") throw new Error("show_charts must be a boolean");
      this._defaultCharts = config.show_charts === true;
      this._customTitle = config.title;
      this._localize();
    }
    _localize() {
      translate(this.shadowRoot, this._hass);
      this.shadowRoot.querySelector("h2").textContent = this._customTitle || text(this._hass, "Loona statistics");
      this._get("refresh").setAttribute("aria-label", text(this._hass, "Refresh"));
      if (this._data) this._render(this._data);
      if (this._errorKey) {
        this._get("error").textContent = text(this._hass, this._errorKey);
        if (!this._data) this._get("state").textContent = text(this._hass, "Unable to load statistics");
      }
      const metadata = window.customCards?.find(card => card.type === elementName);
      if (metadata) { metadata.name = text(this._hass, "Loona statistics"); metadata.description = text(this._hass, "Live filtering statistics and latest page loads"); }
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
      this._observer?.disconnect();
      this._sequence++;
      this._loading = false;
    }
    async _fetch() {
      if (!this.isConnected || !this._hass?.user?.is_admin || !this._hass.connection?.connected) return;
      const sequence = ++this._sequence;
      this._loading = true;
      this._lastRequest = Date.now();
      this._get("refresh").disabled = true;
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
        if (!this._data) this._get("state").textContent = text(this._hass, 'Unable to load statistics');
      } finally {
        if (sequence === this._sequence) {
          this._loading = false;
          this._get("refresh").disabled = false;
          if (!this._errorKey && this._data?.version===cardVersion && this._chartsEnabled() && !this._historyRequested) this._fetch();
        }
      }
    }
    async _reset() {
      if (!this._data?.reset_entity || this._resetting || !this._hass?.user?.is_admin) return;
      const account = this._hass.user.id;
      if (!await confirmAction(this, "Reset live statistics?",
          "Clear live counters, page-load records and browser measurements? Filtering settings and recorded history are preserved.", "Reset live statistics")) return;
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
      return typeof preference==="boolean" ? preference : this._defaultCharts===true;
    }
    _renderCharts(data) {
      const enabled=this._chartsEnabled();
      this._get("show-charts").checked=enabled;
      this.shadowRoot.querySelectorAll(".metric-text").forEach(root=>root.hidden=enabled);
      for (const id of ["subscriptions-label","subscriptions","estimate"]) this._get(id).hidden=enabled;
      this.shadowRoot.querySelectorAll(".metric-chart").forEach(root=>{ root.hidden=!enabled; if (!enabled) root.replaceChildren(); });
      if (!enabled) return;
      const metrics=data.metrics;
      const history=(data.rate_history || []).filter(row=>Number.isFinite(Date.parse(row.at)) && Number.isFinite(row.sent) && Number.isFinite(row.filtered));
      const max=Math.max(1,metrics.forwarded_rate,metrics.avoided_rate,...history.flatMap(row=>[row.sent,row.filtered]));
      rateChart(this._get("sent-chart"),this._hass,"Sent",metrics.forwarded_rate,history,"sent",max);
      rateChart(this._get("filtered-chart"),this._hass,"Filtered out",metrics.avoided_rate,history,"filtered",max);
      ringChart(this._get("reduction-chart"),this._hass,"Updates filtered",metrics.update_reduction,true,metrics.forwarded_rate+metrics.avoided_rate>0);
      ringChart(this._get("estimate-chart"),this._hass,"Estimated entity reduction",metrics.reduction_estimate,false,true);
      feedChart(this._get("feeds-chart"),this._hass,metrics.filtered_subscriptions,metrics.managed_subscriptions);
    }
    _render(data) {
      const metrics = data.metrics;
      renderVersion(this._get("version"), this._hass, data.version, cardVersion);
      renderNotices(this._get("notices"), this._hass, data.notices || [], data.notice_labels);
      this._renderCharts(data);
      const format = (value) => formatNumber(this._hass, value, { maximumFractionDigits: 1 });
      this._get("content").hidden = false;
      setText(this._get("state"), data.compatibility_problem ? text(this._hass, "A feature is unavailable. Check Loona diagnostics.")
        : !data.complete ? text(this._hass, "Dashboard scan incomplete. All entities are being sent.")
        : !data.controls.enabled || !data.controls.entity_filtering ? text(this._hass, "Entity filtering is disabled")
        : metrics.filtered_subscriptions ? text(this._hass, "Entity filtering is active") : text(this._hass, "No filtered update feed yet. Open a dashboard with a selected account."));
      for (const [id, key] of [["forwarded", "forwarded_rate"], ["avoided", "avoided_rate"], ["reduction", "update_reduction"],
        ["forwarded-total", "forwarded_updates"], ["avoided-total", "avoided_updates"]]) this._get(id).textContent = key.endsWith("_rate") ? formatNumber(this._hass, metrics[key], {minimumFractionDigits:1, maximumFractionDigits:1}) : format(metrics[key]);
      this._get("interval").textContent = (data.sample_seconds
        ? text(this._hass, "Measured over the last {seconds} seconds.", { seconds: format(data.sample_seconds) })
        : text(this._hass, "Rates update within {seconds} seconds.", { seconds: format(data.interval_seconds) }))
        + " " + text(this._hass, "Each update is counted once per update feed, so multiple tabs can increase totals. These numbers do not measure loading speed or network traffic.")
        + " " + text(this._hass,"Charts show up to 15 minutes of completed samples. Rate charts share the same scale and refresh with statistics.");
      this._get("subscriptions").textContent = format(metrics.filtered_subscriptions) + " / " + format(metrics.managed_subscriptions);
      this._get("scope").textContent = text(this._hass, metrics.current_scope === 1 ? "1 entity" : "{count} entities", { count: format(metrics.current_scope) });
      this._get("estimate").textContent = formatNumber(this._hass, metrics.reduction_estimate / 100, {style:"percent",maximumFractionDigits:1});
      this._get("reset-time").textContent = text(this._hass, "Since {time}", { time: formatDateTime(this._hass, data.reset_at) });
      this._get("reset").disabled = !data.reset_entity || this._resetting;
      this._get("load-count").textContent = "(" + data.page_loads.length + ")";
      this._get("load-rows").replaceChildren(...(data.page_loads.length ? data.page_loads.map(row => {
        const item = node("li"); item.append(node("strong", row.title));
        item.append(node("p", formatDateTime(this._hass, row.at)));
        item.append(node("p", text(this._hass, "Entities sent: {sent} / {available}", row.entities)));
        item.append(node("p", row.resources ? text(this._hass, "Card files sent: {sent} / {available}", row.resources) : text(this._hass, "No card file count was recorded for this load.")));
        return item;
      }) : [node("li", text(this._hass, "No page loads recorded yet. Reload one of your dashboards."))]));
      this._get("noisy-rows").replaceChildren(...(data.noisy_entities?.entities || []).map(row => {
        const item=node("li"); const label=row.label || this._hass?.states?.[row.entity_id]?.attributes?.friendly_name || row.entity_id;
        item.append(node("span",label)); if (label!==row.entity_id) item.append(node("small",row.entity_id));
        item.append(node("p",text(this._hass,"{count} sent updates",{count:format(row.updates)}))); return item;
      }));
      if (data.noisy_entities?.untracked_updates) this._get("noisy-rows").append(node("li",
        text(this._hass, "Tracking limit reached: {count} sent updates were not attributed.", {count:format(data.noisy_entities.untracked_updates)})));
      this._get("performance-rows").replaceChildren(...(data.browser_reports || []).map(row => {
        const item = node("li");
        item.append(node("strong", row.dashboard));
        item.append(node("p", formatDateTime(this._hass, row.at)));
        item.append(node("p", row.loaf_supported ? text(this._hass, "Long frames: {count}; blocking: {ms} ms", {count:format(row.frames), ms:format(row.blocking_ms)})
          : text(this._hass, "Long Animation Frames are unavailable in this browser.")));
        for (const script of row.scripts) {
          const label=data.resource_labels?.[script.source];
          if (label && label!==script.source) item.append(node("p",label));
          item.append(node("p", text(this._hass,
          "{source} ({phase}): {ms} ms; forced layout: {layout} ms", {source:script.source,
            phase:text(this._hass, script.phase === "buffered" ? "earlier buffered" : "measurement window"),
            ms:format(script.duration_ms), layout:format(script.forced_layout_ms)})));
        }
        for (const subscription of row.subscriptions) item.append(node("p", `${subscription.type}: ${format(subscription.count)}`));
        if (row.subscriptions.some(value => value.type === "subscribe_events/state_changed" || value.type === "subscribe_events/*")) {
          item.append(node("p", text(this._hass, "A raw event subscription can bypass entity filtering.")));
        }
        return item;
      }));
    }
  }

  customElements.define(elementName, LoonaStatisticsCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: elementName, name: text(app.hass, "Loona statistics"), description: text(app.hass, "Live filtering statistics and latest page loads"), preview: true });
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
