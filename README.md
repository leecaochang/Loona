# Loona

Loona is a Home Assistant integration that helps your dashboards load and run lighter.

Normally, when you open a dashboard, Home Assistant sends your browser the state of every entity (an entity is anything Home Assistant tracks, like a light or a sensor), then keeps sending live updates for all of them. Most dashboards only show a small slice of that. Loona figures out which entities your chosen dashboards actually use and sends only those. It can also trim the entity, device, area, floor and label lists, skip card files you never use, hold back graphs that are off-screen, and pause animations while a page is busy.

Your dashboards, login and Home Assistant address stay exactly the same. Nothing extra needs to be installed.

Loona is experimental, and smaller data does not guarantee a faster-feeling dashboard. Sending less data helps, but how fast a page feels also depends on your browser, your device and your network. Try it on your own setup and compare before you rely on it. If something looks off, you can switch Loona off in one click and Home Assistant goes back to normal.

## Requirements

- Home Assistant 2024.6.0 or newer. The HACS minimum is the same.
- A current Chrome, Edge, Firefox or Safari browser. Current Chrome is what Loona is tested with; older browsers have not been tested.

Loona checks what your Home Assistant version supports every time it loads. If something is not supported on your setup, Loona quietly falls back to normal Home Assistant behavior for that one feature, and the rest keep working. You will see which features fell back in the statistics card, the Loona device and the Home Assistant log.

## Install and first-time setup

Manual install: copy `custom_components/loona` into the `custom_components` folder in your Home Assistant configuration folder, then restart Home Assistant.

