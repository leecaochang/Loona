/* Shared English/Simplified Chinese messages for Loona cards. */
const chinese = {
  "{source} ({phase}): {ms} ms; forced layout: {layout} ms": "{source}（{phase}）：{ms} 毫秒；强制布局：{layout} 毫秒",
  "earlier buffered": "先前缓冲",
  "measurement window": "测量期间",
  "Performance diagnostics": "性能诊断",
  "Measurements belong to this browser and dashboard. Long frames show only part of CPU work; buffered entries precede the measurement window.": "测量针对当前浏览器和仪表盘。长帧仅反映部分 CPU 工作；缓冲记录来自测量窗口之前。",
  "Measure this dashboard for 30 seconds": "测量当前仪表盘 30 秒",
  "Busiest tracked entities since reset": "重置后更新最频繁的已跟踪实体",
  "Tracking limit reached: {count} sent updates were not attributed.": "已达到跟踪上限：{count} 次已发送更新未归属到具体实体。",
  "Measuring. Keep this dashboard open.": "正在测量，请保持当前仪表盘打开。",
  "Measurement saved.": "测量结果已保存。",
  "Measurement failed. Refresh and keep the dashboard open.": "测量失败，请刷新并保持仪表盘打开。",
  "Long frames: {count}; blocking: {ms} ms": "长帧：{count}；阻塞：{ms} 毫秒",
  "Long Animation Frames are unavailable in this browser.": "此浏览器不支持长动画帧测量。",
  "A raw event subscription can bypass entity filtering.": "原始事件订阅可能绕过实体筛选。",
  "Loading optimizations are unavailable in this browser": "此浏览器无法使用加载优化",
  "Graphs and animations use normal Home Assistant behavior. Other Loona filters remain available.": "图表和动画使用 Home Assistant 的标准行为。Loona 的其他筛选功能仍然可用。",
  "Graph loading": "图表正在加载",
  "Resource scan is incomplete": "资源扫描不完整",
  "Home Assistant is loading all registered files. Check the Home Assistant log for the failed dashboard or resource load, then rescan. Loona retries automatically.": "Home Assistant 正在加载全部已注册的文件。请在 Home Assistant 日志中检查仪表盘或资源加载失败的原因，然后重新扫描。Loona 会自动重试。",
  "Dashboards": "仪表盘",
  "Apply filtering to": "筛选哪些账户",
  "Accounts": "账户",
  "Selected accounts": "指定账户",
  "All accounts": "所有账户",
  "Loona settings": "Loona 设置",
  "Filters and performance": "筛选与性能",
  "Entity filtering": "实体筛选",
  "Current tab updates": "当前标签页更新",
  "Keep this tab and Entity rules live. Hidden tabs stay cached until opened. Dialogs and editing refresh all selected dashboards. Requires Entity filtering.": "实时更新当前标签页和实体规则中的实体。隐藏标签页保留缓存，打开时刷新。对话框和编辑会刷新所有选定仪表盘。需要启用实体筛选。",
  "Registry filtering": "注册表筛选",
  "Pause animations during loading": "加载期间暂停动画",
  "Resource filtering": "资源筛选",
  "Delay card files": "延迟加载卡片文件",
  "Some card files did not load": "部分卡片文件未能加载",
  "Reload the browser to retry. If this continues, turn off Delay card files and check the files under Cards.": "请刷新浏览器重试。如果仍然失败，请关闭“延迟加载卡片文件”，并在“卡片”中检查文件。",
  "Load this dashboard's card files first, then the remaining modules. Navigation and editing load pending files immediately. Reload after enabling.": "优先加载当前仪表盘的卡片文件，再加载其余模块。导航或编辑时立即加载等待中的文件。启用后请刷新页面。",
  "Additional files to load": "额外加载的文件",
  "Enabled": "启用",
  "Rescan dashboards": "重新扫描仪表盘",
  "Reset live statistics": "重置实时统计",
  "Restore defaults": "恢复默认设置",
  "Restore defaults?": "恢复默认设置？",
  "Reset live statistics?": "重置实时统计？",
  "Remove the Loona dashboard?": "删除 Loona 仪表盘？",
  "Reset all Loona settings and live statistics, clear dashboard and account selections, and remove the generated Loona dashboard. Filtering stays inactive until you select dashboards and accounts again. Edited dashboards and recorded history are preserved.": "重置 Loona 的全部设置和实时统计，清空仪表盘与账户选择，并删除自动生成的 Loona 仪表盘。重新选择仪表盘与账户前，筛选不会生效。已编辑的仪表盘和历史记录会保留。",
  "Clear live counters, page-load records and browser measurements? Filtering settings and recorded history are preserved.": "清空实时计数、页面加载记录和浏览器测量？筛选设置和历史记录会保留。",
  "Remove the generated Loona dashboard and its cards? Manually edited dashboards are preserved. You can create it again by selecting Loona dashboard cards.": "删除自动生成的 Loona 仪表盘及其卡片？手动编辑的仪表盘会保留。重新选择 Loona 仪表盘卡片即可再次创建。",
  "Remove dashboard": "删除仪表盘",
  "Defaults restored. Select dashboards and accounts, then reload the browser.": "已恢复默认设置。请选择仪表盘与账户，再刷新浏览器。",
  "Could not restore defaults. Refresh and check the current settings.": "无法恢复默认设置。请刷新并检查当前设置。",
  "Restore defaults clears all Loona settings and live statistics. Confirmation is required.": "恢复默认设置会清空 Loona 的全部设置和实时统计，需要确认。",
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
  "Initial snapshots are filtered when startup dashboard detection succeeds. Startup fallback retains full data. File counts cover registered Lovelace files for the whole page session.": "启动时成功识别仪表盘后，初始实体快照会经过筛选。启动回退会保留完整数据。文件计数涵盖整个页面会话中已注册的 Lovelace 文件。",
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
  "Sign in as an administrator to view Loona statistics.": "请使用管理员账户登录以查看 Loona 统计。",
  "1 entity": "1 个实体",
  "Loona dashboard": "Loona 仪表盘",
  "Loona dashboard cards": "Loona 仪表盘卡片",
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
  "Not used in configured dashboards": "已配置仪表盘未使用",
  "Usage unknown": "用途不确定",
  "Files kept automatically ({count})": "自动保留的文件（{count}）",
  "These files are needed by your dashboards or shared styling.": "这些文件用于仪表盘卡片或共享样式。",
  "Known unused bundles can be skipped for the whole page session. Unknown modules always load. Save, then reload.": "已知未使用的文件可在整个页面会话中跳过。用途不确定的模块始终加载。保存后请刷新。",
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
  "Entities or domain.*": "实体或 domain.*",
  "{count} selected": "已选择 {count} 项",
  "Loona finds dashboard entities automatically. Use these rules to add anything it missed or exclude entities you do not need.": "Loona 会自动查找仪表盘使用的实体。可用这些规则补充遗漏的实体，或排除不需要的实体。",
  "Add entities to the automatic dashboard list.": "在自动发现的仪表盘实体列表中添加实体。",
  "Exclusions override inclusions and may leave cards without data. App status entities stay included.": "排除规则优先于包含规则，可能导致卡片缺少数据。应用状态实体仍会保留。",
  "Turn off to restore full entity and registry feeds. Reload to restore skipped card files.": "关闭后恢复完整实体与注册表订阅。刷新页面以恢复跳过的卡片文件。",
  "Automatically find the entities used by your selected dashboards.": "自动查找所选仪表盘使用的实体。",
  "Keep registry rows related to the included entities and dashboard targets.": "保留与所包含实体及仪表盘目标相关的注册表条目。",
  "Skip known unused card bundles. Keep unknown and shared modules. Reload after changes.": "跳过已知未使用的卡片文件，保留不确定用途及共享的模块。修改后请刷新。",
  "Delay off-screen graphs until the dashboard has loaded. Scrolling to a graph loads it immediately.": "等仪表盘加载完成后再加载屏幕外的图表。滚动到图表时立即加载。",
  "Choose which dashboards you want to filter.": "选择需要筛选的仪表盘。",
  "Choose which accounts receive filtered data while viewing selected dashboards.": "选择哪些账户在查看所选仪表盘时接收筛选后的数据。",
  "Entity and registry feeds follow the selected dashboard scope, including its dialogs.": "实体和注册表订阅遵循所选仪表盘范围，包括在仪表盘中打开的对话框。",
  "Version: {version}": "版本：{version}",
  "Warnings and checks ({count})": "警告与检查（{count}）",
  "No warnings": "没有警告",
  "Warning": "警告",
  "Check": "检查",
  "Affected items ({count})": "相关项目（{count}）",
  "Entity filtering is unavailable": "实体筛选无法使用",
  "Home Assistant is handling entity updates normally. Check Loona diagnostics for the failed capability probe, then reload Loona and your browser.": "Home Assistant 正在正常处理实体更新。请在 Loona 诊断信息中查看未通过的兼容性检测，然后重新加载 Loona 并刷新浏览器。",
  "Dashboard detection is unavailable": "无法识别当前仪表盘",
  "Initial load filtering is limited": "首次加载筛选受限",
  "Some pages start with full data. Loona filters after dashboard detection. Check diagnostics for the failed startup probe.": "部分页面启动时会接收完整数据。识别当前仪表盘后 Loona 会开始筛选。请查看诊断信息中未通过的启动检测。",
  "Loona cannot identify the active dashboard, so filtering is bypassed. Reload Loona and refresh the browser. If this continues, check diagnostics.": "Loona 无法识别当前仪表盘，因此已跳过筛选。请重新加载 Loona 并刷新浏览器。如果问题持续，请查看诊断信息。",
  "Registry filtering is unavailable": "注册表筛选无法使用",
  "Home Assistant is sending normal entity and device information. Check Loona diagnostics for a compatibility problem, then reload Loona.": "Home Assistant 正在发送正常的实体和设备信息。请查看 Loona 诊断信息中的兼容性问题，然后重新加载 Loona。",
  "Loading optimizations are unavailable": "加载优化无法使用",
  "Graphs and animations use normal Home Assistant behavior. Check Loona diagnostics for the failed capability probe.": "图表和动画使用 Home Assistant 的标准行为。请在 Loona 诊断信息中查看未通过的兼容性检测。",
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
  "Loona cannot fully inspect every custom card. If card data is missing, add the needed entities under Entity rules.": "Loona 无法完整分析所有自定义卡片。如果卡片缺少数据，请在“实体规则”中添加所需实体。",
  "Some card files could not be identified": "无法识别部分卡片文件",
  "Check the required files under Cards if a card or icon is missing. You can turn off Resource filtering and refresh the browser to compare.": "如果卡片或图标缺失，请在“卡片”中检查所需文件。可以关闭资源筛选并刷新浏览器进行比较。",
  "Templates may load additional files": "模板可能加载其他文件",
  "Resource filtering is bypassed while templates or strategies can generate additional cards.": "模板或策略可能生成更多卡片时，资源筛选会跳过筛选并加载全部文件。",
  "Unchecked files have unknown usage": "未勾选文件的用途不确定",
  "These files are skipped by Resource filtering. If a card, icon or helper is missing, select the needed files under Cards and refresh the browser.": "资源筛选会跳过这些文件。如果卡片、图标或辅助功能缺失，请在“卡片”中勾选所需文件并刷新浏览器。",
  "Saved card files are no longer registered": "已保存的卡片文件不再注册",
  "Remove unavailable saved files under Cards, or restore their Home Assistant resource registrations if you still need them.": "请在“卡片”中移除不可用的已保存文件；如果仍需使用，请恢复它们在 Home Assistant 中的资源注册。",
  "Enable Loona to change other settings.": "请启用 Loona 后修改其他设置。",
  "Show statistics charts": "显示统计图表",
  "Charts refresh with statistics. This choice is saved for this account in this browser.": "图表随统计数据一起刷新。此选项按账户保存在当前浏览器中。",
  "Filtered update feeds": "已筛选的更新订阅",
  "{filtered} of {total} update feeds filtered": "{total} 个更新订阅中已筛选 {filtered} 个",
  "Accent color shows the filtered share.": "主题强调色表示已筛选的比例。",
  "No visible warnings": "没有未隐藏的警告",
  "No updates counted in this interval": "本时段未记录更新",
  "Dismiss": "隐藏",
  "Show dismissed warnings ({count})": "显示已隐藏的警告（{count}）",
  "Dismissals apply to this account in this browser. Changed warnings appear again.": "隐藏记录仅适用于当前浏览器中的此账户。警告内容变化后会重新显示。",
  "Loaded card: {card}; integration: {integration}. Reload this dashboard to finish the upgrade.": "已加载卡片：{card}；集成：{integration}。请重新加载仪表盘以完成升级。",
  "Reload dashboard": "重新加载仪表盘",
  "Sent: {sent} updates/s; filtered: {filtered} updates/s": "已发送：{sent} 次更新/秒；已筛选：{filtered} 次更新/秒",
  "{percent}% of counted updates filtered": "已筛选记录更新的 {percent}%",
  "{count} sent updates": "已发送 {count} 次更新",
  "Preload tab card files": "预加载标签页卡片文件",
  "Pause off-screen animations": "暂停屏幕外动画",
  "Idle mode": "空闲模式",
  "Idle timing": "空闲时间设置",
  "Idle after (minutes)": "进入空闲前的分钟数",
  "Idle refresh (seconds)": "空闲刷新间隔（秒）",
  "Load this tab's card files first, then the remaining modules. Unknown tab routes use the whole dashboard. Navigation, dialogs and editing load pending files immediately. Reload after enabling.": "优先加载当前标签页的卡片文件，再加载其余模块。无法确定标签页时使用整个仪表盘。导航、对话框和编辑会立即加载等待中的文件。启用后刷新页面。",
  "Fetch and compile verified tab modules early. Home Assistant still loads them normally. Reload after enabling.": "提前获取并编译已确认的标签页模块，由 Home Assistant 正常加载。启用后刷新页面。",
  "Pause repeating animations outside the viewport and resume them when visible. Loading indicators and finite transitions keep running.": "暂停视口外的循环动画，进入视口时恢复。加载指示器和有限过渡动画继续运行。",
  "Pause live entity updates after inactivity. Interaction restores fresh values immediately. Requires Entity filtering. Independent clocks, cameras and card timers may continue.": "无交互后暂停实体实时更新，交互时立即恢复最新值。需要启用实体筛选。独立时钟、相机及卡片计时器可能继续运行。",
  "Selected dashboards enter idle mode after no touch, mouse, keyboard or scrolling. Refresh at the chosen interval; 0 pauses until interaction. Navigation, dialogs and editing restore live updates.": "所选仪表盘在无触摸、鼠标、键盘或滚动交互后进入空闲模式。按所选间隔刷新；0 表示暂停直到交互。导航、对话框和编辑会恢复实时更新。",
  "0 pauses until interaction. Otherwise refresh every 1 to 60 seconds; default 60.": "0 表示暂停直到交互。其他值表示每隔 1 至 60 秒刷新，默认为 60 秒。",
  "Help: {section}": "帮助：{section}",
  "Live updates": "实时更新",
  "Totals and entity scope": "总计与实体范围",
  "Rescan checks dashboard changes now.": "立即检查仪表盘变化。",
  "Reset clears live counters and page-load records; entity counts and recorded history stay unchanged.": "清零实时计数并清除页面加载记录，不影响实体数量或已记录的历史数据。",
  "Charts show up to 15 minutes of completed samples. Rate charts share the same scale and refresh with statistics.": "图表显示最多 15 分钟的已完成采样。速率图使用相同纵轴范围，并随统计数据刷新。",
  "{minutes} min history": "{minutes} 分钟历史",
  "No history yet": "暂无历史",
  "No updates": "没有更新",
  "{label}: {rate} updates/s. {history}": "{label}：每秒 {rate} 次更新。{history}"
};

