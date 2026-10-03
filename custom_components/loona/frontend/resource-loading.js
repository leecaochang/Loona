/* Keep native resource lists intact; delay only verified optional modules. */
if (!window.loonaCreateResourceLoader) {
  window.loonaCreateResourceLoader = (early = true) => {
    const native = {select: rows => rows, policy: () => {}, route: () => {}, flush: () => {}, stop: () => {}};
    if (!early || typeof document.createElement !== "function" || !document.head
        || typeof window.setTimeout !== "function" || typeof window.addEventListener !== "function") return native;
    let plan, timing, used = false, released = false, force = false, stopped = false;
    let deadline, quiet, idle, idleTimer = false, pumping = false, inFlight = 0;
    let path = location.pathname + (location.search || "");
    const pending = new Map(), started = new Set();
    const info = {status: "native", initial: 0, deferred: 0, loaded: 0, failed: 0};
    const publish = () => { window.__loonaResourceLoading = {...info, pending: pending.size}; };
    const clearIdle = () => {
      if (idle !== undefined) {
        if (idleTimer) window.clearTimeout(idle);
        else window.cancelIdleCallback?.(idle);
        idle = undefined;
      }
    };
    const clear = () => {
      window.clearTimeout(deadline); window.clearTimeout(quiet); clearIdle();
      deadline = quiet = undefined;
    };
    const cleanup = () => {
      clear(); window.removeEventListener("hass-panel-ready", ready, true);
    };
    const complete = () => {
      if (info.deferred && !pending.size && !inFlight) {
        info.status = info.failed ? "fallback" : "complete";
        if (info.completed_ms === undefined) info.completed_ms = window.performance.now();
        cleanup(); publish();
      }
    };
    function load(resource, retry = false) {
      // Module identity is its absolute URL, including the query string.
      const app = document.querySelector("home-assistant");
      const url = new URL(resource.url, app?.hass?.auth?.data?.hassUrl || location.href).href;
      if (!retry && started.has(url)) return Promise.resolve();
      started.add(url);
      inFlight++;
      return new Promise(resolve => {
        const element = document.createElement("script");
        element.type = "module"; element.src = url;
        let finished = false;
        const finish = failure => {
          if (finished) return;
          finished = true; window.clearTimeout(timer);
          element.onload = element.onerror = null;
          if (failure) {
            info.failed++; flush();
            // Try an error once more using the same module identity. A timeout
            // leaves the original request running without a duplicate insert.
            if (failure === "error" && !retry) load(resource, true).then(resolve);
            else resolve();
          } else { info.loaded++; resolve(); }
          publish();
        };
        const timer = window.setTimeout(() => finish("timeout"), timing.load_ms);
        element.onload = () => finish(null);
        element.onerror = () => finish("error");
        try { document.head.append(element); }
        catch { finish("error"); }
      }).finally(() => { inFlight--; complete(); });
    }
    function flush() {
      force = released = true; clear();
      const rows = [...pending.values()]; pending.clear();
      if (rows.length) {
        info.status = "loading"; pumping = true; publish();
        Promise.all(rows.map(row => load(row))).finally(() => { pumping = false; complete(); });
      } else complete();
    }
    function pump() {
      if (force || pumping || !pending.size) { complete(); return; }
      const schedule = () => {
        idle = undefined;
        if (force || stopped) return;
        const [key, row] = pending.entries().next().value || [];
        if (!row) { complete(); return; }
        pending.delete(key); pumping = true; info.status = "loading"; publish();
        load(row).finally(() => { pumping = false; if (force) complete(); else pump(); });
      };
      if (typeof window.requestIdleCallback === "function") {
        idleTimer = false; idle = window.requestIdleCallback(schedule, {timeout: plan.idle_ms});
      } else { idleTimer = true; idle = window.setTimeout(schedule, 0); }
    }
    function ready() {
      if (!pending.size || released || stopped) return;
      window.clearTimeout(quiet);
      quiet = window.setTimeout(() => { released = true; pump(); }, plan.quiet_ms);
    }
    function route() {
      const current = location.pathname + (location.search || "");
      if (current !== path) { path = current; flush(); }
    }
    return {
      policy(value) {
        const valid = value && Array.isArray(value.defer) && value.defer.every(url => typeof url === "string")
          && ["quiet_ms", "max_ms", "load_ms", "idle_ms"].every(key => Number.isFinite(value[key]) && value[key] > 0);
        if (!valid || !value.enabled) { if (pending.size) flush(); plan = undefined; return; }
        if (used && plan && JSON.stringify(value) !== JSON.stringify(plan)) flush();
        plan = timing = value;
      },
      select(rows) {
        if (used) return rows;
        used = true;
        if (!Array.isArray(rows) || !rows.every(row => row && typeof row.url === "string")) return rows;
        if (!plan || stopped || force) return rows;
        const delayed = new Set(plan.defer);
        const initial = rows.filter(row => {
          if (row.type !== "module" || !delayed.has(row.url)) return true;
          pending.set(row.url, row); return false;
        });
        info.initial = initial.length; info.deferred = pending.size;
        if (pending.size) {
          info.status = "waiting";
          window.addEventListener("hass-panel-ready", ready, true);
          deadline = window.setTimeout(flush, plan.max_ms);
        } else info.status = "native";
        publish(); return initial;
      },
      route, flush,
      stop() { stopped = true; flush(); cleanup(); },
    };
  };
}
