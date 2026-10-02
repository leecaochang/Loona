/* Prefilled administrator settings using native Loona validation and storage. */
import { language, text, translate } from "./i18n.js?v=0.8.2";

const groups = {
  controls: "Filters and performance", dashboards: "Dashboards", targets: "Accounts",
  extra_entities: "Extra entities", rules: "Advanced entity rules", resources: "Card files",
};
const labels = {
  enabled: "Enabled", entity_filtering: "Entity filtering", registry_filtering: "Registry filtering",
  resource_filtering: "Resource filtering", visible_first_graphs: "Visible-first graphs",
  pause_animations_during_loading: "Pause animations during loading", dashboards: "Dashboards",
  user_ids: "Accounts", extra_entities: "Extra entities", include_domains: "Include entity types",
  include_globs: "Include entities or patterns", exclude_globs: "Exclude entities or patterns",
  always_forward_resources: "Additional files to load",
};
const help = {
  enabled: "Master switch for all Loona filters and loading features.",
  entity_filtering: "Send only entities needed by your selected dashboards and rules.",
  registry_filtering: "Shorten entity and device lists. Turn off if an editor is missing choices.",
  resource_filtering: "Skip unchecked optional files. Review Card files, then reload the browser page.",
  visible_first_graphs: "Load on-screen graphs first. Scrolling to a waiting graph starts it immediately.",
  pause_animations_during_loading: "Pause repeating animations while loading, then resume them automatically.",
};
const groupHelp = {
  dashboards: "Every filtered account receives entities from all dashboards selected here.",
  targets: "Filtering affects every tab, device and app using these accounts, including administrators.",
  extra_entities: "Add entities a card needs but Loona did not find, or entities needed on other pages using these accounts.",
  rules: "Choose entity types such as light, entities, or patterns such as sensor.*. Exclusions override inclusions and can leave cards without data.",
};
const statusLabels = { unused: "Not used in selected dashboards", unclassified: "Usage unknown" };
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
          :host { display:block; color:var(--primary-text-color); }
          ha-card { padding:24px; overflow:hidden; }
          header { display:flex; align-items:start; justify-content:space-between; gap:16px; }
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
          ::selection { background:var(--primary-color); color:var(--text-primary-color,#fff); }
          details { border-top:1px solid var(--divider-color); margin-top:20px; padding-top:16px; }
          summary { min-height:36px; cursor:pointer; font-size:15px; line-height:1.5; }
          .field { margin-top:16px; }
          .field>label { display:block; font-size:14px; margin-bottom:8px; }
          .selection-title { font-size:13px; color:var(--secondary-text-color); margin:12px 0 4px; }
          .choice { display:flex; gap:12px; align-items:center; min-height:44px; font-size:14px; line-height:1.5;
            padding:4px 0; cursor:pointer; overflow-wrap:anywhere; }
          .choice span { min-width:0; }
          .choice small { display:block; color:var(--secondary-text-color); font-size:12px; }
          .choice-list { max-height:260px; overflow:auto; scrollbar-color:var(--divider-color) transparent; }
          .actions { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-top:16px; }
          .actions p { flex:1; margin:0; }
          .required { padding-left:20px; font-size:13px; line-height:1.6; overflow-wrap:anywhere; }
          [role=alert] { color:var(--error-color); overflow-wrap:anywhere; }
          [hidden] { display:none !important; }
          @media(max-width:480px) { ha-card { padding:16px; } }
        </style>
        <ha-card><header><div><h2 data-i18n="Loona settings">Loona settings</h2>
          <p id="state" role="status" data-i18n="Loading settings...">Loading settings...</p></div>
          <button id="refresh" data-i18n="Refresh">Refresh</button></header>
          <p id="error" role="alert" hidden></p><div id="sections"></div>
          <div id="maintenance" hidden><div class="actions">
            <button data-action="rescan" data-i18n="Rescan dashboards">Rescan dashboards</button>
            <button data-action="reset_live_statistics" data-i18n="Reset live statistics">Reset live statistics</button>
          </div><p data-i18n="Rescan checks dashboard changes now. Reset clears live counters and page-load records; entity counts and recorded history stay unchanged.">Rescan checks dashboard changes now. Reset clears live counters and page-load records; entity counts and recorded history stay unchanged.</p>
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
      if (changedUser || !value?.user?.is_admin) {
        this._sequence++; this._data = undefined; this._drafts = {}; this._conflicts.clear();
        this._searches = {}; this._limits = {}; this._loading = false; this._saving = undefined; this._error = undefined; this._saved = undefined; this._rendered = false; this._acting = undefined; this._actionStatus = undefined;
        this.shadowRoot.getElementById("sections").replaceChildren();
        this.shadowRoot.getElementById("error").hidden = true;
      }
      if (changedLanguage) this._localize();
      this._sync();
      if (value?.user?.is_admin && !this._data && !this._loading) this._fetch();
    }
    connectedCallback() { if (this._hass) this._fetch(); }
    disconnectedCallback() { this._sequence++; this._loading = false; this._acting = undefined; }
    _replace(data, savedGroup) {
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
      this._drafts[group] = { ...(this._drafts[group] || structuredClone(this._data.values[group])), [key]:value };
      if (JSON.stringify(this._drafts[group]) === JSON.stringify(this._data.values[group])) delete this._drafts[group];
      this._sync();
    }
    async _press(key) {
      const entity = this._data?.action_entities?.[key];
      if (!entity || !this._hass?.user?.is_admin || this._acting || this._saving || this._loading) return;
      const sequence = ++this._sequence; this._acting = key; this._actionStatus = "Working..."; this._error = undefined; this._sync();
      try {
        await this._hass.callService("button", "press", { entity_id: entity });
        if (sequence === this._sequence) {
          this._actionStatus = key === "rescan" ? "Dashboards rescanned" : "Live statistics reset";
          if (key === "reset_live_statistics") window.dispatchEvent(new Event("loona-statistics-reset"));
        }
      } catch {
        if (sequence === this._sequence) { this._actionStatus = undefined; this._error = "Action failed. Check that Loona is running, then try again."; }
      } finally { if (sequence === this._sequence) { this._acting = undefined; this._sync(); } }
    }
    async _save(group) {
      if (!this._drafts[group] || this._saving || this._acting || this._conflicts.has(group) || !this._hass?.user?.is_admin) return;
      const sequence = ++this._sequence; this._saving = group; this._error = undefined; this._sync();
      try {
        const data = await this._hass.callWS({type:"loona/save_settings", group, revision:this._data.revision, values:structuredClone(this._drafts[group])});
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
    _sync() {
      const admin = this._hass?.user?.is_admin;
      const refresh = this.shadowRoot.getElementById("refresh");
      refresh.disabled = !admin || this._loading || Boolean(this._saving) || Boolean(this._acting) || Object.keys(this._drafts).length > 0;
      refresh.title = Object.keys(this._drafts).length ? this._t("Refresh is unavailable while you have unsaved changes.") : "";
      this.shadowRoot.getElementById("state").textContent = !admin ? this._t("Sign in as an administrator to change Loona settings.")
        : this._data ? this._t("Changes affect every tab, device and app using the selected accounts.") : this._t("Loading settings...");
      const error = this.shadowRoot.getElementById("error"); error.hidden = !this._error || !admin; error.textContent = this._error ? this._t(this._error) : "";
      for (const element of this.shadowRoot.querySelectorAll("[data-save]")) element.disabled = !this._drafts[element.dataset.save] || Boolean(this._saving) || Boolean(this._acting) || this._conflicts.has(element.dataset.save);
      for (const element of this.shadowRoot.querySelectorAll("[data-cancel]")) element.disabled = !this._drafts[element.dataset.cancel] || Boolean(this._saving) || Boolean(this._acting);
      for (const element of this.shadowRoot.querySelectorAll("[data-status]")) element.textContent = this._conflicts.has(element.dataset.status)
        ? this._t("Settings changed elsewhere. Cancel your edits and refresh before saving.")
        : this._drafts[element.dataset.status] ? this._t("Unsaved changes") : this._saved === element.dataset.status ? this._t("Saved") : "";
      for (const element of this.shadowRoot.querySelectorAll("input,select")) element.disabled = Boolean(this._saving) || Boolean(this._acting);
      this.shadowRoot.getElementById("maintenance").hidden = !admin || !this._data;
      this.shadowRoot.getElementById("action-status").textContent = this._actionStatus ? this._t(this._actionStatus) : "";
      for (const element of this.shadowRoot.querySelectorAll("[data-action]")) element.disabled = !admin || !this._data?.action_entities?.[element.dataset.action] || this._loading || Boolean(this._saving) || Boolean(this._acting);
    }
    _render() {
      const container = this.shadowRoot.getElementById("sections");
      const open = new Set([...container.querySelectorAll("details[data-group][open]")].map(e => e.dataset.group));
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
            const list=make("ul",undefined,"required"); this._data.required_resources.forEach(url=>list.append(make("li",url))); required.append(list); section.append(required);
            section.append(make("p",this._t(this._data.resources_editable ? "Checked files load; unchecked files are skipped when Resource filtering is on. Save, then reload the browser page." : "File choices are unavailable on this installation.")));
          }
          for (const key of Object.keys(values)) {
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
      search.addEventListener("input",()=>{this._searches[key]=search.value; this._limits[key]=this._data.choice_page; render();}); render();
    }
    _choices(root,group,key) {
      const values=(this._drafts[group] || this._data.values[group])[key]; const selected=new Set(values);
      const choices=this._data.choices[key] || [];
      const byValue=new Map(choices.map(row=>[row.value,row]));
      const query=(this._searches[key] || "").toLocaleLowerCase(language(this._hass));
      const available=choices.filter(row=>!selected.has(row.value) && (row.label+" "+row.value).toLocaleLowerCase(language(this._hass)).includes(query));
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
        const content=make("span",row.label);
        if (row.label!==row.value) content.append(make("small",row.value));
        if (row.unavailable) content.append(make("small",this._t("Unavailable")));
        else if (row.status) content.append(make("small",this._t(statusLabels[row.status] || "optional")));
        label.append(checkbox,content); return label;
      };
      const selectedRows=make("div",undefined,"choice-list");
      values.slice(0,limit).forEach(value=>selectedRows.append(renderRow(byValue.get(value) || {value,label:value,unavailable:true},true)));
      if (!values.length) selectedRows.append(make("p",this._t("No selections"))); root.append(selectedRows);
      root.append(make("p",this._t("Available choices"),"selection-title"));
      const availableRows=make("div",undefined,"choice-list"); available.slice(0,limit).forEach(row=>availableRows.append(renderRow(row,false)));
      if (!available.length) availableRows.append(make("p",this._t("No matching choices"))); root.append(availableRows);
      if (available.length>limit || values.length>limit) { const more=make("button",this._t("Show more")); more.addEventListener("click",()=>{this._limits[key]=limit+this._data.choice_page; this._choices(root,group,key);}); root.append(more); }
      if (focused) [...root.querySelectorAll("input")].find(e=>e.dataset.choice===focused)?.focus();
    }
  }
  customElements.define("loona-settings-card",LoonaSettingsCard);
  window.customCards=window.customCards || [];
  window.customCards.push({type:"loona-settings-card",name:text(app.hass,"Loona settings"),description:text(app.hass,"Change filters, dashboards and accounts"),preview:true});
}
install();
