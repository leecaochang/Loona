/* Report dashboard context and recover when Core reconnects before Loona. */
import "./resource-loading.js?v=0.9.14";

if (!window.__loonaPanelContext) {
  window.__loonaPanelContext = true;
  const connections = new WeakMap();
  const retired = new WeakMap();
  const entityCallbacks = new WeakMap();
  const prototypes = new WeakSet();
  const subscriptionKinds = new WeakMap();
  const subscriptionCallbacks = new WeakMap();
  const dialogs = new Set();
  const pollMs = Number(new URL(import.meta.url).searchParams.get("poll"));
  let rootDashboard = null;

  function idleController(notify) {
    if (typeof window.setTimeout !== "function" || !document.addEventListener) return {policy() {},context:()=>false,stop() {}};
    let policy, context, active=false, listening=false, timer, last=Date.now();
    const types=["pointerdown","pointermove","keydown","scroll"];
    const clear=()=>{ window.clearTimeout(timer); timer=undefined; };
    const eligible=()=>policy?.enabled && context && !context.expanded && !document.hidden;
    const check=()=>{
      timer=undefined;
      if (!eligible()) return;
      const remaining=policy.after_ms-(Date.now()-last);
      if (remaining>0) timer=window.setTimeout(check,remaining);
      else { active=true; notify(); }
    };
    const wake=()=>{
      last=Date.now();
      const changed=active; active=false;
      if (!timer && eligible()) timer=window.setTimeout(check,policy.after_ms);
      if (changed) notify();
    };
    const visibility=()=>{ clear(); wake(); };
    const listen=value=>{
      if (value===listening) return;
      listening=value;
      for (const type of types) {
        if (value) document.addEventListener(type,wake,{capture:true,passive:true});
        else document.removeEventListener(type,wake,true);
      }
      if (value) document.addEventListener("visibilitychange",visibility);
      else document.removeEventListener("visibilitychange",visibility);
    };
    return {
      policy(value) {
        const valid=value?.version==="0.9.14" && typeof value.enabled==="boolean"
          && Number.isFinite(value.after_ms) && value.after_ms>0
          && Number.isInteger(value.refresh_seconds) && value.refresh_seconds>=0 && value.refresh_seconds<=60;
        const changed=JSON.stringify(policy)!==JSON.stringify(value);
        policy=valid ? value : undefined;
        if (changed) { clear(); listen(Boolean(policy?.enabled)); wake(); }
      },
      context(value) {
        const key=JSON.stringify([value.dashboard,value.view,value.expanded]);
        if (key!==context?.key) { context={...value,key};clear();last=Date.now();active=false; }
        if (eligible() && !active && !timer) timer=window.setTimeout(check,policy.after_ms);
        return active && eligible();
      },
      stop() { policy=undefined; clear(); listen(false); active=false; },
    };
  }

  function dashboard() {
    try {
      const path = decodeURIComponent(location.pathname.split("/")[1] || "");
      const app = document.querySelector("home-assistant");
      return path || (app && app.hass && app.hass.panelUrl) || rootDashboard;
    } catch { return null; }
  }

  function panelReport() {
    let view = null;
    try {
      const parts = location.pathname.split("/");
      if (parts.length === 3 && parts[2]) view = decodeURI(parts[2]);
      if (view?.length > 255) view = null;
    } catch { /* Unresolved routes retain dashboard delivery. */ }
    return {dashboard:dashboard(), view, live_dashboard:true,
      expanded:Boolean(dialogs.size || window.history?.state?.dialog
        || view === "hass-unused-entities"
        || /[?&]edit(?:=|&|$)/.test(location.search || ""))};
  }

  function attach(connection) {
    if (!connection || typeof connection.subscribeMessage !== "function"
        || typeof connection.sendMessagePromise !== "function") return Promise.resolve(false);
    const retry = retired.get(connection);
    if (retry) {
      if (retry.pending || retry.remaining <= 0 || !connection.connected) return Promise.resolve(false);
      retry.remaining--;
      retry.pending = true;
      // Probe through the native sender while unloaded; do not retain wrappers.
      return connection.sendMessagePromise({type:"loona/panel", dashboard:dashboard()}).catch(error => {
        if (error?.code === "not_subscribed") {
          retired.delete(connection);
          return attach(connection);
        }
        return false;
      }).finally(() => { retry.pending = false; });
    }
    if (connections.has(connection)) return connections.get(connection).ready || Promise.resolve(false);
    const state = { dashboard: undefined, subscribed: false, pending: false, disabled: false, socket: connection.socket, generation: 0 };
    connections.set(connection, state);
    state.resources = window.loonaCreateResourceLoader(window.__loonaBootstrap?.status === "waiting");
    state.idle = idleController(()=>report());
    const nativePromise = connection.sendMessagePromise;
    const nativeSubscribe = connection.subscribeMessage;
    let unsubscribe;
    function subscribe() {
      if (!connection.connected || state.pending || state.disabled) return;
      const generation = state.generation;
      state.pending = true;
      const current = panelReport();
      if (state.idle.context(current)) current.idle=true;
      state.dashboard = current.dashboard;
      state.context = JSON.stringify(current);
      // Own reconnect recovery so a startup unknown_command can be retried.
      state.ready = Promise.resolve(nativeSubscribe.call(connection, (value) => {
        if (value?.resources) state.resources.policy(value.resources);
        if (value?.idle) state.idle.policy(value.idle);
        if (value && value.enabled === false) disable();
        if (value && value.resubscribe && state.recoverySocket !== connection.socket
            && typeof connection.reconnect === "function") {
          state.recoverySocket = connection.socket;
          connection.reconnect();
        }
      }, { type: "loona/subscribe_panel", ...current }, { resubscribe: false }))
        .then((remove) => {
          if (generation !== state.generation) return false;
          unsubscribe = remove;
          state.subscribed = true;
          if (state.disabled) disable();
          return !state.disabled;
        }).catch(() => {
          if (generation === state.generation) { state.subscribed = false; state.dashboard = undefined; }
          return false;
        })
        .finally(() => { if (generation === state.generation) state.pending = false; });
    }
    function report() {
      state.resources.route();
      if (!connection.connected || state.disabled) { state.idle.stop();return; }
      if (state.socket !== connection.socket) {
        state.resources.flush();
        state.idle.stop();
        state.socket = connection.socket; state.generation++;
        state.subscribed = false; state.pending = false; unsubscribe = undefined;
        state.prefetch = undefined;
      }
      if (!state.subscribed) { subscribe(); return; }
      const current = panelReport();
      if (state.idle.context(current)) current.idle=true;
      const context = JSON.stringify(current);
      if (current.expanded) state.resources.flush();
      if (state.context === context) return;
      state.prefetch = undefined;
      state.dashboard = current.dashboard;
      state.context = context;
      nativePromise.call(connection, { type: "loona/panel", ...current })
        .catch((error) => {
          state.dashboard = state.context = undefined;
          if (error && (error.code === "unknown_command" || error.code === "not_subscribed")) {
            state.subscribed = false;
            if (unsubscribe) Promise.resolve(unsubscribe()).catch(() => {});
            unsubscribe = undefined;
          }
        });
    }
    state.report = report;
    state.prefetchDashboard = (path) => {
      if (!path || path === "lovelace" || state.disabled || state.prefetchStarted) return;
      state.prefetchStarted = true;
      const promise = nativePromise.call(connection, {type:"lovelace/config", url_path:path, force:false});
      state.prefetch = {dashboard:path, socket:connection.socket, promise};
      promise.catch(() => {});
      if (location.pathname !== "/" && !window.llResProm) {
        window.llResProm = connection.sendMessagePromise({type:"lovelace/resources"});
        window.llResProm.catch(() => {});
      }
    };
    connection.sendMessagePromise = function (message, ...args) {
      if (message.type !== "loona/panel") report();
      if (message.type === "lovelace/config" && message.force === true
          || message.type.startsWith("lovelace/config/")
          || /^lovelace\/resources\/(create|update|delete)$/.test(message.type)) state.resources.flush();
      const cached = state.prefetch;
      if (cached && message.type === "lovelace/config" && message.url_path === cached.dashboard
          && message.force !== false) state.prefetch = undefined;
      if (cached && cached.socket === connection.socket && cached.dashboard === dashboard()
          && message.type === "lovelace/config" && message.url_path === cached.dashboard
          && message.force === false) {
        state.prefetch = undefined;
        return cached.promise;
      }
      const result = nativePromise.call(this, message, ...args);
      return message.type === "lovelace/resources" ? result.then(rows => state.resources.select(rows)) : result;
    };
    const wrappedPromise = connection.sendMessagePromise;
    connection.subscribeMessage = function (callback, message, ...args) {
      if (message.type !== "loona/subscribe_panel") report();
      const explicit = "entity_ids" in message || ["include", "exclude"].some(key =>
        Object.values(message[key] || {}).some(value => Array.isArray(value) ? value.length > 0 : Boolean(value)));
      if (message.type === "subscribe_entities" && !explicit && typeof callback === "function") {
        const original = entityCallbacks.get(callback) || callback;
        let initial = true;
        const socket = connection.socket;
        callback = (event) => {
          if (socket !== connection.socket) return;
          if (initial && event && event.a) {
            initial = false;
            const app = document.querySelector("home-assistant");
            const cached = app && app.hass && app.hass.connection === connection && app.hass.states;
            // Stock collections merge snapshots across reconnects; retire stale cached IDs locally.
            const stale = cached ? Object.keys(cached).filter(id => !(id in event.a)) : [];
            if (stale.length) event = {...event, r:[...new Set([...(event.r || []), ...stale])]};
          }
          original(event);
        };
        entityCallbacks.set(callback, original);
      } else if (typeof callback === "function") {
        const original = subscriptionCallbacks.get(callback) || callback;
        callback = function (event) { return original.call(this, event); };
        subscriptionCallbacks.set(callback, original);
      }
      const result = nativeSubscribe.call(this, callback, message, ...args);
      Promise.resolve(result).then(() => {
        for (const info of connection.commands?.values?.() ?? []) {
          if (info.callback === callback) subscriptionKinds.set(info,
            message.type === "subscribe_events" ? `${message.type}/${message.event_type || "*"}` : message.type);
        }
      }).catch(() => {});
      return result;
    };
    const wrappedSubscribe = connection.subscribeMessage;
    const ready = () => report();
    if (typeof connection.addEventListener === "function") connection.addEventListener("ready", ready);
    function disable() {
      state.resources.stop();
      state.idle.stop();
      state.disabled = true;
      state.subscribed = false;
      if (connection.sendMessagePromise === wrappedPromise) connection.sendMessagePromise = nativePromise;
      if (connection.subscribeMessage === wrappedSubscribe) connection.subscribeMessage = nativeSubscribe;
      if (typeof connection.removeEventListener === "function") connection.removeEventListener("ready", ready);
      if (unsubscribe) { Promise.resolve(unsubscribe()).catch(() => {}); unsubscribe = undefined; }
      connections.delete(connection);
      retired.set(connection, {remaining:30, pending:false});
    }
    report();
    return state.ready || Promise.resolve(false);
  }

  window.loonaAttachBootstrapPanel = async (connection, routing) => {
    if (!connection) return false;
    if (location.pathname === "/") {
      if (!routing) return false;
      // Use the same native user/system/legacy preference order as the probed app.
      const requests = [{ type: "get_panels" }];
      if (routing.preferences) requests.push(
        { type: "frontend/get_user_data", key: "core" },
        { type: "frontend/get_system_data", key: "core" }
      );
      const [panels, user, system] = await Promise.all(requests.map(message => connection.sendMessagePromise(message)));
      const legacy = window.localStorage.getItem("defaultPanel");
      let target = user?.value?.default_panel || system?.value?.default_panel || (legacy ? JSON.parse(legacy) : null) || routing.default;
      if (typeof target !== "string" || !panels || typeof panels !== "object") return false;
      if (routing.default === "home" && target === "lovelace" && !panels.lovelace?.config) target = routing.default;
      rootDashboard = panels[target] ? target : panels[routing.default] ? routing.default : null;
    }
    if (window.__loonaBootstrap?.selected && !window.__loonaBootstrap.selected(dashboard())) return false;
    // Native commands share one ordered socket; queue context before preload.
    // The result acknowledgement is handled by attach without delaying Core.
    attach(connection);
    const state = connections.get(connection);
    if (state && !state.disabled) state.prefetchDashboard(dashboard());
    return Boolean(state && !state.disabled && (state.pending || state.subscribed));
  };
  window.loonaSubscriptionReport = (connection) => {
    const counts = new Map();
    for (const info of connection?.commands?.values?.() ?? []) {
      if (!("subscribe" in info)) continue;
      const reported = subscriptionKinds.get(info) || "unclassified";
      const kind = /^[a-zA-Z0-9_/*:.-]{1,80}$/.test(reported) ? reported : "unclassified";
      counts.set(kind, (counts.get(kind) || 0) + 1);
    }
    return [...counts].slice(0, 40).map(([type, count]) => ({type, count}));
  };
  window.loonaMeasurePerformance = async (hass) => {
    const moduleUrl = new URL("/loona/performance.js", location.href);
    moduleUrl.search = new URL(import.meta.url).search;
    const {measure} = await import(moduleUrl.href);
    return measure(hass, Number(moduleUrl.searchParams.get("measure")));
  };
  window.__loonaBootstrap?.resume?.();

  function update() {
    const app = document.querySelector("home-assistant");
    const constructor = (app && app.constructor) || customElements.get("home-assistant");
    const prototype = constructor && constructor.prototype;
    if (prototype && !prototypes.has(prototype) && typeof prototype.hassConnected === "function") {
      prototypes.add(prototype);
      const nativeConnected = prototype.hassConnected;
      prototype.hassConnected = function (...args) {
        attach(this.hass && this.hass.connection);
        return nativeConnected.apply(this, args);
      };
    }
    window.loonaProbeFrontend?.(app && app.hass);
    const connection = app && app.hass && app.hass.connection;
    attach(connection);
    const state = connections.get(connection);
    if (state) state.report();
  }

  window.addEventListener("location-changed", update, true);
  window.addEventListener("popstate", update, true);
  window.addEventListener("hass-more-info", event => {
    if (event.detail?.entityId) { dialogs.add("ha-more-info-dialog"); update(); }
  }, true);
  window.addEventListener("show-dialog", event => {
    const tag = event.detail?.dialogTag;
    if (typeof tag === "string" && tag.length <= 100) { dialogs.add(tag); update(); }
  }, true);
  window.addEventListener("dialog-closed", event => {
    if (dialogs.delete(event.detail?.dialog)) update();
  }, true);
  update();
  if (Number.isFinite(pollMs) && pollMs > 0) window.setInterval(update, pollMs);
}
