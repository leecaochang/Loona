# Loona

Loona reduces initial entity snapshots and live updates on selected Home Assistant Lovelace dashboards. It also offers optional registry and card resource filtering, delayed graph creation, and temporary animation pausing. Your dashboards, login and Home Assistant address stay the same. No additional runtime software is required.

Loona is experimental. When a compatible entity, registry or resource filter is enabled, an inline hook queues dashboard context before Home Assistant's initial requests on selected dashboard URLs. It does not wait for a context acknowledgement or an extra module to load. Other named routes bypass the hook, and turning off Enabled removes it from newly served pages. The root URL `/` needs one parallel lookup of native dashboard visibility and default-panel preferences; this can add a network round trip even for an untargeted account. That lookup waits at most two seconds after authentication. Failed probes, unsupported root routing or a timeout can leave the initial snapshot full; later filtering still works. Smaller payloads do not guarantee faster page loading.

## Supported Home Assistant versions

Loona requires Home Assistant Core 2024.6.0 or newer. Every integration load, including initial setup and reload, probes the installed native capabilities. An unfamiliar version number does not disable compatible features.

| Capability probe | Fallback when unavailable |
| --- | --- |
| Entity schemas, scoped snapshots, live diffs and read permissions | Full native entity feeds |
| Registry schemas, list envelopes and update subscriptions | Full native registry lists |
| Registered resource commands, schemas and list results | All native card files |
| Native config, frontend registration and browser card hooks | Normal graph creation and animations |
| Connection-local dashboard reporting | Full entity, registry and resource data on unrecognized connections |
| Native HTML ownership, startup promise and root routing | Normal startup with later filtering; unfamiliar root routing affects `/` only |

Features pass or fail independently, so a failed probe can leave other filtering available. Failed backend features appear in diagnostics, the cards and the Home Assistant log; their device switches retain saved preferences but become unavailable. The browser checks its actual card container before changing any method. Missing hooks keep native loading, with a browser-local notice when loading optimizations were requested. A late native container can be probed successfully after it loads. Another integration owning a required handler can disable that feature.

Representative native backend acceptance runs cover Core 2024.6.0, 2024.6.4, 2024.12.5, 2025.6.3, 2026.1.3, 2026.8.3, 2026.9.2, 2026.9.3 and 2026.9.4. These are test samples, not an allowlist or a guarantee of every future internal API. Graph and animation acceptance currently uses the native frontend shipped with Core 2026.9.4; older frontends may retain native loading while backend filtering still works.

The integration syntax requires Python 3.12 or newer. Use the Python version required by your Core release. The HACS installation minimum is also 2024.6.0.

Use a current Chrome, Edge, Firefox or Safari browser. The bundled cards and graph module require ES2020 syntax, including optional chaining; Safari versions older than 13.1 cannot parse them. The panel reporter also uses optional chaining and optional catch bindings. Failed capability checks retain native behavior where the module can execute. Current Chrome is covered by browser acceptance tests; older browser engines have not been tested.

## Install and set up

For manual installation, copy `custom_components/loona` into the `custom_components` folder in your Home Assistant configuration directory, then restart Home Assistant.

