/* Keep Home Assistant's shared collections complete outside selected dashboards. */

if (!window.__loonaPanelContext) {
  window.__loonaPanelContext = true;
  const connections = new WeakMap();
  const prototypes = new WeakSet();
  const pollMs = Number(new URL(import.meta.url).searchParams.get("poll"));

  function dashboard() {
    try {
      const path = decodeURIComponent(location.pathname.split("/")[1] || "");
      return path || document.querySelector("home-assistant")?.hass?.panelUrl || null;
    } catch {
      return null;
    }
  }

  function attach(connection) {
    if (!connection || connections.has(connection)
        || typeof connection.subscribeMessage !== "function"
        || typeof connection.sendMessagePromise !== "function"
        || typeof connection.sendMessage !== "function") return;
    const state = { dashboard: undefined, subscribed: false };
    connections.set(connection, state);
    const nativeSend = connection.sendMessage;
    const nativePromise = connection.sendMessagePromise;
    const nativeSubscribe = connection.subscribeMessage;
    let unsubscribe;
    const report = () => {
      if (!connection.connected || !state.subscribed) return;
      const current = dashboard();
      if (state.dashboard === current) return;
      state.dashboard = current;
      connection.sendMessagePromise({ type: "loona/panel", dashboard: current })
        .catch((error) => {
          if (error?.code === "unknown_command" || error?.code === "not_subscribed") disable();
          else state.dashboard = undefined;
        });
    };
    state.report = report;
    // Resubscription uses the current route, including navigation while offline.
    connection.sendMessage = function (message, ...args) {
      if (message.type === "loona/subscribe_panel") {
        message = { ...message, dashboard: dashboard() };
        state.dashboard = message.dashboard;
        state.subscribed = true;
      }
      return nativeSend.call(this, message, ...args);
    };
    const wrappedSend = connection.sendMessage;
    // Report before the stock client allocates the next command ID.
    connection.sendMessagePromise = function (message, ...args) {
      if (message.type !== "loona/panel") report();
      return nativePromise.call(this, message, ...args);
    };
    const wrappedPromise = connection.sendMessagePromise;
    connection.subscribeMessage = function (callback, message, ...args) {
      if (message.type !== "loona/subscribe_panel") report();
      return nativeSubscribe.call(this, callback, message, ...args);
    };
    const wrappedSubscribe = connection.subscribeMessage;
    function disable() {
      state.subscribed = false;
      // Only restore wrappers installed by this module.
      if (connection.sendMessage === wrappedSend) connection.sendMessage = nativeSend;
      if (connection.sendMessagePromise === wrappedPromise) connection.sendMessagePromise = nativePromise;
      if (connection.subscribeMessage === wrappedSubscribe) connection.subscribeMessage = nativeSubscribe;
      if (unsubscribe) {
        Promise.resolve(unsubscribe()).catch(() => {});
        unsubscribe = undefined;
      }
    }
    Promise.resolve(connection.subscribeMessage((value) => {
      if (value?.enabled === false) disable();
    }, {
      type: "loona/subscribe_panel", dashboard: dashboard(),
    })).then((remove) => {
      unsubscribe = remove;
      if (!state.subscribed) disable();
    }).catch(disable);
  }

  function update() {
    const app = document.querySelector("home-assistant");
    // The extra module can precede native bootstrap and its registry replacement.
    const prototype = (app?.constructor || customElements.get("home-assistant"))?.prototype;
    if (prototype && !prototypes.has(prototype) && typeof prototype.hassConnected === "function") {
      prototypes.add(prototype);
      const nativeConnected = prototype.hassConnected;
      prototype.hassConnected = function (...args) {
        attach(this.hass?.connection);
        return nativeConnected.apply(this, args);
      };
    }
    const connection = app?.hass?.connection;
    attach(connection);
    connections.get(connection)?.report();
  }

  // Capture navigation before a newly mounted panel requests shared data.
  window.addEventListener("location-changed", update, true);
  window.addEventListener("popstate", update, true);
  update();
  // Also cover late bootstrap, replaced accounts, and connections in WebViews.
  if (Number.isFinite(pollMs) && pollMs > 0) window.setInterval(update, pollMs);
}
