/* Shared English/Simplified Chinese messages for Loona cards. */
const chinese = {
  "Dashboards": "仪表盘",
  "Apply filtering to": "筛选哪些账户",
  "Accounts": "账户",
  "Selected accounts": "指定账户",
  "All accounts": "所有账户",
  "Loona settings": "Loona 设置",
  "Filters and performance": "筛选与性能",
  "Entity filtering": "实体筛选",
  "Registry filtering": "注册表筛选",
  "Pause animations during loading": "加载期间暂停动画",
  "Resource filtering": "资源筛选",
  "Additional files to load": "额外加载的文件",
  "Enabled": "启用",
  "Rescan dashboards": "重新扫描仪表盘",
  "Reset live statistics": "重置实时统计",
  "A feature is unavailable. Check Loona diagnostics.": "部分功能无法使用。请查看 Loona 诊断信息。",
  "Loona card title must be text": "Loona 卡片标题必须为文本",
  "Loona statistics": "Loona 统计",
  "Loading statistics...": "正在加载统计…",
  "Refresh": "刷新",
  "Sent": "已发送",
  "Filtered out": "已筛掉",
  "Updates filtered": "更新减少比例",
  "updates/s": "次更新/秒",
  "of counted updates": "占统计更新数",
  "Updates sent since reset": "重置后发送的更新",
  "Updates filtered since reset": "重置后筛掉的更新",
  "Filtered / tracked update feeds": "已筛选 / 跟踪的更新订阅",
  "Entities currently included": "当前包含的实体",
  "Latest page loads": "最近页面加载",
  "Each dashboard's latest browser reload. Entity counts include all selected dashboards. File counts cover registered card files, not Home Assistant's own files or files loaded separately.": "每个仪表盘最近一次浏览器刷新的记录。实体计数包含所有所选仪表盘。文件计数只包含已注册的卡片文件，不包括 Home Assistant 自身文件或单独加载的文件。",
  "Could not load statistics. Check that Loona is running, then press Refresh.": "无法加载统计。请确认 Loona 正在运行，再点击“刷新”。",
  "Unable to load statistics": "无法加载统计",
  "Could not reset statistics. Try Reset live statistics on the Loona device page.": "无法重置统计。请尝试 Loona 设备页面上的“重置实时统计”按钮。",
  "Dashboard scan incomplete. All entities are being sent.": "仪表盘扫描不完整，正在发送全部实体。",
  "Entity filtering is disabled": "实体筛选已关闭",
  "Entity filtering is active": "实体筛选已启用",
  "No filtered update feed yet. Open a dashboard with a selected account.": "还没有被筛选的更新订阅。请使用所选账户打开仪表盘。",
  "Measured over the last {seconds} seconds.": "统计时段为最近 {seconds} 秒。",
  "Rates update within {seconds} seconds.": "更新速率将在 {seconds} 秒内显示。",
  "Each update is counted once per update feed, so multiple tabs can increase totals. These numbers do not measure loading speed or network traffic.": "每次更新按更新订阅分别计数，因此打开多个标签页可能增加总数。这些数字不代表加载速度或网络流量。",
  "{count} entities": "{count} 个实体",
  "Since {time}": "开始于 {time}",
  "Entities sent: {sent} / {available}": "已发送实体：{sent} / {available}",
  "Card files sent: {sent} / {available}": "已发送卡片文件：{sent} / {available}",
  "No card file count was recorded for this load.": "本次加载未记录卡片文件数量。",
  "No page loads recorded yet. Reload one of your dashboards.": "尚无页面加载记录。请刷新一个仪表盘。",
  "Live filtering statistics and latest page loads": "实时筛选统计与最近页面加载",
  "Loading settings...": "正在加载设置…",
  "Sign in as an administrator to change Loona settings.": "请使用管理员账户登录以修改 Loona 设置。",
  "Could not load settings. Check that Loona is running, then press Refresh.": "无法加载设置。请确认 Loona 正在运行，再点击“刷新”。",
  "Save": "保存",
  "Cancel": "取消",
  "Saved": "已保存",
  "Unsaved changes": "有未保存的修改",
  "Settings changed elsewhere. Cancel your edits and refresh before saving.": "设置已在其他地方修改。请取消当前修改并刷新，然后再保存。",
  "Could not save. Your edits are still here. Cancel them and refresh to check the saved settings.": "无法保存，当前修改仍然保留。请取消修改并刷新，以检查已保存的设置。",
  "Some choices are no longer available. Cancel your edits and refresh the lists.": "部分选项已失效。请取消修改并刷新列表。",
  "File choices are unavailable on this installation.": "当前安装无法修改文件选择。",
  "Search available choices": "搜索可用选项",
  "Selected ({count})": "已选择（{count}）",
  "No selections": "未选择",
  "No matching choices": "没有匹配的选项",
  "Available choices": "可用选项",
  "Show more": "显示更多",
  "Unavailable": "不可用",
  "optional": "可选",
  "Not used in selected dashboards": "所选仪表盘未使用",
  "Usage unknown": "用途不确定",
  "Files kept automatically ({count})": "自动保留的文件（{count}）",
  "These files are needed by your dashboards or shared styling.": "这些文件用于仪表盘卡片或共享样式。",
  "Checked files load; unchecked files are skipped when Resource filtering is on. Save, then reload the browser page.": "开启资源筛选时，勾选的文件会加载，未勾选的文件会跳过。保存后，请刷新浏览器页面。",
  "Refresh is unavailable while you have unsaved changes.": "有未保存的修改时无法刷新。",
  "Change filters, dashboards and accounts": "修改筛选、仪表盘和账户",
  "Pause repeating animations while loading, then resume them automatically.": "加载期间暂停循环动画，随后自动恢复。",
  "An update feed receives live entity changes; one tab can have more than one. The entity reduction estimate compares included entities with all current entities, even when filtering is off.": "更新订阅用于接收实体的实时变化，一个标签页可能有多个订阅。实体减少估算通过比较包含的实体与当前全部实体得出，关闭筛选时也会显示。",
  "Rescan checks dashboard changes now. Reset clears live counters and page-load records; entity counts and recorded history stay unchanged.": "重新扫描会立即检查仪表盘变化。重置会清零实时计数并清除页面加载记录，不影响实体数量或已记录的历史数据。",
  "Working...": "正在处理…",
  "Dashboards rescanned": "已重新扫描仪表盘",
  "Live statistics reset": "已重置实时统计",
  "Action failed. Check that Loona is running, then try again.": "操作失败。请确认 Loona 正在运行，然后重试。",
  "Estimated entity reduction": "实体数量减少估算",
  "Entity rules": "实体规则",
  "Cards": "卡片",
  "Delay graph loading": "延迟加载图表",
  "Included": "包含",
  "Excluded": "排除",
  "Entities": "实体",
  "Entity types": "实体类型",
  "Entities or patterns": "实体或匹配规则",
  "{count} selected": "已选择 {count} 项",
  "Loona finds dashboard entities automatically. Use these rules to add anything it missed or exclude entities you do not need.": "Loona 会自动查找仪表盘使用的实体。可用这些规则补充遗漏的实体，或排除不需要的实体。",
  "Add entities to the automatic dashboard list.": "在自动发现的仪表盘实体列表中添加实体。",
  "Exclusions override inclusions and may leave cards without data. Loona's own controls and statistics stay included.": "排除规则优先于包含规则，可能导致卡片缺少数据。Loona 自身的控制和统计实体始终保留。",
  "Turn off to restore standard dashboard behavior immediately.": "关闭后，仪表盘立即恢复标准行为。",
  "Automatically find the entities used by your selected dashboards.": "自动查找所选仪表盘使用的实体。",
  "Reduce the entity and device information sent to dashboards, including names, icons and areas.": "减少发送给仪表盘的实体和设备信息，包括名称、图标和区域等。",
  "Load required files and any additional files selected under Cards. Refresh the browser after changes.": "加载必需的文件和在“卡片”中勾选的其他文件。修改后请刷新浏览器。",
  "Delay off-screen graphs until the dashboard has loaded. Scrolling to a graph loads it immediately.": "等仪表盘加载完成后再加载屏幕外的图表。滚动到图表时立即加载。",
  "Choose which dashboards you want to filter.": "选择需要筛选的仪表盘。",
  "Choose which accounts receive filtered data while viewing selected dashboards.": "选择哪些账户在查看所选仪表盘时接收筛选后的数据。",
  "Filtering applies only to selected accounts viewing selected dashboards.": "仅当所选账户查看所选仪表盘时应用筛选。",
  "Version: {version}": "版本：{version}",
  "Warnings and checks ({count})": "警告与检查（{count}）",
  "No warnings": "没有警告",
  "Warning": "警告",
  "Check": "检查",
  "Affected items ({count})": "相关项目（{count}）",
  "Entity filtering is unavailable": "实体筛选无法使用",
  "Home Assistant is handling entity updates normally. Check Loona diagnostics and the supported Home Assistant versions, then reload Loona and your browser.": "Home Assistant 正在正常处理实体更新。请查看 Loona 诊断信息和支持的 Home Assistant 版本，然后重新加载 Loona 并刷新浏览器。",
  "Dashboard detection is unavailable": "无法识别当前仪表盘",
  "Loona cannot identify the active dashboard, so filtering is bypassed. Reload Loona and refresh the browser. If this continues, check diagnostics.": "Loona 无法识别当前仪表盘，因此已跳过筛选。请重新加载 Loona 并刷新浏览器。如果问题持续，请查看诊断信息。",
  "Registry filtering is unavailable": "注册表筛选无法使用",
  "Home Assistant is sending normal entity and device information. Check Loona diagnostics for a compatibility problem, then reload Loona.": "Home Assistant 正在发送正常的实体和设备信息。请查看 Loona 诊断信息中的兼容性问题，然后重新加载 Loona。",
  "Loading optimizations are unavailable": "加载优化无法使用",
  "Graphs and animations use normal Home Assistant behavior. Check the supported Home Assistant versions and Loona diagnostics.": "图表和动画使用 Home Assistant 的标准行为。请检查支持的 Home Assistant 版本和 Loona 诊断信息。",
  "Resource filtering is unavailable": "资源筛选无法使用",
  "Home Assistant is loading its normal card files. Check Loona diagnostics, then reload Loona and the browser.": "Home Assistant 正在正常加载卡片文件。请查看 Loona 诊断信息，然后重新加载 Loona 并刷新浏览器。",
  "The Loona dashboard could not be created": "无法创建 Loona 仪表盘",
  "Check for an existing dashboard at loona-statistics and check Loona diagnostics. Your other dashboards are preserved. Reload Loona after resolving the problem.": "请检查是否已有路径为 loona-statistics 的仪表盘，并查看 Loona 诊断信息。其他仪表盘会保留。解决问题后请重新加载 Loona。",
  "Dashboard scan is incomplete": "仪表盘扫描不完整",
  "Entity and registry filtering are paused. Check the selected dashboards and accounts, save automatically generated dashboards, and rescan. Unsupported templates, strategies or auto-entities rules may need changes. Filtering resumes after a complete scan.": "实体和注册表筛选已暂停。请检查所选仪表盘和账户，保存自动生成的仪表盘，然后重新扫描。不受支持的模板、策略或 auto-entities 规则可能需要修改。扫描完整后会恢复筛选。",
  "Referenced entities were not found": "未找到引用的实体",
  "Check these IDs for typos or deleted entities. Temporary entities may return later. Missing references alone do not pause filtering.": "请检查这些 ID 是否拼写错误或对应实体已被删除。临时实体可能稍后恢复。缺少引用的实体本身不会暂停筛选。",
  "Excluded entities are used by cards": "排除的实体正在被卡片使用",
  "These exclusions may leave cards without data. Remove the matching exclusions under Entity rules, or keep them if intentional.": "这些排除规则可能导致卡片缺少数据。可在“实体规则”中移除对应的排除项，或在确实需要时保留。",
  "Custom cards may use additional entities": "自定义卡片可能使用其他实体",
  "Loona cannot fully inspect every custom card. If card data is missing, add the needed entities under Entity rules. No action is needed if the cards work.": "Loona 无法完整分析所有自定义卡片。如果卡片缺少数据，请在“实体规则”中添加所需实体。卡片正常工作时无需操作。",
  "Some card files could not be identified": "无法识别部分卡片文件",
  "Check the required files under Cards if a card or icon is missing. You can turn off Resource filtering and refresh the browser to compare. No action is needed if everything works.": "如果卡片或图标缺失，请在“卡片”中检查所需文件。可以关闭资源筛选并刷新浏览器进行比较。一切正常时无需操作。",
  "Templates may load additional files": "模板可能加载其他文件",
  "Template-driven cards can need files Loona cannot detect. If something is missing, select its file under Cards and refresh the browser. No action is needed if everything works.": "由模板控制的卡片可能需要 Loona 无法识别的文件。如果内容缺失，请在“卡片”中选择对应文件并刷新浏览器。一切正常时无需操作。",
  "Unchecked files have unknown usage": "未勾选文件的用途不确定",
  "These files are skipped by Resource filtering. If a card, icon or helper is missing, select the needed files under Cards and refresh the browser. No action is needed if everything works.": "资源筛选会跳过这些文件。如果卡片、图标或辅助功能缺失，请在“卡片”中勾选所需文件并刷新浏览器。一切正常时无需操作。",
  "Saved card files are no longer registered": "已保存的卡片文件不再注册",
  "Remove unavailable saved files under Cards, or restore their Home Assistant resource registrations if you still need them.": "请在“卡片”中移除不可用的已保存文件；如果仍需使用，请恢复它们在 Home Assistant 中的资源注册。"
};
export function language(hass) {
  return String(hass?.language || hass?.locale?.language || hass?.config?.language || "en");
}
export function text(hass, key, values = {}) {
  const message = language(hass).toLowerCase().startsWith("zh") ? chinese[key] || key : key;
  return message.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}
