/* Shared English/Simplified Chinese messages for Loona cards. */
const chinese = {
  "Measurements": "测量读数",
  "Measurement": "测量项目",
  "Setting": "设置项",
  "Value": "数值",
  "Dashboard": "仪表盘",
  "Tab": "标签页",
  "Completed": "完成时间",
  "Method": "测量方式",
  "Pass": "轮次",
  "Mode": "模式",
  "Ready (s)": "就绪（秒）",
  "Data (KB)": "数据（KB）",
  "Updates": "更新次数",
  "Blocking (ms)": "阻塞（毫秒）",
  "Right-click the image above and choose Copy Image. On a touch screen, touch and hold it.": "右键点击上方图片并选择复制图片。使用触屏时，请长按图片。",

  "Detailed report": "详细报告",
  "Executive summary": "结果摘要",
  "Test details": "测试信息",
  "Interpretation and next steps": "结果说明与下一步",
  "Individual passes": "各轮读数",
  "Measurement limits": "测量范围",
  "Start over to run a new comparison.": "点击重新开始以运行新的比较。",
  "{percent}% less data": "数据减少 {percent}%",
  "{percent}% more data": "数据增加 {percent}%",
  "{percent}% less file data": "文件数据减少 {percent}%",
  "{percent}% more file data": "文件数据增加 {percent}%",
  "{percent}% fewer updates": "更新减少 {percent}%",
  "{percent}% more updates": "更新增加 {percent}%",
  "More observed with Loona": "Loona 模式下观测值更高",
  "Less time observed": "观测耗时更少",
  "More time observed": "观测耗时更多",
  "No clear timing difference": "未测得明确时间差异",
  "Not supported in this browser": "此浏览器不支持",
  "{label}: {status}. Native HA: {native}; Loona: {loona}.": "{label}：{status}。原生 HA：{native}；Loona：{loona}。",
  "Dashboard: {dashboard}; tab: {view}": "仪表盘：{dashboard}；标签页：{view}",
  "Completed: {date}": "完成时间：{date}",
  "The loading or blocking times are similar or overlap across passes. This does not indicate an interrupted test. Data savings can still be measured without a proven speed improvement.": "各轮加载或阻塞时间相近或范围重叠，这不代表测试被中断。即使未证明速度提升，仍可测得数据节省。",
  "This browser does not expose Long Animation Frames. Blocking is unavailable; the other comparisons remain valid. Use a browser supporting this API to measure blocking.": "此浏览器不提供 Long Animation Frames，无法测量阻塞；其他比较仍有效。如需测量阻塞，请使用支持该 API 的浏览器。",
  "Some servers hide file sizes. File counts are still available; use the browser Network panel to inspect sizes.": "部分服务器隐藏文件大小。文件数量仍可查看；请使用浏览器网络面板检查大小。",
  "Fewer than three valid readings are available. Resolve the issues below and repeat the test.": "有效读数不足三轮。请解决下方问题后重测。",
  "To inspect individual card files, open Settings > Dashboards > Resources, or filter the browser Network panel to JavaScript and reload. The comparison above reports totals without repeating files for every pass.": "如需检查单个卡片文件，请打开设置 > 仪表盘 > 资源，或在浏览器网络面板中筛选 JavaScript 后刷新。上方比较只报告总量，不重复列出每轮文件。",
  "Entities to include": "包含的实体",
  "Entities to exclude": "排除的实体",
  "Ready: {ready}s; data: {data} KB; files: {files}; updates: {updates}; blocking: {blocking} ms.": "就绪：{ready} 秒；数据：{data} KB；文件：{files} 个；更新：{updates} 次；阻塞：{blocking} 毫秒。",
  "Copy text": "复制文本",
  "Save text": "保存文本",
  "Text copied.": "已复制文本。",
  "Could not copy the text. Save the text instead.": "无法复制文本。请改为保存文本。",
  "Copy image": "复制图片",
  "Right-click the image and choose Copy Image. On a touch screen, touch and hold the image.": "右键点击图片并选择复制图片。使用触屏时，请长按图片。",

  "Loona benchmark": "Loona 基准测试",
  "Benchmark interrupted": "基准测试已中断",
  "No valid comparison was completed.": "未完成有效比较。",
  "See the detailed report for recovery steps.": "请在详细报告中查看恢复步骤。",
  "Benchmark this dashboard": "测试当前仪表盘",
  "Benchmark Results": "基准测试结果",
  "Some results are inconclusive": "部分结果尚不确定",
  "Native HA and current Loona settings": "原生 HA 与当前 Loona 设置",
  "Visible cards ready": "可见卡片就绪",
  "Initial dashboard data": "仪表盘初始数据",
  "Card files loaded": "已加载卡片文件",
  "Browser blocking": "浏览器阻塞",
  "s": "秒",
  "ms": "毫秒",
  "{count} card files": "{count} 个卡片文件",
  "Comparison available": "可进行比较",
  "Incomplete measurement": "测量不完整",
  "No updates observed": "未观察到更新",
  "No measurable change": "未测得明显变化",
  "Inconclusive": "结果不确定",
  "{pairs} pairs · {seconds}s observation · cached reloads": "{pairs} 组 · 观察 {seconds} 秒 · 使用缓存刷新",
  "Visible cards did not become ready in time. Put the benchmark card near the top, keep another card visible, fix loading cards and start over.": "可见卡片未能及时就绪。请将测试卡片放在顶部附近，保持另一张卡片可见，修复未完成加载的卡片后重新开始。",
  "A visible card reported an error. Fix that card and start over.": "可见卡片发生错误。请修复该卡片后重新开始。",
  "A card file failed to load. Check dashboard resources and the connection, then start over.": "卡片文件加载失败。请检查仪表盘资源及网络连接后重新开始。",
  "The observer reached its limit. Try a smaller tab with fewer cards and start over.": "观察器已达到上限。请使用卡片较少的标签页重新开始。",
  "Detailed report (may contain private information)": "详细报告（可能包含私人信息）",
  "What will be measured": "测量内容",
  "Paused. Return to this page to repeat this pass.": "已暂停。返回当前页面后将重测本轮。",
  "Observing": "正在观察",
  "Saving pass": "正在保存本轮",
  "Loading dashboard": "正在加载仪表盘",
  "Pass {pass} of {total}": "第 {pass} 轮，共 {total} 轮",
  "Cancel benchmark": "取消基准测试",
  "Sign in as an administrator to benchmark this dashboard.": "请使用管理员账户登录以测试此仪表盘。",
  "Copy": "复制",
  "Start over": "重新开始",
  "Remove": "移除",
  "Go": "开始",
  "Clipboard copying needs a secure browser connection. Save the PNG instead.": "复制到剪贴板需要安全的浏览器连接。请改为保存 PNG。",
  "Compare native Home Assistant with your saved Loona settings on this tab. About 4 minutes, with automatic page reloads.": "比较此标签页上的原生 Home Assistant 与已保存的 Loona 设置。约需 4 分钟，期间页面会自动刷新。",
  "Keep this page in the foreground without touching, scrolling or resizing it. Put this card near the top with another card visible.": "请保持此页面在前台，不触摸、不滚动、不调整窗口大小。将此卡片放在顶部附近，并保持另一张卡片可见。",
  "Reloads use the browser cache. This is not a cold-cache or hard-refresh test.": "刷新会使用浏览器缓存。本测试不测量无缓存加载或强制刷新。",
  "Readiness means known visible cards have mounted and loading indicators have settled. Cameras, charts and custom content may still be loading.": "就绪表示已知的可见卡片已挂载，加载指示器已停止。摄像头、图表或自定义内容可能仍在加载。",
  "JSON sizes are logical UTF-8 message sizes, before network compression. Card file sizes are decoded content sizes when the browser exposes them.": "JSON 大小是网络压缩前的 UTF-8 逻辑消息大小。卡片文件大小是浏览器可提供的解码后内容大小。",
  "Browser blocking uses Long Animation Frames. It does not measure total CPU, GPU, memory, battery or all response delays.": "浏览器阻塞使用 Long Animation Frames 测量，不代表总 CPU、GPU、内存、电池消耗或全部响应延迟。",
  "Each mode gets a warm-up, then three alternating pairs. Live activity can differ between passes. Overlapping timing ranges are inconclusive.": "两种模式先分别预热，再交替进行三组比较。各轮实时活动可能不同。时间范围重叠时，结果不确定。",
  "Idle savings appear only if the configured idle threshold is reached. This test does not isolate the benefit of each setting.": "只有达到设置的空闲阈值时，才能看到空闲模式节省。本测试不单独衡量每项设置的效果。",
  "A required reading is unavailable. Check the per-pass issues below. For blocking measurements use a browser that supports Long Animation Frames; file sizes may be hidden by cross-origin servers.": "缺少必要读数。请检查下方各轮问题。测量阻塞需使用支持 Long Animation Frames 的浏览器；跨域服务器可能隐藏文件大小。",
  "Timing ranges overlap. Close other busy applications, keep the same viewport and repeat the test.": "时间范围重叠。请关闭其他繁忙应用，保持相同窗口大小后重测。",
  "No live updates were observed. Repeat while the dashboard entities are changing.": "未观察到实时更新。请在仪表盘实体发生变化时重测。",
  "Saved settings": "已保存的设置",
  "Disabled": "禁用",
  "{key}: {value}": "{key}：{value}",
  "Warm-up (excluded)": "预热（不计入结果）",
  "Ready: {ready}s; observation: {duration}s; initial entities: {entities}; initial JSON: {initial} KB; registry JSON: {registry} KB; live updates: {updates} ({bytes} KB).": "就绪：{ready} 秒；观察：{duration} 秒；初始实体：{entities}；初始 JSON：{initial} KB；注册表 JSON：{registry} KB；实时更新：{updates} 次（{bytes} KB）。",
  "Startup blocking: {startup} ms; observation blocking: {live} ms; long frames: {frames}.": "启动阻塞：{startup} 毫秒；观察期间阻塞：{live} 毫秒；长帧：{frames}。",
  "Browser: {browser}; viewport: {width} x {height}": "浏览器：{browser}；窗口：{width} x {height}",
  "{source}: {bytes} KB ({phase}, {cache})": "{source}：{bytes} KB（{phase}，{cache}）",
  "Cached": "已缓存",
  "Downloaded": "已下载",
  "{source} ({phase}): {ms} ms": "{source}（{phase}）：{ms} 毫秒",
  "Keep the benchmark tab visible before starting.": "开始前请保持测试标签页可见。",
  "Benchmark could not start. Refresh and try again.": "无法开始基准测试。请刷新后重试。",
  "Remove benchmark card?": "移除基准测试卡片？",
  "Remove this benchmark card from this tab? Saved PNGs are kept.": "从当前标签页移除此基准测试卡片？已保存的 PNG 将保留。",
  "Remove this card manually in the dashboard editor or YAML source.": "请在仪表盘编辑器或 YAML 源码中手动移除此卡片。",
  "PNG copied.": "已复制 PNG。",
  "Could not copy the PNG. Save it instead.": "无法复制 PNG。请改为保存。",
  "PNG export failed. Start over and try again.": "PNG 导出失败。请重新开始后重试。",
  "Close": "关闭",
  "Benchmark complete. Results are ready.": "基准测试已完成，结果已就绪。",
  "Show results": "查看结果",

  "{source} ({phase}): {ms} ms, including {layout} ms re-measuring the page": "{source}（{phase}）：{ms} 毫秒，其中 {layout} 毫秒用于重新计算页面布局",
  "before measuring": "测量开始前",
  "while measuring": "测量期间",
  "Browser performance": "浏览器性能",
  "These readings come from this browser and dashboard only. Slow frames show only part of the work your browser does. Items marked 'before measuring' happened before Loona started watching.": "这些数据仅来自当前浏览器和仪表盘。卡顿帧只反映浏览器工作量的一部分。标记为“测量开始前”的项目发生在 Loona 开始观察之前。",
  "Measure this dashboard for 30 seconds": "测量当前仪表盘 30 秒",
  "Entities sending the most updates since reset": "重置后发送更新最多的实体",
  "Only the busiest entities are listed. {count} more updates came from entities not shown.": "仅列出更新最多的实体。另有 {count} 次更新来自未列出的实体。",
  "Measuring. Keep this dashboard open.": "正在测量，请保持当前仪表盘打开。",
  "Measurement saved.": "测量结果已保存。",
  "Measurement failed. Refresh and keep the dashboard open.": "测量失败，请刷新并保持仪表盘打开。",
  "Slow frames: {count}, adding up to {ms} ms of delay": "卡顿帧：{count} 个，累计延迟 {ms} 毫秒",
  "This browser can't report slow frames.": "此浏览器无法统计卡顿帧。",
  "This dashboard listens to all Home Assistant events, which can bypass entity filtering.": "此仪表盘监听了 Home Assistant 的全部事件，可能绕过实体筛选。",
  "Faster loading is not available in this browser": "此浏览器无法使用加快加载的功能",
  "Graphs and animations load the normal way. Loona's other filters still work.": "图表和动画将按 Home Assistant 的常规方式加载。Loona 的其他筛选功能仍可使用。",
  "Graph loading": "图表正在加载",
  "Card file scan is incomplete": "卡片文件扫描不完整",
  "Home Assistant is loading all card files for now. Check the Home Assistant log for a dashboard or file that failed to load, then rescan. Loona keeps retrying on its own.": "目前 Home Assistant 会加载全部卡片文件。请在 Home Assistant 日志中查看加载失败的仪表盘或文件，然后重新扫描。Loona 会自动重试。",
  "Dashboards": "仪表盘",
  "Apply filtering to": "筛选哪些账户",
  "Accounts": "账户",
  "Selected accounts": "指定账户",
  "All accounts": "所有账户",
  "Loona settings": "Loona 设置",
  "Filters and performance": "筛选与性能",
  "Entity filtering": "实体筛选",
  "Live updates for current tab only": "仅实时更新当前标签页",
  "After the page loads, only send live changes for the tab you're viewing, plus your Entity rules. Other tabs show their last known values until you open them. Pop-ups and editing temporarily update everything. Needs Entity filtering.": "页面加载后，只实时更新你正在查看的标签页和“实体规则”中的实体。其他标签页在打开前显示最近一次的值。弹窗和编辑时会临时更新全部内容。需要启用实体筛选。",
  "Device and area filtering": "设备与区域筛选",
  "Pause animations during loading": "加载期间暂停动画",
  "Skip unused card files": "跳过未使用的卡片文件",
  "Load current tab first": "优先加载当前标签页",
  "Some card files did not load": "部分卡片文件未能加载",
  "Refresh your browser to try again. If it keeps happening, turn off Load current tab first and check the files under Card files.": "请刷新浏览器重试。如果问题持续，请关闭“优先加载当前标签页”，并在“卡片文件”中检查文件。",
  "Load this dashboard's card files first, then the remaining modules. Navigation and editing load pending files immediately. Reload after enabling.": "优先加载当前仪表盘的卡片文件，再加载其余模块。导航或编辑时立即加载等待中的文件。启用后请刷新页面。",
  "Extra card files to load": "额外加载的卡片文件",
  "Enabled": "启用",
  "Rescan dashboards": "重新扫描仪表盘",
  "Reset live statistics": "重置实时统计",
  "Restore defaults": "恢复默认设置",
  "Restore defaults?": "恢复默认设置？",
  "Reset live statistics?": "重置实时统计？",
  "Remove the Loona dashboard?": "删除 Loona 仪表盘？",
  "This resets every Loona setting and the live statistics, clears your dashboard and account choices, and removes the Loona dashboard that Loona created. Nothing is filtered until you choose dashboards and accounts again. Dashboards you've edited and recorded history are kept.": "这会重置 Loona 的所有设置和实时统计，清除你选择的仪表盘和账户，并删除 Loona 自动创建的仪表盘。重新选择仪表盘和账户之前，不会进行任何筛选。你编辑过的仪表盘和历史记录会保留。",
  "Clear the live counters, page-load records and browser readings? Your settings and recorded history are kept.": "清除实时计数、页面加载记录和浏览器测量数据？你的设置和历史记录会保留。",
  "Remove the Loona dashboard that Loona created, along with its cards? Dashboards you've edited yourself are kept. To get it back, choose Loona dashboard cards again.": "删除 Loona 自动创建的仪表盘及其卡片？你自己编辑过的仪表盘会保留。如需恢复，请重新选择 Loona 仪表盘卡片。",
  "Remove dashboard": "删除仪表盘",
  "Defaults restored. Choose your dashboards and accounts, then reload your browser.": "已恢复默认设置。请选择仪表盘和账户，然后刷新浏览器。",
  "Could not restore defaults. Refresh and check the current settings.": "无法恢复默认设置。请刷新并检查当前设置。",
  "Resets all Loona settings and live statistics. You'll be asked to confirm.": "重置 Loona 的所有设置和实时统计。操作前会要求确认。",
  "Some features are unavailable. See Loona's diagnostics.": "部分功能无法使用。请查看 Loona 诊断信息。",
  "Loona card title must be text": "Loona 卡片标题必须为文本",
  "Loona statistics": "Loona 统计",
  "Loading statistics...": "正在加载统计…",
  "Refresh": "刷新",
  "Sent": "已发送",
  "Filtered out": "已筛掉",
  "Updates filtered out": "已筛掉的更新占比",
  "updates/s": "次更新/秒",
  "of all updates": "占全部更新",
  "Updates sent since reset": "重置后发送的更新",
  "Updates filtered out since reset": "重置后筛掉的更新",
  "Connections filtered / total": "已筛选 / 全部实时连接",
  "Entities currently included": "当前包含的实体",
  "Recent page loads": "最近页面加载",
  "For each dashboard, what was sent the last time its page fully loaded. If Loona recognized the dashboard at startup, only the entities it needs were sent; otherwise everything was. File counts cover the whole page session.": "显示每个仪表盘最近一次完整加载页面时发送的内容。如果 Loona 在启动时识别出仪表盘，只会发送它需要的实体，否则会发送全部实体。文件数量涵盖整个页面会话。",
  "Could not load statistics. Check that Loona is running, then press Refresh.": "无法加载统计。请确认 Loona 正在运行，再点击“刷新”。",
  "Unable to load statistics": "无法加载统计",
  "Could not reset statistics. Try Reset live statistics on the Loona device page.": "无法重置统计。请尝试 Loona 设备页面上的“重置实时统计”按钮。",
  "Dashboard scan incomplete. All entities are being sent.": "仪表盘扫描不完整，正在发送全部实体。",
  "Entity filtering is disabled": "实体筛选已关闭",
  "Entity filtering is active": "实体筛选已启用",
  "Nothing is being filtered yet. Open a selected dashboard with a selected account.": "目前没有任何筛选。请使用所选账户打开一个所选仪表盘。",
  "Measured over the last {seconds} seconds.": "统计时段为最近 {seconds} 秒。",
  "Rates update within {seconds} seconds.": "更新速率将在 {seconds} 秒内显示。",
  "Each update counts once for every live connection, so having several tabs open raises the totals. These numbers aren't a measure of loading speed or network traffic.": "每次更新会按每个实时连接分别计数，因此打开多个标签页会让总数增加。这些数字不代表加载速度或网络流量。",
  "Sign in as an administrator to view Loona statistics.": "请使用管理员账户登录以查看 Loona 统计。",
  "1 entity": "1 个实体",
  "Loona dashboard": "Loona 仪表盘",
  "Loona dashboard cards": "Loona 仪表盘卡片",
  "{count} entities": "{count} 个实体",
  "Counting since {time}": "统计开始于 {time}",
  "Entities sent: {sent} out of {available}": "已发送实体：{available} 个中的 {sent} 个",
  "Card files sent: {sent} out of {available}": "已发送卡片文件：{available} 个中的 {sent} 个",
  "No card file count was recorded for this load.": "本次加载未记录卡片文件数量。",
  "No page loads recorded yet. Reload one of your dashboards.": "尚无页面加载记录。请刷新一个仪表盘。",
  "Live filtering statistics and recent page loads": "实时筛选统计与最近页面加载",
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
  "Card file choices aren't available right now.": "目前无法选择卡片文件。",
  "Search available choices": "搜索可用选项",
  "Selected ({count})": "已选择（{count}）",
  "No selections": "未选择",
  "No matching choices": "没有匹配的选项",
  "Available choices": "可用选项",
  "Show more": "显示更多",
  "Unavailable": "不可用",
  "optional": "可选",
  "Not used by any of your dashboards": "你的仪表盘均未使用",
  "Purpose unknown": "用途不确定",
  "Files Loona always loads ({count})": "始终加载的文件（{count}）",
  "These files are needed by your dashboards or shared styling.": "这些文件用于仪表盘卡片或共享样式。",
  "Card files that no dashboard uses can be skipped. Files Loona can't identify always load. Save, then reload your browser.": "任何仪表盘都没用到的卡片文件可以跳过。Loona 无法确定用途的文件始终加载。保存后请刷新浏览器。",
  "Refresh is unavailable while you have unsaved changes.": "有未保存的修改时无法刷新。",
  "Change filters, dashboards and accounts": "修改筛选、仪表盘和账户",
  "Pause repeating animations while the dashboard loads, then resume them automatically.": "仪表盘加载期间暂停循环动画，之后自动恢复。",
  "Each open dashboard tab keeps a live connection to Home Assistant, sometimes more than one. 'Connections filtered / total' shows how many of them Loona is filtering. 'Estimated entities trimmed' compares the entities Loona keeps with all entities in Home Assistant, even when filtering is off.": "每个打开的仪表盘标签页都会与 Home Assistant 保持一个实时连接，有时不止一个。“已筛选 / 全部实时连接”显示 Loona 正在筛选其中多少个。“估计精简的实体”会将 Loona 保留的实体与 Home Assistant 中的全部实体进行比较，即使筛选已关闭也会显示。",
  "Rescan checks dashboard changes now. Reset clears live counters and page-load records; entity counts and recorded history stay unchanged.": "重新扫描会立即检查仪表盘变化。重置会清零实时计数并清除页面加载记录，不影响实体数量或已记录的历史数据。",
  "Working...": "正在处理…",
  "Dashboards rescanned": "已重新扫描仪表盘",
  "Live statistics reset": "已重置实时统计",
  "Action failed. Check that Loona is running, then try again.": "操作失败。请确认 Loona 正在运行，然后重试。",
  "Estimated entities trimmed": "估计精简的实体",
  "Entity rules": "实体规则",
  "Card files": "卡片文件",
  "Delay graph loading": "延迟加载图表",
  "Included": "包含",
  "Excluded": "排除",
  "Entities": "实体",
  "Entity types": "实体类型",
  "Entities or patterns": "实体或匹配规则",
  "{count} selected": "已选择 {count} 项",
  "Loona finds the entities your dashboards use on its own. Use these rules to add ones it missed or to leave some out. Entity types are groups such as sensor or light. In patterns, * matches anything, like sensor.kitchen_*.": "Loona 会自动找出你的仪表盘用到的实体。可以用这些规则补充它遗漏的实体，或排除一些实体。实体类型是 sensor、light 这样的分组；在匹配规则中，* 可匹配任意内容，例如 sensor.kitchen_*。",
  "Always keep these, even if no dashboard uses them.": "即使没有仪表盘用到，也始终保留这些实体。",
  "Never send these. Exclusions win over inclusions, and cards that use them may show no data. Entities Home Assistant itself needs (people, updates, zones) are always kept.": "不发送这些实体。排除规则优先于包含规则，使用它们的卡片可能没有数据。Home Assistant 自身需要的实体（人员、更新、区域）始终保留。",
  "Turn this off to stop all filtering and send everything as usual. Reload your browser to bring back any skipped card files.": "关闭后，所有筛选都会停止，一切数据将恢复为正常发送。请刷新浏览器以恢复被跳过的卡片文件。",
  "Send only the entities your selected dashboards use, plus anything in Entity rules.": "只发送所选仪表盘用到的实体，以及“实体规则”中的实体。",
  "Also trim the entity, device and area lists Home Assistant loads, so they match your dashboards.": "同时精简 Home Assistant 加载的实体、设备和区域列表，使其与你的仪表盘相符。",
  "Don't load card files that none of your dashboards use. Files Loona can't identify are always kept. Reload your browser after changing this.": "不加载任何仪表盘都没用到的卡片文件。Loona 无法确定用途的文件始终保留。更改后请刷新浏览器。",
  "Wait to load off-screen graphs until the rest of the dashboard is ready. Scrolling to a graph loads it right away.": "等仪表盘其余部分就绪后，再加载屏幕外的图表。滚动到某个图表时会立即加载。",
  "Choose which dashboards you want to filter.": "选择需要筛选的仪表盘。",
  "Choose which accounts get filtered data while viewing the selected dashboards.": "选择哪些账户在查看所选仪表盘时接收筛选后的数据。",
  "Version: {version}": "版本：{version}",
  "Warnings and checks ({count})": "警告与检查（{count}）",
  "No warnings": "没有警告",
  "Warning": "警告",
  "Check": "检查",
  "Affected items ({count})": "相关项目（{count}）",
  "Entity filtering is unavailable": "实体筛选无法使用",
  "Home Assistant is still sending all entity updates as usual. One of Loona's compatibility checks failed. See Loona's diagnostics, then reload Loona and refresh your browser.": "Home Assistant 仍在正常发送全部实体更新。Loona 的一项兼容性检查未通过。请查看 Loona 诊断信息，然后重新加载 Loona 并刷新浏览器。",
  "Loona can't tell which dashboard is open": "Loona 无法识别当前仪表盘",
  "Filtering may start late on some pages": "部分页面可能较晚开始筛选",
  "Some pages load all entities first, and Loona starts filtering once it recognizes the dashboard. A startup check failed. See Loona's diagnostics for details.": "部分页面会先加载全部实体，Loona 识别出仪表盘后才开始筛选。启动检查未通过，详情请查看 Loona 诊断信息。",
  "Filtering is paused because Loona can't identify the dashboard you're viewing. Reload Loona and refresh your browser. If it keeps happening, see Loona's diagnostics.": "由于 Loona 无法识别你正在查看的仪表盘，筛选已暂停。请重新加载 Loona 并刷新浏览器。如果问题持续，请查看 Loona 诊断信息。",
  "Device and area filtering is unavailable": "设备与区域筛选无法使用",
  "Home Assistant is still sending its full entity, device and area lists. See Loona's diagnostics for the compatibility problem, then reload Loona.": "Home Assistant 仍在发送完整的实体、设备和区域列表。请在 Loona 诊断信息中查看兼容性问题，然后重新加载 Loona。",
  "Faster loading is unavailable": "无法使用加快加载的功能",
  "Graphs and animations load the normal way. See Loona's diagnostics for the check that failed.": "图表和动画将按常规方式加载。请在 Loona 诊断信息中查看未通过的检查。",
  "Skipping unused card files is unavailable": "无法跳过未使用的卡片文件",
  "Home Assistant is still loading all card files. See Loona's diagnostics, then reload Loona and refresh your browser.": "Home Assistant 仍在加载全部卡片文件。请查看 Loona 诊断信息，然后重新加载 Loona 并刷新浏览器。",
  "The Loona dashboard could not be created": "无法创建 Loona 仪表盘",
  "Check whether another dashboard already uses the address loona-statistics, and see Loona's diagnostics. Your other dashboards are untouched. Reload Loona once it's fixed.": "请检查是否已有地址为 loona-statistics 的仪表盘，并查看 Loona 诊断信息。你的其他仪表盘不受影响。问题解决后请重新加载 Loona。",
  "Dashboard scan is incomplete": "仪表盘扫描不完整",
  "Entity and device filtering is paused so nothing goes missing. Check your selected dashboards and accounts, save any automatically generated dashboards, then rescan. Unsupported templates, dashboard strategies or auto-entities rules may need changing. Filtering resumes after a full scan.": "为避免遗漏数据，实体和设备筛选已暂停。请检查所选仪表盘和账户，保存自动生成的仪表盘，然后重新扫描。不受支持的模板、仪表盘策略或 auto-entities 规则可能需要修改。完整扫描后会恢复筛选。",
  "Some entities your dashboards use don't exist": "你的仪表盘使用了一些不存在的实体",
  "Check these IDs for typos or deleted entities. Some may come back later. This alone doesn't pause filtering.": "请检查这些 ID 是否拼写错误，或对应的实体已被删除。部分实体可能稍后恢复。仅此一项不会暂停筛选。",
  "Excluded entities are used by cards": "排除的实体正在被卡片使用",
  "Cards may show no data because of these exclusions. Remove them under Entity rules, or keep them if that's what you want.": "这些排除规则可能让卡片没有数据。可在“实体规则”中移除，或在确实需要时保留。",
  "Custom cards may use additional entities": "自定义卡片可能使用其他实体",
  "Loona can't fully check every custom card. If a card is missing data, add its entities under Entity rules.": "Loona 无法完整检查所有自定义卡片。如果某张卡片缺少数据，请在“实体规则”中添加它所需的实体。",
  "Loona can't tell what some card files are for": "Loona 无法确定部分卡片文件的用途",
  "If a card or icon is missing, check the files under Card files. You can also turn off Skip unused card files and refresh to compare.": "如果卡片或图标缺失，请在“卡片文件”中检查所需文件。也可以关闭“跳过未使用的卡片文件”并刷新对比。",
  "Templates may need more card files": "模板可能需要更多卡片文件",
  "All card files are loaded while templates or dashboard strategies can create more cards.": "只要模板或仪表盘策略可能生成更多卡片，就会加载全部卡片文件。",
  "Some card files are being skipped": "部分卡片文件被跳过了",
  "Loona isn't sure what these files are for, so it skips them. If a card, icon or helper goes missing, tick the files you need under Card files and refresh your browser.": "Loona 无法确定这些文件的用途，因此将它们跳过。如果卡片、图标或辅助功能缺失，请在“卡片文件”中勾选所需文件并刷新浏览器。",
  "Some saved card files no longer exist": "部分已保存的卡片文件已不存在",
  "Remove unavailable saved files under Card files, or add them back in Home Assistant's dashboard resources if you still need them.": "请在“卡片文件”中移除不可用的已保存文件；如果仍需使用，请在 Home Assistant 的仪表盘资源中重新添加。",
  "Enable Loona to change other settings.": "请启用 Loona 后修改其他设置。",
  "Show statistics charts": "显示统计图表",
  "Charts refresh with statistics. This choice is saved for this account in this browser.": "图表随统计数据一起刷新。此选项按账户保存在当前浏览器中。",
  "Filtered connections": "已筛选的连接",
  "{filtered} of {total} live connections filtered": "{total} 个实时连接中已筛选 {filtered} 个",
  "Accent color shows the filtered share.": "主题强调色表示已筛选的比例。",
  "No visible warnings": "没有未隐藏的警告",
  "No updates counted in this interval": "本时段未记录更新",
  "Dismiss": "隐藏",
  "Show dismissed warnings ({count})": "显示已隐藏的警告（{count}）",
  "Dismissals apply to this account in this browser. Changed warnings appear again.": "隐藏记录仅适用于当前浏览器中的此账户。警告内容变化后会重新显示。",
  "This card is version {card} but the integration is version {integration}. Reload the page to finish updating.": "此卡片版本为 {card}，而集成版本为 {integration}。请重新加载页面以完成更新。",
  "Reload page": "重新加载页面",
  "Sent: {sent} updates/s; filtered: {filtered} updates/s": "已发送：{sent} 次更新/秒；已筛选：{filtered} 次更新/秒",
  "{percent}% of counted updates filtered": "已筛选记录更新的 {percent}%",
  "{count} updates sent": "已发送 {count} 次更新",
  "Preload card files": "预加载卡片文件",
  "Pause off-screen animations": "暂停屏幕外动画",
  "Idle mode": "空闲模式",
  "Idle timing": "空闲时间设置",
  "Idle after (minutes)": "进入空闲前的分钟数",
  "Idle refresh (seconds)": "空闲刷新间隔（秒）",
  "Load the card files your current tab needs first, and the rest once the page is ready. Switching tabs, opening pop-ups or editing loads anything still waiting. Reload your browser after turning this on.": "优先加载当前标签页所需的卡片文件，页面就绪后再加载其余文件。切换标签页、打开弹窗或编辑时，会立即加载仍在等待的文件。启用后请刷新浏览器。",
  "Start downloading the card files this tab needs as early as possible. Home Assistant still loads them in its usual order. Reload your browser after turning this on.": "尽早开始下载当前标签页所需的卡片文件。Home Assistant 仍按常规顺序加载它们。启用后请刷新浏览器。",
  "Pause repeating animations on cards you can't see, and resume them when you scroll back. Loading spinners and one-time animations keep running.": "暂停看不到的卡片上的循环动画，滚动回来时恢复。加载指示器和一次性动画不受影响。",
  "After a while with no activity, pause live updates. They come back as soon as you touch, click, type or scroll. Needs Entity filtering. Clocks, cameras and some cards may keep updating on their own.": "一段时间无操作后，暂停实时更新。触摸、点击、输入或滚动时会立即恢复。需要启用实体筛选。时钟、摄像头和部分卡片可能仍会自行更新。",
  "Selected dashboards go idle after no touch, mouse, keyboard or scrolling. While idle they refresh at the interval you choose, or not at all if it's 0. Switching tabs, opening pop-ups or editing brings live updates back.": "所选仪表盘在没有触摸、鼠标、键盘或滚动操作后进入空闲状态。空闲期间按你设定的间隔刷新；设为 0 则完全不刷新。切换标签页、打开弹窗或编辑会恢复实时更新。",
  "0 means no refreshing until you interact. Otherwise it refreshes every 1 to 60 seconds (default 60).": "0 表示在你操作之前不刷新。否则每隔 1 至 60 秒刷新一次（默认 60 秒）。",
  "Help: {section}": "帮助：{section}",
  "Live updates": "实时更新",
  "Totals and entities": "总计与实体",
  "Check your dashboards for changes right now.": "立即检查仪表盘是否有变化。",
  "Clears the live counters and page-load records. Your settings and Home Assistant's recorded history aren't touched.": "清除实时计数和页面加载记录。你的设置和 Home Assistant 的历史记录不受影响。",
  "Charts show up to 15 minutes of history and refresh along with the statistics. Sent and filtered out share one scale.": "图表最多显示 15 分钟的历史数据，并随统计数据一起刷新。“已发送”和“已筛掉”使用同一刻度。",
  "{minutes} min history": "{minutes} 分钟历史",
  "No history yet": "暂无历史",
  "{minutes} min ago": "{minutes} 分钟前",
  "Now": "现在",
  "On the moons, the lit part shows the percentage and the dark part is the rest.": "月亮图中，亮的部分表示该百分比，暗的部分表示其余。",
  "No updates": "没有更新",
  "{label}: {rate} updates/s. {history}": "{label}：每秒 {rate} 次更新。{history}"
};

