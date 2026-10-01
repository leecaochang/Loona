import { StartupMotion } from "./startup-motion.js?v=0.6.3";

// Optional graph scheduling for the tested native Home Assistant card container.
// Dashboard configuration and loaded card elements remain native.
if (!window[Symbol.for("loona.graph-loading")]) {
  window[Symbol.for("loona.graph-loading")] = true;
  const moduleVersion = "0.6.3";
  const motion = new StartupMotion(moduleVersion);
  const connectedCards = new Set();
  const records = new WeakMap();
  const policies = new WeakMap();
  const subscriptions = new WeakSet();
  const events = [];
  const started = performance.now();
  let sequence = 0;
  let nativeLoad;
  let lastPolicy;
  let construction;
  const lifecycleRoots = new Set();
  const lifecycleObserver = new MutationObserver(() => {
    for (const card of connectedCards) {
      if (!card._owner.isConnected || (card._card && card._owner._element !== card._card)) {
        card.release();
      }
    }
  });

  function watchLifecycle(owner) {
    let node = owner;
    while (node) {
      const root = node.getRootNode();
      if (!lifecycleRoots.has(root)) {
        lifecycleRoots.add(root);
        lifecycleObserver.observe(root, { childList: true, subtree: true });
      }
      node = root.host;
    }
  }

  function valid(policy) {
    return policy?.version === moduleVersion && typeof policy.enabled === "boolean"
      && Array.isArray(policy.dashboards) && policy.dashboards.every((key) => typeof key === "string")
      && Number.isFinite(policy.quiet_ms) && policy.quiet_ms > 0
      && Number.isFinite(policy.poll_ms) && policy.poll_ms > 0
      && Number.isInteger(policy.trace_limit) && policy.trace_limit > 0
      && policy.profiles && typeof policy.profiles === "object";
  }

  function timing() {
    return lastPolicy;
  }

  function policyFor(hass) {
    const connection = hass?.connection;
    if (!connection) return undefined;
    let policy = policies.get(connection);
    if (!policy && valid(hass.config?.loona_graph_loading)) {
      policy = hass.config.loona_graph_loading;
      policies.set(connection, policy);
      lastPolicy = policy;
      motion.update(policy, hass);
    }
    if (!subscriptions.has(connection) && typeof connection.subscribeMessage === "function") {
      subscriptions.add(connection);
      const update = (value) => {
        policies.set(connection, valid(value) ? value : { enabled: false });
        motion.update(valid(value) ? value : undefined, hass);
        if (valid(value)) lastPolicy = value;
        for (const card of connectedCards) {
          if (card._hass?.connection === connection && !eligible(card._owner, card._config)) {
            card._load(false, "disabled");
          }
        }
      };
      Promise.resolve(connection.subscribeMessage(update, { type: "loona/subscribe_graph_loading" }))
        .catch(() => update(undefined));
    }
    return valid(policy) ? policy : undefined;
  }

  function eligible(owner, config) {
    const policy = policyFor(owner?.hass ?? construction?.hass);
    if (!policy?.enabled || owner.preview || construction?.preview
      || (owner.layout ?? construction?.layout) === "panel") return false;
    let dashboard;
    try { dashboard = decodeURIComponent(location.pathname.split("/")[1] ?? ""); }
    catch { return false; }
    if (!policy.dashboards.includes(dashboard)) return false;
    const profile = policy.profiles[config?.type];
    if (!profile || !Number.isFinite(profile.height) || !Number.isFinite(profile.size)
      || !Number.isFinite(profile.columns) || !Number.isFinite(profile.rows)) return false;
    return config.type !== "sensor" || config.graph === "line";
  }

  function trace(card, event, priority = "") {
    const now = performance.now();
    events.push({
      at_ms: Math.round((now - started) * 10) / 10,
      graph: card._traceId,
      card: card._config?.type,
      entity: card._config?.entity ?? card._config?.series?.[0]?.entity ?? "",
      event,
      priority,
      visible: card._visible,
      since_visible_ms: card._visibleSince === undefined ? null
        : Math.round((now - card._visibleSince) * 10) / 10,
    });
    if (events.length > timing().trace_limit) events.shift();
  }
  // Custom cards have no shared "loaded" event. Observe rendering and HA requests,
  // then use a quiet interval before allowing one background graph at a time.
  class VisibleFirstQueue {
    constructor() {
      this.jobs = new Map();
      this.renders = new Map();
      this.renderPromises = new WeakMap();
      this.roots = new Set();
      this.renderGeneration = 0;
      this.activity = () => this.touch();
    }

    pending() {
      return [...connectedCards].filter((card) => card._owner?.isConnected && !card._owner.hidden && !card._card && !card._failed);
    }

    changed() {
      if (!this.pending().length) {
        this.stop();
        return;
      }
      if (!this.active) {
        this.active = true;
        this.renderGeneration++;
        this.lastActivity = performance.now();
        document.addEventListener("scroll", this.activity, { capture: true, passive: true });
        document.addEventListener("pointerdown", this.activity, { passive: true });
        document.addEventListener("visibilitychange", this.activity);
        if (typeof PerformanceObserver === "function") {
          this.performanceObserver = new PerformanceObserver(this.activity);
          const entryTypes = (PerformanceObserver.supportedEntryTypes ?? []).filter(
            (type) => type === "resource" || type === "longtask",
          );
          if (entryTypes.length) this.performanceObserver.observe({ entryTypes });
        }
        if (typeof MutationObserver === "function") {
          this.mutationObserver = new MutationObserver((records) => {
            if (records.some((record) => this.visible(record.target))) this.touch();
            for (const record of records) {
              for (const node of record.addedNodes) this.watchTree(node);
            }
          });
        }
      }
      this.touch();
    }

    visible(node) {
      const element = node.host ?? (node.nodeType === 3 ? node.parentElement : node);
      if (!element?.getBoundingClientRect) return false;
      const rect = element.getBoundingClientRect();
      return rect.bottom > 0 && rect.right > 0 && rect.top < window.innerHeight
        && rect.left < window.innerWidth;
    }

    watchTree(node) {
      if (!this.active || !node) return;
      if (node.shadowRoot) {
        if (!this.roots.has(node.shadowRoot)) {
          this.watchRoot(node.shadowRoot);
          this.touch();
        } else {
          this.watchTree(node.shadowRoot);
        }
      }
      if (this.visible(node)) {
        const promise = node.isUpdatePending === false ? undefined : node.updateComplete;
        if (promise?.then && this.renderPromises.get(node) !== promise) {
          this.renderPromises.set(node, promise);
          this.renders.set(promise, node);
          const session = this.renderGeneration;
          Promise.resolve(promise).catch(() => {}).finally(() => {
            if (session !== this.renderGeneration) return;
            this.renders.delete(promise);
            this.touch();
          });
        }
      }
      for (const child of node.children ?? []) this.watchTree(child);
    }

    watchRoot(root) {
      if (this.roots.has(root)) return;
      this.roots.add(root);
      this.mutationObserver?.observe(root, {
        subtree: true, childList: true, characterData: true,
        attributes: true, attributeFilter: ["src", "href", "d"],
      });
      this.watchTree(root);
    }

    watchViews() {
      const views = new Set();
      for (const card of connectedCards) {
        let node = card._owner;
        while (node) {
          if (["HUI-SECTIONS-VIEW", "HUI-MASONRY-VIEW", "HUI-PANEL-VIEW"].includes(node.tagName)) {
            views.add(node);
            break;
          }
          node = node.parentElement ?? node.getRootNode?.().host;
        }
      }
      for (const view of views) {
        if (!this.roots.has(view)) this.watchRoot(view);
        else this.watchTree(view);
      }
    }

    busy(except) {
      // Give startup motion its first idle restoration before background graphs.
      if (motion.active) return true;
      if (document.hidden || [...this.renders.values()].some((node) => node.isConnected && this.visible(node))
        || [...this.jobs.keys()].some((job) => job !== except)) return true;
      if (document.fonts?.status === "loading") return true;
      // Native HA keeps subscriptions in this map indefinitely. Only ordinary
      // command promises represent requests that have not received their result.
      for (const connection of new Set([...connectedCards].map((card) => card._hass?.connection))) {
        if (connection?.connected === false) return true;
        if (connection?.commands instanceof Map) {
          for (const info of connection.commands.values()) {
            if (!("subscribe" in info)) return true;
          }
        }
      }
      for (const root of this.roots) {
        for (const image of root.querySelectorAll?.("img") ?? []) {
          if (!image.complete && this.visible(image)) return true;
        }
      }
      return false;
    }

    ready(except) {
      return this.active && !this.busy(except) && performance.now() - this.lastActivity >= timing().quiet_ms;
    }

    cancelScheduled() {
      clearTimeout(this.timer);
      this.timer = undefined;
      if (this.idle !== undefined) window.cancelIdleCallback(this.idle);
      this.idle = undefined;
    }

    touch() {
      if (!this.active) return;
      this.wasBusy = false;
      this.lastActivity = performance.now();
      this.cancelScheduled();
      this.timer = setTimeout(() => this.wake(), timing().quiet_ms);
    }

    wake() {
      this.timer = undefined;
      if (!this.pending().length) return this.stop();
      if (this.busy()) {
        this.wasBusy = true;
        this.timer = setTimeout(() => this.wake(), timing().poll_ms);
        return;
      }
      if (this.wasBusy) {
        this.touch();
        return;
      }
      // Late-attached Lit shadow roots also need watching before background work.
      this.watchViews();
      if (!this.ready()) {
        if (this.timer === undefined) this.timer = setTimeout(() => this.wake(), timing().poll_ms);
        return;
      }
      const run = () => {
        this.idle = undefined;
        this.timer = undefined;
        if (!this.ready()) {
          this.timer = setTimeout(() => this.wake(), timing().poll_ms);
          return;
        }
        const card = this.pending().find((item) => !item._loading);
        if (card) card._load(true);
        else this.timer = setTimeout(() => this.wake(), timing().poll_ms);
      };
      if (typeof window.requestIdleCallback === "function") {
        this.idle = window.requestIdleCallback(run);
      } else {
        this.timer = setTimeout(run, 0);
      }
    }

    begin(card) {
      const job = {};
      this.jobs.set(job, card);
      return job;
    }

    end(job) {
      this.jobs.delete(job);
      this.changed();
    }

    invalidate(card) {
      for (const [job, owner] of this.jobs) {
        if (owner === card) this.jobs.delete(job);
      }
      this.changed();
    }

    stop() {
      this.active = false;
      this.renderGeneration++;
      this.cancelScheduled();
      this.performanceObserver?.disconnect();
      this.mutationObserver?.disconnect();
      this.roots.clear();
      this.renders.clear();
      this.renderPromises = new WeakMap();
      document.removeEventListener("scroll", this.activity, true);
      document.removeEventListener("pointerdown", this.activity);
      document.removeEventListener("visibilitychange", this.activity);
    }
  }

  const queue = new VisibleFirstQueue();

  window.loonaGraphLoadingTrace = () => events.map((event) => ({ ...event }));
  window.loonaGraphLoadingReport = () => ({
    version: moduleVersion,
    hook_installed: Boolean(nativeLoad),
    strategy: "visible-first-background",
    connected: connectedCards.size,
    created: [...connectedCards].filter((card) => card._card).length,
    pending: queue.pending().length,
    active_loads: queue.jobs.size,
    pending_renders: queue.renders.size,
    graphs: [...connectedCards].map((card) => ({
      graph: card._traceId,
      card: card._config?.type,
      entity: card._config?.entity ?? card._config?.series?.[0]?.entity ?? "",
      visible: card._visible,
      state: card._failed ? "failed" : card._loading ? "loading" : card._card ? "created" : "pending",
      child: card._card?.tagName ?? "",
    })),
  });

  // HA replaces the registry and HTMLElement during bootstrap. Both the class
  // and its registration must wait for the native card container to be ready.
  customElements.whenDefined("hui-card").then(() => {
    class GraphPlaceholder extends HTMLElement {
      constructor() {
        super();
        this._traceId = ++sequence;
        this._generation = 0;
        this._visible = false;
        this.attachShadow({ mode: "open" }).innerHTML = `
          <style>
            :host { display: block; min-width: 0; height: 100%; }
            div { min-height: var(--loona-graph-height);
              background: var(--ha-card-background, var(--card-background-color));
              border-radius: var(--ha-card-border-radius, 12px); }
          </style><div aria-hidden="true"></div>`;
      }

      setConfig(config) {
        this._config = config.type === "custom:loona-graph-placeholder" ? config.card : config;
        if (this._owner) {
          this._profile = policyFor(this._owner.hass)?.profiles[this._config.type];
          this.style.setProperty("--loona-graph-height", `${this._profile?.height ?? 0}px`);
          if (this.isConnected && !eligible(this._owner, this._config)) {
            queueMicrotask(() => this._load(false, "configuration"));
          }
        }
      }

      getCardSize() { return this._profile?.size; }
      getGridOptions() { return { columns: this._profile?.columns, rows: this._profile?.rows }; }
      set hass(value) { this._hass = value; }
      set preview(value) {
        this._preview = value;
        if (value && this.isConnected) this._load(false, "preview");
      }

      connectedCallback() {
        this._owner = this.parentElement;
        this._profile = policyFor(this._owner?.hass)?.profiles[this._config.type];
        if (!nativeLoad) return;
        this.style.setProperty("--loona-graph-height", `${this._profile?.height ?? 0}px`);
        records.set(this._owner, this);
        connectedCards.add(this);
        watchLifecycle(this._owner);
        queue.changed();
        if (!eligible(this._owner, this._config) || typeof IntersectionObserver !== "function") {
          this._load(false, this._preview ? "preview" : "native");
          return;
        }
        this._observer = new IntersectionObserver((entries) => {
          const entry = entries.at(-1);
          if (!this._owner?.isConnected || this._owner.hidden) return;
          const visible = Boolean(entry?.isIntersecting);
          if (visible && !this._visible) {
            this._visibleSince = Number.isFinite(entry.time) ? entry.time : performance.now();
          }
          this._visible = visible;
          trace(this, "viewport");
          queue.touch();
          // Newly visible cards always bypass the background readiness gate.
          if (visible) this._load();
        }, { rootMargin: "0px", threshold: 0 });
        this._observer.observe(this._owner);
      }

      disconnectedCallback() {
        if (!this._promoting) this.release();
      }

      release() {
        this._observer?.disconnect();
        this._observer = undefined;
        connectedCards.delete(this);
        if (!connectedCards.size) {
          lifecycleObserver.disconnect();
          lifecycleRoots.clear();
        }
        this._generation++;
        this._loading = false;
        this._visible = false;
        this._visibleSince = undefined;
        queue.invalidate(this);
      }

      async _load(background = false, reason) {
        const owner = this._owner;
        if (this._card || this._loading || this._failed || !owner?.isConnected) return;
        if (owner.hidden && !owner.preview) return;
        this._loading = true;
        const generation = this._generation;
        const job = queue.begin(this);
        const priority = reason ?? (this._visible ? "visible" : background ? "background" : "native");
        try {
          trace(this, "create", priority);
          this._promoting = true;
          nativeLoad.call(owner, owner.config);
          this._card = owner._element;
          owner.dispatchEvent(new CustomEvent("card-updated", { bubbles: true, composed: true }));
          queue.watchTree(this._card);
          await this._card?.updateComplete;
          if (generation === this._generation) trace(this, "first-render", priority);
        } catch (error) {
          this._failed = true;
          trace(this, "error", priority);
          console.error("Loona graph loading:", error);
        } finally {
          this._promoting = false;
          if (generation === this._generation) this._loading = false;
          queue.end(job);
        }
      }
    }

    customElements.define("loona-graph-placeholder", GraphPlaceholder);
    const prototype = customElements.get("hui-card").prototype;
    if (!["_loadElement", "_updateElement", "_setElementVisibility"]
      .every((name) => typeof prototype[name] === "function")) return;
    nativeLoad = prototype._loadElement;
    prototype._loadElement = function (config) {
      // Existing graphs and native rebuilds keep Home Assistant's ordinary path.
      const pending = records.get(this);
      if (pending) pending.release();
      const previous = construction;
      construction = {
        hass: this.hass ?? previous?.hass,
        preview: this.preview || previous?.preview,
        layout: this.layout ?? previous?.layout,
      };
      try {
        if ((!this._element || this._element instanceof GraphPlaceholder)
          && eligible(this, config)) {
          nativeLoad.call(this, { type: "custom:loona-graph-placeholder", card: config });
          if (!(this._element instanceof GraphPlaceholder)) {
            // Optional scheduling must never replace a valid native graph with
            // an error card when a registry or another extension declines it.
            nativeLoad.call(this, config);
            return;
          }
          // Keep native editing and same-type config updates keyed to the original.
          this._elementConfig = config;
          if (this._element instanceof GraphPlaceholder) {
            this._element._profile = policyFor(construction.hass)?.profiles[config.type];
          }
        } else {
          nativeLoad.call(this, config);
        }
      } finally {
        const hass = construction.hass;
        queueMicrotask(() => {
          motion.track(this, hass, policyFor(hass));
        });
        construction = previous;
      }
    };
  });
}
