/* Report dashboard context and recover when Core reconnects before Loona. */

if (!window.__loonaPanelContext) {
  window.__loonaPanelContext = true;
  const connections = new WeakMap();
  const retired = new WeakMap();
  const entityCallbacks = new WeakMap();
  const prototypes = new WeakSet();
  const pollMs = Number(new URL(import.meta.url).searchParams.get("poll"));
  let rootDashboard = null;

  function dashboard() {
    try {
      const path = decodeURIComponent(location.pathname.split("/")[1] || "");
      const app = document.querySelector("home-assistant");
      return path || (app && app.hass && app.hass.panelUrl) || rootDashboard;
    } catch { return null; }
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
    const nativePromise = connection.sendMessagePromise;
    const nativeSubscribe = connection.subscribeMessage;
    let unsubscribe;
    function subscribe() {
      if (!connection.connected || state.pending || state.disabled) return;
      const generation = state.generation;
      state.pending = true;
      state.dashboard = dashboard();
      // Own reconnect recovery so a startup unknown_command can be retried.
      state.ready = Promise.resolve(nativeSubscribe.call(connection, (value) => {
        if (value && value.enabled === false) disable();
        if (value && value.resubscribe && state.recoverySocket !== connection.socket
            && typeof connection.reconnect === "function") {
          state.recoverySocket = connection.socket;
          connection.reconnect();
        }
      }, { type: "loona/subscribe_panel", dashboard: state.dashboard }, { resubscribe: false }))
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
      if (!connection.connected || state.disabled) return;
      if (state.socket !== connection.socket) {
        state.socket = connection.socket; state.generation++;
        state.subscribed = false; state.pending = false; unsubscribe = undefined;
      }
      if (!state.subscribed) { subscribe(); return; }
      const current = dashboard();
      if (state.dashboard === current) return;
      state.dashboard = current;
      nativePromise.call(connection, { type: "loona/panel", dashboard: current })
        .catch((error) => {
          state.dashboard = undefined;
          if (error && (error.code === "unknown_command" || error.code === "not_subscribed")) {
            state.subscribed = false;
            if (unsubscribe) Promise.resolve(unsubscribe()).catch(() => {});
            unsubscribe = undefined;
          }
        });
    }
    state.report = report;
    connection.sendMessagePromise = function (message, ...args) {
      if (message.type !== "loona/panel") report();
      return nativePromise.call(this, message, ...args);
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
      }
      return nativeSubscribe.call(this, callback, message, ...args);
    };
    const wrappedSubscribe = connection.subscribeMessage;
    const ready = () => report();
    if (typeof connection.addEventListener === "function") connection.addEventListener("ready", ready);
    function disable() {
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
    return Boolean(state && !state.disabled && (state.pending || state.subscribed));
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
  update();
  if (Number.isFinite(pollMs) && pollMs > 0) window.setInterval(update, pollMs);
}