HACS: add [leecaochang/Loona](https://github.com/leecaochang/Loona) as a custom repository with category **Integration**, download Loona, then restart Home Assistant.

Then set it up:

1. Open **Settings > Devices & services > Add integration** and choose **Loona**. Only one instance can be installed.
2. Pick the dashboards you want Loona to filter.
3. Choose **Selected accounts** or **All accounts**. Home Assistant permissions still apply; Loona never grants or removes anyone's access.
4. Optionally pick the **Loona settings**, **Loona statistics** and **Loona benchmark** cards. Loona then creates a **Loona** dashboard with those cards, visible to administrators only. Pick none to skip it.
5. Refresh your browser so the new card files load.

## Dashboard cards and settings

You can change settings from the **Loona settings** card or from the integration's **Configure** menu. The Loona device also has switches and buttons for the same things, which is handy for automations.

If you skipped the generated dashboard, you can still add the cards to any dashboard yourself with `type: custom:loona-statistics-card` and `type: custom:loona-settings-card`. Both need an administrator account. After upgrading Loona, reload your open dashboard pages. If the card version and the integration version differ, the cards offer a **Reload page** button (in the settings card it stays unavailable while you have unsaved edits).

### Controls

| Control | What it does |
| --- | --- |
| Enabled | The master switch, on by default. Turning it off puts Home Assistant's normal behavior back. Your other settings are kept. |
| Entity filtering | On by default. Sends only the entities your chosen dashboards use, plus anything you add under Entity rules. |
| Device and area filtering | Off by default. Trims the entity, device, area, floor and label lists. |
| Live updates for current tab only | Off by default. After the first load, only the tab you are looking at (plus shared items, Entity rules and parts of the Home Assistant interface) keeps updating. Other tabs show their last known values and refresh when you open them. Needs Entity filtering. |
| Skip unused card files | Off by default. Leaves out card files that none of your dashboards use. Reload the page after changing it. |
| Delay graph loading | Off by default. Waits to build graphs that are off-screen until the rest of the page has settled. Scrolling to a graph loads it right away. |
| Load current tab first | Off by default. Loads the card files for the tab you opened first, then the others once the page has rendered. Opening a pop-up, switching pages or editing loads the rest right away. |
| Preload card files | Off by default. Starts downloading the card files the current tab needs a little earlier. Home Assistant still runs them in its normal order. |
| Pause off-screen animations | Off by default. Pauses repeating animations on cards that are scrolled out of view and resumes them when you scroll back. |
| Pause animations during loading | Off by default. Pauses repeating animations while the dashboard starts up, then resumes them. |
| Idle mode | Off by default. After a period with no activity, stops live updates and refreshes values only now and then. Any click, key press, scroll or navigation brings live updates back. Needs Entity filtering. |
| Idle after (minutes) | Part of Idle timing. How long to wait before going idle, from 1 to 60. The default is 5. |
| Idle refresh (seconds) | Part of Idle timing. How often to refresh while idle, from 0 to 60. The default is 60. Choose 0 to freeze values until you interact with the page. |

Buttons:

| Button | What it does |
| --- | --- |
| Rescan dashboards | Looks through your dashboards again right now. Editing a dashboard normally triggers this on its own, and Loona also checks now and then to catch changes made in YAML. |
| Reset live statistics | Clears the live counters and recent page-load records. Your settings and Home Assistant's recorded history are untouched. |
| Restore defaults | Asks for confirmation first. Puts every switch back to its default, clears your dashboard and account choices, Entity rules, card-file exceptions and live statistics, and removes the generated Loona dashboard if you have not edited it. You will need to choose dashboards and accounts again before filtering resumes. Dashboards you edited, cards you placed yourself and recorded history are kept. |
| Reload page | Shows up only when the card version and the integration version differ. Reloads the page so everything matches. |

A few things worth knowing:

- The settings card and Configure menu have these sections: Dashboards, Accounts, Filters and performance, Idle timing, Entity rules (Included and Excluded), Card files and Loona dashboard.
- In the settings card, turning Enabled off greys out the other fields and Save buttons but keeps their values. Live updates for current tab only and Idle mode are greyed out while Entity filtering is off.
- Reset live statistics, Restore defaults and removing the Loona dashboard from the card selection all ask you to confirm. Cancel leaves everything as it was.
- Restore defaults also clears that account's chart and dismissed-warning preferences in the current browser.
- Loona only updates or removes the Loona dashboard it generated, and only while you have not edited it. If you delete that dashboard yourself, Loona will not recreate it, even after a reload. If you edit it, you manage it by hand from then on.
- The Loona cards are in English and Simplified Chinese, following your profile language. Other Chinese profiles fall back to English. Entity and device names follow Home Assistant's system language.

## Dashboard benchmark card

Choose **Loona benchmark** in setup or under **Loona dashboard cards** in the settings card to place it on the generated Loona dashboard. The card registers after Home Assistant finishes frontend bootstrap, so browser startup cannot discard its registration. For another dashboard, manually add `type: custom:loona-benchmark-card` to the dashboard tab you want to test, preferably near the top with another card visible. Sign in as an administrator and press **Go**. The card compares native Home Assistant with your saved Loona settings on that one tab, using two warm-ups and three alternating pairs. Allow about four minutes and keep the page in the foreground without scrolling, interacting or resizing. Page reloads are automatic; **Cancel benchmark** stops the run. Hidden pages repeat the interrupted pass when you return.

The finished **Benchmark Results** SVG shows visible-card readiness, initial JSON data, registered card files loaded, live update rate and browser blocking. The image contains aggregate readings and versions only. Data and update comparisons show percentage changes; overlapping timing ranges say **No clear timing difference**, while unsupported blocking is identified separately. **Copy** copies a PNG when image clipboard access is available; on HTTP it opens the PNG for the browser's native **Copy Image** command. **Save** downloads the same PNG. Exports use a fixed size and the colours recorded at completion, including exports from the completion notification dialog. Filenames include the Loona version, dashboard name and UTC completion time. **Detailed report** opens a scrollable area capped at 360px, starting with an executive summary, followed by friendly settings labels, concise pass readings, interpretation and measurement limits. **Copy text** and **Save text** export that report separately. To inspect individual card files, use Home Assistant's dashboard resources or the browser Network panel. The browser keeps the latest result for up to ten tested tabs for this account. A completion toast offers **Show results**, including when the installed card is hidden.

This measures reloads with the browser cache, not cold-cache loads or a guaranteed hard refresh. Readiness covers known visible card elements and loading indicators; custom content, graphs and cameras can finish later. JSON sizes are logical UTF-8 messages before network compression. File sizes cover observed registered resource entry files, not every imported dependency; cross-origin servers may hide their sizes. Browser blocking requires Long Animation Frames and covers the live observation window. It does not measure total CPU, GPU, memory or battery use. No activity, missing readings, errors and overlapping timing ranges are identified explicitly. Idle savings require reaching the configured idle threshold. Settings that do not apply to the chosen account or tab will not produce a filtering benefit.

Benchmark sessions preserve Home Assistant permissions and bypass Loona only on the initiating connection during native passes. They leave saved Loona settings and dashboard configuration unchanged. **Start over** clears this tab's displayed result and any failed browser session, and closes the disclosure. **Remove** asks for confirmation and removes only an exact, uniquely identifiable card from a UI-managed dashboard; YAML dashboards and ambiguous wrappers require manual removal. Removing it from an untouched generated Loona dashboard also updates the saved card selection; if it was the only selected card, that generated dashboard is removed. Historical trend charts are not included.

## How filtering decides what to send

Loona only steps in when all three of these are true: the account is one you selected, the person is looking at a dashboard you selected, and Loona understands that dashboard fully. Settings pages, Developer Tools, other pages, dashboards you did not select, and anyone who is not selected get normal Home Assistant data. Moving between pages updates what Loona does for that browser tab straight away.

What gets sent is everything your selected dashboards use, plus whatever you add under **Entity rules**. Person, update and zone entities are always included, because the Home Assistant interface needs them.

**Entity rules** have two lists, Included and Excluded:

- You can add single entities, a whole entity type (like `sensor` or `light`), or patterns such as `sensor.kitchen_*`, which means every sensor whose name starts with `kitchen_`.
- Excluded wins over Included. The interface entities above stay protected either way.
- The search boxes look for every word you type anywhere in the name or ID, so `bathroom fan` finds `Bathroom ceiling fan`. Friendly names show above the entity IDs.

Things to keep in mind:

- Quick-bar search, pop-ups, dashboard editors and service pickers opened from a filtered dashboard only see the filtered data. If you need an entity there, add it under Entity rules, or switch filtering off while you work. Loona cannot guess every entity a custom card or pop-up might want.
- If even one selected dashboard cannot be fully scanned (for example, it uses a template, strategy or auto-entities rule that Loona cannot read, or an unsaved auto-generated Overview), Loona pauses entity and device and area filtering for all of them rather than risk hiding something. Save generated dashboards and check dynamic cards. An entity ID that simply does not exist does not trigger this.
- Settings changes take effect on already-open pages automatically. Cards that ask for specific entities in an unusual way, or listen to raw events, can still receive everything.

### Live updates for current tab only

This option is separate and experimental. The first load still contains everything your selected dashboards use. After that, only the tab you are viewing keeps getting live updates, along with shared items, Entity rules and interface entities. Other tabs and other selected dashboards keep their last known values, which can go stale until you open them. Opening a tab (including by URL or the back button), opening a pop-up or editing a dashboard refreshes values right away. If Loona cannot tell which tab you are on, it keeps the whole dashboard live. Custom pop-ups that read entities from hidden tabs may show old values; add those entities under Entity rules or leave this option off. It does not reduce every source of browser work, so try it on your device first.

### Idle mode

When Idle mode is on and you have not touched the page for the Idle after time (default 5 minutes), live updates pause. If Idle refresh is above 0, you get a fresh snapshot of current values at that interval (default 60 seconds); changes in between are not replayed. At 0, values stay frozen until you interact. Clicks, key presses, scrolling, changing tabs, opening pop-ups or editing bring back live values. It affects ordinary live connections only. Cameras, independent clocks, card timers and raw event listeners can keep going. Home Assistant itself and its recorded history carry on as usual.

## Card files

Each page loads the card files (custom card code) your dashboards use. **Skip unused card files** leaves out ones that none of your configured dashboards need, including dashboards you did not select, since a page loads its card files once.

Loona keeps anything it cannot safely judge: style sheets, helpers such as card-mod, UIX and kiosk-mode, extra files Home Assistant is told to load, and newly installed files it has not seen. If Loona cannot be sure, it keeps the full list. Dashboards that use Home Assistant's built-in strategies and map need no custom card files. Simple templates in button-card, Mushroom, Bubble Card, card-mod and UIX styles are understood; templates that generate cards, unknown strategies and incomplete scans keep the full list.

Under **Card files** in the settings card or Configure menu, you can tick **Extra card files to load** for optional files your pop-ups or other features need even though no saved dashboard uses them. Files that are always kept have no checkbox. If a file is known from HACS, its name shows above its address.

Turning the option off brings the full list back, but a page that is already open needs a reload to pick up files it skipped. Reload whenever you change this or compare before and after. This never changes your stored resource list or Home Assistant's own files.

For selected dashboards that are not the default one, Loona also asks for the dashboard's configuration and card file list a little earlier, so the work overlaps. How much that helps depends on your network.

**Load current tab first** puts the tab you opened first. The rest load one at a time when the browser is idle, shortly after the page has finished showing the first tab. If the page never reports that it is ready, the remaining files are released after ten seconds. Opening a pop-up, switching pages or tabs, editing, or turning the option off releases them immediately. If a file fails to load, the rest are released and that file gets one retry. This does not reduce total work, only reorders it, and slow hardware can still stutter briefly. Reload after enabling it.

**Preload card files** only asks the browser to start downloading the files the current tab needs. Nothing runs earlier, and its benefit depends on your cache and network. It is not a measured speedup.

Check what works on your setup before relying on these. If a card or icon goes missing, switch off Skip unused card files and reload.

## Graphs and animations

**Delay graph loading** works with Home Assistant's built-in sensor cards using `graph: line`, Mini Graph Card and ApexCharts Card, including when they sit in stacks. Other cards and layouts load as usual, and dashboard editing and previews always build real cards.

Graphs you can see load immediately. Graphs further down wait until the page has settled and been quiet for a moment, then start one at a time. Because custom cards give no common "I'm done" signal, this is an educated guess. A placeholder holds the space meanwhile, and scrolling to one loads it right away.

**Pause animations during loading** pauses repeating browser animations while the dashboard starts, then lets them run. **Pause off-screen animations** pauses repeating animations on cards that are scrolled away and resumes them on return. Both leave one-time transitions, loading spinners, visible pop-up animations and animations that were already paused alone. Interaction, navigation, editing, previews, turning the option off or hiding the page resume them. Animations driven by JavaScript timers or some other methods are outside what these options can pause.

Turning Enabled off bypasses all of this and releases anything waiting. Code a page has already loaded stays until you reload it.

## Statistics card and diagnostics

The **Loona statistics** card shows how much Loona is filtering, whether anything fell back to normal behavior, and what recent page loads looked like. The numbers refresh about every 30 seconds, and the first rate after startup or a reset appears at the next refresh. Hover, focus or tap the question mark icons beside sections and actions for a short explanation. Escape or a tap elsewhere closes it.

What the terms mean:

- **Sent** is the number of entity changes passed on to your dashboards.
- **Filtered out** is the number of entity changes Loona held back because the dashboard did not need them.
- **Updates filtered out** is the share of changes held back.
- **Estimated entities trimmed** is the share of Home Assistant's entities that sit outside what your dashboards use. It is shown even while filtering is off.
- **Totals and entities** shows the running totals since the last reset, how many entities Loona currently keeps, and the moon and constellation charts.
- **Recent page loads** shows the latest page load Loona saw for each dashboard.
- **Browser performance** lists the 20 entities that sent the most updates since the last reset, plus what browsers report about slow frames and scripts, and a flag for raw event listeners that can get around filtering. It is partial: it cannot tell you the total loading time.
- **Warnings and checks** lists problems with steps to fix them. **Dismiss** hides that type of warning for your account in this browser only, with no reminder. New kinds of warning can still appear, and dismissing never changes how Loona behaves.

Counting rules: the counters count real entity changes your selected accounts would receive on their live connections. A live connection is the link a dashboard tab keeps open to Home Assistant; each open tab has one, sometimes more, so several tabs raise the totals. First snapshots, denied entities, unselected accounts and changes to Loona's own entities are not counted. When filtering is bypassed, changes count as sent. These numbers are not bytes, bandwidth, CPU or loading speed. They reset when Home Assistant restarts or when you press Reset live statistics. The footer line "Counting since" shows when the live counters started (Home Assistant start or the last reset).

### Charts

**Show statistics charts** is on by default and sits below the charts. It adds:

- Moon gauges. The lit side fills from the left and equals the percentage; the dark side is the remainder, with the exact percentage underneath. One moon shows Updates filtered out and another shows Estimated entities trimmed.
- A stream chart that overlays Sent as a solid line and Filtered out as a dashed line on one scale, for up to 15 minutes. Hover or touch it to read any point.
- A constellation of live connections, where each filtered connection is a lit star, next to the label "Connections filtered / total".

Chart history is kept only in memory and clears on reset or restart. Charts animate once when first shown, unless your device asks for reduced motion. Turning them off removes them completely. The choice is saved per account in each browser, so a desktop and a slow phone can differ. If you place the statistics card yourself, `show_charts: false` starts it with charts off; the browser's saved choice wins afterward.

### Loona device

The Loona device in Home Assistant has these sensors:

| Entity | In plain words |
| --- | --- |
| Included entities, Available included entities | How many entities Loona keeps, and how many of those currently have a state |
| Estimated entities trimmed | The share of current entities outside that set |
| Tracked connections, Filtered connections | Live connections Loona manages, and how many are currently narrowed |
| Entity updates sent per second, Entity updates filtered out per second | Average changes passed on and held back in the latest measured interval |
| Share of updates filtered out | The share of counted changes held back in that interval |
| Entity updates sent, Entity updates filtered out | Running totals since Home Assistant started or the last reset |
| Compatibility, Dashboard scan | Whether features are available, and whether discovery of your dashboards is complete |
| Last successful scan, Scan duration | When the latest full scan finished and how long it took |
| Version, Warnings | The installed version, and the number of active warnings (not counting informational checks) |

Each selected dashboard also has its own device with **Referenced entities** and **Entities not found** counts. Not found means there is neither a current state nor a registry entry for it. These counts are about what a dashboard asks for, not how much traffic it causes.

Loona does not create Home Assistant Repairs items, and removes old ones. Compatibility changes and failures are written to the Home Assistant log.

## Troubleshooting

**Missing data on a card or in a picker:** turn Enabled off and compare. Check your Entity rules, selected dashboards and accounts. Remember that pop-ups opened from a filtered dashboard only see its data.

**Missing card or icon:** turn off Skip unused card files and reload. Look at the optional files under Card files and at the Home Assistant log.

**Nothing seems filtered:** check Enabled, Entity filtering, accounts and dashboard selections. Look at Compatibility, Dashboard scan and any notices in the cards. Refresh your browser after upgrading; short startup hiccups retry automatically.

**Incomplete scan:** check for removed dashboards or accounts, save auto-generated dashboards, and review dynamic cards or templates Loona cannot read. Home Assistant's normal data is used while a scan is unsafe. Missing entity IDs alone do not cause this.

**Limited compatibility:** check Compatibility and the cards for which feature fell back. Features that work stay available on 2024.6.0 or newer. Reload Loona after fixing the cause, and refresh your browser for page changes. Another integration that already handles the same part of Home Assistant can turn off the matching Loona feature.

Report problems at [Loona issues](https://github.com/leecaochang/Loona/issues) with your Home Assistant version, the affected card type and the integration's diagnostics. Downloaded diagnostics hide account and entity IDs, dashboard paths, card file addresses and where things are referenced.

## Uninstall

Remove Loona from **Settings > Devices & services**. This removes its card files and its saved settings, and deletes the Loona dashboard if you have not edited it. Dashboards you edited or created yourself are kept for you to manage. Remove any Loona cards you placed yourself and refresh your browser pages. If you installed through HACS, remove its files there afterward.

Uninstalling also permanently deletes the long-term and short-term statistics of the Loona sensors. Your dashboard entities and their statistics are not touched. Ordinary state history follows the Recorder's usual retention. If the database cleanup fails or takes over 15 seconds, it is logged and may finish afterward.

## Performance measurements

These are lab numbers from a synthetic setup, not a promise about your dashboard.

The fake setup has 10,000 sensors with registry entries, 1,000 devices, 100 areas, 10 floors and 100 labels. The selected scope has 200 sensors and their metadata. Each state has a name, a power unit and class, and a 64-byte padding attribute. An update burst changes 1,000 evenly spaced sensors, 20 of which are in scope.

Measured on Loona 0.9.1, Core 2026.9.4, Python 3.14.6 and the stock JS websocket client 9.6.0 on Node 22.23.2, on an Apple M2 Ultra with 64 GiB RAM running macOS. Timings are medians of five samples after warmup, with Home Assistant's own caches warm. These are measured after a selected dashboard has been reported, so they show the size of the filtered replies, not normal browser startup.

| Measurement after context | Full data | Scoped data |
| --- | ---: | ---: |
| State snapshot entities | 10,000 | 200 |
| State snapshot JSON bytes | 2,640,852 | 52,850 |
| Full entity registry JSON bytes | 5,305,698 | 105,870 |
| Compact entity registry JSON bytes | 1,269,116 | 25,496 |
| Logical events in update burst | 1,000 | 20 |
| Update burst JSON bytes | 143,209 | 2,861 |
| Stock client snapshot processing | 12.68 ms | 0.24 ms |
| Stock client update processing | 2,396.18 ms | 0.76 ms |

A separate startup comparison measures the first state stream. When Loona's context arrives first, it sends 200 states in 52,959 JSON bytes, with no reconciliation. Native startup sends 10,000 states in 2,640,919 bytes. If the startup hook falls back and context arrives late, full data plus reconciliation uses 3,026,084 bytes, about 15% more than native startup. The test setup contains only sensors, so on a real installation the always-included interface entity types can make the scope bigger. Live Chrome checks confirm a single scoped first snapshot and first-request card file omission, but none of these checks measure how fast the page looks.

JSON sizes include the message wrappers before compression, but not websocket framing. Node timings include decoding and state updates, but exclude network time, dashboard rendering and tablet interaction. Smaller replies can cost more server work: the full entity registry request took 4.40 ms while bypassed and 15.55 ms while filtered, because Loona has to read the full response first.

To reproduce, with uv and Node.js installed:

```sh
uv venv --python 3.14 venv
uv pip install --python venv/bin/python -r pyproject.toml --extra test
npm ci
LOONA_BENCHMARK=1 LOONA_BENCHMARK_OUTPUT=/tmp/loona-benchmark.json venv/bin/python -m pytest tests/test_benchmark.py -q -s
```

The benchmark runs in memory, with no Home Assistant server or login. Ordinary tests use a smaller setup and check the final stock-client state. To judge real use, compare real page loads and interactions yourself with the same dashboard, account, device, browser and network, and reload when changing card file settings.

## Development tests

Run the full test suite, pyflakes and mypy like this:

```sh
venv/bin/python -m pytest tests/ -q
venv/bin/python -m pyflakes custom_components/loona/ tests/
venv/bin/python -m mypy custom_components/loona/
```

The full development suite is pinned to Core 2026.9.4 and needs Python 3.14.2 or newer. Loona itself only needs the Python version your Home Assistant requires.

<details>
<summary>Technical details</summary>

- **Startup hook:** when a compatible filter is enabled, a small inline script on selected dashboard URLs queues dashboard context before Home Assistant's first requests, without waiting for a reply. Other named routes skip normal filtering setup. A session-marker guard remains available with filtering off so an explicitly started benchmark can authorize its native passes; it starts no benchmark observer without that marker. The root URL `/` needs one parallel lookup of dashboard visibility and default-page preferences (up to two seconds after sign-in), which can add a network round trip even for an untargeted account. Failed lookups, unsupported root routing or a timeout can leave the first snapshot full; later filtering still works.
- **Capability checks:** each load probes entity schemas, scoped snapshots, live diffs and read permissions; registry schemas and update subscriptions; card file commands and results; frontend registration and browser hooks; connection-local dashboard reporting; and HTML ownership, startup promise and root routing. Failed backend features appear in diagnostics, the cards and the log, and their switches become unavailable while keeping saved values. The browser checks its own card container before changing anything.
- **Tested versions:** native backend acceptance runs cover Core 2024.6.0, 2024.6.4, 2024.12.5, 2025.6.3, 2026.1.3, 2026.8.3, 2026.9.2, 2026.9.3 and 2026.9.4. These are samples, not an allowlist. Graph and animation acceptance uses the frontend shipped with Core 2026.9.4; older frontends may keep normal loading while backend filtering still works.
- **Browser syntax:** the bundled cards and graph code use ES2020 syntax such as optional chaining, so Safari older than 13.1 cannot parse them. The page reporter also uses optional catch bindings. Python 3.12 or newer is the syntax floor.
- **Reconnect and replay:** after startup or reload, an early native feed can trigger one stock-client reconnect so its original requests are replayed through Loona. The reporter drops stale cached entities when the new first snapshot arrives. After an integration unload, it restores native methods and probes for a reload for about one minute. Explicit native subscription scopes (including an explicit empty `entity_ids` list) keep native behavior.
- **Card file scope:** Loona filters native registered resource-list responses. It does not change stored registrations, core frontend bundles, extra module registrations or direct file requests. UIX's native module also satisfies legacy `custom:mod-card` dependencies.
- **Load ordering:** Load current tab first releases files one at a time after a dashboard-ready event plus 750 ms of quiet, with a ten-second deadline. Preload card files adds same-origin `modulepreload` hints and keeps query strings; no module is evaluated early and no saved route cache is used. Graph delay waits for rendering and Home Assistant requests to settle plus 750 ms of quiet.
- **Animations:** only running browser animations with infinite iterations are paused. JavaScript timers, SMIL and closed shadow roots are out of scope. Off-screen pausing uses viewport observation and watches open card trees only as needed.
- **Statistics internals:** Browser performance uses Long Animation Frames, same-origin script paths and forced layout time where the browser supports them; reports are kept separately from the counters, limited to the latest report for each of at most 30 dashboards, and cleared with live statistics. Script URL queries and foreign origins are excluded, and downloaded diagnostics redact script paths and entity IDs. Entity attribution keeps at most 1,024 entity IDs. Chart history is bounded in memory and sent to the card only while charts are enabled.
- **Uninstall cleanup:** statistics are deleted for Loona sensors verified through native registry records, including previously removed ones and records left by earlier uninstalls. An entity ID now reused by another integration, or an unregistered active entity, is protected. Cleanup uses the Recorder's own queue.
- **Automated checks:** the commit- and image-digest-pinned GitHub Actions workflow runs eight representative Core and frontend environments with the full pytest suite (including frontend and Chromium acceptance tests), pyflakes, mypy, hassfest and HACS validation. Dependabot watches action, Python and npm dependencies. The matrix does not control runtime admission.

</details>

## License

[MIT](LICENSE).