For HACS, add [leecaochang/Loona](https://github.com/leecaochang/Loona) as a custom repository with category **Integration**, download Loona, then restart Home Assistant.

1. Open **Settings > Devices & services > Add integration** and choose **Loona**. Only one instance can be installed.
2. Select the dashboards to filter.
3. Choose **Selected accounts** or **All accounts**. Home Assistant permissions still apply; Loona does not restrict or grant access.
4. Optionally select the **Loona settings** card, the **Loona statistics** card, or both. Loona creates an administrator-only **Loona** dashboard containing those cards. Choose neither to skip it.
5. Refresh the browser to load the installed modules.

## Controls and settings

Use the **Loona settings** card or the integration's **Configure** menu. The Loona device also exposes switches and action buttons.

| Control | Behavior |
| --- | --- |
| Enabled | Master switch, on by default. Turning it off restores managed live entity feeds and native registry responses. |
| Entity filtering | On by default. Keeps entities discovered in selected dashboards and added by Entity rules. |
| Current dashboard updates | Off by default. Keeps the current dashboard, Entity rules and interface entities live while retaining the other selected dashboards' cached values. Requires Entity filtering. |
| Registry filtering | Off by default. Narrows native entity, device, area, floor and label lists. |
| Resource filtering | Off by default. Skips recognized card bundles unused by all configured dashboards. A browser reload is required to change loaded files. |
| Delay graph loading | Off by default. Defers eligible off-screen graphs until visible work settles. Scrolling to one loads it immediately. |
| Delay card files | Off by default. Loads the current dashboard's modules first, then other known modules after rendering. Navigation and editing release pending files immediately. |
| Pause animations during loading | Off by default. Temporarily pauses repeating animations during dashboard startup, then resumes them. |
| Rescan dashboards | Runs discovery now. Dashboard edits normally trigger a scan; periodic checks cover YAML changes. |
| Reset live statistics | Clears live counters and page-load records without changing settings or recorded Home Assistant history. |

Configure includes **Dashboards**, **Accounts**, **Filters and performance**, **Entity rules**, **Cards** for resource exceptions, and **Loona dashboard** for the generated dashboard. Card selections can be changed after setup. Loona updates or removes only its exact unedited generated configuration. An edited dashboard requires manual management. Deleting the owned dashboard opts out of automatic recreation, including after a reload. Upgrading an older entry without a card selection does not create a new dashboard.

You can place `type: custom:loona-statistics-card` and `type: custom:loona-settings-card` on your own dashboards even if you skip the generated one. Both require an administrator account.

## Entity and registry scope

Each browser connection reports its current panel. Entity and registry filtering applies to selected accounts while viewing selected dashboards. Settings, Developer Tools, other panels, unselected dashboards and clients without a report receive native data. Navigation updates the current connection's scope. Person, update and zone entities are always retained for the Home Assistant interface.

The entity scope is the union of selected dashboard dependencies and your Entity rules. Add individual entities, whole domains, known entity IDs or domain patterns such as `sensor.*`. Previously saved custom patterns remain available for removal or reuse. Exclusions override ordinary inclusions, while interface entities remain protected. The settings card searches large entity lists on the server rather than downloading the full catalog.

Quick-bar search, dialogs, dashboard editors and service selectors opened within a selected dashboard still see its scoped data. Add entities they need under Entity rules, or disable filtering while using broader selectors. Loona cannot infer every dependency of a custom card or popup.

**Current dashboard updates** is a separate experimental control. The first snapshot still contains the selected-dashboard union. Ongoing updates then cover the current dashboard, including all its views, plus explicit Entity rules and protected interface entities. Other selected-dashboard values remain cached and can become stale. Navigating to another selected dashboard refreshes its current values without removing the retained union. Native dialogs, including more-info, and dashboard editing refresh the union and temporarily keep it live. Closing them resumes dashboard delivery. A deleted inactive entity is reconciled when the subscription next changes. Initial payload and included-entity counts still describe the union; live counters reflect the narrower delivery.

This control uses the existing complete-scan requirement and native read permissions. Older reporters keep union delivery until the browser refreshes. Disabling it refreshes union values; disabling Entity filtering or Enabled, leaving selected dashboards or unloading Loona restores native behavior. Custom popups or cards that read entities from other dashboards may not report native dialog events; add those entities under Entity rules to keep them live, or leave this control off. No entity outside the existing permitted scope is added by opening a dialog. Raw event subscriptions and explicit native scopes retain their behavior and can still deliver unrelated updates. Validate on your device before relying on the control; it does not reduce every source of browser CPU work.

One incomplete selected dashboard pauses entity and registry filtering for the whole union. This avoids dropping data whose dependencies cannot be determined. Save automatically generated dashboards and check unsupported templates, strategies or dynamic auto-entities rules. Missing but valid entity references alone do not cause bypass.

Ordinary subscriptions are reconciled when rules, accounts, dashboard selections or switches change. Explicit native subscription scopes, including an explicit empty `entity_ids` list, retain native behavior. After startup or reload, an early native feed can trigger one stock-client reconnect so its original requests are replayed through Loona. The reporter removes stale cached entities locally when the ordinary feed receives its new first snapshot; explicit subscriptions retain their original events. A transient reporter error is retried. After an integration unload, the reporter restores native methods and probes for a reload for about one minute. A reload during that window reattaches context and can recover ordinary feeds through one stock-client reconnect. Refresh after a slower reload or a Loona upgrade to load the current frontend code.

## Card resource filtering

Lovelace loads registered modules once for the whole page session. Loona therefore considers the saved configurations of all configured dashboards, including unselected ones, before omitting a recognized unused card bundle. It retains CSS, global helpers such as card-mod, UIX and kiosk-mode, native extra modules, and files whose usage it cannot safely classify. UIX's registered native module also satisfies legacy `custom:mod-card` dependencies. Newly installed unknown files are retained automatically. Native Map, the unsaved default Overview and recognized built-in strategies do not require registered custom card files. Supported scalar templates in button-card display/styles, Mushroom template fields, Bubble styles and card-mod/UIX styles allow resource filtering when their expressions can be classified safely. Card-generating templates, unknown template contexts, custom or unknown strategies, unmatched custom types or an incomplete resource scan retain the full list. An unsaved selected Overview still pauses entity and registry filtering because its generated entity dependencies cannot be determined safely.

Under **Cards**, automatically retained files have no checkbox. Select additional known optional bundles needed by popups or other features outside the saved configurations. Saved unavailable files remain removable. Disabling Resource filtering restores the registered list, but cannot unload JavaScript already running in a page or load a previously skipped module by itself. Reload after resource changes or when comparing enabled and disabled behavior.

This feature filters native registered Lovelace resource-list responses, including Core's first request on `/` and `/lovelace/` when the startup hook establishes selected context. It does not change stored registrations, core frontend bundles, extra module registrations or direct file requests. Startup fallback or an incomplete resource dependency scan retains the full list.

For a selected non-default dashboard, the startup hook requests its native configuration and registered resources early. The panel consumes the prefetched configuration once on the same socket and route; forced refreshes remain native. Core's own root-route resource preload is preserved. This overlaps requests without waiting for a context acknowledgement, and its benefit depends on network latency.

**Delay card files** is a separate experimental control. It prioritizes the saved configuration of the initial selected dashboard, including all its views. CSS, classic JavaScript, global helpers, unknown files, extra modules and files selected under Cards load immediately. Other recognized optional modules load one at a time when the browser is idle, starting after a dashboard-ready event and 750 ms of quiet. A ten-second deadline releases remaining modules if rendering never reports readiness. The files retain their original URLs and load later in the same page session; this does not reduce their eventual memory or total evaluation cost.

Changing the view, dashboard or panel, entering editing, forcing a configuration refresh, or disabling the feature releases pending files immediately. A module error also releases the remaining queue and makes one bounded retry with the same URL. A timed-out request stays in flight without a duplicate insertion. Missing or incompatible startup hooks, uncertain dependency scans and late context reporting keep normal loading. This control works with or without Resource filtering; when filtering is enabled, globally omitted files remain omitted. Refresh after enabling it. Validate on your device before relying on it; background evaluation can still cause brief pauses on slow hardware.

## Graphs and animations

Delayed loading supports native sensor cards with `graph: line`, Mini Graph Card and ApexCharts Card, including native stacks. Other cards and panel layouts load normally. Dashboard editing and previews create real cards immediately.

Visible graphs start immediately. Background graphs wait for visible rendering and Home Assistant requests to settle, followed by 750 ms without activity, then start one at a time when the browser is idle. Custom cards have no common completion signal, so this is a heuristic. Temporary placeholders reserve estimated space and expose their loading state. Disabling the feature starts pending graphs immediately.

Animation pausing affects running browser animations with infinite iterations in supported dashboard views. Finite transitions, progress indicators, previews and already paused animations are preserved. Interaction, navigation, disabling, page hiding or the maximum startup interval resumes owned pauses. JavaScript, SMIL and closed-shadow animations are outside this feature's scope.

Turning off Enabled bypasses these features and releases queued work. Modules and lightweight reporting hooks already loaded in a page remain until it reloads. Newly served pages omit the startup hook while Enabled is off; disabling Loona preserves its settings.

## Diagnostics

The **Loona statistics** card shows live update rates, totals, filtering status and the latest observed full page load for each dashboard. Visible statistics refresh about every 30 seconds. The first rate reading after startup or reset appears at the next interval. Both bundled cards show **Warnings and checks** with recovery steps.

Live counters count logical permission-eligible entity changes per tracked ordinary selected-account feed. Multiple tabs can increase totals. Initial snapshots, denied entities, explicit scopes, unselected accounts and changes to Loona's own entities are excluded. When filtering is bypassed, eligible changes count as sent. These figures do not measure bytes, bandwidth, CPU or loading speed.

**Performance diagnostics** lists the 20 busiest tracked entities by sent updates since reset. Attribution keeps at most 1,024 entity IDs and reports updates beyond that limit. Administrators can measure the current dashboard for 30 seconds. Supported browsers report Long Animation Frames, same-origin script paths and forced layout time; earlier buffered script entries are separated from the measurement window. Long frames cover only part of CPU work and cannot establish total loading time. Browser subscription counts flag raw state-change event feeds that can bypass entity filtering; feeds created before the reporter attached may be unclassified. Measurements are browser-supplied, kept separately from native counters, bounded to the latest report for each of at most 30 dashboards, and cleared with live statistics. Script URL queries and foreign origins are excluded; downloaded diagnostics redact script paths and entity IDs.

| Device diagnostic | Meaning |
| --- | --- |
| Included entities / Available included entities | Computed scope size / scope IDs with a current state |
| Estimated entity reduction | Fraction of current state IDs outside the scope, even while filtering is off |
| Tracked / Filtered update feeds | Owned ordinary subscriptions / subscriptions currently narrowed |
| Entity updates sent / filtered per second | Changes averaged over the latest measured interval |
| Live update reduction | Fraction of counted live changes omitted during that interval |
| Compatibility / Dashboard scan | Feature availability / completeness of selected dashboard discovery |
| Last successful scan / Scan duration | Latest complete entity scan time / latest scan duration |
| Version / Warnings | Installed version / active warning conditions, excluding informational checks |

Each selected dashboard has a device with **Referenced entities** and **Entities not found** counts before Entity rules. Missing means neither a current state nor a registry entry exists. These counts do not attribute traffic to individual dashboards. Loona's diagnostic entities are included in filtered feeds only when referenced or explicitly selected.

Counters and page-load records reset on reload or restart. **Reset live statistics** also clears them. Recorded Home Assistant history remains unchanged. No Home Assistant Repairs notifications are created; legacy Loona Repairs are removed. Compatibility changes and native-operation failures are recorded in the Home Assistant log, with debug details for scan failures.

The integration and cards support English and Simplified Chinese. Traditional Chinese profiles fall back to English. Cards follow profile language and number/time preferences. Native entity and device labels follow Home Assistant's system language.

## Performance measurements

The synthetic fixture contains 10,000 sensor states and registry entries, 1,000 devices, 100 areas, 10 floors and 100 labels. The selected scope contains 200 sensors and their metadata. Each state includes a name, power unit/class and a 64-byte padding attribute. A burst changes 1,000 evenly spaced sensors, of which 20 are in scope.

Measurements use Loona 0.9.1, Core 2026.9.4, Python 3.14.6 and stock JS websocket client 9.6.0 on Node 22.23.2, on an Apple M2 Ultra with 64 GiB RAM and macOS. Timings are medians of five samples after warmup; native serialization caches are warm. The following requests occur after a selected dashboard report, so these are scoped-response measurements, not normal browser startup measurements.

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

A separate bootstrap comparison measures the context acknowledgement and initial state stream. Context first sends 200 states in 52,959 JSON bytes, with no reconciliation. Native startup sends 10,000 states in 2,640,919 bytes. If the startup hook falls back and context arrives late, full data plus reconciliation uses 3,026,084 bytes, about 15% more than native startup. The fixture contains only sensors; interface-domain retention can increase the scope on a real installation. Stock-client tests exercise Core's preload sequence, and live Chrome checks confirm a single scoped first snapshot and first-request resource omission, including the root route and a delayed reporter. These checks do not measure visible rendering speed.

JSON sizes include logical event/result envelopes before compression, excluding websocket framing and grouped-message separators. Node timings include decoding and state collection updates, excluding network time, dashboard rendering and tablet interaction. Registry filtering parses the full native response: the full registry request took 4.40 ms while bypassed and 15.55 ms while filtered. Smaller replies can cost more server processing.

To reproduce with uv and Node.js installed:

```sh
uv venv --python 3.14 venv
uv pip install --python venv/bin/python -r pyproject.toml --extra test
npm ci
LOONA_BENCHMARK=1 LOONA_BENCHMARK_OUTPUT=/tmp/loona-benchmark.json venv/bin/python -m pytest tests/test_benchmark.py -q -s
```

The fixture runs in memory without a Home Assistant server or login. Ordinary tests use a smaller fixture and check final stock-client state. Compare real browser loads and interactions separately, using the same dashboard, account, device, browser and network, and reload when changing resource policy.

## Troubleshooting

**Missing card data or selector choices:** turn off Enabled and compare. Check Entity rules, selected dashboards and accounts. Dialogs opened inside a filtered dashboard retain its scope.

**Missing card or icon:** turn off Resource filtering and reload. Check optional files under Cards and the Home Assistant log. Unknown global modules are retained automatically.

**No filtered feed:** check Enabled, Entity filtering, accounts and dashboard selections. Check Compatibility, Dashboard scan and the cards' notices. Refresh after upgrading; transient startup reporting failures retry automatically.

**Incomplete scan:** check removed dashboards/accounts, save generated dashboards and review unsupported dynamic constructs. Native data is retained while a scan is unsafe. Missing entity IDs alone do not make it incomplete.

**Limited compatibility:** inspect the failed capability probe in diagnostics. Compatible features remain usable on Core 2024.6.0 or newer. Reload Loona after resolving missing APIs or conflicting handler ownership; refresh the browser for frontend changes.

Report problems at [Loona issues](https://github.com/leecaochang/Loona/issues) with the Core version, affected card type and integration diagnostics. Diagnostics redact account/entity IDs, dashboard paths, resource URLs and reference locations.

## Uninstall

Remove Loona through **Settings > Devices & services**. This unregisters its modules, deletes its saved controls and dashboard ownership record through native Stores, and removes only its unedited owned dashboard. Native entry selections are deleted with the entry, so a new installation starts with defaults. Edited or foreign dashboards are preserved for manual management. Remove manually placed Loona cards and refresh browser pages. If installed through HACS, remove its files there afterward.

Uninstall also permanently deletes short-term and long-term Recorder statistics for sensors verified as belonging to Loona. Native registry records include previously removed Loona sensors and retained records from earlier uninstalls; an entity ID currently reused by another integration or an unregistered active entity is protected. Dashboard entities and their statistics are preserved. Ordinary state history follows Recorder's usual retention policy. Cleanup uses Recorder's own queue; a database failure or a wait longer than 15 seconds is logged, and queued deletion can finish afterward.

## Development tests

The commit- and image-digest-pinned GitHub Actions workflow defines eight representative native Core/frontend environments, the full pytest suite including frontend and Chromium acceptance tests, pyflakes, mypy, hassfest and HACS validation. Dependabot monitors action, Python and npm dependencies; validator image digests require deliberate updates. The native matrix exercises the minimum baseline and representative later releases. It does not control runtime admission. Update native frontend fixtures and their provenance when the container changes.

The native runner checks setup/unload, storage and YAML loading, discovery, permissions, options, controls, resources, live updates, dashboard ownership and restoration. The full development suite is pinned to Core 2026.9.4 and requires Python 3.14.2 or newer. Loona's own syntax floor remains Python 3.12. Use each older Core's matching interpreter and constraints for its native runner.

```sh
venv/bin/python -m pytest tests/ -q
venv/bin/python -m pyflakes custom_components/loona/ tests/
venv/bin/python -m mypy custom_components/loona/
```

## License

[MIT](LICENSE).
