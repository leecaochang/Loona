/* Prefilled administrator settings using native Loona validation and storage. */
import { language, text, translate, renderVersion, saveCardPreferences, setText, confirmAction, cancelConfirmation } from "./i18n.js?v=0.9.7";

const groups = {
  controls: "Filters and performance", dashboards: "Dashboards", targets: "Accounts",
  rules: "Entity rules", resources: "Cards", cards: "Loona dashboard",
};
const cardVersion = "0.9.7";
const labels = {
  enabled: "Enabled", entity_filtering: "Entity filtering", registry_filtering: "Registry filtering",
  current_dashboard_updates: "Current tab updates",
  resource_filtering: "Resource filtering", visible_first_graphs: "Delay graph loading",
  delay_card_resources: "Delay card files",
  pause_animations_during_loading: "Pause animations during loading", dashboards: "Dashboards",
  user_ids: "Accounts", extra_entities: "Entities", include_domains: "Entity types",
  include_globs: "Entities or domain.*", exclude_globs: "Entities or domain.*",
  dashboard_cards: "Loona dashboard cards",
  always_forward_resources: "Additional files to load",
};
const help = {
  enabled: "Turn off to restore full entity and registry feeds. Reload to restore skipped card files.",
  entity_filtering: "Automatically find the entities used by your selected dashboards.",
  current_dashboard_updates: "Keep this tab and Entity rules live. Hidden tabs stay cached until opened. Dialogs and editing refresh all selected dashboards. Requires Entity filtering.",
  registry_filtering: "Keep registry rows related to the included entities and dashboard targets.",
  resource_filtering: "Skip known unused card bundles. Keep unknown and shared modules. Reload after changes.",
  delay_card_resources: "Load this dashboard's card files first, then the remaining modules. Navigation and editing load pending files immediately. Reload after enabling.",
  visible_first_graphs: "Delay off-screen graphs until the dashboard has loaded. Scrolling to a graph loads it immediately.",
  pause_animations_during_loading: "Pause repeating animations while loading, then resume them automatically.",
};
const groupHelp = {
  dashboards: "Choose which dashboards you want to filter.",
  targets: "Choose which accounts receive filtered data while viewing selected dashboards.",
  rules: "Loona finds dashboard entities automatically. Use these rules to add anything it missed or exclude entities you do not need.",
};
const statusLabels = { unused: "Not used in configured dashboards", unclassified: "Usage unknown" };
const make = (tag, content, cls) => {
  const element = document.createElement(tag);
  if (content !== undefined) element.textContent = content;
  if (cls) element.className = cls;
  return element;
};

