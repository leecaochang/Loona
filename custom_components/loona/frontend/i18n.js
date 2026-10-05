/* Shared English/Simplified Chinese messages for Loona cards. */
const chinese = {
  "Measurements": "测量结果",
  "Measurement": "测量项目",
  "Setting": "设置项",
  "Value": "数值",
  "Dashboard": "仪表盘",
  "Tab": "选项卡",
  "Completed": "完成时间",
  "Method": "测量方式",
  "Pass": "轮次",
  "Mode": "模式",
  "Ready (s)": "就绪（秒）",
  "Data (KB)": "数据（KB）",
  "Updates": "更新次数",
  "Blocking (ms)": "阻塞（毫秒）",
  "Right-click the image above and choose Copy Image. On a touch screen, touch and hold it.": "右键点击上方图片，选择“复制图片”。触屏设备请长按图片。",

  "Detailed report": "详细报告",
  "Executive summary": "结果摘要",
  "Test details": "测试信息",
  "Interpretation and next steps": "结果说明与下一步",
  "Individual passes": "各轮结果",
  "Caveats": "注意事项",
  "Start over to run a new comparison.": "点击“重新开始”可以再测一次。",
  "{percent}% less data": "数据减少 {percent}%",
  "{percent}% more data": "数据增加 {percent}%",
  "{percent}% less file data": "文件数据减少 {percent}%",
  "{percent}% more file data": "文件数据增加 {percent}%",
  "{percent}% fewer files": "文件数量减少 {percent}%",
  "{percent}% more files": "文件数量增加 {percent}%",
  "{percent}% fewer updates": "更新减少 {percent}%",
  "{percent}% more updates": "更新增加 {percent}%",
  "More observed with Loona": "Loona 模式下观测值更高",
  "Less time observed": "观测耗时更少",
  "More time observed": "观测耗时更多",
  "No clear timing difference": "未测得明确的时间差异",
  "The loading or blocking times are similar or overlap across passes. This does not indicate an interrupted test. Data savings can still be measured without a proven speed improvement.": "各轮的加载或阻塞时间相近，或范围有重叠。这并不表示测试被中断。即使无法证明速度更快，仍然可以测出数据量的节省。",
  "Some card file sizes are unavailable in this browser. Card files loaded instead compares file counts for both modes; fewer files does not establish less file data.": "此浏览器无法提供部分卡片文件的大小，因此“已加载卡片文件”改为比较两种模式的文件数量；文件更少并不代表文件数据更少。",
  "Safari and the Home Assistant Companion app for iOS and macOS use WebKit, which may not report decoded file sizes for cached scripts, even when the files loaded successfully. After the benchmark ends, Loona tries to recover the missing file sizes using cache-only reads. Cross-origin restrictions can also hide sizes. If any pass still lacks a file size, Card files loaded instead compares file counts for both modes.": "Safari 和适用于 iOS、macOS 的 Home Assistant Companion 应用使用 WebKit，它可能不会报告已缓存脚本的解码后大小，即使文件已成功加载。基准测试结束后，Loona 会尝试通过仅读缓存的方式找回缺失的文件大小。跨域限制也可能导致无法获取文件大小。如果某一轮仍然缺少文件大小，“已加载卡片文件”会改为比较两种模式的文件数量。",
  "Blocking is measured alongside live updates in the same observation window. It does not add a separate test phase.": "阻塞与实时更新在同一观察时段内一起测量，不会增加单独的测试阶段。",
  "Blocking was skipped because this browser does not expose Long Animation Frames. Chrome and Edge 123+ support it; Firefox, Safari and the iOS and macOS Companion apps (WebKit) do not. Skipping it does not shorten the run because it shares the live-update observation window.": "此浏览器不提供 Long Animation Frames，因此已跳过阻塞测量。Chrome 和 Edge 123 及以上版本支持它；Firefox、Safari 以及 iOS 和 macOS 版 Companion 应用（WebKit）不支持。阻塞与实时更新共用观察时段，所以跳过它并不会缩短测试时间。",
  "Fewer than three valid readings are available. Resolve the issues below and repeat the test.": "有效读数不足三轮。请先解决下方的问题，再重新测试。",
  "To inspect individual card files, open Settings > Dashboards > Resources, or filter the browser Network panel to JavaScript and reload. The comparison above reports totals without repeating files for every pass.": "如需查看单个卡片文件，请打开“设置 > 仪表盘 > 资源”，或在浏览器开发者工具的“网络”面板中筛选 JavaScript 后刷新。上方的比较只报告总量，不会逐轮列出文件。",
  "Entities to include": "要包含的实体",
  "Entities to exclude": "要排除的实体",
  "Copy text": "复制文本",
  "Save text": "保存文本",
  "Text copied.": "已复制文本。",
  "Could not copy the text. Save the text instead.": "无法复制文本。请改为保存文本。",

  "Loona benchmark": "Loona 基准测试",
  "Benchmark interrupted": "基准测试已中断",
  "No valid comparison was completed.": "未完成有效的比较。",
  "See the detailed report for recovery steps.": "请在详细报告中查看恢复步骤。",
  "Benchmark this dashboard": "测试此仪表盘",
  "Benchmark Results": "基准测试结果",
  "Native HA and your saved Loona settings": "原生 HA 与你保存的 Loona 设置",
  "Native Home Assistant": "原生 Home Assistant",
  "Native HA": "原生 HA",
  "This report can include dashboard and account names, entity names, card file addresses and browser details. Review it before posting.": "此报告可能包含仪表盘和用户名称、实体名称、卡片文件地址以及浏览器信息。发布前请先检查。",
  "Hides this warning type for your account in this browser, including future occurrences. It does not resolve the problem or change Loona's behavior.": "在此浏览器中，为你的用户隐藏这类警告，包括今后再次出现的警告。这不会解决问题，也不会改变 Loona 的行为。",
  "Visible-card readiness": "可见卡片就绪",
  "Initial JSON data": "初始 JSON 数据",
  "Card files loaded": "已加载卡片文件",
  "Browser blocking": "浏览器阻塞",
  "s": "秒",
  "ms": "毫秒",
  "{count} card files": "{count} 个卡片文件",
  "Incomplete measurement": "测量不完整",
  "No updates observed": "未观察到更新",
  "No measurable change": "未测得明显变化",
  "{pairs} pairs · {seconds}s observation · cached reloads": "{pairs} 组 · 观察 {seconds} 秒 · 使用缓存刷新",
  "Visible cards did not become ready in time. Put the benchmark card near the top, keep another card visible, fix loading cards and start over.": "可见卡片未能及时就绪。请把基准测试卡片放在靠近顶部的位置，并保持另一张卡片可见；修复加载有问题的卡片后重新开始。",
  "A visible card reported an error. Fix that card and start over.": "有可见卡片报告了错误。请修复该卡片后重新开始。",
  "A card file failed to load. Check dashboard resources and the connection, then start over.": "有卡片文件加载失败。请检查仪表盘资源和网络连接，然后重新开始。",
  "The observer reached its limit. Try a smaller tab with fewer cards and start over.": "观察器已达到上限。请换一个卡片较少的选项卡，再重新开始。",
  "What will be measured": "测量内容",
  "Paused. Return to this page to repeat this pass.": "已暂停。回到此页面后会重测本轮。",
  "Observing": "正在观察",
  "Saving pass": "正在保存本轮",
  "Loading dashboard": "正在加载仪表盘",
  "Pass {pass} of {total}": "第 {pass} 轮，共 {total} 轮",
  "Cancel benchmark": "取消基准测试",
  "Sign in as an administrator to benchmark this dashboard.": "请以管理员身份登录，再测试此仪表盘。",
  "Copy": "复制",
  "Start over": "重新开始",
  "Remove": "移除",
  "Go": "开始",
  "Compares native Home Assistant with your saved Loona settings on this tab, using two warm-ups and three alternating pairs. Allow about four minutes. Page reloads are automatic.": "在此选项卡上，用两轮预热和三组交替测试，比较原生 Home Assistant 与你保存的 Loona 设置。请预留约四分钟，页面会自动刷新。",
  "Keep the page in the foreground without scrolling, interacting or resizing. Put this card near the top with another card visible.": "测试期间请让页面保持在前台，不要滚动、操作或调整窗口大小。请把此卡片放在靠近顶部的位置，并保持另一张卡片可见。",
  "The benchmark measures reloads with the browser cache, not cold-cache loads or a guaranteed hard refresh.": "基准测试测量的是使用浏览器缓存的重新加载，不是无缓存加载，也不保证是强制刷新。",
  "Readiness waits for visible cards and icons to render, visible images and fonts to load, and pending native requests to finish. Cameras, charts and custom content may still be loading.": "就绪时间会等待可见卡片和图标渲染完成、可见图片和字体加载完成，以及待完成的原生请求结束。摄像头、图表和自定义内容仍可能在加载。",
  "JSON sizes are logical UTF-8 message sizes, before network compression. File sizes cover observed registered resource entry files, not every imported dependency.": "JSON 大小是网络压缩前的 UTF-8 逻辑消息大小。文件大小只涵盖观察到的已注册资源入口文件，不包括每一个被导入的依赖项。",
  "Browser blocking uses Long Animation Frames. It does not measure total CPU, GPU, memory, battery or all response delays.": "浏览器阻塞基于 Long Animation Frames 测量，不代表总 CPU、GPU、内存、电池消耗或全部响应延迟。",
  "Each mode gets a warm-up, then three alternating pairs. Live activity can differ between passes. Overlapping timing ranges are inconclusive.": "两种模式各先预热一轮，再交替进行三组测试。各轮的实时活动可能不同。时间范围重叠时，结果不确定。",
  "Idle savings only appear if the configured idle threshold is reached. This test does not isolate the benefit of each setting.": "只有达到设置的空闲阈值，才会出现空闲模式带来的节省。本测试不会单独衡量每项设置的效果。",
  "No live updates were observed. Repeat while the dashboard entities are changing.": "未观察到实时更新。请在仪表盘上的实体发生变化时重测。",
  "Saved settings": "已保存的设置",
  "Disabled": "已禁用",
  "Browser: {browser}; viewport: {width} x {height}": "浏览器：{browser}；窗口大小：{width} x {height}",
  "Keep the benchmark tab visible before starting.": "开始前请保持基准测试所在的选项卡可见。",
  "Benchmark could not start. Refresh and try again.": "无法开始基准测试。请刷新后重试。",
  "Remove benchmark card?": "移除基准测试卡片？",
  "Remove this benchmark card from this tab? Saved PNGs are kept.": "要从此选项卡移除这张基准测试卡片吗？已保存的 PNG 会保留。",
  "Remove this card manually in the dashboard editor or YAML source.": "请在仪表盘编辑器或 YAML 源码中手动移除此卡片。",
  "PNG copied.": "已复制 PNG。",
  "PNG export failed. Start over and try again.": "PNG 导出失败。请重新开始后再试。",
  "Close": "关闭",
  "Benchmark complete. Results are ready.": "基准测试已完成，结果已就绪。",
  "Show results": "查看结果",

  "{source} ({phase}): {ms} ms, including {layout} ms re-measuring the page": "{source}（{phase}）：{ms} 毫秒，其中 {layout} 毫秒用于重新计算页面布局",
  "before measuring": "测量开始前",
  "while measuring": "测量期间",
  "Browser performance": "浏览器性能",
  "Lists the 20 entities with the most updates sent since reset, alongside browser reports of slow frames, script work and event subscriptions that may bypass filtering. These reports cover only part of the browser's work. Items marked 'before measuring' happened before Loona started watching.": "列出重置以来发送更新最多的 20 个实体，以及浏览器报告的卡顿帧、脚本耗时和可能绕过筛选的事件订阅。这些报告只涵盖浏览器工作量的一部分。标记为“测量开始前”的项目发生在 Loona 开始观察之前。",
  "Entities sending the most updates since reset": "重置以来发送更新最多的实体",
  "Only the busiest entities are listed. {count} more updates came from entities not shown.": "只列出最活跃的实体。另有 {count} 次更新来自未列出的实体。",
  "Slow frames: {count}, adding up to {ms} ms of delay": "卡顿帧：{count} 个，累计延迟 {ms} 毫秒",
  "This browser cannot report slow frames.": "此浏览器无法统计卡顿帧。",
  "This dashboard listens to all Home Assistant events, which can bypass entity filtering.": "此仪表盘监听了 Home Assistant 的全部事件，这可能绕过实体筛选。",
  "Faster loading is not available in this browser": "此浏览器无法使用加速加载功能",
  "Graphs and animations load the normal way. Loona's other filters still work.": "图表和动画将按常规方式加载。Loona 的其他筛选功能仍然可用。",
  "Graph loading": "图表正在加载",
  "Card file scan is incomplete": "卡片文件扫描不完整",
  "Home Assistant is loading all card files for now. Check the Home Assistant log for a dashboard or file that failed to load, then rescan. Loona keeps retrying on its own.": "目前 Home Assistant 会加载全部卡片文件。请在 Home Assistant 日志中查看加载失败的仪表盘或文件，然后重新扫描。Loona 也会自动重试。",
  "Dashboards": "仪表盘",
  "Apply filtering to": "筛选适用于",
  "Accounts": "用户",
  "Selected accounts": "所选用户",
  "All accounts": "所有用户",
  "Loona settings": "Loona 设置",
  "Filters and performance": "筛选与性能",
  "Entity filtering": "实体筛选",
  "Live updates for current tab only": "仅实时更新当前选项卡",
  "After the first load, only the tab you are viewing keeps updating, along with any entities in your Entity rules. Hidden tabs will not update until you view them. Opening a tab, opening a pop-up, or editing a dashboard refreshes values right away. Requires Entity filtering enabled.": "首次加载之后，只有你正在查看的选项卡以及“实体规则”中的实体会继续更新。隐藏的选项卡要等你切换过去才会更新。打开选项卡、打开弹窗或编辑仪表盘时，数值会立即刷新。需要启用“实体筛选”。",
  "Device and area filtering": "设备与区域筛选",
  "Pause animations during loading": "加载期间暂停动画",
  "Skip unused card files": "跳过未使用的卡片文件",
  "Prioritize current tab": "优先加载当前选项卡",
  "Some card files did not load": "部分卡片文件未能加载",
  "Refresh your browser to try again. If it keeps happening, turn off Prioritize current tab and check the files under Card files.": "请刷新浏览器重试。如果问题持续出现，请关闭“优先加载当前选项卡”，并在“卡片文件”中检查相关文件。",
  "Extra card files to load": "额外加载的卡片文件",
  "Enabled": "启用",
  "Rescan dashboards": "重新扫描仪表盘",
  "Reset live statistics": "重置实时统计",
  "Restore defaults": "恢复默认设置",
  "Restore defaults?": "恢复默认设置？",
  "Reset live statistics?": "重置实时统计？",
  "Remove the Loona dashboard?": "移除 Loona 仪表盘？",
  "Restores Loona back to default settings, as if you had installed it fresh. Also removes the Loona dashboard (if you have not edited it). You will need to select dashboards and accounts again before filtering resumes. An edited Loona dashboard, Loona cards you placed yourself, and recorded history are kept.": "将 Loona 恢复为默认设置，就像刚安装时一样。同时会移除 Loona 仪表盘（如果你没有编辑过它）。你需要重新选择仪表盘和用户，筛选才会恢复。你编辑过的 Loona 仪表盘、自己放置的 Loona 卡片以及历史记录都会保留。",
  "Clear the live counters, recent page-load records and browser readings? Your Loona settings and Home Assistant's recorded history are untouched.": "要清除实时计数、最近的页面加载记录和浏览器读数吗？你的 Loona 设置和 Home Assistant 的历史记录不受影响。",
  "Remove the Loona dashboard, along with its cards? An edited Loona dashboard is kept. To get it back, choose Loona dashboard cards again.": "要移除 Loona 仪表盘及其卡片吗？你编辑过的 Loona 仪表盘会保留。如需恢复，请重新选择“Loona 仪表盘卡片”。",
  "Remove dashboard": "移除仪表盘",
  "Defaults restored. You will need to select dashboards and accounts again before filtering resumes, then reload your browser.": "已恢复默认设置。你需要重新选择仪表盘和用户，筛选才会恢复，然后请刷新浏览器。",
  "Could not restore defaults. Refresh and check the current settings.": "无法恢复默认设置。请刷新并检查当前设置。",
  "Restores Loona back to default settings, as if you had installed it fresh. Also removes the Loona dashboard (if you have not edited it). You will need to select dashboards and accounts again before filtering resumes. You will be asked to confirm.": "将 Loona 恢复为默认设置，就像刚安装时一样。同时会移除 Loona 仪表盘（如果你没有编辑过它）。你需要重新选择仪表盘和用户，筛选才会恢复。操作前会要求你确认。",
  "Some features are unavailable. See Loona's diagnostics.": "部分功能无法使用。请查看 Loona 的诊断信息。",
  "Loona card title must be text": "Loona 卡片标题必须是文本",
  "Loona statistics": "Loona 统计",
  "Loading statistics...": "正在加载统计…",
  "Refresh": "刷新",
  "Sent": "已发送",
  "Filtered out": "已筛除",
  "Updates filtered out": "已筛除的更新",
  "updates/s": "次更新/秒",
  "of all updates": "占全部更新",
  "Updates sent since reset": "重置后发送的更新",
  "Updates filtered out since reset": "重置后筛除的更新",
  "Connections filtered / total": "已筛选 / 全部实时连接",
  "Entities currently included": "当前包含的实体",
  "Recent page loads": "最近的页面加载",
  "Shows how many entities and card files were sent versus available for each dashboard's latest recorded page load. It does not measure loading time.": "显示每个仪表盘最近一次记录的页面加载中，已发送的实体和卡片文件数量与可用数量的对比。它不衡量加载时间。",
  "Could not load statistics. Check that Loona is running, then press Refresh.": "无法加载统计。请确认 Loona 正在运行，然后点击“刷新”。",
  "Unable to load statistics": "无法加载统计",
  "Could not reset statistics. Try Reset live statistics on the Loona device page.": "无法重置统计。请到 Loona 设备页面尝试“重置实时统计”。",
  "Dashboard scan incomplete. All entities are being sent.": "仪表盘扫描不完整，正在发送全部实体。",
  "Entity filtering is disabled": "实体筛选已关闭",
  "Entity filtering is active": "实体筛选已启用",
  "Nothing is being filtered yet. Open a selected dashboard with a selected account.": "目前没有任何筛选。请用所选用户打开一个所选仪表盘。",
  "Measured over the last {seconds} seconds.": "统计时段为最近 {seconds} 秒。",
  "Rates update within {seconds} seconds.": "速率将在 {seconds} 秒内显示。",
  "Each update counts once per connection, so opening more tabs increases the totals. These figures measure entity updates, not data size, bandwidth, CPU usage or loading speed.": "每次更新按每个连接分别计数，因此打开更多浏览器标签页会让总数增加。这些数字衡量的是实体更新，不是数据大小、带宽、CPU 占用或加载速度。",
  "Sign in as an administrator to view Loona statistics.": "请以管理员身份登录，再查看 Loona 统计。",
  "1 entity": "1 个实体",
  "Loona dashboard cards": "Loona 仪表盘卡片",
  "Loona will create a Loona dashboard with the cards you choose, visible to administrators only. Choose none to remove it (if you have not edited it).": "Loona 会用你选择的卡片创建一个 Loona 仪表盘，仅管理员可见。全部取消选择则会移除它（如果你没有编辑过它）。",
  "{count} entities": "{count} 个实体",
  "Counting since {time}": "自 {time} 起统计",
  "Entities sent: {sent} out of {available}": "已发送实体：{available} 个中的 {sent} 个",
  "Card files sent: {sent} out of {available}": "已发送卡片文件：{available} 个中的 {sent} 个",
  "No card file count was recorded for this load.": "本次加载未记录卡片文件数量。",
  "No page loads recorded yet. Reload one of your dashboards.": "尚无页面加载记录。请刷新其中一个仪表盘。",
  "Live filtering statistics and recent page loads": "实时筛选统计与最近的页面加载",
  "Loading settings...": "正在加载设置…",
  "Sign in as an administrator to change Loona settings.": "请以管理员身份登录，再修改 Loona 设置。",
  "Could not load settings. Check that Loona is running, then press Refresh.": "无法加载设置。请确认 Loona 正在运行，然后点击“刷新”。",
  "Save": "保存",
  "Cancel": "取消",
  "Saved": "已保存",
  "Unsaved changes": "有未保存的更改",
  "Settings changed elsewhere. Cancel your edits and refresh before saving.": "设置已在别处被修改。请先取消你的修改并刷新，再保存。",
  "Could not save. Your edits are still here. Cancel them and refresh to check the saved settings.": "无法保存，你的修改仍然保留在这里。请取消修改并刷新，以查看已保存的设置。",
  "Some choices are no longer available. Cancel your edits and refresh the lists.": "部分选项已不可用。请取消修改并刷新列表。",
  "Card file choices are not available right now.": "暂时无法选择卡片文件。",
  "Search available choices": "搜索可选项",
  "Selected ({count})": "已选择（{count}）",
  "No selections": "未选择",
  "No matching choices": "没有匹配的选项",
  "Available choices": "可选项",
  "Show more": "显示更多",
  "Unavailable": "不可用",
  "optional": "可选",
  "Not used by any of your dashboards": "你的仪表盘都没用到",
  "Purpose unknown": "用途不明",
  "Files Loona always loads ({count})": "Loona 始终加载的文件（{count}）",
  "These files are needed by your dashboards or shared styling.": "你的仪表盘或共享样式需要这些文件。",
  "Selecting Skip unused card files will load only the card files your dashboards need. Loona will still load anything it cannot safely judge. Always reload the dashboard after you make a change.": "选择“跳过未使用的卡片文件”后，只会加载你的仪表盘需要的卡片文件。Loona 无法确定用途的文件仍会加载。每次修改后，请务必刷新仪表盘。",
  "Refresh is unavailable while you have unsaved changes.": "有未保存的更改时无法刷新。",
  "Change filters, dashboards and accounts": "修改筛选、仪表盘和用户",
  "Briefly pauses repeating animations while the dashboard starts up, then resumes them.": "仪表盘启动期间会短暂暂停循环动画，随后恢复。",
  "A live connection is the link a dashboard tab keeps open to Home Assistant. Each open tab usually has one connection, sometimes more. 'Connections filtered / total' shows how many of them Loona is filtering. 'Estimated entities trimmed' is the percentage of Home Assistant's entities outside Loona's configured inclusion set. It describes potential entity reduction, not measured update reduction, and remains visible when filtering is off.": "实时连接是仪表盘所在的浏览器标签页与 Home Assistant 之间保持的连接。每个打开的标签页通常有一个连接，有时不止一个。“已筛选 / 全部实时连接”显示 Loona 正在筛选其中多少个。“估计精简的实体”是不在 Loona 已配置的包含范围内的 Home Assistant 实体所占的百分比。它描述的是可能减少的实体数量，而不是实测减少的更新量；即使筛选已关闭，也会显示。",
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
  "What gets sent to the dashboard is only what your selected dashboards actually use, plus whatever you add under Entity rules. You can add single entities, a whole entity type (like sensor or light), or patterns such as sensor.kitchen_*, which means every sensor whose name starts with kitchen_.": "发送到仪表盘的，只有你所选仪表盘实际用到的实体，加上你在“实体规则”中添加的内容。你可以添加单个实体、整个实体类型（例如 sensor 或 light），或形如 sensor.kitchen_* 的匹配规则，它表示名称以 kitchen_ 开头的所有 sensor。",
  "Always keep these, even if no dashboard uses them.": "即使没有仪表盘用到，也始终保留这些实体。",
  "The Excluded list takes precedence over Included. Person, update and zone entities cannot be excluded, because the Home Assistant interface needs them. Cards that use excluded entities may show no data.": "“排除”列表的优先级高于“包含”列表。person、update 和 zone 实体无法被排除，因为 Home Assistant 界面需要它们。使用了被排除实体的卡片可能没有数据。",
  "The master switch. Turning it off resumes Home Assistant's normal behavior. Your settings are kept as-is. Reload your browser to bring back any skipped card files.": "总开关。关闭后，Home Assistant 将恢复正常行为，你的设置会原样保留。请刷新浏览器，以恢复被跳过的卡片文件。",
  "Sends only the entities your chosen dashboards use, plus any specific entities you added under Entity rules.": "只发送你所选仪表盘用到的实体，以及你在“实体规则”中添加的指定实体。",
  "Trims the entity, device, area, floor and label lists.": "精简实体、设备、区域、楼层和标签列表。",
  "Prevents loading the card files that none of your dashboards actually use. Loona will still load anything it cannot safely judge. Reload your dashboard after changing this.": "不加载你的仪表盘都没用到的卡片文件。Loona 无法确定用途的文件仍会加载。更改后请刷新仪表盘。",
  "Delays building graphs that are off-screen until the rest of the page has settled. Scrolling a graph into view loads it right away.": "延迟构建屏幕外的图表，等页面其余部分稳定后再处理。把图表滚动到可见位置时，会立即加载。",
  "Select the dashboards you want Loona to filter.": "选择要让 Loona 筛选的仪表盘。",
  "Choose Selected accounts or All accounts. Home Assistant permissions always apply; Loona never grants or removes anyone's access.": "选择“所选用户”或“所有用户”。Home Assistant 的权限始终有效；Loona 不会授予或移除任何人的访问权限。",
  "Version: {version}": "版本：{version}",
  "Warnings and checks ({count})": "警告与检查（{count}）",
  "Warning": "警告",
  "Check": "检查",
  "Affected items ({count})": "相关项目（{count}）",
  "Entity filtering is unavailable": "实体筛选无法使用",
  "Home Assistant is still sending all entity updates as usual. One of Loona's compatibility checks failed. See Loona's diagnostics, then reload Loona and refresh your browser.": "Home Assistant 仍在正常发送全部实体更新。Loona 有一项兼容性检查未通过。请查看 Loona 的诊断信息，然后重新加载 Loona 并刷新浏览器。",
  "Loona cannot tell which dashboard is open": "Loona 无法识别当前打开的仪表盘",
  "Filtering may start late on some pages": "部分页面可能较晚开始筛选",
  "Some pages load all entities first, and Loona starts filtering once it recognizes the dashboard. A startup check failed. See Loona's diagnostics for details.": "部分页面会先加载全部实体，Loona 识别出仪表盘后才开始筛选。启动检查未通过，详情请查看 Loona 的诊断信息。",
  "Filtering is paused because Loona cannot identify the dashboard you are viewing. Reload Loona and refresh your browser. If it keeps happening, see Loona's diagnostics.": "由于 Loona 无法识别你正在查看的仪表盘，筛选已暂停。请重新加载 Loona 并刷新浏览器。如果问题持续出现，请查看 Loona 的诊断信息。",
  "Device and area filtering is unavailable": "设备与区域筛选无法使用",
  "Home Assistant is still sending its full entity, device and area lists. See Loona's diagnostics for the compatibility problem, then reload Loona.": "Home Assistant 仍在发送完整的实体、设备和区域列表。请在 Loona 的诊断信息中查看兼容性问题，然后重新加载 Loona。",
  "Faster loading is unavailable": "加速加载功能无法使用",
  "Graphs and animations load the normal way. See Loona's diagnostics for the check that failed.": "图表和动画将按常规方式加载。请在 Loona 的诊断信息中查看未通过的检查。",
  "Skipping unused card files is unavailable": "无法跳过未使用的卡片文件",
  "Home Assistant is still loading all card files. See Loona's diagnostics, then reload Loona and refresh your browser.": "Home Assistant 仍在加载全部卡片文件。请查看 Loona 的诊断信息，然后重新加载 Loona 并刷新浏览器。",
  "The Loona dashboard could not be created": "无法创建 Loona 仪表盘",
  "Check whether another dashboard already uses the address loona-statistics, and see Loona's diagnostics. Your other dashboards are untouched. Reload Loona once it is fixed.": "请检查是否已有仪表盘使用了地址 loona-statistics，并查看 Loona 的诊断信息。你的其他仪表盘不受影响。问题解决后，请重新加载 Loona。",
  "Dashboard scan is incomplete": "仪表盘扫描不完整",
  "Loona has disabled entity, device, and area filtering for all of your selected dashboards rather than risk breaking something. Check for removed dashboards or accounts, save auto-generated dashboards, and review dynamic cards or templates Loona cannot read, then press Rescan dashboards. Missing entity IDs alone do not cause this. Filtering resumes after a full scan.": "为避免出错，Loona 已对你所选的全部仪表盘关闭实体、设备和区域筛选。请检查是否有已删除的仪表盘或用户，保存自动生成的仪表盘，并检查 Loona 无法读取的动态卡片或模板，然后点击“重新扫描仪表盘”。仅仅是实体 ID 不存在，不会导致这种情况。完整扫描后会恢复筛选。",
  "Some entities your dashboards use do not exist": "你的仪表盘用到了一些不存在的实体",
  "Check these IDs for typos or deleted entities. Some may come back later. Missing entity IDs alone do not pause filtering.": "请检查这些 ID 是否拼写错误，或对应的实体已被删除。有些实体可能稍后恢复。仅仅是实体 ID 不存在，不会暂停筛选。",
  "Excluded entities are used by cards": "被排除的实体正在被卡片使用",
  "Cards may show no data because of these exclusions. Remove them under Entity rules, or keep them if that is what you want.": "这些排除规则可能导致卡片没有数据。可以在“实体规则”中移除它们；如果这正是你想要的，也可以保留。",
  "Custom cards may use additional entities": "自定义卡片可能使用其他实体",
  "Loona cannot always correctly guess every entity a custom card or pop-up requires. If a card is missing data, add the missing entities under Entity rules.": "Loona 不一定能准确判断自定义卡片或弹窗所需的每个实体。如果某张卡片缺少数据，请在“实体规则”中添加缺失的实体。",
  "Loona cannot tell what some card files are for": "Loona 无法确定部分卡片文件的用途",
  "If a card or icon is missing, turn off Skip unused card files and reload. Look at the optional files under Card files and at the Home Assistant log.": "如果卡片或图标缺失，请关闭“跳过未使用的卡片文件”并刷新。查看“卡片文件”中的可选文件，以及 Home Assistant 日志。",
  "Templates may need more card files": "模板可能需要更多卡片文件",
  "If Loona finds a template or dashboard strategy it cannot read on any dashboard, every card file is loaded.": "只要在任何仪表盘上发现 Loona 无法读取的模板或仪表盘策略，就会加载全部卡片文件。",
  "Some saved card files no longer exist": "部分已保存的卡片文件已不存在",
  "Remove unavailable saved files under Card files, or add them back in Home Assistant's dashboard resources if you still need them.": "请在“卡片文件”中移除不可用的已保存文件；如果仍然需要，也可以在 Home Assistant 的仪表盘资源中重新添加。",
  "Enable Loona to change other settings.": "启用 Loona 后才能修改其他设置。",
  "Show statistics charts": "显示统计图表",
  "Filtered connections": "已筛选的连接",
  "{filtered} of {total} live connections filtered": "{total} 个实时连接中已筛选 {filtered} 个",
  "Dismiss": "忽略",
  "This card is version {card} but the integration is version {integration}. Reload the page to finish updating.": "此卡片的版本是 {card}，而集成的版本是 {integration}。请刷新页面以完成更新。",
  "Reload page": "刷新页面",
  "{count} updates sent": "已发送 {count} 次更新",
  "Preload card files": "预加载卡片文件",
  "Pause off-screen animations": "暂停屏幕外动画",
  "Idle mode": "空闲模式",
  "Idle timing": "空闲时间设置",
  "Idle after (minutes)": "空闲等待时间（分钟）",
  "Idle refresh (seconds)": "空闲刷新间隔（秒）",
  "Delays other tabs' card files until the current tab has rendered, then loads them gradually. Opening a pop-up, switching tabs or pages, or editing loads the remaining files right away. Reload your dashboard after changing this.": "其他选项卡的卡片文件会延后加载，等当前选项卡渲染完成后再逐步加载。打开弹窗、切换选项卡或页面、或进行编辑时，会立即加载剩余文件。更改后请刷新仪表盘。",
  "Starts downloading the current tab's card files before Home Assistant requests them. This does not change when they run. Reload your dashboard after changing this.": "在 Home Assistant 请求之前，就开始下载当前选项卡的卡片文件。这不会改变它们的运行时机。更改后请刷新仪表盘。",
  "Pauses repeating animations on cards that are scrolled out of view and resumes them when you scroll back. Loading spinners and one-time animations keep running.": "暂停已滚出视野的卡片上的循环动画，滚动回来时恢复。加载指示器和一次性动画不受影响。",
  "After a period of no activity, the dashboard stops live updates and refreshes its values only at a set interval, until any interaction brings live updates back. You can set the Idle after time and the Idle refresh interval. Requires Entity filtering enabled. This affects ordinary live connections only - cameras, independent clocks, card timers and raw event listeners will keep going.": "一段时间没有操作后，仪表盘会停止实时更新，只按设定的间隔刷新数值，直到有任何操作才会恢复实时更新。你可以设置“空闲等待时间”和“空闲刷新间隔”。需要启用“实体筛选”。这只影响普通的实时连接，摄像头、独立的时钟、卡片计时器和原始事件监听器仍会继续运行。",
  "When Idle mode is on and you have not touched the page for the Idle after time, live updates pause. A fresh snapshot of current values loads at the Idle refresh interval. Changes in between are not displayed.": "开启空闲模式后，如果你在“空闲等待时间”内没有操作页面，实时更新就会暂停。Loona 会按“空闲刷新间隔”加载当前数值的最新快照，期间的变化不会显示。",
  "Idle after is 1 to 60 minutes (default 5). Idle refresh is 1 to 60 seconds (default 60). At 0, values remain frozen until you interact.": "空闲等待时间为 1 至 60 分钟（默认 5 分钟）。空闲刷新间隔为 1 至 60 秒（默认 60 秒）。设为 0 时，数值会一直保持不变，直到你有操作。",
  "Help: {section}": "帮助：{section}",
  "Live updates": "实时更新",
  "Live update rate": "实时更新速率",
  "Totals and entities": "总计与实体",
  "Editing a dashboard normally triggers this automatically; press this button to force a rescan now.": "编辑仪表盘后通常会自动触发扫描；点击此按钮可立即强制重新扫描。",
  "Clears the live counters, recent page-load records and browser readings. Your Loona settings and Home Assistant's recorded history are untouched.": "清除实时计数、最近的页面加载记录和浏览器读数。你的 Loona 设置和 Home Assistant 的历史记录不受影响。",
  "Charts show up to 15 minutes of history and refresh along with the statistics. Chart history is kept only in memory and clears on reset or restart. Sent and filtered out share one scale.": "图表最多显示 15 分钟的历史数据，并随统计一起刷新。图表历史只保存在内存中，重置或重启后会清空。“已发送”和“已筛除”使用同一刻度。",
  "{minutes} min history": "{minutes} 分钟历史",
  "No history yet": "暂无历史",
  "{minutes} min ago": "{minutes} 分钟前",
  "Now": "现在",
  "On the moons, the lit part shows the percentage and the dark part is the rest.": "月亮图中，亮的部分表示该百分比，暗的部分表示其余。",
  "{count} of {total} improved": "{total} 项中 {count} 项有改善",
  "No updates": "没有更新",

  // Benchmark messages that used to be English only.
  "Benchmark connection is unavailable": "基准测试的连接不可用",
  "Startup authorization failed. Start over.": "启动授权失败。请重新开始。",
  "Startup authorization timed out. Check the connection and start over.": "启动授权超时。请检查网络连接后重新开始。",
  "The viewport changed during measurement. Keep the page still and start over.": "测量期间窗口发生了变化。请保持页面不动，然后重新开始。",
  "Interaction interrupted measurement. Keep the page still and start over.": "操作打断了测量。请保持页面不动，然后重新开始。",
  "Page hidden. Return to repeat this pass.": "页面已隐藏。回到页面后会重测本轮。",
  "Could not repeat the interrupted pass. Start over.": "无法重测被中断的一轮。请重新开始。",
  "Viewport size changed during testing. Keep the same orientation and start over.": "测试期间窗口大小发生了变化。请保持相同的屏幕方向，然后重新开始。",
  "Viewport size changed during testing. Start over.": "测试期间窗口大小发生了变化。请重新开始。",
  "Connection changed during testing. Check the connection and start over.": "测试期间连接发生了变化。请检查网络连接后重新开始。",
  "Tab changed during testing. Return to the benchmark tab and start over.": "测试期间切换了选项卡。请回到基准测试所在的选项卡，然后重新开始。",
  "Could not save the pass. Check the connection and start over.": "无法保存本轮结果。请检查网络连接后重新开始。",
  "Tab is unavailable. Open the tab containing the benchmark card.": "该选项卡不可用。请打开放有基准测试卡片的选项卡。",
  "Benchmark session is unavailable. Start over.": "基准测试会话不可用。请重新开始。",
  "Benchmark session expired. Start over.": "基准测试会话已过期。请重新开始。",
  "Benchmark is no longer running. Start over.": "基准测试已不在运行。请重新开始。",
  "Loona settings changed during testing. Start over.": "测试期间 Loona 设置发生了变化。请重新开始。",
  "Dashboard changed during testing. Start over.": "测试期间仪表盘发生了变化。请重新开始。",
  "Dashboard is unavailable. Refresh this page.": "仪表盘不可用。请刷新此页面。",
  "This card cannot be uniquely identified. Remove it manually.": "无法唯一确定这张卡片。请手动移除它。",
  "Dashboard changed. Refresh before removing the card.": "仪表盘已发生变化。请先刷新，再移除卡片。",
  "Early startup measurement is unavailable. Check Loona diagnostics and reload.": "无法进行早期启动测量。请查看 Loona 诊断信息并重新加载。",
  "Add the benchmark card to this tab before starting.": "开始前，请先把基准测试卡片添加到此选项卡。",
  "Too many benchmark sessions. Try again later.": "基准测试会话过多。请稍后再试。",
  "Benchmark route or pass changed. Start over.": "基准测试的页面路径或轮次发生了变化。请重新开始。",
  "Benchmark is already attached to a browser. Start over.": "基准测试已关联到一个浏览器。请重新开始。",
  "Benchmark pass is no longer attached. Start over.": "本轮基准测试已断开关联。请重新开始。",
  "Observation duration was interrupted. Repeat the benchmark.": "观察时段被中断。请重新运行基准测试。",
  "Too many interrupted passes. Keep the page visible and start over.": "被中断的轮次过多。请保持页面可见，然后重新开始。",
  "Compare native Home Assistant with your saved Loona settings on one tab.": "在一个选项卡上，比较原生 Home Assistant 与你保存的 Loona 设置。",
  "Benchmark progress": "基准测试进度",
  "show_charts must be a boolean": "show_charts 必须是布尔值（true 或 false）",
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
    "Loona cannot tell which dashboard is open",
    "Filtering is paused because Loona cannot identify the dashboard you are viewing. Reload Loona and refresh your browser. If it keeps happening, see Loona's diagnostics."
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
    "Check whether another dashboard already uses the address loona-statistics, and see Loona's diagnostics. Your other dashboards are untouched. Reload Loona once it is fixed."
  ],
  "scan_incomplete": [
    "Dashboard scan is incomplete",
    "Loona has disabled entity, device, and area filtering for all of your selected dashboards rather than risk breaking something. Check for removed dashboards or accounts, save auto-generated dashboards, and review dynamic cards or templates Loona cannot read, then press Rescan dashboards. Missing entity IDs alone do not cause this. Filtering resumes after a full scan."
  ],
  "resource_scan": [
    "Card file scan is incomplete",
    "Home Assistant is loading all card files for now. Check the Home Assistant log for a dashboard or file that failed to load, then rescan. Loona keeps retrying on its own."
  ],
  "resource_loading_failure": [
    "Some card files did not load",
    "Refresh your browser to try again. If it keeps happening, turn off Prioritize current tab and check the files under Card files."
  ],
  "missing_entities": [
    "Some entities your dashboards use do not exist",
    "Check these IDs for typos or deleted entities. Some may come back later. Missing entity IDs alone do not pause filtering."
  ],
  "excluded_dependencies": [
    "Excluded entities are used by cards",
    "Cards may show no data because of these exclusions. Remove them under Entity rules, or keep them if that is what you want."
  ],
  "unknown_cards": [
    "Custom cards may use additional entities",
    "Loona cannot always correctly guess every entity a custom card or pop-up requires. If a card is missing data, add the missing entities under Entity rules."
  ],
  "unmatched_resources": [
    "Loona cannot tell what some card files are for",
    "If a card or icon is missing, turn off Skip unused card files and reload. Look at the optional files under Card files and at the Home Assistant log."
  ],
  "dynamic_resources": [
    "Templates may need more card files",
    "If Loona finds a template or dashboard strategy it cannot read on any dashboard, every card file is loaded."
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
      dismiss.title=text(hass,"Hides this warning type for your account in this browser, including future occurrences. It does not resolve the problem or change Loona's behavior.");
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
