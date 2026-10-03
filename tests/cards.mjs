// Exercise shipped cards against a real DOM, asynchronous replies and locale changes.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { build } from "esbuild";
import { Window } from "happy-dom";
const i18n = await import(`data:text/javascript;base64,${Buffer.from(readFileSync(new URL("../custom_components/loona/frontend/i18n.js",import.meta.url),"utf8")).toString("base64")}`);
const numericHass = {language:"de",locale:{number_format:"quote_decimal",time_format:"24",time_zone:"server"},config:{time_zone:"UTC"}};
assert.equal(i18n.formatNumber(numericHass,1234.5).replace("’", "'"),"1'234.5");
for(const [date_format,prefix] of [["DMY","2.10.2026"],["MDY","10.2.2026"],["YMD","2026.10.2"]]) {
  const formatted=i18n.formatDateTime({...numericHass,locale:{...numericHass.locale,date_format}},"2026-10-02T01:02:03Z");
  assert.ok(formatted.startsWith(prefix+", "),formatted);
  assert.ok(formatted.endsWith("01:02:03"),formatted);
}
const window = new Window({url:"http://ha.test/wall-panel/main"});
for (const key of ["document","customElements","HTMLElement","Element","Node","MutationObserver","CustomEvent","Event","location"]) globalThis[key]=window[key];
globalThis.window=window;
globalThis.IntersectionObserver=class { observe() {} disconnect() {} };
const app=document.createElement("home-assistant"); document.body.append(app);
let current={
  version:"0.9.7",revision:"a".repeat(64),choice_page:50,
  values:{controls:{enabled:true,entity_filtering:true,current_dashboard_updates:true},dashboards:{dashboards:["wall-panel"]},targets:{target_mode:"all",user_ids:[]},
    rules:{extra_entities:[],include_domains:[],include_globs:[],exclude_globs:[]},resources:{always_forward_resources:[]},cards:{dashboard_cards:[]}},
  choices:{dashboards:[{value:"wall-panel",label:"Wall"}],user_ids:[],extra_entities:[{value:"sensor.wall",label:"Wall"}],include_domains:[],include_globs:[],exclude_globs:[],always_forward_resources:[],dashboard_cards:[{value:"statistics",label:"statistics"}]},
  paged_choices:{extra_entities:true,include_globs:false,exclude_globs:false},required_resources:[],resources_editable:true,action_entities:{},notices:[],
};
const copy=value=>JSON.parse(JSON.stringify(value));
let conflict=false;
const requests=[];
const services=[];
const statistics={version:"0.9.7",controls:{enabled:true,entity_filtering:true},complete:true,metrics:{current_scope:1,filtered_subscriptions:1,managed_subscriptions:1,forwarded_rate:1,avoided_rate:2,update_reduction:3,forwarded_updates:4,avoided_updates:5,reduction_estimate:6},reset_at:"2026-10-02T01:00:00Z",page_loads:[],notices:[],interval_seconds:30};
const hass={user:{id:"admin",is_admin:true},language:"en",connection:Object.assign(new window.EventTarget(),{connected:true}),locale:{language:"en",number_format:"decimal_comma",time_format:"24",time_zone:"server"},config:{time_zone:"UTC"},
  async callWS(request) {
    requests.push(request);
    if(request.type==="loona/statistics") return copy(statistics);
    if(request.type==="loona/settings_choices") return {choices:[{value:"sensor.remote",label:"Remote"}],selected:[],more:false};
    if(request.type==="loona/save_settings") {
      if(conflict) throw {code:"conflict"};
      current.values[request.group]=copy(request.values); return copy(current);
    }
    return copy(current);
  },async callService(...args) { services.push(args); },
};
app.hass=hass;
for (const file of ["settings-card.js","statistics-card.js"]) {
  const source=(await build({entryPoints:[`custom_components/loona/frontend/${file}`],bundle:true,write:false,format:"esm"})).outputFiles[0].text;
  await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`);
}
const settings=document.createElement("loona-settings-card"); settings.setConfig({}); document.body.append(settings); settings.hass=hass;
const stats=document.createElement("loona-statistics-card"); stats.setConfig({}); document.body.append(stats); stats.hass=hass;
await new Promise(setImmediate);
assert.equal(stats.shadowRoot.getElementById("scope").textContent,"1 entity");
assert.equal(stats.shadowRoot.getElementById("forwarded").textContent,"1,0");
assert.ok(stats.shadowRoot.getElementById("reset-time").textContent.includes("01:00:00"));
// Charts are opt-in and share the existing data without additional requests.
assert.equal(stats.shadowRoot.getElementById("charts").children.length,0);
const beforeCharts=requests.length;
stats.shadowRoot.getElementById("show-charts").click();
assert.equal(stats.shadowRoot.querySelectorAll("#charts svg").length,2);
assert.equal(requests.length,beforeCharts);
assert.ok(stats.shadowRoot.querySelector('[data-chart="pie"]').getAttribute("stroke-dasharray").startsWith("3 "));
assert.equal(stats.shadowRoot.querySelector('[data-chart="percentage"]').textContent,"3%");
const pie=stats.shadowRoot.querySelector("#charts svg");
stats._render(copy(statistics));
assert.equal(stats.shadowRoot.querySelector("#charts svg"),pie,"Reuse SVG nodes during normal refresh");
stats._renderCharts({...statistics.metrics,forwarded_rate:0,avoided_rate:0});
assert.equal(stats.shadowRoot.querySelectorAll("#charts svg").length,0);
assert.ok(stats.shadowRoot.getElementById("charts").textContent.includes("No updates"));
stats.shadowRoot.getElementById("show-charts").click();
assert.equal(stats.shadowRoot.getElementById("charts").children.length,0);
// Disable Current tab updates immediately for an unsaved filtering change.
settings.shadowRoot.querySelector('[data-control="entity_filtering"]').click();
assert.ok(settings.shadowRoot.querySelector('[data-control="current_dashboard_updates"]').disabled);
assert.ok(settings._drafts.controls.current_dashboard_updates,"Preserve the opt-in while temporarily disabled");
settings.shadowRoot.querySelector('[data-cancel="controls"]').click();
assert.ok(!settings.shadowRoot.querySelector('[data-control="current_dashboard_updates"]').disabled);
// Non-contiguous words survive the browser's filtering of server results.
settings._data.choices.include_globs=[{value:"fan.bathroom_ceiling",label:"Bathroom ceiling fan"}];
settings._searches.include_globs="bathroom fan";
const matches=document.createElement("div"); settings._choices(matches,"rules","include_globs");
assert.ok(matches.textContent.includes("Bathroom ceiling fan"));
assert.equal(matches.querySelector("small").textContent,"fan.bathroom_ceiling");
// Reconnect checks the backend version while preserving an unsaved draft.
settings._edit("rules","extra_entities",["sensor.wall"]);
statistics.version="0.9.8";
hass.connection.dispatchEvent(new Event("ready")); await new Promise(setImmediate);
assert.ok(settings._drafts.rules);
assert.ok(settings.shadowRoot.getElementById("version").querySelector("button").disabled);
settings.shadowRoot.querySelector('[data-cancel="rules"]').click();
statistics.version="0.9.7";
// Loaded-module mismatch offers reload; settings drafts prevent accidental loss.
stats._render({...copy(statistics),version:"0.9.8"});
assert.ok(stats.shadowRoot.getElementById("version").textContent.includes("Reload dashboard"));
settings._data.version="0.9.8"; settings._render(); settings._edit("controls","enabled",false);
assert.ok(settings.shadowRoot.getElementById("version").querySelector("button").disabled);
settings.shadowRoot.querySelector('[data-cancel="controls"]').click();
assert.ok(!settings.shadowRoot.getElementById("version").querySelector("button").disabled);
settings._data.version="0.9.7"; settings._render(); stats._render(copy(statistics));
// Dismissals survive card reconstruction, stay account-local and change with items.
statistics.notices=[{code:"missing_entities",severity:"warning",items:["sensor.lost"]}];
statistics.notice_labels={"sensor.lost":"Missing sensor"};
await stats._fetch();
assert.equal(stats.shadowRoot.querySelector(".notice-items small").textContent,"sensor.lost");
stats.shadowRoot.querySelector('[data-dismiss="missing_entities"]').click();
assert.equal(stats.shadowRoot.querySelector('[data-notice="missing_entities"]'),null);
await stats._fetch();
assert.ok(stats.shadowRoot.querySelector("[data-restore-warnings]"));
const second=document.createElement("loona-statistics-card"); second.setConfig({}); document.body.append(second); second.hass=hass;
await new Promise(setImmediate);
assert.equal(second.shadowRoot.querySelector('[data-notice="missing_entities"]'),null);
second.hass={...hass,user:{id:"other-admin",is_admin:true}}; await new Promise(setImmediate);
assert.ok(second.shadowRoot.querySelector('[data-notice="missing_entities"]'));
second.remove();
statistics.notices[0].items.push("sensor.new_missing"); await stats._fetch();
assert.ok(stats.shadowRoot.querySelector('[data-notice="missing_entities"]'),"Changed warnings must reappear");
statistics.notices[0].items.pop(); await stats._fetch();
stats.shadowRoot.querySelector("[data-restore-warnings]").click();
assert.ok(stats.shadowRoot.querySelector('[data-notice="missing_entities"]'));
statistics.notices=[]; await stats._fetch();
let finishMeasurement;
window.loonaMeasurePerformance = () => new Promise(resolve => { finishMeasurement = resolve; });
const measurement = stats._measure();
await stats._fetch();
finishMeasurement();
await measurement;
assert.equal(stats.shadowRoot.getElementById("measure-status").textContent,"Measurement saved.","Normal polling must not discard a completed measurement");
const staleMeasurement = stats._measure();
stats.hass = {...hass,user:{id:"reader",is_admin:false}};
finishMeasurement();
await staleMeasurement;
assert.equal(stats.shadowRoot.getElementById("measure-status").textContent, "", "An account change clears measurement status");
stats.hass = hass;
await new Promise(setImmediate);
const state=settings.shadowRoot.getElementById("state");
let announcements=0;
const observer=new MutationObserver(rows=>announcements+=rows.length);
observer.observe(state,{childList:true,characterData:true,subtree:true});
settings._sync(); settings._sync(); await new Promise(setImmediate);
assert.equal(announcements,0,"Unchanged live-region messages must not be rewritten");
assert.ok(!settings.shadowRoot.querySelector("style").textContent.includes('content:"+"'));
// Saved and canceled edits work without structuredClone on legacy browsers.
globalThis.structuredClone=undefined;
settings.shadowRoot.querySelector('[data-control="enabled"]').click();
assert.equal(settings._drafts.controls.enabled,false);
assert.ok([...settings.shadowRoot.querySelectorAll("input,select")].filter(e=>e.dataset.control!=="enabled").every(e=>e.disabled));
assert.ok(!settings.shadowRoot.querySelector('[data-control="enabled"]').disabled);
settings.shadowRoot.querySelector('[data-cancel="controls"]').click();
assert.equal(settings._drafts.controls,undefined);
settings.shadowRoot.querySelector('[data-control="enabled"]').click(); await settings._save("controls");
assert.equal(current.values.controls.enabled,false);
// Keep both drafts after a conflict; refresh stays disabled until cancellation.
settings._edit("rules","extra_entities",["sensor.wall"]); settings._edit("dashboards","dashboards",[]);
assert.ok(settings.shadowRoot.querySelector('[data-save="rules"]').disabled);
conflict=true; await settings._save("rules");
assert.ok(settings._conflicts.has("rules") && settings._drafts.dashboards);
assert.ok(settings.shadowRoot.getElementById("refresh").disabled);
conflict=false;
// Server search and paging reach choices absent from the initial payload.
const search=settings.shadowRoot.querySelector('[data-field="extra_entities"]');
settings._searches.extra_entities="remote";
await settings._loadChoices(search.closest(".field").lastElementChild,"rules","extra_entities",false);
assert.ok(requests.some(row=>row.type==="loona/settings_choices" && row.query==="remote"));
assert.ok(settings._data.choices.extra_entities.some(row=>row.value==="sensor.remote"));
assert.ok(settings.shadowRoot.querySelector('[data-choice="sensor.remote"]').disabled,"Late search replies must respect Disabled");
stats.hass={...hass,language:"zh-Hans"};
assert.equal(stats.shadowRoot.getElementById("scope").textContent,"1 个实体");
stats.hass={...hass,language:"zh-Hant"};
assert.equal(stats.shadowRoot.querySelector("h2").textContent,"Loona statistics");
window.__loonaGraphCapability = { status:"unavailable", enabled:true };
window.dispatchEvent(new Event("loona-capabilities"));
assert.equal(settings.shadowRoot.getElementById("notices"),null,"Warnings live only on the statistics card");
assert.ok(stats.shadowRoot.getElementById("notices").textContent.includes("Loading optimizations are unavailable in this browser"));
window.__loonaGraphCapability.status = "available";
window.dispatchEvent(new Event("loona-capabilities"));
assert.ok(!stats.shadowRoot.getElementById("notices").textContent.includes("Loading optimizations are unavailable in this browser"));
// Confirmation gates do not mutate until accepted and retain drafts on cancel.
current.action_entities = {reset_live_statistics:"button.reset"};
settings._replace(copy(current));
statistics.reset_entity = "button.reset";
await stats._fetch();
for (const card of [settings, stats]) {
  const operation = card === settings ? card._press("reset_live_statistics") : card._reset();
  assert.equal(services.length, 0);
  assert.ok(card.shadowRoot.querySelector("dialog").open);
  card.shadowRoot.querySelector("[data-confirm-cancel]").click();
  await operation;
  assert.equal(services.length, 0);
  assert.equal(card.shadowRoot.querySelector("dialog"), null);
}
const reset = stats._reset();
stats.shadowRoot.querySelector("[data-confirm-accept]").click();
await reset;
assert.equal(services.length, 1);
settings._data.values.cards.dashboard_cards = ["statistics"];
settings._edit("cards", "dashboard_cards", []);
const beforeRemoval = requests.length;
let removal = settings._save("cards");
settings.shadowRoot.querySelector("[data-confirm-cancel]").click();
await removal;
assert.equal(requests.length, beforeRemoval);
assert.deepEqual(settings._drafts.cards.dashboard_cards, []);
removal = settings._save("cards");
settings.shadowRoot.querySelector("[data-confirm-accept]").click();
await removal;
assert.equal(requests.findLast(row=>row.type==="loona/save_settings").confirmed, true);
settings._edit("rules", "extra_entities", ["sensor.wall"]);
const beforeRestore = requests.length;
let restore = settings._restore();
settings.shadowRoot.querySelector("[data-confirm-cancel]").click();
await restore;
assert.equal(requests.length, beforeRestore);
assert.ok(settings._drafts.rules);
restore = settings._restore();
settings.shadowRoot.querySelector("[data-confirm-accept]").click();
await restore;
assert.equal(requests.findLast(row=>row.type==="loona/restore_defaults").confirmed, true);
assert.equal(Object.keys(settings._drafts).length, 0);
// Account changes cancel an outstanding approval before any request is sent.
const beforeAccount = requests.length;
restore = settings._restore();
settings.hass={...hass,user:{id:"reader",is_admin:false}};
await restore;
assert.equal(requests.length, beforeAccount);
assert.equal(settings.shadowRoot.querySelector("dialog"), null);
settings.hass=hass;
await new Promise(setImmediate);
stats.hass={...hass,user:{id:"reader",is_admin:false},language:"zh-Hans"};
settings.hass={...hass,user:{id:"reader",is_admin:false}};
assert.equal(stats.shadowRoot.getElementById("state").textContent,"请使用管理员账户登录以查看 Loona 统计。");
assert.equal(settings.shadowRoot.getElementById("sections").children.length,0);
assert.ok(stats.shadowRoot.getElementById("content").hidden);
observer.disconnect(); settings.remove(); stats.remove(); await window.happyDOM.abort();
console.log("Cards pass drafts, conflicts, server search, locales, permission changes and stable announcements");