export function cancelConfirmation(host) {
  host._cancelConfirmation?.();
}

export function confirmAction(host, title, message, confirmLabel) {
  if (host._cancelConfirmation) return Promise.resolve(false);
  const dialog = document.createElement("dialog");
  if (typeof dialog.showModal !== "function") return Promise.resolve(window.confirm(text(host._hass, title) + "\n\n" + text(host._hass, message)));
  dialog.setAttribute("aria-labelledby", "loona-confirm-title");
  dialog.setAttribute("aria-describedby", "loona-confirm-message");
  const style = document.createElement("style");
  style.textContent = `dialog { box-sizing:border-box; width:calc(100% - 32px); max-width:480px;
    max-height:calc(100% - 32px); overflow:auto; padding:24px; border:1px solid var(--divider-color);
    border-radius:var(--ha-border-radius,12px); background:var(--card-background-color); color:var(--primary-text-color); }
    dialog::backdrop { background:rgba(0,0,0,.45); }
    dialog h2 { margin:0 0 16px; font-size:1.25rem; } dialog p { margin:0; line-height:1.5; }
    dialog .actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:8px; margin-top:24px; }
    dialog button { font:inherit; min-height:44px; padding:8px 16px; border:0; border-radius:var(--ha-border-radius,8px);
      background:transparent; color:var(--primary-color); cursor:pointer; }
    dialog button:hover { background:var(--secondary-background-color); }
    dialog button:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }`;
  const heading = document.createElement("h2"); heading.id = "loona-confirm-title"; heading.textContent = text(host._hass, title); heading.dataset.i18n = title;
  const body = document.createElement("p"); body.id = "loona-confirm-message"; body.textContent = text(host._hass, message); body.dataset.i18n = message;
  const actions = document.createElement("div"); actions.className = "actions";
  const cancel = document.createElement("button"); cancel.textContent = text(host._hass, "Cancel"); cancel.dataset.confirmCancel = ""; cancel.dataset.i18n = "Cancel";
  const confirm = document.createElement("button"); confirm.textContent = text(host._hass, confirmLabel); confirm.dataset.confirmAccept = ""; confirm.dataset.i18n = confirmLabel;
  actions.append(cancel, confirm); dialog.append(style, heading, body, actions); host.shadowRoot.append(dialog);
  const focused = host.shadowRoot.activeElement;
  return new Promise(resolve => {
    const finish = accepted => {
      if (host._cancelConfirmation !== dismiss) return;
      host._cancelConfirmation = undefined;
      dialog.close(); dialog.remove(); focused?.focus(); resolve(accepted);
    };
    const dismiss = () => finish(false);
    host._cancelConfirmation = dismiss;
    cancel.addEventListener("click", dismiss);
    confirm.addEventListener("click", () => finish(true));
    dialog.addEventListener("cancel", event => { event.preventDefault(); dismiss(); });
    dialog.addEventListener("close", dismiss);
    dialog.showModal(); cancel.focus();
  });
}
export function language(hass) {
  return String(hass?.language || hass?.locale?.language || hass?.config?.language || "en");
}
export function text(hass, key, values = {}) {
  const locale = language(hass).toLowerCase();
  const simplified = locale.startsWith("zh") && !/^zh-(hant|tw|hk|mo)/.test(locale);
  const message = simplified ? chinese[key] || key : key;
  return message.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}
