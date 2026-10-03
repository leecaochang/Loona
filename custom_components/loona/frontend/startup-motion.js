// Temporarily yield continuous card motion to initial dashboard work.
export function animationProtected(target, view, progressTags) {
  let card=false;
  for (let node=target; node && node!==view; node=node.parentElement ?? node.getRootNode?.().host) {
    if (node.preview || node.editMode || node.hidden || node.getAttribute?.("aria-busy")==="true"
      || node.getAttribute?.("role")==="progressbar" || progressTags.includes(node.tagName)) return true;
    if (node.tagName==="HUI-CARD") card=true;
  }
  return !card || view.editMode || view.lovelace?.editMode;
}

export class StartupMotion {
  constructor(version) {
    this.version = version;
    this.owned = new Set();
    this.roots = new Set();
    this.renders = new Map();
    this.renderPromises = new WeakMap();
    this.phase = "disabled";
    this.pausedTotal = 0;
    this.generation = 0;
    this.interact = () => this.finish("interaction");
    this.navigate = () => {
      if (this.path !== location.pathname) {
        this.finish("navigation");
        this.view = undefined;
      }
    };
    window.addEventListener("location-changed", this.navigate);
    window.addEventListener("popstate", this.navigate);
    window.addEventListener("pagehide", () => this.finish("page-hidden"));
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) this.finish("page-hidden");
    });
    window.loonaStartupMotionReport = () => ({
      version: this.version, enabled: Boolean(this.policy?.motion?.enabled),
      phase: this.phase, paused: this.owned.size, paused_total: this.pausedTotal,
      resumed_after_ms: this.resumedAfter ?? null,
    });
  }

  allowed(policy = this.policy) {
    let dashboard;
    try { dashboard = decodeURIComponent(location.pathname.split("/")[1] ?? ""); }
    catch { return false; }
    return policy?.version === this.version && policy.motion?.enabled === true
      && policy.dashboards?.includes(dashboard)
      && [policy.motion.quiet_ms, policy.motion.poll_ms, policy.motion.max_ms]
        .every((value) => Number.isFinite(value) && value > 0)
      && Array.isArray(policy.motion.progress_tags) && Array.isArray(policy.motion.view_tags);
  }

  update(policy, hass) {
    // A stale callback from a different connection cannot change this view.
    if (this.connection && this.connection !== hass?.connection) return;
    this.policy = policy;
    if (!this.allowed()) this.finish("disabled");
  }

  parent(node) { return node?.parentElement ?? node?.getRootNode?.().host; }

  track(owner, hass, policy) {
    if (!owner.isConnected) return;
    if (this.connection !== hass?.connection) {
      this.finish("connection-changed");
      this.view = undefined;
      this.connection = hass?.connection;
    }
    this.update(policy, hass);
    if (!this.allowed() || document.hidden || owner.preview || owner.layout === "panel") return;
    let view = owner;
    while (view && !this.policy.motion.view_tags.includes(view.tagName)) {
      if (view.preview || view.editMode || view.lovelace?.editMode) return;
      view = this.parent(view);
    }
    if (!view?.isConnected || view.editMode || view.lovelace?.editMode) return;
    if (this.view === view && this.path === location.pathname) return;
    this.finish("navigation");
    this.view = view;
    this.path = location.pathname;
    this.connection = hass?.connection;
    this.active = true;
    this.phase = "loading";
    this.pausedTotal = 0;
    this.resumedAfter = undefined;
    this.started = this.lastActivity = performance.now();
    const generation = ++this.generation;
    this.observer = new MutationObserver((records) => {
      if (records.some((record) => this.visible(record.target))) this.touch();
    });
    if (typeof PerformanceObserver === "function") {
      this.performanceObserver = new PerformanceObserver(() => this.touch());
      const entryTypes = (PerformanceObserver.supportedEntryTypes ?? [])
        .filter((type) => type === "resource" || type === "longtask");
      if (entryTypes.length) this.performanceObserver.observe({ entryTypes });
    }
    for (const type of ["pointerdown", "keydown", "scroll"]) {
      document.addEventListener(type, this.interact, { capture: true, passive: true });
    }
    this.deadline = setTimeout(() => this.finish("time-limit"), this.policy.motion.max_ms);
    this.tick();
    // Native children may attach their shadow roots after the factory returns.
    queueMicrotask(() => { if (this.active && this.generation === generation) this.tick(); });
  }

  visible(node) {
    node = node?.host ?? (node?.nodeType === 3 ? node.parentElement : node);
    const rect = node?.getBoundingClientRect?.();
    return rect && rect.width !== 0 && rect.height !== 0 && rect.bottom > 0
      && rect.right > 0 && rect.top < window.innerHeight && rect.left < window.innerWidth;
  }

  touch() { if (this.active) this.lastActivity = performance.now(); }

  protected(target) {
    return animationProtected(target,this.view,this.policy.motion.progress_tags);
  }

  watch(node, animations) {
    if (!node) return;
    if (node === this.view || node.host) {
      if (!this.roots.has(node)) {
        this.roots.add(node);
        this.observer.observe(node, { subtree: true, childList: true, characterData: true,
          attributes: true, attributeFilter: ["src", "href", "d"] });
        this.touch();
      }
      for (const animation of node.getAnimations?.({ subtree: true }) ?? []) animations.add(animation);
    }
    const promise = node.isUpdatePending === false ? undefined : node.updateComplete;
    if (promise?.then && this.renderPromises.get(node) !== promise && this.visible(node)) {
      this.renderPromises.set(node, promise);
      this.renders.set(promise, node);
      const generation = this.generation;
      Promise.resolve(promise).catch(() => {}).finally(() => {
        if (generation !== this.generation) return;
        this.renders.delete(promise);
        this.touch();
      });
    }
    if (node.shadowRoot) this.watch(node.shadowRoot, animations);
    for (const child of node.children ?? []) this.watch(child, animations);
  }

  busy() {
    if (this.connection?.connected === false || document.fonts?.status === "loading") return true;
    if ([...this.renders.values()].some((node) => node.isConnected && this.visible(node))) return true;
    for (const info of this.connection?.commands?.values?.() ?? []) {
      if (!("subscribe" in info)) return true;
    }
    for (const root of this.roots) {
      for (const image of root.querySelectorAll?.("img") ?? []) {
        if (!image.complete && this.visible(image)) return true;
      }
    }
    return false;
  }

  tick() {
    clearTimeout(this.timer);
    if (!this.active) return;
    if (!this.view.isConnected || this.path !== location.pathname) return this.finish("navigation");
    if (!this.allowed() || this.view.editMode || this.view.lovelace?.editMode) return this.finish("disabled");
    const animations = new Set();
    this.watch(this.view, animations);
    for (const animation of this.owned) {
      if (!animations.has(animation) || this.protected(animation.effect?.target)) {
        try { if (animation.playState === "paused") animation.play(); }
        catch { /* Detached animations can be invalidated by their card. */ }
        this.owned.delete(animation);
      }
    }
    for (const animation of animations) {
      const target = animation.effect?.target;
      if (animation.playState !== "running" || !target || this.protected(target)
        || animation.effect.getTiming().iterations !== Infinity) continue;
      try {
        animation.pause();
        this.owned.add(animation);
        this.pausedTotal++;
      } catch { /* An animation can disappear between collection and pause. */ }
    }
    if (this.busy()) this.touch();
    if (performance.now() - this.lastActivity >= this.policy.motion.quiet_ms) {
      // Resume once during an idle opportunity. Later state updates and
      // background graphs do not repeatedly pause a settled dashboard.
      if (typeof window.requestIdleCallback === "function") {
        if (this.idle === undefined) this.idle = window.requestIdleCallback(() => {
          this.idle = undefined;
          if (!this.active) return;
          if (!this.busy() && performance.now() - this.lastActivity >= this.policy.motion.quiet_ms) {
            this.finish("settled");
          }
        }, { timeout: this.policy.motion.poll_ms });
      } else this.finish("settled");
    }
    if (this.active) this.timer = setTimeout(() => this.tick(), this.policy.motion.poll_ms);
  }

  finish(reason) {
    clearTimeout(this.timer);
    clearTimeout(this.deadline);
    if (this.idle !== undefined) window.cancelIdleCallback(this.idle);
    this.idle = undefined;
    this.observer?.disconnect();
    this.performanceObserver?.disconnect();
    for (const type of ["pointerdown", "keydown", "scroll"]) document.removeEventListener(type, this.interact, true);
    for (const animation of this.owned) {
      try { if (animation.playState === "paused") animation.play(); }
      catch { /* Removed animations may no longer be playable. */ }
    }
    this.owned.clear();
    this.roots.clear();
    this.renders.clear();
    this.renderPromises = new WeakMap();
    if (this.active) {
      this.phase = reason;
      this.resumedAfter = Math.round(performance.now() - this.started);
    } else if (reason === "disabled") this.phase = reason;
    this.active = false;
    this.generation++;
    window.dispatchEvent(new window.Event("loona-startup-motion-finished"));
  }
}