export function translate(root, hass) {
  root.querySelectorAll("[data-i18n]").forEach(element => { element.textContent = text(hass, element.dataset.i18n); });
  root.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
    element.placeholder = text(hass, element.dataset.i18nPlaceholder);
  });
}

const notices = {
  "entity_compatibility": [
    "Entity filtering is unavailable",
    "Home Assistant is handling entity updates normally. Check Loona diagnostics and the supported Home Assistant versions, then reload Loona and your browser."
  ],
  "panel_compatibility": [
    "Dashboard detection is unavailable",
    "Loona cannot identify the active dashboard, so filtering is bypassed. Reload Loona and refresh the browser. If this continues, check diagnostics."
  ],
  "registry_compatibility": [
    "Registry filtering is unavailable",
    "Home Assistant is sending normal entity and device information. Check Loona diagnostics for a compatibility problem, then reload Loona."
  ],
  "graph_compatibility": [
    "Loading optimizations are unavailable",
    "Graphs and animations use normal Home Assistant behavior. Check the supported Home Assistant versions and Loona diagnostics."
  ],
  "resource_compatibility": [
    "Resource filtering is unavailable",
    "Home Assistant is loading its normal card files. Check Loona diagnostics, then reload Loona and the browser."
  ],
  "card_installation": [
    "The Loona dashboard could not be created",
    "Check for an existing dashboard at loona-statistics and check Loona diagnostics. Your other dashboards are preserved. Reload Loona after resolving the problem."
  ],
  "scan_incomplete": [
    "Dashboard scan is incomplete",
    "Entity and registry filtering are paused. Check the selected dashboards and accounts, save automatically generated dashboards, and rescan. Unsupported templates, strategies or auto-entities rules may need changes. Filtering resumes after a complete scan."
  ],
  "missing_entities": [
    "Referenced entities were not found",
    "Check these IDs for typos or deleted entities. Temporary entities may return later. Missing references alone do not pause filtering."
  ],
  "excluded_dependencies": [
    "Excluded entities are used by cards",
    "These exclusions may leave cards without data. Remove the matching exclusions under Entity rules, or keep them if intentional."
  ],
  "unknown_cards": [
    "Custom cards may use additional entities",
    "Loona cannot fully inspect every custom card. If card data is missing, add the needed entities under Entity rules. No action is needed if the cards work."
  ],
  "unmatched_resources": [
    "Some card files could not be identified",
    "Check the required files under Cards if a card or icon is missing. You can turn off Resource filtering and refresh the browser to compare. No action is needed if everything works."
  ],
  "dynamic_resources": [
    "Templates may load additional files",
    "Template-driven cards can need files Loona cannot detect. If something is missing, select its file under Cards and refresh the browser. No action is needed if everything works."
  ],
  "unchecked_resources": [
    "Unchecked files have unknown usage",
    "These files are skipped by Resource filtering. If a card, icon or helper is missing, select the needed files under Cards and refresh the browser. No action is needed if everything works."
  ],
  "stale_resources": [
    "Saved card files are no longer registered",
    "Remove unavailable saved files under Cards, or restore their Home Assistant resource registrations if you still need them."
  ]
};