export const helpStyles = `
  ha-card { position:relative; }
  .help { display:inline-flex; vertical-align:middle; margin-inline-start:auto; }
  .help-button { display:inline-flex; align-items:center; justify-content:center; min-width:44px; height:44px; padding:8px; flex-shrink:0; }
  .help-button svg { width:20px; height:20px; }
  .help-text { position:fixed; z-index:1000; box-sizing:border-box; width:320px; max-width:calc(100vw - 32px);
    max-height:calc(100vh - 32px); overflow:auto; padding:16px; border:1px solid var(--divider-color);
    border-radius:var(--ha-border-radius,8px); background:var(--card-background-color); color:var(--primary-text-color);
    font-family:inherit; font-size:14px; font-weight:400; line-height:1.5; text-align:start; white-space:normal; }
  .section-heading { display:flex; align-items:center; justify-content:space-between; gap:8px; }
  .section-heading h2 { flex:1; min-width:0; }
  summary.section-heading,summary.section-summary { display:list-item; line-height:44px; }
  summary .help { float:right; float:inline-end; }
  .action-help { display:inline-flex; align-items:center; }
`;
let helpSequence = 0, activeHelp;
export function closeHelp(root) {
  if (!root || activeHelp?.root.getRootNode() === root) activeHelp?.close();
}
export function createHelp(hass, section, message, id) {
  const root=document.createElement("span"); root.className="help";
  const button=document.createElement("button"); button.type="button"; button.className="help-button"; button.dataset.helpSection=section;
  button.setAttribute("aria-label",text(hass,"Help: {section}",{section:text(hass,section)}));
  button.setAttribute("aria-expanded","false");
  button.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="16.5" r=".8" fill="currentColor"/></svg>';
  const body=document.createElement("span"); body.className="help-text"; body.id=id || "loona-help-"+(++helpSequence); body.setAttribute("role","tooltip"); body.hidden=true;
  body.textContent=text(hass,message); if (message) body.dataset.i18n=message;
  button.setAttribute("aria-describedby",body.id); root.append(button,body);
  let leaveTimer;
  const close=()=>{
    window.clearTimeout(leaveTimer);
    body.hidden=true; button.setAttribute("aria-expanded","false");
    document.removeEventListener("pointerdown",outside); document.removeEventListener("keydown",escape);
    window.removeEventListener("resize",close); window.removeEventListener("scroll",close,true);
    if (activeHelp?.root===root) activeHelp=undefined;
  };
  const outside=event=>{ if (!event.composedPath().includes(root)) close(); };
  const escape=event=>{ if (event.key==="Escape") { event.preventDefault(); event.stopPropagation(); close(); } };
  const open=pinned=>{
    if (activeHelp?.root!==root) activeHelp?.close();
    activeHelp={root,close,pinned}; body.hidden=false; button.setAttribute("aria-expanded","true");
    const bounds=button.getBoundingClientRect(), width=Math.min(320,window.innerWidth-32);
    body.style.left=Math.max(16,Math.min(bounds.right-width,window.innerWidth-width-16))+"px";
    body.style.top="16px";
    const height=body.getBoundingClientRect().height;
    body.style.top=Math.max(16,bounds.bottom+height+8<=window.innerHeight-16 ? bounds.bottom+8 : bounds.top-height-8)+"px";
    document.addEventListener("pointerdown",outside); document.addEventListener("keydown",escape);
    window.addEventListener("resize",close); window.addEventListener("scroll",close,true);
  };
  button.addEventListener("pointerenter",()=>{ if (!activeHelp?.pinned) open(false); });
  button.addEventListener("focus",()=>{ if (activeHelp?.root!==root) open(false); });
  button.addEventListener("click",event=>{
    event.preventDefault(); event.stopPropagation();
    if (activeHelp?.root===root && activeHelp.pinned) close(); else open(true);
  });
  root.addEventListener("pointerenter",()=>window.clearTimeout(leaveTimer));
  root.addEventListener("pointerleave",()=>{ if (activeHelp?.root===root && !activeHelp.pinned && root.getRootNode().activeElement!==button) leaveTimer=window.setTimeout(close,150); });
  button.addEventListener("blur",()=>{ if (activeHelp?.root===root && !activeHelp.pinned) close(); });
  return root;
}
export function translate(root, hass) {
  root.querySelectorAll("[data-help-section]").forEach(button=>button.setAttribute("aria-label",text(hass,"Help: {section}",{section:text(hass,button.dataset.helpSection)})));
  root.querySelectorAll("[data-i18n]").forEach(element => { element.textContent = text(hass, element.dataset.i18n); });
  root.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
    element.placeholder = text(hass, element.dataset.i18nPlaceholder);
  });
}