function install() {
  const app = document.querySelector("home-assistant");
  if (!app?.hass) { window.setTimeout(install, 100); return; }
  if (customElements.get("loona-settings-card")) return;
  class LoonaSettingsCard extends HTMLElement {
    constructor() {
      super(); this.attachShadow({ mode: "open" });
      this._drafts = {}; this._conflicts = new Set(); this._searches = {}; this._limits = {};
      this._sequence = 0;
      this.shadowRoot.innerHTML = `
        <style>
          :host { user-select:text; -webkit-user-select:text; display:block; color:var(--primary-text-color); }
          ha-card { user-select:text; -webkit-user-select:text; padding:24px; overflow:hidden; }
          header { display:flex; align-items:start; justify-content:space-between; gap:16px; }
          header>div { flex:1; min-width:0; }
          header>button { flex-shrink:0; white-space:nowrap; }
          h2 { margin:0; font-size:20px; font-weight:500; line-height:1.4; }
          p { margin:8px 0 0; font-size:14px; line-height:1.5; color:var(--secondary-text-color); }
          button,input,select { font:inherit; }
          button { min-height:44px; padding:8px 12px; border:0; background:transparent;
            color:var(--primary-color); border-radius:var(--ha-border-radius,8px); cursor:pointer; }
          button:hover { background:var(--secondary-background-color); }
          button:disabled { color:var(--disabled-text-color); cursor:default; }
          input,select { color:var(--primary-text-color); accent-color:var(--primary-color); caret-color:var(--primary-color); }
          input[type=search],select { width:100%; box-sizing:border-box; min-height:44px; padding:8px 12px;
            border:1px solid var(--divider-color); background:var(--card-background-color); border-radius:var(--ha-border-radius,8px); }
          input::placeholder { color:var(--secondary-text-color); }
          input[type=checkbox] { width:18px; height:18px; flex-shrink:0; }
          button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible {
            outline:2px solid var(--primary-color); outline-offset:2px; }
          .required small { display:block; color:var(--secondary-text-color); }
          ::selection { background:var(--primary-color); color:var(--text-primary-color,#fff); }
          details { border-top:1px solid var(--divider-color); margin-top:20px; padding-top:16px; }
          summary { min-height:36px; cursor:pointer; font-size:15px; line-height:1.5; }
          #sections { margin-top:20px; }
          #sections>details { margin-top:0; padding-top:0; }
          #sections>details>summary { box-sizing:border-box; min-height:48px; padding:12px 0; font-weight:500; }
          #sections>details[open] { padding-bottom:20px; }
          .field { margin-top:16px; }
          .rule-groups { display:grid; gap:24px; margin-top:24px; }
          .rule-group { min-width:0; margin:0; padding:0 16px 16px; border:1px solid var(--divider-color); border-radius:12px; }
          .rule-group legend { padding:0 8px; font-size:18px; font-weight:600; }
          .rule-group legend ha-icon { margin-inline-end:8px; --mdc-icon-size:20px; }
          .rule-group>p { margin:4px 0 16px; }
          .rule-field { margin-top:12px; padding-top:12px; }
          .rule-field summary { display:flex; align-items:center; justify-content:space-between; gap:12px; list-style:revert; }
          .rule-field summary span { font-weight:500; }
          .rule-field summary small { margin-inline-start:auto; color:var(--secondary-text-color); font-variant-numeric:tabular-nums; }
          .rule-field .field { margin-top:8px; }
          .rule-field .field>label { font-size:0; }
          .rule-field input[type=search] { font-size:14px; }
          .selected-choices { background:var(--secondary-background-color); border-radius:8px; padding:0 10px; }
          .choice-list:empty { display:none; }
          #version { font-size:12px; }

          .field>label { display:block; font-size:14px; margin-bottom:8px; }
          .selection-title { font-size:13px; color:var(--secondary-text-color); margin:12px 0 4px; }
          .choice { display:flex; gap:12px; align-items:center; min-height:44px; font-size:14px; line-height:1.5;
            padding:4px 0; cursor:pointer; overflow-wrap:anywhere; }
          .choice span { min-width:0; }
          .choice small { display:block; color:var(--secondary-text-color); font-size:12px; }
          .choice-list { max-height:260px; overflow:auto; scrollbar-color:var(--divider-color) transparent; }
          .actions { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-top:16px; }
          .actions p { flex:1; margin:0; }
          .required { padding-inline-start:20px; font-size:13px; line-height:1.6; overflow-wrap:anywhere; }
          [role=alert] { color:var(--error-color); overflow-wrap:anywhere; }
          [hidden] { display:none !important; }
          @media(max-width:480px) { ha-card { padding:16px; } }
        </style>
        <ha-card><header><div><h2 data-i18n="Loona settings">Loona settings</h2>
          <p id="state" role="status" data-i18n="Loading settings...">Loading settings...</p></div>
          <button id="refresh" data-i18n="Refresh">Refresh</button></header>
          <p id="version"></p><p id="error" role="alert" hidden></p><div id="sections"></div>
          <div id="maintenance" hidden><div class="actions">
            <button data-action="rescan" data-i18n="Rescan dashboards">Rescan dashboards</button>
            <button data-action="reset_live_statistics" data-i18n="Reset live statistics">Reset live statistics</button>
            <button data-action="restore_defaults" data-i18n="Restore defaults">Restore defaults</button>
          </div><p data-i18n="Rescan checks dashboard changes now. Reset clears live counters and page-load records; entity counts and recorded history stay unchanged.">Rescan checks dashboard changes now. Reset clears live counters and page-load records; entity counts and recorded history stay unchanged.</p>
          <p data-i18n="Restore defaults clears all Loona settings and live statistics. Confirmation is required.">Restore defaults clears all Loona settings and live statistics. Confirmation is required.</p>
          <p id="action-status" role="status"></p></div></ha-card>`;
      this.shadowRoot.getElementById("refresh").addEventListener("click", () => this._fetch());
      this.shadowRoot.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => this._press(button.dataset.action)));
    }
    static getStubConfig() { return { type: "custom:loona-settings-card" }; }
    getCardSize() { return 6; }
    getGridOptions() { return { columns:12, min_columns:6 }; }
    setConfig(config) {
      if (config.title !== undefined && typeof config.title !== "string") throw new Error(text(this._hass, "Loona card title must be text"));
      this._customTitle = config.title; this._localize();
    }
    _t(key, values) { return text(this._hass, key, values); }
    _localize() {
      translate(this.shadowRoot, this._hass);
      this.shadowRoot.querySelector("h2").textContent = this._customTitle || this._t("Loona settings");
      if (this._data) this._render();
      this._sync();
      const metadata = window.customCards?.find(card => card.type === "loona-settings-card");
      if (metadata) { metadata.name = this._t("Loona settings"); metadata.description = this._t("Change filters, dashboards and accounts"); }
    }
    set hass(value) {
      const changedUser = this._hass?.user?.id !== value?.user?.id;
      const changedLanguage = language(this._hass) !== language(value);
      this._hass = value;
      this._watchConnection();
      if (changedUser || !value?.user?.is_admin) {
        cancelConfirmation(this);
        this._sequence++; this._data = undefined; this._drafts = {}; this._conflicts.clear();
        this._searches = {}; this._limits = {}; this._loading = false; this._saving = undefined; this._error = undefined; this._saved = undefined; this._rendered = false; this._acting = undefined; this._actionStatus = undefined;
        this.shadowRoot.getElementById("sections").replaceChildren();
        this.shadowRoot.getElementById("version").textContent = "";
        this.shadowRoot.getElementById("error").hidden = true;
      }
      if (changedLanguage) this._localize();
      this._sync();
      if (value?.user?.is_admin && !this._data && !this._loading) this._fetch();
    }
    connectedCallback() {
      this._watchConnection();
      if (this._hass) this._fetch();
    }
    disconnectedCallback() {
      cancelConfirmation(this);
      this._versionConnection?.removeEventListener?.("ready", this._versionListener);
      this._versionConnection = undefined;
      this._sequence++; this._loading = false; this._acting = undefined;
    }
    _watchConnection() {
      const connection = this.isConnected ? this._hass?.connection : undefined;
      if (connection === this._versionConnection) return;
      this._versionConnection?.removeEventListener?.("ready", this._versionListener);
      this._versionConnection = connection;
      this._versionListener = () => this._checkVersion();
      connection?.addEventListener?.("ready", this._versionListener);
    }
    async _checkVersion() {
      const data=this._data, hass=this._hass, account=hass?.user?.id;
      if (!data || !hass?.user?.is_admin || !hass.connection?.connected) return;
      try {
        const report=await hass.callWS({type:"loona/statistics"});
        if (!this.isConnected || this._data!==data || this._hass?.user?.id!==account || !this._hass.user.is_admin || this._hass.connection!==hass.connection) return;
        data.version=report.version;
        renderVersion(this.shadowRoot.getElementById("version"),this._hass,report.version,cardVersion);
        this._sync();
      } catch { /* Refresh can retry after a transient reconnect failure. */ }
    }
    _replace(data, savedGroup) {
      this._searches = {}; this._offsets = {}; this._choiceSequences = {};
      for (const group of Object.keys(this._drafts)) {
        if (group !== savedGroup && this._data && JSON.stringify(data.values[group]) !== JSON.stringify(this._data.values[group])) this._conflicts.add(group);
      }
      if (savedGroup) { delete this._drafts[savedGroup]; this._conflicts.delete(savedGroup); }
      this._data = data; this._render();
    }
    async _fetch() {
      if (!this.isConnected || !this._hass?.user?.is_admin || !this._hass.connection?.connected || Object.keys(this._drafts).length || this._saving || this._acting) return;
      const sequence = ++this._sequence; this._loading = true; this._sync();
      try {
        const data = await this._hass.callWS({ type:"loona/settings" });
        if (sequence !== this._sequence || !this._hass?.user?.is_admin) return;
        this._error = undefined; this._replace(data);
      } catch { if (sequence === this._sequence) this._error = "Could not load settings. Check that Loona is running, then press Refresh."; }
      finally { if (sequence === this._sequence) { this._loading = false; this._sync(); } }
    }
    _edit(group, key, value) {
      this._drafts[group] = { ...(this._drafts[group] || JSON.parse(JSON.stringify(this._data.values[group]))), [key]:value };
      if (JSON.stringify(this._drafts[group]) === JSON.stringify(this._data.values[group])) delete this._drafts[group];
      const count=this.shadowRoot.querySelector(`[data-rule-count="${key}"]`);
      if (count) count.textContent=this._t("{count} selected",{count:value.length});
      this._sync();
    }
    async _press(key) {
      if (key === "restore_defaults") { await this._restore(); return; }
      const entity = this._data?.action_entities?.[key];
      if (!entity || !this._hass?.user?.is_admin || this._acting || this._saving || this._loading) return;
      const account = this._hass.user.id;
      if (key === "reset_live_statistics" && !await confirmAction(this, "Reset live statistics?",
          "Clear live counters, page-load records and browser measurements? Filtering settings and recorded history are preserved.", "Reset live statistics")) return;
      if (this._hass?.user?.id !== account || !this._hass.user.is_admin || this._acting || this._saving || !this.isConnected) return;
      const sequence = ++this._sequence; this._acting = key; this._actionStatus = "Working..."; this._error = undefined; this._sync();
      try {
        await this._hass.callService("button", "press", { entity_id: entity });
        if (sequence === this._sequence) {
          this._actionStatus = key === "rescan" ? "Dashboards rescanned" : "Live statistics reset";
          const report = await this._hass.callWS({type:"loona/statistics"});
          if (sequence !== this._sequence || !this._hass?.user?.is_admin) return;
          this._data.notices = report.notices;
          window.dispatchEvent(new Event("loona-statistics-reset"));
        }
      } catch {
        if (sequence === this._sequence) { this._actionStatus = undefined; this._error = "Action failed. Check that Loona is running, then try again."; }
      } finally { if (sequence === this._sequence) { this._acting = undefined; this._sync(); } }
    }
    async _save(group) {
      if (!this._drafts[group] || this._saving || this._acting || this._conflicts.has(group) || !this._hass?.user?.is_admin) return;
      const revision = this._data.revision;
      const values = JSON.parse(JSON.stringify(this._drafts[group]));
      let confirmed = false;
      if (group === "cards" && this._data.values.cards.dashboard_cards.length && !values.dashboard_cards.length) {
        confirmed = await confirmAction(this, "Remove the Loona dashboard?",
          "Remove the generated Loona dashboard and its cards? Manually edited dashboards are preserved. You can create it again by selecting Loona dashboard cards.", "Remove dashboard");
        if (!confirmed || !this._hass?.user?.is_admin || !this.isConnected || revision !== this._data?.revision
            || JSON.stringify(values) !== JSON.stringify(this._drafts[group])) return;
      }
      const sequence = ++this._sequence; this._saving = group; this._error = undefined; this._sync();
      try {
        const data = await this._hass.callWS({type:"loona/save_settings", group, revision, values, confirmed});
        if (sequence !== this._sequence || !this._hass?.user?.is_admin) return;
        this._replace(data, group); this._saved = group;
      } catch (error) {
        if (sequence !== this._sequence) return;
        this._error = error.code === "conflict" ? "Settings changed elsewhere. Cancel your edits and refresh before saving."
          : ["invalid_selection","no_dashboards","no_accounts"].includes(error.code) ? "Some choices are no longer available. Cancel your edits and refresh the lists."
          : "Could not save. Your edits are still here. Cancel them and refresh to check the saved settings.";
        if (error.code === "conflict") this._conflicts.add(group);
      } finally { if (sequence === this._sequence) { this._saving = undefined; this._sync(); } }
    }
    async _restore() {
      if (!this._data || !this._hass?.user?.is_admin || this._acting || this._saving || this._loading) return;
      const revision = this._data.revision;
      const account = this._hass.user.id;
      if (!await confirmAction(this, "Restore defaults?",
          "Reset all Loona settings and live statistics, clear dashboard and account selections, and remove the generated Loona dashboard. Filtering stays inactive until you select dashboards and accounts again. Edited dashboards and recorded history are preserved.", "Restore defaults")) return;
      if (this._hass?.user?.id !== account || !this._hass.user.is_admin || !this.isConnected || revision !== this._data?.revision) return;
      const sequence = ++this._sequence; this._acting = "restore_defaults"; this._error = undefined; this._sync();
      try {
        const data = await this._hass.callWS({type:"loona/restore_defaults", revision, confirmed:true});
        if (sequence !== this._sequence || !this._hass?.user?.is_admin) return;
        this._drafts = {}; this._conflicts.clear(); this._saved = undefined; this._replace(data);
        saveCardPreferences(this._hass, {}, true);
        this._actionStatus = "Defaults restored. Select dashboards and accounts, then reload the browser.";
        window.dispatchEvent(new Event("loona-statistics-reset"));
      } catch (error) {
        if (sequence === this._sequence) this._error = error.code === "conflict"
          ? "Settings changed elsewhere. Cancel your edits and refresh before saving."
          : "Could not restore defaults. Refresh and check the current settings.";
      } finally { if (sequence === this._sequence) { this._acting = undefined; this._sync(); } }
    }
    _sync() {
      const admin = this._hass?.user?.is_admin;
      const refresh = this.shadowRoot.getElementById("refresh");
      refresh.disabled = !admin || this._loading || Boolean(this._saving) || Boolean(this._acting) || Object.keys(this._drafts).length > 0;
      refresh.title = Object.keys(this._drafts).length ? this._t("Refresh is unavailable while you have unsaved changes.") : "";
      setText(this.shadowRoot.getElementById("state"), !admin ? this._t("Sign in as an administrator to change Loona settings.")
        : this._data ? this._t((this._drafts.controls || this._data.values.controls).enabled
          ? "Entity and registry feeds follow the selected dashboard scope, including its dialogs."
          : "Enable Loona to change other settings.") : this._t("Loading settings..."));
      const error = this.shadowRoot.getElementById("error"); error.hidden = !this._error || !admin; error.textContent = this._error ? this._t(this._error) : "";
      const controls = this._drafts.controls || this._data?.values.controls;
      for (const element of this.shadowRoot.querySelectorAll("[data-save]")) element.disabled = !admin || element.dataset.save !== "controls" && !controls?.enabled || !this._drafts[element.dataset.save] || Boolean(this._saving) || Boolean(this._acting) || this._conflicts.has(element.dataset.save);
      for (const element of this.shadowRoot.querySelectorAll("[data-cancel]")) element.disabled = !this._drafts[element.dataset.cancel] || Boolean(this._saving) || Boolean(this._acting);
      for (const element of this.shadowRoot.querySelectorAll("[data-status]")) setText(element, this._conflicts.has(element.dataset.status)
        ? this._t("Settings changed elsewhere. Cancel your edits and refresh before saving.")
        : this._drafts[element.dataset.status] ? this._t("Unsaved changes") : this._saved === element.dataset.status ? this._t("Saved") : "");
      for (const element of this.shadowRoot.querySelectorAll("input,select")) element.disabled = !admin || Boolean(this._saving) || Boolean(this._acting)
        || element.dataset.control !== "enabled" && !controls?.enabled
        || element.dataset.control === "current_dashboard_updates" && !controls?.entity_filtering;
      const reload = this.shadowRoot.getElementById("version").querySelector("button");
      if (reload) reload.disabled = Object.keys(this._drafts).length > 0 || Boolean(this._saving) || Boolean(this._acting);
      this.shadowRoot.getElementById("maintenance").hidden = !admin || !this._data;
      setText(this.shadowRoot.getElementById("action-status"), this._actionStatus ? this._t(this._actionStatus) : "");
      for (const element of this.shadowRoot.querySelectorAll("[data-action]")) element.disabled = !admin || !this._data
        || element.dataset.action !== "restore_defaults" && !this._data.action_entities?.[element.dataset.action]
        || this._loading || Boolean(this._saving) || Boolean(this._acting);
    }
    _render() {
      renderVersion(this.shadowRoot.getElementById("version"), this._hass, this._data.version, cardVersion);
      const container = this.shadowRoot.getElementById("sections");
      const open = new Set([...container.querySelectorAll("details[data-group][open]")].map(e => e.dataset.group));
      const openFields = new Set([...container.querySelectorAll("details[data-rule-field][open]")].map(e => e.dataset.ruleField));
      const focused = this.shadowRoot.activeElement;
      const focusKey = focused?.dataset.field;
      container.replaceChildren();
      for (const [group,title] of Object.entries(groups)) {
        const section = make("details"); section.dataset.group = group; section.open = open.has(group) || group === "controls" && !this._rendered;
        section.append(make("summary", this._t(title)));
        if (groupHelp[group]) section.append(make("p", this._t(groupHelp[group])));
        const values = this._drafts[group] || this._data.values[group];
        if (group === "controls") {
          for (const [key,value] of Object.entries(values)) {
            const row = make("label",undefined,"choice"); const checkbox = make("input"); checkbox.type="checkbox"; checkbox.checked=value; checkbox.dataset.control=key;
            checkbox.addEventListener("change",()=>this._edit(group,key,checkbox.checked));
            const content = make("span",this._t(labels[key])); content.append(make("small",this._t(help[key])));
            row.append(checkbox,content); section.append(row);
          }
        } else {
          if (group === "targets") {
            const label = make("label",this._t("Apply filtering to")); const select = make("select"); select.setAttribute("aria-label",this._t("Apply filtering to")); select.dataset.field="target_mode";
            for (const [value,title] of [["selected","Selected accounts"],["all","All accounts"]]) { const option=make("option",this._t(title)); option.value=value; select.append(option); }
            select.value=values.target_mode; select.addEventListener("change",()=>{this._edit(group,"target_mode",select.value); this._render();});
            label.append(select); section.append(label);
          }
          if (group === "resources") {
            const required=make("details"); required.append(make("summary",this._t("Files kept automatically ({count})",{count:this._data.required_resources.length})),make("p",this._t("These files are needed by your dashboards or shared styling.")));
            const list=make("ul",undefined,"required"); this._data.required_resources.forEach(url=>{
              const item=make("li"); const label=this._data.resource_labels?.[url] || url;
              item.append(make("span",label)); if (label!==url) item.append(make("small",url)); list.append(item);
            }); required.append(list); section.append(required);
            section.append(make("p",this._t(this._data.resources_editable ? "Known unused bundles can be skipped for the whole page session. Unknown modules always load. Save, then reload." : "File choices are unavailable on this installation.")));
          }
          if (group === "rules") {
            const panels = make("div", undefined, "rule-groups");
            for (const [kind, title, description, keys, icon] of [
              ["included", "Included", "Add entities to the automatic dashboard list.", ["extra_entities", "include_domains", "include_globs"], "mdi:plus-circle-outline"],
              ["excluded", "Excluded", "Exclusions override inclusions and may leave cards without data. App status entities stay included.", ["exclude_globs"], "mdi:minus-circle-outline"],
            ]) {
              const panel = make("fieldset", undefined, "rule-group"); panel.dataset.ruleGroup=kind;
              const legend = make("legend"); const symbol=make("ha-icon"); symbol.setAttribute("icon",icon); symbol.setAttribute("aria-hidden","true");
              legend.append(symbol,make("span",this._t(title))); panel.append(legend,make("p",this._t(description)));
              for (const key of keys) {
                const field=make("details",undefined,"rule-field"); field.dataset.ruleField=key; field.open=openFields.has(key);
                const summary=make("summary"); const count=make("small",this._t("{count} selected",{count:values[key].length})); count.dataset.ruleCount=key;
                summary.append(make("span",this._t(labels[key])),count); field.append(summary);
                this._field(field,group,key); panel.append(field);
              }
              panels.append(panel);
            }
            section.append(panels);
          }
          for (const key of group === "rules" ? [] : Object.keys(values)) {
            if (key === "target_mode" || key === "user_ids" && values.target_mode === "all" || group === "resources" && !this._data.resources_editable) continue;
            this._field(section,group,key);
          }
        }
        const actions=make("div",undefined,"actions"); const status=make("p"); status.dataset.status=group; status.setAttribute("role","status");
        const cancel=make("button",this._t("Cancel")); cancel.dataset.cancel=group;
        cancel.addEventListener("click",()=>{delete this._drafts[group]; this._conflicts.delete(group); this._error=undefined; this._render();});
        const save=make("button",this._t("Save")); save.dataset.save=group; save.addEventListener("click",()=>this._save(group));
        actions.append(status,cancel,save); section.append(actions); container.append(section);
      }
      this._rendered=true;
      if (focusKey) [...container.querySelectorAll("input,select")].find(e=>e.dataset.field===focusKey)?.focus();
      this._sync();
    }
    _field(section,group,key) {
      const field=make("div",undefined,"field"); const label=make("label",this._t(labels[key]));
      const search=make("input"); search.type="search"; search.dataset.field=key; search.value=this._searches[key] || "";
      search.placeholder=this._t("Search available choices"); search.setAttribute("aria-label",this._t(labels[key])+": "+this._t("Search available choices"));
      label.append(search); const rows=make("div"); field.append(label,rows); section.append(field);
      const render=()=>this._choices(rows,group,key);
      search.addEventListener("input",()=>{
        this._searches[key]=search.value; this._limits[key]=this._data.choice_page;
        if (key in (this._data.paged_choices || {})) {
          this._choiceSequences = this._choiceSequences || {};
          this._choiceSequences[key] = (this._choiceSequences[key] || 0) + 1;
          window.clearTimeout(search._timer);
          search._timer = window.setTimeout(()=>this._loadChoices(rows,group,key,false),200);
        } else render();
      }); render();
    }
    async _loadChoices(root,group,key,append) {
      this._choiceSequences = this._choiceSequences || {};
      this._offsets = this._offsets || {};
      const sequence = this._choiceSequences[key] = (this._choiceSequences[key] || 0) + 1;
      const data = this._data;
      const query = this._searches[key] || "";
      const offset = append ? (this._offsets[key] || data.choice_page) : 0;
      try {
        const page = await this._hass.callWS({type:"loona/settings_choices",key,query,offset});
        if (data !== this._data || sequence !== this._choiceSequences[key] || !this._hass?.user?.is_admin || !root.isConnected) return;
        const selected = new Set((this._drafts[group] || data.values[group])[key]);
        const retained = data.choices[key].filter(row=>selected.has(row.value));
        const rows = append ? data.choices[key] : retained;
        data.choices[key] = [...new Map([...rows,...page.selected,...page.choices].map(row=>[row.value,row])).values()];
        data.paged_choices[key] = page.more; this._offsets[key] = offset + data.choice_page;
        this._limits[key] = this._offsets[key]; this._choices(root,group,key);
      } catch {
        if (data === this._data && sequence === this._choiceSequences[key]) {
          this._error = "Could not load settings. Check that Loona is running, then press Refresh."; this._sync();
        }
      }
    }
    _choices(root,group,key) {
      const values=(this._drafts[group] || this._data.values[group])[key]; const selected=new Set(values);
      const choices=this._data.choices[key] || [];
      const byValue=new Map(choices.map(row=>[row.value,row]));
      const query=(this._searches[key] || "").toLocaleLowerCase(language(this._hass));
      const words=query.split(/\s+/).filter(Boolean);
      const available=choices.filter(row=>!selected.has(row.value) && words.every(word=>(row.label+" "+row.value).toLocaleLowerCase(language(this._hass)).includes(word)));
      const limit=this._limits[key] || this._data.choice_page;
      const focused=this.shadowRoot.activeElement?.dataset.choice;
      root.replaceChildren();
      const chosenTitle=make("p",this._t("Selected ({count})",{count:values.length}),"selection-title"); root.append(chosenTitle);
      const renderRow=(row,checked)=>{
        const label=make("label",undefined,"choice"); const checkbox=make("input"); checkbox.type="checkbox"; checkbox.checked=checked; checkbox.dataset.choice=row.value;
        checkbox.addEventListener("change",()=>{
          const latest=(this._drafts[group] || this._data.values[group])[key];
          this._edit(group,key,checkbox.checked ? [...latest,row.value] : latest.filter(v=>v!==row.value));
          this._choices(root,group,key);
          [...root.querySelectorAll("input")].find(e=>e.dataset.choice===row.value)?.focus();
        });
        const labelText=key==="dashboard_cards" ? this._t("Loona "+row.value) : row.label;
        const content=make("span",labelText);
        if (key!=="dashboard_cards" && row.label!==row.value) content.append(make("small",row.value));
        if (row.unavailable) content.append(make("small",this._t("Unavailable")));
        else if (row.status) content.append(make("small",this._t(statusLabels[row.status] || "optional")));
        label.append(checkbox,content); return label;
      };
      const selectedRows=make("div",undefined,"choice-list selected-choices");
      values.slice(0,limit).forEach(value=>selectedRows.append(renderRow(byValue.get(value) || {value,label:value,unavailable:true},true)));
      if (!values.length) selectedRows.append(make("p",this._t("No selections"))); root.append(selectedRows);
      root.append(make("p",this._t("Available choices"),"selection-title"));
      const availableRows=make("div",undefined,"choice-list"); available.slice(0,limit).forEach(row=>availableRows.append(renderRow(row,false)));
      if (!available.length) availableRows.append(make("p",this._t("No matching choices"))); root.append(availableRows);
      if (available.length>limit || values.length>limit || this._data.paged_choices?.[key]) {
        const more=make("button",this._t("Show more")); more.addEventListener("click",()=>{
          if (this._data.paged_choices?.[key]) this._loadChoices(root,group,key,true);
          else { this._limits[key]=limit+this._data.choice_page; this._choices(root,group,key); }
        }); root.append(more);
      }
      this._sync();
      if (focused) [...root.querySelectorAll("input")].find(e=>e.dataset.choice===focused)?.focus();
    }
  }
  customElements.define("loona-settings-card",LoonaSettingsCard);
  window.customCards=window.customCards || [];
  window.customCards.push({type:"loona-settings-card",name:text(app.hass,"Loona settings"),description:text(app.hass,"Change filters, dashboards and accounts"),preview:true});
}
install();
