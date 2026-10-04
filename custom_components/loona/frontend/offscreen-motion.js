/* Pause owned infinite browser animations only while their card is off screen. */
import { animationProtected } from "./startup-motion.js?v=0.9.10";

export class OffscreenMotion {
  constructor(version,startup) {
    this.version=version; this.startup=startup; this.cards=new Map();
    this.lifecycleRoots=new Set();
    this.lifecycle=new MutationObserver(()=>{
      for (const state of this.cards.values()) if (!state.owner.isConnected) this.remove(state);
    });
    this.navigate=()=>{ this.stop(); if (this.allowed()) this.discover(); };
    window.addEventListener("location-changed",this.navigate);
    window.addEventListener("popstate",this.navigate);
    window.addEventListener("pagehide",()=>this.stop());
    document.addEventListener("visibilitychange",()=>{ this.stop(); if (!document.hidden && this.allowed()) this.discover(); });
    window.addEventListener("loona-startup-motion-finished",()=>{
      if (this.allowed()) for (const state of this.cards.values()) if (!state.visible) this.schedule(state);
    });
    window.loonaOffscreenMotionReport=()=>({enabled:this.allowed(),tracked:this.cards.size,
      paused:[...this.cards.values()].reduce((total,state)=>total+state.owned.size,0)});
  }

  allowed() {
    let dashboard;
    try { dashboard=decodeURIComponent(location.pathname.split("/")[1] || ""); } catch { return false; }
    return Boolean(this.policy?.version===this.version && this.policy.offscreen===true
      && this.policy.dashboards?.includes(dashboard) && Array.isArray(this.policy.motion?.view_tags)
      && Array.isArray(this.policy.motion?.progress_tags) && typeof IntersectionObserver==="function");
  }

  update(policy,hass) {
    const current=document.querySelector("home-assistant")?.hass?.connection;
    if (current && current!==hass?.connection) return;
    const was=this.allowed();
    if (this.connection && this.connection!==hass?.connection) this.stop();
    this.connection=hass?.connection; this.policy=policy;
    if (!this.allowed()) this.stop();
    else if (!was && !document.hidden) this.discover();
  }

  discover() {
    if (this.discovery!==undefined) return;
    this.discovery=window.requestAnimationFrame(()=>{
      this.discovery=undefined;
      if (!this.allowed() || document.hidden) return;
      const visit=root=>{
        for (const node of root.querySelectorAll("*")) {
          if (node.tagName==="HUI-CARD") this.track(node,{connection:this.connection},this.policy);
          if (node.shadowRoot) visit(node.shadowRoot);
        }
      };
      visit(document);
    });
  }

  visible(node) {
    const rect=node.getBoundingClientRect?.();
    return Boolean(rect && rect.width!==0 && rect.height!==0 && rect.bottom>0 && rect.right>0
      && rect.top<window.innerHeight && rect.left<window.innerWidth);
  }

  ownsTarget(target,owner) {
    for (let node=target; node; node=node.parentElement ?? node.getRootNode?.().host) {
      if (node.tagName==="HUI-CARD") return node===owner;
    }
    return false;
  }