export function renderNotices(root, hass, items) {
  const open = root.querySelector("details")?.open;
  root.replaceChildren();
  if (!items.length) {
    const healthy=document.createElement("p"); healthy.textContent=text(hass,"No warnings"); root.append(healthy); return;
  }
  const section=document.createElement("details"); section.className="loona-notices"; section.open=Boolean(open);
  const summary=document.createElement("summary"); summary.textContent=text(hass,"Warnings and checks ({count})",{count:items.length}); section.append(summary);
  const list=document.createElement("ul");
  for (const item of items) {
    const message=notices[item.code]; if (!message) continue;
    const row=document.createElement("li"); row.dataset.notice=item.code;
    const title=document.createElement("h3"); title.textContent=text(hass,item.severity === "warning" ? "Warning" : "Check")+": "+text(hass,message[0]);
    const body=document.createElement("p"); body.textContent=text(hass,message[1]); row.append(title,body);
    if (item.items?.length) {
      const details=document.createElement("details"); const heading=document.createElement("summary");
      heading.textContent=text(hass,"Affected items ({count})",{count:item.items.length});
      const values=document.createElement("div"); values.className="notice-items";
      for (const value of item.items) { const line=document.createElement("p"); line.textContent=value; values.append(line); }
      details.append(heading,values); row.append(details);
    }
    list.append(row);
  }
  section.append(list); root.append(section);
}