export function cancelConfirmation(host) {
  host._cancelConfirmation?.();
}

const confirmIcons = { "Reset live statistics": "reset", "Restore defaults": "restore", "Remove dashboard": "trash" };
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
    `;
  const heading = document.createElement("h2"); heading.id = "loona-confirm-title"; heading.textContent = text(host._hass, title); heading.dataset.i18n = title;
  const body = document.createElement("p"); body.id = "loona-confirm-message"; body.textContent = text(host._hass, message); body.dataset.i18n = message;
  const actions = document.createElement("div"); actions.className = "actions";
  const cancel = makeButton(host._hass, "Cancel", "cancel", "quiet"); cancel.dataset.confirmCancel = "";
  const confirm = makeButton(host._hass, confirmLabel, confirmIcons[confirmLabel] || "save", "primary"); confirm.dataset.confirmAccept = "";
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
// Shared brand mark: the Loona logo, served beside the card modules.
const markUrl = (() => { try { return new URL("./icon-512.png", import.meta.url).href; } catch { return ""; } })();
export const markHtml = markUrl ? `<img class="mark" src="${markUrl}" alt="" width="52" height="52" decoding="async">` : "";
export const hideBrokenMark = root => root.querySelector(".mark")?.addEventListener("error", event => { event.target.hidden = true; });
// One icon family (24px grid, 1.9 stroke, round caps) and one button system shared by Loona cards.
const iconPaths = {
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V4H4v12h4"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  play: '<path d="m8 4 12 8-12 8Z"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  reset: '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 8v4l2.5 2"/>',
  rescan: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="11" cy="11" r="3"/><path d="m16 16-2.9-2.9"/>',
  restore: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  save: '<path d="M20 6 9 17l-5-5"/>',
  cancel: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  more: '<path d="m6 9 6 6 6-6"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="m6 6 1 14h10l1-14"/>',
};
export const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${iconPaths[name] || iconPaths.save}</svg>`;
// kind: "" tonal, "primary" filled, "quiet" outlined neutral, "caution" neutral with an error-colored icon; add "small" for compact rows.
export function makeButton(hass, label, iconName, kind = "") {
  const button = document.createElement("button");
  button.type = "button"; button.className = ("btn " + kind).trim();
  button.insertAdjacentHTML("afterbegin", icon(iconName));
  const span = document.createElement("span"); span.textContent = text(hass, label); span.dataset.i18n = label;
  button.append(span); return button;
}
export const buttonStyles = `
  .btn { display:inline-flex; align-items:center; justify-content:center; gap:8px; box-sizing:border-box; min-height:44px; padding:8px 18px 8px 14px;
    border:1px solid color-mix(in srgb,var(--primary-color) 34%,var(--divider-color)); border-radius:999px;
    background:color-mix(in srgb,var(--primary-color) 9%,transparent); color:var(--primary-color); font:inherit; font-weight:500; line-height:1.2; white-space:nowrap;
    cursor:pointer; transition:background-color .15s,border-color .15s,color .15s,transform .15s; }
  .btn .icon { width:18px; height:18px; flex:none; }
  .btn:not(:disabled):hover { background:color-mix(in srgb,var(--primary-color) 18%,transparent); border-color:var(--primary-color); }
  .btn:not(:disabled):active { transform:scale(.97); }
  .btn.primary { background:var(--primary-color); border-color:var(--primary-color); color:var(--text-primary-color,#fff); }
  .btn.primary:not(:disabled):hover { background:color-mix(in srgb,var(--primary-color) 86%,#000); }
  .btn.quiet { background:transparent; border-color:var(--divider-color); color:var(--primary-text-color); }
  .btn.quiet:not(:disabled):hover { background:var(--secondary-background-color); border-color:var(--secondary-text-color); }
  .btn.caution { background:transparent; border-color:var(--divider-color); color:var(--primary-text-color); }
  .btn.caution .icon { color:var(--error-color); }
  .btn.caution:not(:disabled):hover { background:var(--secondary-background-color); border-color:var(--error-color); }
  .btn.small { min-height:36px; padding:4px 14px 4px 10px; font-size:13px; }
  .btn.icon-only { width:44px; padding:0; }
  .btn.icon-only .icon { width:20px; height:20px; }
  .btn:disabled,.btn.primary:disabled { background:transparent; border-color:var(--divider-color); color:var(--disabled-text-color); cursor:default; transform:none; }
  .btn:disabled .icon { color:inherit; }
  .btn:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }
  .btn[data-busy] .icon { animation:loona-spin .9s linear infinite; }
  @keyframes loona-spin { to { transform:rotate(360deg); } }
  @media (prefers-reduced-motion:reduce) { .btn[data-busy] .icon { animation:none; } .btn { transition:none; } }
`;
export const markStyles = `
  .mark { width:52px; height:52px; flex-shrink:0; border-radius:50%; object-fit:cover; }
  .brand { display:flex; align-items:flex-start; gap:14px; min-width:0; }
  .heading { flex:1; min-width:0; }
  .heading h2 { min-width:0; }
  .heading #version { margin:2px 0 0; font-size:12px; line-height:1.5; }
`;
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
  .action-help { display:inline-flex; align-items:center; gap:4px; }
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
  "bootstrap_compatibility": ["Filtering may start late on some pages", "Some pages load all entities first, and Loona starts filtering once it recognizes the dashboard. A startup check failed. See Loona's diagnostics for details."],
  "graph_frontend_compatibility": [
    "Faster loading is not available in this browser",
    "Graphs and animations load the normal way. Loona's other filters still work."
  ],
  "entity_compatibility": [
    "Entity filtering is unavailable",
    "Home Assistant is still sending all entity updates as usual. One of Loona's compatibility checks failed. See Loona's diagnostics, then reload Loona and refresh your browser."
  ],
  "panel_compatibility": [
    "Loona can't tell which dashboard is open",
    "Filtering is paused because Loona can't identify the dashboard you're viewing. Reload Loona and refresh your browser. If it keeps happening, see Loona's diagnostics."
  ],
  "registry_compatibility": [
    "Device and area filtering is unavailable",
    "Home Assistant is still sending its full entity, device and area lists. See Loona's diagnostics for the compatibility problem, then reload Loona."
  ],
  "graph_compatibility": [
    "Faster loading is unavailable",
    "Graphs and animations load the normal way. See Loona's diagnostics for the check that failed."
  ],
  "resource_compatibility": [
    "Skipping unused card files is unavailable",
    "Home Assistant is still loading all card files. See Loona's diagnostics, then reload Loona and refresh your browser."
  ],
  "card_installation": [
    "The Loona dashboard could not be created",
    "Check whether another dashboard already uses the address loona-statistics, and see Loona's diagnostics. Your other dashboards are untouched. Reload Loona once it's fixed."
  ],
  "scan_incomplete": [
    "Dashboard scan is incomplete",
    "Entity and device filtering is paused so nothing goes missing. Check your selected dashboards and accounts, save any automatically generated dashboards, then rescan. Unsupported templates, dashboard strategies or auto-entities rules may need changing. Filtering resumes after a full scan."
  ],
  "resource_scan": [
    "Card file scan is incomplete",
    "Home Assistant is loading all card files for now. Check the Home Assistant log for a dashboard or file that failed to load, then rescan. Loona keeps retrying on its own."
  ],
  "resource_loading_failure": [
    "Some card files did not load",
    "Refresh your browser to try again. If it keeps happening, turn off Load current tab first and check the files under Card files."
  ],
  "missing_entities": [
    "Some entities your dashboards use don't exist",
    "Check these IDs for typos or deleted entities. Some may come back later. This alone doesn't pause filtering."
  ],
  "excluded_dependencies": [
    "Excluded entities are used by cards",
    "Cards may show no data because of these exclusions. Remove them under Entity rules, or keep them if that's what you want."
  ],
  "unknown_cards": [
    "Custom cards may use additional entities",
    "Loona can't fully check every custom card. If a card is missing data, add its entities under Entity rules."
  ],
  "unmatched_resources": [
    "Loona can't tell what some card files are for",
    "If a card or icon is missing, check the files under Card files. You can also turn off Skip unused card files and refresh to compare."
  ],
  "dynamic_resources": [
    "Templates may need more card files",
    "All card files are loaded while templates or dashboard strategies can create more cards."
  ],
  "unchecked_resources": [
    "Some card files are being skipped",
    "Loona isn't sure what these files are for, so it skips them. If a card, icon or helper goes missing, tick the files you need under Card files and refresh your browser."
  ],
  "stale_resources": [
    "Some saved card files no longer exist",
    "Remove unavailable saved files under Card files, or add them back in Home Assistant's dashboard resources if you still need them."
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
  message.textContent = text(hass, "This card is version {card} but the integration is version {integration}. Reload the page to finish updating.", {card:cardVersion, integration:version});
  const reload = makeButton(hass, "Reload page", "refresh", "primary small"); reload.disabled = blocked;
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
      const dismiss=makeButton(hass,"Dismiss","cancel","quiet small"); dismiss.dataset.dismiss=item.code;
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