  track(owner,hass,policy) {
    this.update(policy,hass);
    const existing=this.cards.get(owner);
    if (existing && (!this.allowed() || !owner.isConnected || owner.preview || owner.layout==="panel"
      || existing.view.editMode || existing.view.lovelace?.editMode)) this.remove(existing);
    if (!this.allowed() || document.hidden || !owner.isConnected || owner.preview || owner.layout==="panel") return;
    let view=owner;
    while (view && !this.policy.motion.view_tags.includes(view.tagName)) {
      if (view.preview || view.editMode || view.lovelace?.editMode) return;
      view=view.parentElement ?? view.getRootNode?.().host;
    }
    if (!view?.isConnected || view.editMode || view.lovelace?.editMode) return;
    if (this.cards.has(owner)) return;
    if (!this.observer) this.observer=new IntersectionObserver(entries=>{
      for (const entry of entries) {
        const state=this.cards.get(entry.target);
        if (!state) continue;
        state.visible=entry.isIntersecting;
        if (state.visible) this.resume(state); else this.schedule(state);
      }
    });
    const state={owner,view,visible:this.visible(owner),owned:new Set(),roots:new Set(),frame:undefined};
    state.changed=()=>this.schedule(state);
    state.mutations=new MutationObserver(state.changed);
    this.cards.set(owner,state); this.observer.observe(owner);
    for (let node=owner; node;) {
      const root=node.getRootNode();
      if (!this.lifecycleRoots.has(root)) {
        this.lifecycleRoots.add(root);this.lifecycle.observe(root,{childList:true,subtree:true});
      }
      node=root.host;
    }
    if (!state.visible) this.schedule(state);
    Promise.resolve(owner.updateComplete).catch(()=>{}).finally(()=>{
      if (this.cards.get(owner)===state && !state.visible) this.schedule(state);
    });
  }

  schedule(state) {
    if (state.frame!==undefined || state.visible) return;
    state.frame=window.requestAnimationFrame(()=>{ state.frame=undefined;this.scan(state); });
  }

  scan(state) {
    if (!state.owner.isConnected || !state.view.isConnected) { this.remove(state);return; }
    if (!this.allowed() || state.owner.preview || state.owner.layout==="panel"
      || state.view.editMode || state.view.lovelace?.editMode) { this.remove(state);return; }
    if (state.visible || document.hidden || this.startup.active) return;
    const animations=new Set();
    const visit=root=>{
      if (!state.roots.has(root)) {
        state.roots.add(root);
        state.mutations.observe(root,{subtree:true,childList:true,attributes:true,attributeFilter:["class","style","hidden","aria-busy"]});
        root.addEventListener("animationstart",state.changed,true);
      }
      for (const animation of root.getAnimations?.({subtree:true}) || []) animations.add(animation);
      for (const node of root.querySelectorAll("*")) if (node.shadowRoot) visit(node.shadowRoot);
    };
    visit(state.owner);
    if (state.owner.shadowRoot) visit(state.owner.shadowRoot);
    for (const animation of [...state.owned]) {
      const target=animation.effect?.target;
      if (!animations.has(animation) || !target?.isConnected || this.visible(target)
        || animationProtected(target,state.view,this.policy.motion.progress_tags)) {
        this.play(animation); state.owned.delete(animation);
      }
    }
    for (const animation of animations) {
      const target=animation.effect?.target;
      if (animation.playState!=="running" || !target?.isConnected || !this.ownsTarget(target,state.owner) || this.visible(target)
        || animationProtected(target,state.view,this.policy.motion.progress_tags)
        || animation.effect.getTiming().iterations!==Infinity) continue;
      try { animation.pause();state.owned.add(animation); } catch { /* The card can invalidate its animation. */ }
    }
  }

  play(animation) { try { if (animation.playState==="paused") animation.play(); } catch { /* Detached animation. */ } }
  resume(state) {
    for (const animation of state.owned) this.play(animation);
    state.owned.clear(); state.mutations.disconnect();
    for (const root of state.roots) root.removeEventListener("animationstart",state.changed,true);
    state.roots.clear();
    if (state.frame!==undefined) window.cancelAnimationFrame(state.frame);
    state.frame=undefined;
  }
  remove(state) {
    this.resume(state);this.observer?.unobserve(state.owner);this.cards.delete(state.owner);
    if (!this.cards.size) { this.lifecycle.disconnect();this.lifecycleRoots.clear(); }
  }
  stop() {
    if (this.discovery!==undefined) window.cancelAnimationFrame(this.discovery);
    this.discovery=undefined;
    for (const state of this.cards.values()) this.resume(state);
    this.cards.clear();this.observer?.disconnect();this.observer=undefined;
    this.lifecycle.disconnect();this.lifecycleRoots.clear();
  }
}
