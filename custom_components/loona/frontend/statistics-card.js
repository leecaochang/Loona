/* Native-themed live filtering statistics. */
import { language, text, translate, renderNotices, setText, formatNumber, formatDateTime } from "./i18n.js?v=0.9.4";

const command = "loona/statistics";
const elementName = "loona-statistics-card";

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
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
      this._measureSequence = 0;
      this._visible = true;
      this._lastRequest = 0;
      this.shadowRoot.innerHTML = `
        <style>
          :host { display:block; color:var(--primary-text-color); }
          ha-card { padding:24px; overflow:hidden; }
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
            <dl class="rates">
              <div><dt data-i18n="Sent">Sent</dt><dd><span id="forwarded">0</span><small data-i18n="updates/s">updates/s</small></dd></div>
              <div><dt data-i18n="Filtered out">Filtered out</dt><dd><span id="avoided">0</span><small data-i18n="updates/s">updates/s</small></dd></div>
              <div><dt data-i18n="Updates filtered">Updates filtered</dt><dd><span id="reduction">0</span>%<small data-i18n="of counted updates">of counted updates</small></dd></div>
            </dl>
            <p id="interval"></p>
            <dl class="facts">
              <dt data-i18n="Updates sent since reset">Updates sent since reset</dt><dd id="forwarded-total"></dd>
              <dt data-i18n="Updates filtered since reset">Updates filtered since reset</dt><dd id="avoided-total"></dd>
              <dt data-i18n="Filtered / tracked update feeds">Filtered / tracked update feeds</dt><dd id="subscriptions"></dd>
              <dt data-i18n="Entities currently included">Entities currently included</dt><dd id="scope"></dd>
              <dt data-i18n="Estimated entity reduction">Estimated entity reduction</dt><dd id="estimate"></dd>
            </dl>
            <p data-i18n="An update feed receives live entity changes; one tab can have more than one. The entity reduction estimate compares included entities with all current entities, even when filtering is off.">An update feed receives live entity changes; one tab can have more than one. The entity reduction estimate compares included entities with all current entities, even when filtering is off.</p>
            <div class="actions"><p id="reset-time"></p><button id="reset" data-i18n="Reset live statistics">Reset live statistics</button></div>
            <details id="loads"><summary><span data-i18n="Latest page loads">Latest page loads</span> <span id="load-count"></span></summary>
              <p data-i18n="Initial snapshots are filtered when startup dashboard detection succeeds. Startup fallback retains full data. File counts cover registered Lovelace files for the whole page session.">Initial snapshots are filtered when startup dashboard detection succeeds. Startup fallback retains full data. File counts cover registered Lovelace files for the whole page session.</p>
              <ul id="load-rows" class="rows"></ul>
            </details>
            <details><summary data-i18n="Performance diagnostics">Performance diagnostics</summary>
              <p data-i18n="Measurements belong to this browser and dashboard. Long frames show only part of CPU work; buffered entries precede the measurement window.">Measurements belong to this browser and dashboard. Long frames show only part of CPU work; buffered entries precede the measurement window.</p>
              <button id="measure" data-i18n="Measure this dashboard for 30 seconds">Measure this dashboard for 30 seconds</button>
              <p id="measure-status" role="status"></p>
              <ul id="performance-rows" class="rows"></ul>
              <p data-i18n="Busiest tracked entities since reset">Busiest tracked entities since reset</p>
              <ul id="noisy-rows" class="rows"></ul>
            </details>
          </div>
        </ha-card>`;
      this._get("refresh").addEventListener("click", () => this._fetch());
      this._get("reset").addEventListener("click", () => this._reset());
      this._get("measure").addEventListener("click", () => this._measure());
    }

    static getStubConfig() { return { type: "custom:loona-statistics-card" }; }
    setConfig(config) {
      if (config.title !== undefined && typeof config.title !== "string") throw new Error(text(this._hass, "Loona card title must be text"));
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
        this._sequence++;
        this._measureSequence++;
        this._data = undefined;
        this._errorKey = undefined; this._get("error").hidden = true;
        this._loading = false;
        this._get("content").hidden = true;
        this._get("load-rows").replaceChildren();
        this._get("notices").replaceChildren();
        this._get("noisy-rows").replaceChildren();
        this._get("performance-rows").replaceChildren();
        this._get("measure-status").textContent = "";
        this._get("version").textContent = "";
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
      this._capabilityListener = () => { if (this._data) renderNotices(this._get("notices"), this._hass, this._data.notices || []); };
      window.addEventListener("loona-capabilities", this._capabilityListener);
      this._resetListener = () => this._fetch(); window.addEventListener("loona-statistics-reset", this._resetListener);
      if (this._hass) this._fetch();
    }
    disconnectedCallback() {
      window.removeEventListener("loona-capabilities", this._capabilityListener);
      window.removeEventListener("loona-statistics-reset", this._resetListener);
      window.clearInterval(this._timer);
      this._observer?.disconnect();
      this._sequence++;
      this._measureSequence++;
      this._loading = false;
    }
    async _fetch() {
      if (!this.isConnected || !this._hass?.user?.is_admin || !this._hass.connection?.connected) return;
      const sequence = ++this._sequence;
      this._loading = true;
      this._lastRequest = Date.now();
      this._get("refresh").disabled = true;
      try {
        const data = await this._hass.callWS({ type: command });
        if (sequence !== this._sequence || !this._hass?.user?.is_admin) return;
        this._data = data;
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
        }
      }
    }
    async _reset() {
      if (!this._data?.reset_entity || this._resetting) return;
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
    async _measure() {
      if (!this._hass?.user?.is_admin || this._measuring) return;
      this._measuring = true;
      const sequence = this._measureSequence;
      this._get("measure").disabled = true;
      this._get("measure-status").textContent = text(this._hass, "Measuring. Keep this dashboard open.");
      try {
        if (typeof window.loonaMeasurePerformance !== "function") throw new Error("Reporter unavailable");
        await window.loonaMeasurePerformance(this._hass);
        if (sequence !== this._measureSequence) return;
        this._get("measure-status").textContent = text(this._hass, "Measurement saved.");
        await this._fetch();
      } catch {
        if (sequence === this._measureSequence) this._get("measure-status").textContent = text(this._hass, "Measurement failed. Refresh and keep the dashboard open.");
      } finally {
        this._measuring = false;
        this._get("measure").disabled = false;
      }
    }
    _render(data) {
      const metrics = data.metrics;
      this._get("version").textContent = text(this._hass, "Version: {version}", {version:data.version});
      renderNotices(this._get("notices"), this._hass, data.notices || []);
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
        + " " + text(this._hass, "Each update is counted once per update feed, so multiple tabs can increase totals. These numbers do not measure loading speed or network traffic.");
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
      this._get("noisy-rows").replaceChildren(...(data.noisy_entities?.entities || []).map(row =>
        node("li", `${row.entity_id}: ${format(row.updates)}`)));
      if (data.noisy_entities?.untracked_updates) this._get("noisy-rows").append(node("li",
        text(this._hass, "Tracking limit reached: {count} sent updates were not attributed.", {count:format(data.noisy_entities.untracked_updates)})));
      this._get("performance-rows").replaceChildren(...(data.browser_reports || []).map(row => {
        const item = node("li");
        item.append(node("strong", row.dashboard));
        item.append(node("p", formatDateTime(this._hass, row.at)));
        item.append(node("p", row.loaf_supported ? text(this._hass, "Long frames: {count}; blocking: {ms} ms", {count:format(row.frames), ms:format(row.blocking_ms)})
          : text(this._hass, "Long Animation Frames are unavailable in this browser.")));
        for (const script of row.scripts) item.append(node("p", text(this._hass,
          "{source} ({phase}): {ms} ms; forced layout: {layout} ms", {source:script.source,
            phase:text(this._hass, script.phase === "buffered" ? "earlier buffered" : "measurement window"),
            ms:format(script.duration_ms), layout:format(script.forced_layout_ms)})));
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
