// Administrator-requested measurement. No observer runs between measurements.
let running = false;

export async function measure(hass, duration) {
  if (!hass?.user?.is_admin || running) throw new Error("Administrator measurement unavailable");
  if (!Number.isFinite(duration) || duration < 1000 || duration > 60000) throw new Error("Invalid measurement duration");
  const dashboard = decodeURIComponent(location.pathname.split("/")[1] || hass.panelUrl || "");
  const connection = hass.connection;
  const socket = connection.socket;
  const started = performance.now();
  const scripts = new Map();
  let frames = 0;
  let blocking = 0;
  let entriesSeen = 0;
  let observer;
  running = true;
  const supported = typeof PerformanceObserver === "function"
    && PerformanceObserver.supportedEntryTypes?.includes("long-animation-frame") === true;
  const collect = (entries) => {
    for (const frame of entries) {
      if (++entriesSeen > 10000) break;
      const phase = frame.startTime < started ? "buffered" : "window";
      if (phase === "window") { frames++; blocking += frame.blockingDuration || 0; }
      for (const script of frame.scripts || []) {
        let url;
        try { url = new URL(script.sourceURL); } catch { continue; }
        if (url.origin !== location.origin || !/^\/(frontend_latest|hacsfiles|local|uix|loona)\//.test(url.pathname)
            || url.pathname.length > 512 || /\s/.test(url.pathname)) continue;
        const key = phase + url.pathname;
        let row = scripts.get(key);
        if (!row) {
          if (scripts.size >= 40) continue;
          row = {source:url.pathname, phase, duration_ms:0, forced_layout_ms:0};
          scripts.set(key, row);
        }
        row.duration_ms += script.duration || 0;
        row.forced_layout_ms += script.forcedStyleAndLayoutDuration || 0;
      }
    }
  };
  try {
    if (supported) {
      observer = new PerformanceObserver(list => collect(list.getEntries()));
      observer.observe({type:"long-animation-frame", buffered:true});
    }
    await new Promise(resolve => setTimeout(resolve, duration));
    if (observer) collect(observer.takeRecords());
    if (hass.connection !== connection || connection.socket !== socket || !connection.connected
        || dashboard !== decodeURIComponent(location.pathname.split("/")[1] || hass.panelUrl || "")) {
      throw new Error("Dashboard changed during measurement");
    }
    const report = {dashboard, duration_ms:performance.now() - started, loaf_supported:supported,
      frames, blocking_ms:blocking, scripts:[...scripts.values()],
      subscriptions:window.loonaSubscriptionReport?.(connection) || []};
    await connection.sendMessagePromise({type:"loona/browser_report", ...report});
    return report;
  } finally {
    observer?.disconnect();
    running = false;
  }
}
