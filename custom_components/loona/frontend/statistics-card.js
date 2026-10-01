/* Optional native-themed statistics and administrator dependency preview. */
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
    window.setTimeout(install, 100);
    return;
  }
  if (customElements.get(elementName)) return;

  class LoonaStatisticsCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._search = "";
      this._status = "all";
      this._offset = 0;
      this._sequence = 0;
      this._visible = true;
      this._lastRequest = 0;
      this.shadowRoot.innerHTML = `
        <style>
          :host { display:block; color:var(--primary-text-color); }
          ha-card { padding:24px; overflow:hidden; }
          header { display:flex; justify-content:space-between; align-items:start; gap:16px; }
          h2 { margin:0; font-size:20px; line-height:1.4; font-weight:500; }
          p { margin:8px 0 0; font-size:14px; line-height:1.5; color:var(--secondary-text-color); }
          .state { color:var(--primary-text-color); }
          button,input,select { font:inherit; color:var(--primary-text-color); }
          button { border:0; border-radius:var(--ha-border-radius,8px); min-height:44px;
            padding:8px 12px; background:transparent; color:var(--primary-color); cursor:pointer; }
          button:hover { background:var(--secondary-background-color); }
          button:disabled { color:var(--disabled-text-color); cursor:default; }
          button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible {
            outline:2px solid var(--primary-color); outline-offset:2px; }
          ::selection { background:var(--primary-color); color:var(--text-primary-color,#fff); }
          .rates { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:20px 16px;
            margin:24px 0 0; font-variant-numeric:tabular-nums; }
          dt { font-size:14px; color:var(--secondary-text-color); line-height:1.5; }
          dd { margin:6px 0 0; font-size:26px; font-weight:500; line-height:1.2; }
          dd small { display:block; font-size:12px; margin-top:4px; font-weight:400; color:var(--secondary-text-color); }
          .facts { display:grid; grid-template-columns:1fr auto; gap:8px 16px; margin:20px 0;
            font-size:14px; font-variant-numeric:tabular-nums; }
          .facts dd { margin:0; font-size:14px; text-align:right; }
          .facts dt { color:var(--primary-text-color); }
          .actions { display:flex; justify-content:space-between; align-items:center; gap:12px;
            border-top:1px solid var(--divider-color); padding-top:12px; }
          .actions p { margin:0; font-size:12px; }
          details { margin-top:20px; border-top:1px solid var(--divider-color); padding-top:16px; }
          summary { cursor:pointer; min-height:36px; font-size:15px; line-height:1.5; }
          .tools { display:flex; gap:12px; margin:12px 0; }
          input,select { box-sizing:border-box; min-height:44px; border:1px solid var(--divider-color);
            border-radius:var(--ha-border-radius,8px); background:var(--card-background-color);
            padding:8px 12px; min-width:0; caret-color:var(--primary-color); }
          input { flex:1; width:100%; }
          input::placeholder { color:var(--secondary-text-color); }
          .rows { margin:0; padding:0; list-style:none; }
          .rows>li { border-top:1px solid var(--divider-color); padding:12px 0; }
          .rows details { border:0; margin:0; padding:0; }
          .rows summary { overflow-wrap:anywhere; font-size:14px; }
          .reason { margin:8px 0 0; padding-left:20px; font-size:13px; line-height:1.6; overflow-wrap:anywhere; }
          .tag { color:var(--secondary-text-color); font-size:12px; margin:4px 0 0; }
          .pagination { display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:13px; }
          #error { color:var(--error-color); overflow-wrap:anywhere; }
          [hidden] { display:none !important; }
          @media(max-width:480px) { ha-card { padding:16px; } .rates { gap:16px 10px; }
            dd { font-size:23px; } .tools { flex-direction:column; } .actions { align-items:start; }
            .actions p { max-width:55%; } }
        </style>
        <ha-card>
          <header><div><h2>Loona statistics</h2><p class="state" id="state" role="status">Loading statistics...</p></div>
            <button id="refresh" aria-label="Refresh Loona statistics">Refresh</button></header>
          <p id="error" role="alert" hidden></p>
          <div id="content" hidden>
            <dl class="rates">
              <div><dt>Forwarded</dt><dd><span id="forwarded">0</span><small>updates/s</small></dd></div>
              <div><dt>Avoided</dt><dd><span id="avoided">0</span><small>updates/s</small></dd></div>
              <div><dt>Live reduction</dt><dd><span id="reduction">0</span>%<small>eligible updates</small></dd></div>
            </dl>
            <p id="interval"></p>
            <dl class="facts">
              <dt>Updates forwarded since reset</dt><dd id="forwarded-total"></dd>
              <dt>Updates avoided since reset</dt><dd id="avoided-total"></dd>
              <dt>Filtered / managed subscriptions</dt><dd id="subscriptions"></dd>
              <dt>Current entity scope</dt><dd id="scope"></dd>
              <dt>Entity count reduction estimate</dt><dd id="estimate"></dd>
            </dl>
            <div class="actions"><p id="reset-time"></p><button id="reset">Reset live statistics</button></div>
            <details id="loads"><summary>Latest page loads <span id="load-count"></span></summary>
              <p>Latest full browser load for each dashboard. Entity snapshots use the selected dashboards' combined scope.
                Resource counts cover registered Lovelace resources, excluding core bundles and extra modules.</p>
              <ul id="load-rows" class="rows"></ul>
            </details>
            <details id="dependencies"><summary>Entity dependencies <span id="dependency-count"></span></summary>
              <p>Inspect retained, excluded and unresolved IDs. Exclusions can break cards. Details describe the configured scope;
                incomplete scans or disabled filtering pass through full data.</p>
              <div class="tools"><input id="search" type="search" maxlength="160" placeholder="Search entity IDs" aria-label="Search entity dependencies">
                <select id="filter" aria-label="Filter entity dependencies"><option value="all">All dependencies</option>
                  <option value="retained">Retained</option><option value="excluded">Excluded</option><option value="unresolved">Unresolved</option></select></div>
              <ul id="dependency-rows" class="rows"></ul>
              <div class="pagination"><button id="previous">Previous</button><span id="page"></span><button id="next">Next</button></div>
            </details>
          </div>
        </ha-card>`;
      this._get("refresh").addEventListener("click", () => this._fetch());
      this._get("reset").addEventListener("click", () => this._reset());
      this._get("search").addEventListener("input", (event) => {
        this._search = event.target.value;
        this._offset = 0;
        window.clearTimeout(this._debounce);
        this._debounce = window.setTimeout(() => this._fetch(), 250);
      });
      this._get("filter").addEventListener("change", (event) => {
        this._status = event.target.value;
        this._offset = 0;
        this._fetch();
      });
      this._get("previous").addEventListener("click", () => {
        this._offset = Math.max(0, this._offset - this._data.page_size); this._fetch();
      });
      this._get("next").addEventListener("click", () => {
        this._offset += this._data.page_size; this._fetch();
      });
    }

    static getStubConfig() { return { type: "custom:loona-statistics-card" }; }
    setConfig(config) {
      if (config.title !== undefined && typeof config.title !== "string") throw new Error("Loona card title must be text");
      this.shadowRoot.querySelector("h2").textContent = config.title || "Loona statistics";
    }
    getCardSize() { return 7; }
    getGridOptions() { return { columns: 12, min_columns: 6 }; }
    _get(id) { return this.shadowRoot.getElementById(id); }
    set hass(value) {
      const changedUser = this._hass?.user?.id !== value?.user?.id;
      this._hass = value;
      if (changedUser || !value?.user?.is_admin) {
        this._sequence++;
        this._data = undefined;
        this._loading = false;
        this._get("content").hidden = true;
        this._get("dependency-rows").replaceChildren();
        this._get("load-rows").replaceChildren();
        this._dependencySignature = undefined;
      }
      if (!value?.user?.is_admin) {
        this._get("content").hidden = true;
        this._get("state").textContent = "Administrator access is required for dependency details.";
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
      if (this._hass) this._fetch();
    }
    disconnectedCallback() {
      window.clearInterval(this._timer);
      window.clearTimeout(this._debounce);
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
        const data = await this._hass.callWS({ type: command, search: this._search, status: this._status, offset: this._offset });
        if (sequence !== this._sequence || !this._hass?.user?.is_admin) return;
        this._data = data;
        this._get("error").hidden = true;
        this._render(data);
      } catch (error) {
        if (sequence !== this._sequence) return;
        this._get("error").textContent = "Statistics unavailable. Check that Loona is loaded, then refresh. " + (error.message || "");
        this._get("error").hidden = false;
        if (!this._data) this._get("state").textContent = "Unable to load statistics";
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
        this._get("error").textContent = "Reset failed. Check the Reset live statistics button in Loona's settings.";
        this._get("error").hidden = false;
      } finally {
        this._resetting = false;
        this._get("reset").disabled = !this._data?.reset_entity;
      }
    }
    _render(data) {
      const metrics = data.metrics;
      const format = (value) => Number(value).toLocaleString(undefined, { maximumFractionDigits: 3 });
      this._get("content").hidden = false;
      this._get("state").textContent = data.compatibility_problem ? "Compatibility issue: " + data.compatibility_problem
        : !data.complete ? "Incomplete scope: filtering passes through full data"
        : !data.controls.enabled || !data.controls.entity_filtering ? "Entity filtering is disabled"
        : metrics.filtered_subscriptions ? "Entity filtering is active" : "Waiting for a filtered subscription";
      for (const [id, key] of [["forwarded", "forwarded_rate"], ["avoided", "avoided_rate"], ["reduction", "update_reduction"],
        ["forwarded-total", "forwarded_updates"], ["avoided-total", "avoided_updates"]]) this._get(id).textContent = format(metrics[key]);
      this._get("interval").textContent = (data.sample_seconds ? "Latest " + data.sample_seconds + "-second sample. "
        : "Waiting for the next rate sample, up to " + data.interval_seconds + " seconds. ")
        + "Counts are logical entity updates per selected-account subscription, not bytes or load-time savings.";
      this._get("subscriptions").textContent = format(metrics.filtered_subscriptions) + " / " + format(metrics.managed_subscriptions);
      this._get("scope").textContent = format(metrics.current_scope) + " entities";
      this._get("estimate").textContent = format(metrics.reduction_estimate) + "%";
      this._get("reset-time").textContent = "Since " + new Date(data.reset_at).toLocaleString();
      this._get("reset").disabled = !data.reset_entity || this._resetting;
      this._get("dependency-count").textContent = "(" + format(data.total) + ")";
      const signature = JSON.stringify(data.dependencies);
      if (signature !== this._dependencySignature) {
        this._dependencySignature = signature;
        const expanded = new Set([...this._get("dependency-rows").querySelectorAll("details[open]")].map(item => item.dataset.entity));
        const focused = this.shadowRoot.activeElement?.closest("details[data-entity]")?.dataset.entity;
        const rows = data.dependencies.map(row => {
        const item = node("li");
        const details = node("details"); details.dataset.entity = row.entity_id; details.open = expanded.has(row.entity_id);
        details.append(node("summary", row.entity_id));
        details.append(node("p", row.status + (row.unresolved ? "; unresolved: no registry entry or current state" : ""), "tag"));
        const reasons = node("ul", undefined, "reason"); row.reasons.forEach(reason => reasons.append(node("li", reason)));
        details.append(reasons); item.append(details); return item;
      });
        this._get("dependency-rows").replaceChildren(...(rows.length ? rows : [node("li", "No dependencies match this search.")]));
        if (focused) [...this._get("dependency-rows").querySelectorAll("details")].find(item => item.dataset.entity === focused)?.querySelector("summary").focus();
      }
      this._get("previous").disabled = this._offset === 0;
      this._get("next").disabled = this._offset + data.page_size >= data.total;
      this._get("page").textContent = data.total ? (data.offset + 1) + "-" + Math.min(data.total, data.offset + data.page_size) + " of " + data.total : "0 results";
      this._get("load-count").textContent = "(" + data.page_loads.length + ")";
      this._get("load-rows").replaceChildren(...(data.page_loads.length ? data.page_loads.map(row => {
        const item = node("li"); item.append(node("strong", row.title));
        item.append(node("p", new Date(row.at).toLocaleString()));
        item.append(node("p", "Entities sent: " + row.entities.sent + " / " + row.entities.available));
        item.append(node("p", row.resources ? "Resources sent: " + row.resources.sent + " / " + row.resources.available : "Resource filtering counts were not observed."));
        return item;
      }) : [node("li", "No page loads recorded yet. Reload a dashboard after installing this card.")]));
    }
  }

  customElements.define(elementName, LoonaStatisticsCard);
  window.customCards = window.customCards || [];
  window.customCards.push({ type: elementName, name: "Loona statistics", description: "Live filtering statistics and administrator dependency preview", preview: true });
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