const notices = {
  "bootstrap_compatibility": ["Initial load filtering is limited", "Some pages start with full data. Loona filters after dashboard detection. Check diagnostics for the failed startup probe."],
  "graph_frontend_compatibility": [
    "Loading optimizations are unavailable in this browser",
    "Graphs and animations use normal Home Assistant behavior. Other Loona filters remain available."
  ],
  "entity_compatibility": [
    "Entity filtering is unavailable",
    "Home Assistant is handling entity updates normally. Check Loona diagnostics for the failed capability probe, then reload Loona and your browser."
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
    "Graphs and animations use normal Home Assistant behavior. Check Loona diagnostics for the failed capability probe."
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
  "resource_scan": [
    "Resource scan is incomplete",
    "Home Assistant is loading all registered files. Check the Home Assistant log for the failed dashboard or resource load, then rescan. Loona retries automatically."
  ],
  "resource_loading_failure": [
    "Some card files did not load",
    "Reload the browser to retry. If this continues, turn off Delay card files and check the files under Cards."
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
    "Loona cannot fully inspect every custom card. If card data is missing, add the needed entities under Entity rules."
  ],
  "unmatched_resources": [
    "Some card files could not be identified",
    "Check the required files under Cards if a card or icon is missing. You can turn off Resource filtering and refresh the browser to compare."
  ],
  "dynamic_resources": [
    "Templates may load additional files",
    "Resource filtering is bypassed while templates or strategies can generate additional cards."
  ],
  "unchecked_resources": [
    "Unchecked files have unknown usage",
    "These files are skipped by Resource filtering. If a card, icon or helper is missing, select the needed files under Cards and refresh the browser."
  ],
  "stale_resources": [
    "Saved card files are no longer registered",
    "Remove unavailable saved files under Cards, or restore their Home Assistant resource registrations if you still need them."
  ]
};

const localPreferences = new Map();
function preferenceKey(hass) { return "loona-card-preferences:" + hass?.user?.id; }
export function cardPreferences(hass) {
  const key = preferenceKey(hass);
  try {
    const stored = JSON.parse(window.localStorage.getItem(key) || "null");
    if (stored && typeof stored === "object" && !Array.isArray(stored)) {
      localPreferences.set(key, stored); return stored;
    }
  } catch { /* Private browsing may block persistent storage. */ }
  return localPreferences.get(key) || {};
}
export function saveCardPreferences(hass, changes, reset = false, notify = true) {
  if (!hass?.user?.is_admin) return;
  const key = preferenceKey(hass);
  const values = reset ? {} : {...cardPreferences(hass), ...changes};
  localPreferences.set(key, values);
  try { window.localStorage.setItem(key, JSON.stringify(values)); } catch { /* Keep session preferences. */ }
  if (notify) window.dispatchEvent(new Event("loona-card-preferences"));
}
function noticeFingerprint(item) {
  // Two independent hashes avoid storing affected entity IDs in browser preferences.
  const value = JSON.stringify([item.code, item.severity, [...(item.items || [])].sort()]);
  let first = 2166136261, second = 5381;
  for (let index = 0; index < value.length; index++) {
    first = Math.imul(first ^ value.charCodeAt(index), 16777619);
    second = Math.imul(second, 33) ^ value.charCodeAt(index);
  }
  return (first >>> 0).toString(16) + ":" + (second >>> 0).toString(16);
}
export function renderVersion(root, hass, version, cardVersion, blocked = false) {
  root.replaceChildren();
  if (version === cardVersion) { root.textContent = text(hass, "Version: {version}", {version}); return; }
  const message = document.createElement("span");
  message.textContent = text(hass, "Loaded card: {card}; integration: {integration}. Reload this dashboard to finish the upgrade.", {card:cardVersion, integration:version});
  const reload = document.createElement("button"); reload.textContent = text(hass, "Reload dashboard"); reload.disabled = blocked;
  reload.addEventListener("click", () => window.location.reload()); root.append(message, reload);
}
export function renderNotices(root, hass, items, labels = {}) {
  const source = items;
  if (window.__loonaResourceLoading?.failed) items = [...items, {code:"resource_loading_failure", severity:"warning"}];
  if (window.__loonaGraphCapability?.status === "unavailable" && window.__loonaGraphCapability.enabled) {
    items = [...items, {code:"graph_frontend_compatibility", severity:"warning"}];
  }
  items = items.filter(item => notices[item.code]);
  const preferences = cardPreferences(hass);
  const legacy = new Set(Array.isArray(preferences.dismissed) ? preferences.dismissed : []);
  const dismissed = new Set(Array.isArray(preferences.dismissedCodes) ? preferences.dismissedCodes : []);
  let migrated=false;
  for (const item of items) if (!dismissed.has(item.code) && legacy.has(noticeFingerprint(item))) { dismissed.add(item.code); migrated=true; }
  if (migrated) saveCardPreferences(hass,{dismissedCodes:[...dismissed]},false,false);
  const visible = items.filter(item => !dismissed.has(item.code));
  const open = root.querySelector("details")?.open;
  root.replaceChildren();
  if (visible.length) {
    const section=document.createElement("details"); section.className="loona-notices"; section.open=Boolean(open);
    const summary=document.createElement("summary"); summary.textContent=text(hass,"Warnings and checks ({count})",{count:visible.length}); section.append(summary);
    const list=document.createElement("ul");
    for (const item of visible) {
      const message=notices[item.code];
      const row=document.createElement("li"); row.dataset.notice=item.code;
      const title=document.createElement("h3"); title.textContent=text(hass,item.severity === "warning" ? "Warning" : "Check")+": "+text(hass,message[0]);
      const body=document.createElement("p"); body.textContent=text(hass,message[1]); row.append(title,body);
      if (item.items?.length) {
        const details=document.createElement("details"); const heading=document.createElement("summary");
        heading.textContent=text(hass,"Affected items ({count})",{count:item.items.length});
        const values=document.createElement("div"); values.className="notice-items";
        for (const value of item.items) {
          const line=document.createElement("p"); const label=labels[value] || hass?.states?.[value]?.attributes?.friendly_name;
          if (label && label !== value) {
            const name=document.createElement("span"); name.textContent=label;
            const id=document.createElement("small"); id.textContent=value; line.append(name,id);
          } else line.textContent=value;
          values.append(line);
        }
        details.append(heading,values); row.append(details);
      }
      const dismiss=document.createElement("button"); dismiss.textContent=text(hass,"Dismiss"); dismiss.dataset.dismiss=item.code;
      dismiss.setAttribute("aria-label",text(hass,"Dismiss")+": "+text(hass,message[0]));
      dismiss.addEventListener("click", () => {
        const latest=cardPreferences(hass);
        const previous=Array.isArray(latest.dismissedCodes) ? latest.dismissedCodes : [];
        saveCardPreferences(hass,{dismissedCodes:[...new Set([...previous,item.code])].filter(code=>notices[code])});
        renderNotices(root,hass,source,labels);
        root.querySelector("summary,button")?.focus();
      });
      row.append(dismiss); list.append(row);
    }
    section.append(list); root.append(section);
  }
}

export function setText(element, value) {
  if (element.textContent !== value) element.textContent = value;
}
export function formatNumber(hass, value, options = {}) {
  const format = hass?.locale?.number_format;
  const locales = {comma_decimal:"en-US", decimal_comma:"de-DE", space_comma:"fr-FR", quote_decimal:"de-CH"};
  const locale = locales[format] || (format === "system" ? undefined : language(hass));
  return Number(value).toLocaleString(locale, {...options, ...(format === "none" ? {useGrouping:false} : {})});
}
export function formatDateTime(hass, value) {
  const locale = hass?.locale || {};
  const date = new Date(value);
  const zone = locale.time_zone === "server" && hass?.config?.time_zone ? {timeZone:hass.config.time_zone} : {};
  const formatter = new Intl.DateTimeFormat(locale.date_format === "system" ? undefined : language(hass), {year:"numeric", month:"numeric", day:"numeric", ...zone});
  let day = formatter.format(date);
  const order = {DMY:["day","month","year"], MDY:["month","day","year"], YMD:["year","month","day"]}[locale.date_format];
  if (order) {
    const parts = formatter.formatToParts(date);
    const separator = parts.find(part => part.type === "literal")?.value || "/";
    const last = parts[parts.length - 1];
    const suffix = last?.type === "literal" && !(language(hass) === "bg" && locale.date_format === "YMD") ? last.value : "";
    day = order.map(type => parts.find(part => part.type === type)?.value).join(separator) + suffix;
  }
  const options = {hour:locale.time_format === "24" ? "2-digit" : "numeric", minute:"2-digit", second:"2-digit", ...zone};
  if (locale.time_format === "12" || locale.time_format === "24") options.hourCycle = locale.time_format === "12" ? "h12" : "h23";
  return `${day}, ${date.toLocaleTimeString(language(hass), options)}`;
}
