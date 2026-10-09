
# Loona

English | [简体中文](README.zh-Hans.md)

[![CI](https://github.com/leecaochang/Loona/actions/workflows/compatibility.yml/badge.svg)](https://github.com/leecaochang/Loona/actions/workflows/compatibility.yml) [![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz) [![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.6%2B-41BDF5?logo=home-assistant&logoColor=white)](https://www.home-assistant.io)

Loona helps your Home Assistant Lovelace dashboards load and run lighter. Loona acts transparently - your dashboards, login, and Home Assistant URL all stay exactly the same. Works on any device with a current browser. No proxies - no extra software. Installs in seconds. **Set it and forget it.**

## How does Loona work?

Normally, whenever you open a dashboard, Home Assistant sends your browser the state of every entity (an entity is anything Home Assistant tracks, like a light or a sensor), and then keeps sending live updates for all of them. Most dashboards only need or show a small slice of that. Loona figures out which entities your chosen dashboards actually use and sends only those. Additionally, Loona can trim the entity, device, area, floor and label lists, skip loading card files you never use, delay drawing graphs that are off-screen, and pause animations while a page is busy.

## Results vary

**Less data does not guarantee a faster-feeling dashboard.** It helps, but how *fast* a page feels also depends on your browser, your device, and your network. Try it on your own setup and compare before you rely on it - Loona has a benchmark tool if you want to know the cold hard facts. If anything looks wrong, you can switch Loona off with the **Enabled** setting and Home Assistant goes back to normal.

## Dashboard screenshots

<p align="center"><img src="https://raw.githubusercontent.com/leecaochang/Loona/main/assets/settings.png" width="30%" alt="Settings" align="top"> <img src="https://raw.githubusercontent.com/leecaochang/Loona/main/assets/statistics.png" width="30%" alt="Statistics" align="top"> <img src="https://raw.githubusercontent.com/leecaochang/Loona/main/assets/benchmark.png" width="30%" alt="Benchmark" align="top"></p>

## Requirements

- Home Assistant (HA) 2024.6.0 or newer.
- A current Chrome, Edge, Firefox or Safari browser, or the Home Assistant Companion app.

Certain features are not supported on older versions of Home Assistant; it is recommended to use the latest Home Assistant release for full compatibility. Loona tests what your Home Assistant supports each time it loads and activates features accordingly, quietly falling back to normal Home Assistant behavior for any unsupported features.

## Install and first-time setup

Manual install: copy `custom_components/loona` into the `custom_components` folder in your Home Assistant configuration folder, then restart Home Assistant.

HACS: add [https://github.com/leecaochang/Loona](https://github.com/leecaochang/Loona) as a custom repository with category **Integration**, download Loona, then restart Home Assistant.

Then set it up:

1. Open **Settings > Devices & services > Add integration** and choose **Loona**.
2. Select the dashboards you want Loona to filter.
3. Choose **Selected accounts** or **All accounts**. Home Assistant permissions always apply; Loona never grants or removes anyone's access.
4. Optionally install the **Loona settings**, **Loona statistics** and **Loona benchmark** cards. Loona will create a **Loona** dashboard with those cards, visible to administrators only. Pick none to skip this step.
5. Refresh your browser so the new dashboard card files load.

## Supported languages

The Loona setup and Configure screens and the Loona dashboard cards are available in English and Simplified Chinese, following your HA profile language. Entity and device names follow Home Assistant's system language.

## Developed with AI

Loona development is led by a human software engineer with the assistance of an LLM. If you have any reservations about the quality or safety of this software, I encourage you to point your favorite LLM at the Loona repo and request a code audit.

## Using dashboard cards vs Settings

You can change settings either from the **Loona settings** dashboard card or from the integration's **Configure** menu. The dashboard cards are not required. For automations and monitoring, Loona also provides HA sensors, switches (for the on/off settings), and buttons (for rescanning and resetting statistics).

If you skipped the dashboard on install, you can add the cards to any dashboard yourself later with:

- `type: custom:loona-statistics-card`
- `type: custom:loona-settings-card`
- `type: custom:loona-benchmark-card`

All cards require an administrator account to be installed or viewed. Reload your open dashboard pages after installing or upgrading Loona to load the new cards.

### Settings

| Control | What it does |
| --- | --- |
| Enabled | **The master switch, on by default.** Turning it off resumes Home Assistant's normal behavior. Your settings are kept as-is. |
| Entity filtering | **On by default.** Sends only the entities your chosen dashboards use, plus any specific entities you added under Entity rules. |
| Device and area filtering | **Off by default.** Trims the entity, device, area, floor and label lists. |
| Live updates for current tab only | **Off by default.** After the first load, only the tab you are viewing keeps updating. Hidden tabs will not update until you view them. Requires Entity filtering enabled. |
| Skip unused card files | **Off by default.** Prevents loading the card files that none of your dashboards actually use. Reload your dashboard after changing this. |
| Delay graph loading | **Off by default.** Delays building graphs that are off-screen until the rest of the page has settled. Scrolling a graph into view loads it right away. |
| Idle mode | **Off by default.** After a period of no activity, the dashboard stops live updates and refreshes its values only at a set interval, until any interaction brings live updates back. You can set the **Idle after** time and the **Idle refresh** interval. Requires Entity filtering enabled. |
| Pause animations during loading | **Off by default.** Briefly pauses repeating animations while the dashboard starts up, then resumes them. |
| Pause off-screen animations | **Off by default.** Pauses repeating animations on cards that are scrolled out of view and resumes them when you scroll back. |
| Preload card files | **Off by default.** Starts downloading the current tab's card files before Home Assistant requests them. This does not change when they run. |
| Prioritize current tab | **Off by default.** Delays other tabs' card files until the current tab has rendered, then loads them gradually. Opening a pop-up, switching tabs or pages, or editing loads the remaining files right away. |

### Buttons

| Button | What it does |
| --- | --- |
| Rescan dashboards | Editing a dashboard normally triggers this automatically; press this button to force a rescan now. |
| Reset live statistics | Clears the live counters, recent page-load records and browser readings. Your Loona settings and Home Assistant's recorded history are untouched. |
| Restore defaults | Restores Loona back to default settings, as if you had installed it fresh. Also removes the Loona dashboard (if you have not edited it). You will need to select dashboards and accounts again before filtering resumes. An edited Loona dashboard, Loona cards you placed yourself, and recorded history are kept. |
| Reload page | Visible only when the dashboard card version and the integration version differ. |

# Advanced

**You now have enough information to get started with Loona. Continue reading for a more in-depth discussion of Loona's functionality.**

## Filtering

Loona filters a dashboard only when:

 1. The dashboard is one you selected.
 2. The account viewing the dashboard is covered by your **Selected accounts** or **All accounts** choice.
 3. Loona is enabled, with at least one setting enabled.
 4. Loona can read every card on the dashboard.

All other dashboards, and the rest of the Home Assistant UI, remain unaffected.

While you edit a dashboard, Loona sends it every entity. Filtering resumes when you stop editing.

What gets sent to the dashboard is only what your selected dashboards actually use, plus whatever you add under **Entity rules**.

Person, update and zone entities cannot be excluded, because the Home Assistant interface requires them.

**Entity rules** have two lists, Included and Excluded:

- You can add single entities, a whole entity type (like `sensor` or `light`), or patterns such as `sensor.kitchen_*`, which means every sensor whose name starts with `kitchen_`.
- The Excluded list takes precedence over Included.

### Caveats

Loona cannot always correctly guess every entity a custom card or pop-up requires. Examples of things that may only see the filtered data:

- A quick-bar search.
- Pop-ups.
- Service pickers opened from a filtered dashboard.

Resolve this by adding the missing entities under Entity rules, or switch filtering off while you work.

Cards that ask for specific entities in an unusual way, or that listen to raw events, can still receive everything.

### Why a dashboard is not filtered

Loona filters a dashboard only when it can work out every entity that dashboard needs. If it cannot read a card, Loona sends that dashboard every entity, as if you had not selected it, and keeps filtering your other selected dashboards. The statistics card then shows **Some dashboards are not filtered** under **Warnings and checks**, listing each card that caused it by dashboard, view and card, with the reason.

If none of your selected dashboards can be read, or a selected account no longer exists, Loona stops filtering everywhere and shows **Dashboard scan is incomplete** instead.

| Cause | Example | How to fix |
| --- | --- | --- |
| The dashboard or account is not selected | Viewing a dashboard you did not select | Select the dashboard and account in Configure. |
| A template that works out which entities to read as it runs | A button-card template such as `hass.states[variables.room]` | Name the entities directly in the template, such as `states['light.kitchen']`, or move the calculation into a template sensor and show that sensor. Adding the entities in Configure does not help, because Loona still cannot tell what else the template might read. |
| An auto-entities rule Loona cannot read | A `template` filter, a `/regex/` pattern, or a rule that filters only by `state` or `attributes` | Add a `domain`, `entity_id` or `area` to the rule. |
| A dashboard strategy | The Map dashboard, or a dashboard built by a custom strategy | Do not select it, or edit it and save its cards. |
| An unsaved auto-generated Overview | The default Overview before you edit it | Edit the Overview and save its cards. |
| A selected dashboard or account no longer exists | A dashboard you deleted after selecting it | Update your dashboard and account choices again in Configure. |

These do not stop filtering:

- Templates in markdown cards, in Mushroom template cards, chips, badges and titles, and in card-mod or UIX styles. Home Assistant fills these in itself, so your browser does not need their entities.
- auto-entities rules that filter by `domain`, `entity_id` or `area`, even if they also filter by `state` or `attributes`.
- button-card and Bubble Card templates that name their entities directly, such as `states['light.kitchen']`.

Missing entity IDs alone do not pause filtering.

## Card files

These files are typically JavaScript libraries installed via HACS. Every dashboard loads all the card files registered in Home Assistant's dashboard resources, even if that dashboard does not use them. Home Assistant's automatically generated dashboards and maps do not use custom card files.

Selecting **Skip unused card files** will load only the card files your dashboards need.

### Caveats

 Loona will still load anything it cannot safely judge, such as:

- Style sheets
- Helpers such as card-mod, UIX and kiosk-mode.
- Miscellaneous files Home Assistant is told to load.
- Any newly installed files it has not yet seen.
- Templates or dashboard strategies Loona cannot read (if one is found on any dashboard, every card file is loaded)

Simple templates used by button-card, Mushroom, Bubble Card, card-mod, and UIX are understood by Loona.

**Extra card files to load**, under **Card files** in the settings card or Configure menu, lets you keep specific card files that Loona would otherwise skip, such as files your pop-ups or other features need even though no dashboard uses them. This is not a common use case.

**Prioritize current tab** loads the visible tab first. The rest of the tabs load one at a time when the browser is idle, shortly after the page has finished displaying the first tab. If the tab never reports that it is ready, the remaining card files load after ten seconds.

Opening a pop-up, switching pages or tabs, editing, or turning the option off loads all card files immediately.

**Preload card files** tells the browser to start downloading the files the current tab needs even before it is asked for them. Nothing runs earlier, and its benefit depends on your cache and network.

Always reload the dashboard after you make a change. Check what works on your setup before relying on these - if a card or icon goes missing, switch off these settings and reload.

## Graphs and animations

**Delay graph loading** works with Home Assistant's built-in sensor cards using `graph: line`, Mini Graph Card and ApexCharts Card.

Visible graphs always load immediately. Graphs out of view wait until the page has settled for a moment, then start one at a time. Because custom cards give no common "I'm done" signal, this is an educated guess. Scrolling to a hidden graph loads it right away.

**Pause animations during loading** pauses repeating browser animations while the dashboard starts, then lets them run.

**Pause off-screen animations** pauses repeating animations on cards that are not visible and resumes them when visible. Animations driven by JavaScript timers or some other methods are outside the scope of these options.

## Experimental options

### Live updates for current tab only

The first load of a dashboard contains all the entities your selected dashboards use. When this setting is enabled, only the tab you are viewing will keep getting live updates. Other tabs and other selected dashboards will keep their last known values.

Opening a tab, opening a pop-up, or editing a dashboard refreshes values right away.

If Loona cannot determine which tab you are looking at, it will ignore this setting and keep the entire dashboard live. Custom pop-ups that read entities from hidden tabs may show old values, so add those entities under Entity rules, or just leave this option off.

### Idle mode

When Idle mode is on and you have not touched the page for the Idle after time (default 5 minutes), live updates pause. This is not recommended for informational dashboard displays, as the dashboard contents will "freeze" until refreshed or interacted with again.

This affects ordinary live connections only - cameras, independent clocks, card timers and raw event listeners will keep going.

#### Idle after
- How long the page can go untouched before Idle mode starts, from 1 to 60 minutes (default 5).
#### Idle refresh
- How often a fresh snapshot of current values is loaded while idle, from 1 to 60 seconds (default 60). Changes in between are not displayed.
- At 0, values remain frozen until you interact.

## Statistics card and diagnostics

The **Loona statistics** dashboard card shows how much Loona is filtering, whether anything fell back to normal behavior, and what recent page loads looked like. The numbers are live and refresh every 30 seconds. What the terms mean:

- **Sent** is the number of entity updates passed on to your dashboards per second.
- **Filtered out** is the number of entity updates Loona held back per second.
- **Updates filtered out** is the percentage of updates held back during the latest sampling interval.
- **Estimated entities trimmed** is the percentage of Home Assistant's entities outside Loona's configured inclusion set. It describes potential entity reduction, not measured update reduction, and remains visible when filtering is off.
- **Totals and entities** shows updates sent and filtered out since reset, the number of entities currently included, and how many live connections are being filtered. Optional charts visualize the entity percentage and connection counts.
- **Recent page loads** shows how many entities and card files were filtered out of those available for each dashboard's latest recorded page load. It does not measure loading time.
- **Browser performance** lists the 20 entities with the most updates sent since reset, alongside browser reports of slow frames, script work and event subscriptions that may bypass filtering. These reports cover only part of the browser's work.
- **Warnings and checks** explains detected problems and suggested actions. **Dismiss** hides that warning type for your account in this browser, including future occurrences. It does not resolve the problem or change Loona's behavior; other warning types can still appear.


### Counting rules

The counters measure entity updates on live connections belonging to your selected accounts. Each update counts once per connection: if the same change would reach three connections, it counts as three updates.

A live connection is the link a dashboard tab keeps open to Home Assistant. Each open tab usually has one connection, sometimes more, so opening more tabs increases the totals.

The initial entity snapshot sent when a connection starts is not counted. Neither are changes to entities the account cannot access, updates for unselected accounts, or changes to Loona's own entities.

Updates blocked by filtering count as filtered out. Updates passed through count as sent, including while filtering is bypassed.

These figures measure entity updates, not data size, bandwidth, CPU usage or loading speed.

The live counters reset when Home Assistant restarts or when you press **Reset live statistics**. **Since** shows when the current counting period began.

### Charts

**Show statistics charts** is on by default and sits below the charts. If you place this statistics dashboard card yourself, adding `show_charts: false` starts it with charts off; the browser's saved choice wins afterward.

Chart history is kept only in memory and clears on reset or restart.

## Dashboard benchmark card

Choose **Loona benchmark** in setup or under **Loona dashboard cards** in the settings card to place it on the generated Loona dashboard. Generally you do not need to run the benchmark on the Loona dashboard itself; you should test your own dashboards. Before running an actual benchmark, you must temporarily install this card on the dashboard you want to test. You must be a HA administrator to run the benchmark.

1. Configure Loona with the filters and performance settings you want to test.
2. Manually add the card `type: custom:loona-benchmark-card` to the dashboard tab you want to test, preferably near the top with another card visible.
3. Press **Go**.

The benchmark compares native Home Assistant with your saved Loona settings on that one tab, using two warm-ups and three alternating pairs. Allow about four minutes and keep the page in the foreground without scrolling, interacting or resizing. Page reloads are automatic.

**Cancel benchmark** stops the run instantly.

A Home Assistant toast notification will inform you when the benchmark is complete.

The finished **Benchmark Results** image shows visible-card readiness, initial JSON data, registered card files loaded, live update rate, and browser blocking when supported. It contains aggregate readings and versions only.

**Detailed report** opens a report, starting with an executive summary, followed by detailed measurement commentary.

- **Copy** copies a PNG image to the clipboard.
- **Save** downloads a PNG image to disk.
- **Copy text** copies the report as markdown text.
- **Save text** downloads the report as a `.md` file.

**Start over** clears this tab's result and resets the card for another run.

**Remove** removes the benchmark card from a UI-managed dashboard - YAML dashboards and manually altered cards require manual removal.

### Caveats

**Card file sizes:** Safari and the Home Assistant Companion app for iOS and macOS use WebKit, which may not report decoded file sizes for cached scripts, even when the files loaded successfully. After the benchmark ends, Loona tries to recover the missing file sizes using cache-only reads. If any pass still lacks a file size, **Card files loaded** instead compares file counts for both modes.

**Browser blocking:** Loona detects support for [Long Animation Frames](https://developer.mozilla.org/en-US/docs/Web/API/PerformanceLongAnimationFrameTiming#browser_compatibility). Chrome and Edge 123+ support it; Firefox, Safari and the iOS and macOS Companion apps (WebKit) do not. Unsupported browsers skip the blocking observer and omit its chart, summary entry and per-pass column.

- The benchmark measures reloads with the browser cache, not cold-cache loads or a guaranteed hard refresh.
- Readiness waits for visible cards and icons to render, visible images and fonts to load, and pending native requests to finish. Cameras, charts and custom content may still be loading.
- File sizes cover observed registered resource entry files, not every imported dependency.
- No activity, missing readings, errors and overlapping timing ranges are identified explicitly.
- Idle savings only appear if the configured idle threshold is reached.
- Cross-origin restrictions can also hide sizes.


## HA sensors

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

Each selected dashboard also has its own Loona device with **Referenced entities** and **Entities not found** counts. Not found means there is neither a current state nor a registry entry for it. Deselecting a dashboard removes its device and deletes the long-term and short-term statistics of these two sensors.

## Troubleshooting

**Missing text or data on a card or in a picker:** turn Enabled off and compare. Check your Entity rules, selected dashboards and accounts. Remember that pop-ups opened from a filtered dashboard only see its data.

**Missing card or icon:** turn off Skip unused card files and reload. Look at the optional files under Card files and at the Home Assistant log.

**Nothing seems filtered:** check Enabled, Entity filtering, accounts and dashboard selections. Look at Compatibility, Dashboard scan and any notices in the cards. Refresh your browser after upgrading; short startup hiccups retry automatically.

**Incomplete scan or unfiltered dashboards:** open **Warnings and checks** on the statistics card. **Dashboard scan is incomplete** or **Some dashboards are not filtered** lists each card that caused it; "Why a dashboard is not filtered" above explains how to fix each one. Missing entity IDs alone do not cause this.

**Limited compatibility:** check Compatibility and the cards to see which feature fell back. Features that work stay available on 2024.6.0 or newer. Another HA integration may also be interfering with Loona. Temporarily disable it to test.

Report problems at [Loona issues](https://github.com/leecaochang/Loona/issues) with your Home Assistant version, the affected card type, and the integration's diagnostics or a benchmark report. Downloaded diagnostics and the benchmark image hide account and entity IDs, dashboard paths and card file addresses. The detailed report and its Markdown copy list your saved Loona settings and browser details, which can include dashboard and account names, entity names and card file addresses, so review them before posting.

## Uninstall

Remove Loona from **Settings > Devices & services**. This removes its card files and its saved settings, deletes the long-term and short-term statistics of the Loona sensors, and deletes the Loona dashboard if you have not edited it. Remove any Loona cards you manually placed yourself. If you installed through HACS, remove its files there afterward.

## Development tests

Set up once, with uv and Node.js 22 installed:

```sh
uv venv --python 3.14 venv
uv pip install --python venv/bin/python -r pyproject.toml --extra test
npm ci
```

The browser animation test also needs Chrome or Chromium and is skipped if none is found.

Run the full test suite, pyflakes and mypy like this:

```sh
venv/bin/python -m pytest tests/ -q
venv/bin/python -m pyflakes custom_components/loona/ tests/
venv/bin/python -m mypy custom_components/loona/
```

The full development suite is pinned to Core 2026.10.0 and needs Python 3.14.2 or newer. Loona itself only needs the Python version your Home Assistant requires.

## License

[MIT](LICENSE).
