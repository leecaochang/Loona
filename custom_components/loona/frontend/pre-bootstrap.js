/* Parser-blocking hook, before Core registers its startup promise reactions. */
(() => {
  const config = /* LOONA_CONFIG */ {};
  function routeKey(path) {
    let value = 2166136261;
    for (const byte of new TextEncoder().encode(path)) value = Math.imul(value ^ byte, 16777619) >>> 0;
    return value.toString(16).padStart(8, "0");
  }
  const selected = path => config.routes == null || config.routes.includes(routeKey(path));
  let path;
  try { path = decodeURIComponent(location.pathname.split("/")[1] || ""); } catch { return; }
  if (!config.enabled || (path ? !selected(path) : !config.routing)) return;
  if (window.__loonaBootstrap || Object.getOwnPropertyDescriptor(window, "hassConnection")) return;
  const state = window.__loonaBootstrap = { status: "installed", routing: config.routing, selected };
  /* LOONA_REPORTER */
  let promise;
  Object.defineProperty(window, "hassConnection", {
    configurable: true,
    enumerable: true,
    get() { return promise; },
    set(nativePromise) {
      // Restore a plain property before invoking third-party code or native callbacks.
      promise = Promise.resolve(nativePromise).then(value => new Promise(resolve => {
        let finished = false;
        const finish = status => {
          if (finished) return;
          finished = true;
          window.clearTimeout(timer);
          state.status = status;
          delete state.resume;
          resolve(value);
        };
        const timer = window.setTimeout(() => finish("timeout"), config.timeout);
        state.status = "waiting";
        state.resume = () => {
          if (finished || state.started || typeof window.loonaAttachBootstrapPanel !== "function") return;
          state.started = true;
          Promise.resolve().then(() => window.loonaAttachBootstrapPanel(value?.conn, state.routing))
            .then(ready => finish(ready ? "ready" : "fallback"), () => finish("fallback"));
        };
        state.resume();
      }));
      Object.defineProperty(window, "hassConnection", { value: promise, writable: true, configurable: true, enumerable: true });
    }
  });
})();
