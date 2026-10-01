# Loona

Loona reduces the entity states sent to Home Assistant dashboards, can filter dashboard resource modules, and can prioritize visible graphs and temporarily pause continuous animations during loading. Select the dashboards and accounts to filter, then continue using your existing dashboards at your normal Home Assistant address.

Loona is experimental. Feature availability depends on your Home Assistant version and successful native API checks.

## Home Assistant compatibility

| Core version | Available features |
| --- | --- |
| **2024.5.5, 2024.12.5, 2025.6.3, 2026.1.3, 2026.8.3** | Entity, registry and resource filtering, resource dependency controls, dashboard/account selection, advanced entity rules, diagnostics and statistics. |
| **2026.9.3, 2026.9.4** | All of the above, plus visible-first graphs and animation pausing. |

Only the listed releases are admitted; this is not a claim that every intervening release is supported. On unlisted releases, the entity adapter reports a compatibility problem and preserves native subscriptions. The HACS installation minimum is **2024.5.5**.

Loona offers only available feature switches and options. The absence of an optional feature on an older supported release is expected and does not trigger a compatibility problem. Older releases do not load Loona's graph or animation modules. Native handlers, schemas, ownership and permission behavior are checked before entity filtering is installed; unexpected changes leave the affected feature bypassed.

## Install

For manual installation, copy the `custom_components/loona` directory into your Home Assistant configuration directory under `custom_components`, then restart Home Assistant.

For HACS, add `https://github.com/leecaochang/Loona` as a custom repository with category **Integration**, download Loona, and restart Home Assistant. You need access to the repository to download it.

Go to **Settings > Devices & services > Add integration**, search for **Loona**, and complete setup. Only one Loona integration can be configured.

## Set up

1. Select one or more dashboards. Loona uses their combined entity dependencies for every filtered account. Storage dashboards and YAML dashboards are supported. Save an automatically generated Overview dashboard before selecting it.
2. Choose **Selected accounts** and select the accounts to filter, or choose **All accounts**. Administrators can be selected and receive the same filtering as other selected accounts.
3. Reload any browser pages that were already open when Loona was added. New connections use the selected scope automatically.

**Targeting applies to the whole account.** Every tab, tablet, Companion session, and other application using that account's ordinary unfiltered entity subscription receives the same combined scope, regardless of which dashboard or page it opens. Accounts outside the selection retain their full entity state list. A separate account for a wall panel makes it easier to keep other sessions fully populated.

Loona preserves clients that explicitly request their own entity list or native filters. Home Assistant permissions still apply. Filtering reduces routine updates; it does not prevent an authorized client from requesting other entities through Home Assistant APIs.

## Controls

Open the **Loona** device under **Settings > Devices & services** to find the controls available on your version. They can also be used in normal Home Assistant automations.

| Control | What it does |
| --- | --- |
| Enabled | Master switch. Turn it off to restore full entity states, registry lists and subsequent resource lists, release graphs waiting to load, and restore paused animations. |
| Entity filtering | Turns entity state filtering on or off while keeping the master switch independent. Both switches must be on for filtering. |
| Registry filtering | Limits entity, device, area, floor, and label lists to dashboard dependencies and related metadata. Off by default. The Enabled switch must also be on. |
| Resource filtering | Optional, defaults to off. Forward required Lovelace modules, shared stylesheets and exceptions for selected accounts. Review the dependency preview first and hard-reload after changing it. |
| Visible-first graphs | Starts visible graphs immediately, then creates off-screen graphs one at a time after visible activity settles. Off by default. The Enabled switch must also be on. |
| Pause animations during loading | Temporarily pauses continuous card animations while a selected dashboard loads, then restores them automatically. Off by default. The Enabled switch must also be on. |
| Rescan dashboards | Reloads the selected configurations and rebuilds the scope. Use this for troubleshooting; ordinary dashboard changes are handled automatically. |

Switch states survive Home Assistant restarts. Switch changes update existing subscriptions managed by Loona without requiring a page reload. Turning filtering back on also applies to those subscriptions automatically.

Registry filtering includes parent devices, areas, floors, labels, and direct dashboard targets, even when a target has no entities. Entity display lists preserve Home Assistant's enabled-entry behavior. Registry changes and filter changes refresh existing managed registry subscriptions. Registry filtering works independently of Entity filtering and passes through full metadata when the dashboard scope is incomplete.

Editors, entity pickers, and administration pages may need metadata outside the selected dashboards. Turn off Registry filtering, use an unfiltered account, or turn off Enabled when using those features. Registry mutation commands and their permission checks remain native.

Dashboard edits, relevant registry changes, entity additions and removals, and group membership changes trigger automatic scans. Changes are grouped briefly before scanning. YAML file changes are checked about once a minute; the rescan button applies them sooner.

Options changes also update existing managed subscriptions. After reloading the integration itself, reload browser pages once so their subscriptions are managed by the new instance of Loona. Removing the integration restores full state subscriptions for connections it managed.

## Change settings

Use Loona's **Configure** menu under **Settings > Devices & services**.

| Menu | Use |
| --- | --- |
| Dashboards | Change which dashboards contribute to the shared scope. |
| Targets | Change the selected accounts or choose all accounts. |
| Filters and performance | Change filtering, visible-first graphs, and the temporary animation pause shown on the Loona device. |
| Extra entities | Include additional entities needed by custom cards or other sessions using a filtered account. |
| Advanced entity rules | Include whole domains or entity patterns, or exclude entities. |

For advanced rules, a domain is a name such as `light`. An entity pattern is a glob such as `sensor.room_*` or `light.*`. Loona combines discovered dependencies, extra entities, domain inclusions, and pattern inclusions; it then applies exclusions. Loona's own controls and statistics are always retained.

Excluding an entity used by a card can break that card. Loona reports a Repair when exclusions remove discovered dashboard dependencies. Prefer extra entities or inclusions when a card needs additional states.

## Statistics

The Loona device provides these sensors. Counts and percentages are gauges that can be displayed in ordinary history and statistics graph cards. They describe entity scope, not measured network bandwidth or CPU savings.

| Sensor | Meaning |
| --- | --- |
| Union entities | Entity IDs retained after inclusions, exclusions, and protection of Loona entities. Includes referenced entities that do not currently exist. |
| Current scope entities | Retained IDs that currently have a Home Assistant state. |
| Entity count reduction estimate | Percentage of current Home Assistant state IDs outside the computed scope. This estimate is still shown when filtering is bypassed. |
| Managed subscriptions | Ordinary unfiltered entity subscriptions seen by Loona, including accounts currently passing through. This is not a browser count. |
| Filtered subscriptions | Managed subscriptions currently receiving a restricted scope. |
| Last successful scan | Time of the most recent complete scope scan. |
| Scan duration | Duration of the latest scan in milliseconds. |

Subscription counts refresh about every 30 seconds. Each selected dashboard also has a related device with **Discovered entities** and **Unresolved entities** sensors. On Core 2026.9 these use native child devices; older releases use the native via-device relationship. These count that dashboard's dependencies before advanced rules; unresolved IDs have neither a registry entry nor a current state. They do not measure traffic for an individual dashboard.

## Supported dashboards and limitations

Loona discovers explicit entity references in nested cards, sections, badges, conditions, picture elements, camera fields, and action targets. It also reads name-to-entity mappings under `entities`, including the Sunsynk power flow card's sensor configuration. It expands groups and supported device, area, floor, and label targets. Referenced entity IDs that are currently missing remain in the scope so their states can appear later.

Loona scans supported templates without executing them. Jinja display and style templates can use literal entity references in `states`, `is_state`, `is_state_attr`, `state_attr`, and `has_value`, including conditions, local values, common numeric/text filters, and clock formatting. For `custom:button-card`, supported JavaScript includes the card's explicit `entity`, literal `states['sensor.example']` or `hass.states['sensor.example']` lookups, scalar calculations, conditions, and common number/string formatting. Every branch contributes dependencies, even when it is currently inactive.

Computed entity IDs, state enumeration, unknown helpers or filters, templated entity/target fields, and code outside the supported subset prevent a complete scan. Loona passes through full data for those cases. Extra entities do not make an unsupported template complete.

For `custom:auto-entities`, Loona supports include rules based on `entity_id` globs and `domain` patterns. It retains a conservative set of matches, including entities an auto-entities exclusion might hide. Other filters, template-generated entity lists, and dashboard strategies can prevent a reliable scan.

When a selected dashboard fails to load or has an unsupported dynamic construct, or when the combined scope is empty, Loona passes through full entity states and registry lists for the entire selected union and reports a scope problem. It resumes filtering automatically after a complete scan. Extra entities do not override an incomplete scan.

Unknown custom card types can still use their explicit references. Cards that calculate additional entity names or inspect `hass.states` may need extra entities or domain inclusions. Loona cannot infer every custom card's runtime dependencies.

This release filters entity state subscriptions and optionally registry lists and Lovelace resource lists. History, services, themes and other Home Assistant APIs retain native handling.

## Resource dependency preview and filtering

Open **Loona > Configure > Resource dependencies** to inspect the selected dashboards' combined JavaScript and CSS needs. Required resources stay enabled automatically, without a checkbox. Their list is collapsed by default under **Required resources**, which shows the count; expand it to see URLs and reasons. Other resources appear as individual checkboxes under Optional resources to load, with their URL, type and classification. New optional resources default to unchecked; checking one includes it and unchecking omits it while Resource filtering is enabled. It also reports unresolved custom types, templates/strategies that may hide dependencies, and exceptions whose URLs are no longer registered. The master switch and optional checkboxes are available on every admitted Core release when its resource adapter passes the native API checks.

Save your optional selections and turn on **Resource filtering** in the same form, then hard-reload the dashboard. This is the same persisted category switch found on the Loona device and under Filters and performance; turning it off restores the full native resource list. The separate Loona Enabled switch must also be on. Selected accounts receive required modules, shared stylesheets, the card-mod module, Browser Mod's frontend/Cast companion and checked optional resources. All selected dashboards contribute, including nested stacks, hidden conditional branches, popup configurations, card templates, badges, features and custom layouts. The filter preserves each release's native resource-list commands, original rows and URL query strings, and never deletes registrations or changes native resource editing permissions. Core 2024.5.5 exposes one list command; later admitted releases expose both aliases. Newly installed modules are evaluated from the current collection on the next request; dashboard edits refresh dependency discovery automatically.

Automatic mappings include Battery State Card, Plotly Graph, My Cards, Swipe Card, Universal Remote/Android TV Card, Multiple Entity Row, Energy Period Selector Plus, Custom Card Features, Calendar Card Pro, Config Template Card, HTML Template Card and Nodalia's verified card types, in addition to the existing supported bundles. A selected dashboard's root `kiosk_mode` configuration retains the standard kiosk-mode module. Without that configuration, kiosk-mode stays unclassified because browser settings or URL options can still require it. Home Assistant's built-in icons are unaffected; custom icon packs still need optional inclusion when unclassified.

Automatic mappings cover the standard local/HACS filenames for Bubble Card, Button Card, Mini Graph Card, ApexCharts Card, Sunsynk Power Flow Card, Horizon Card, Mushroom, Stack In Card, Vertical Stack In Card, Auto Entities, Layout Card and Yet Another Media Player. Layout Card's gap and layout-break helpers and custom layouts share its bundle. Card-mod remains included because it can style native cards and themes without appearing as a custom card. Stylesheets remain included because their effects can be global. Loona's graph and animation companion is registered separately as an extra frontend module and is unaffected.

This is bounded mapping coverage, not universal dependency discovery. Renamed bundles, remote module URLs, custom icon packs, separately registered helper libraries, modules loaded for side effects and generated card types may be unclassified. **Unclassified modules are omitted when filtering is enabled**, and a native Repair directs you to the preview. If a needed card, icon or helper is unclassified, check its resource under **Optional resources to load**, or turn off Resource filtering. Existing Always forward selections are preserved as checked optional resources. Optional selections are preserved across unrelated options changes. A selected resource that becomes required has its checkbox hidden while its saved preference is retained; it becomes editable again if it stops being required. A changed query string creates a different exception URL and is reported when the old URL disappears.

Resource targeting applies to the whole selected account, including resource editors and other dashboards, so use an unfiltered account or disable the filter when full resource lists are needed. An empty retained set returns an empty list. Failed dashboard loads or invalid account selections bypass resource filtering; an entity-discovery problem alone does not prevent the separate resource scan. An unexpected native resource API or ownership failure disables only this adapter and reports a compatibility problem.

HA loads resources once per page, so switches, exceptions, dashboard/resource changes and integration reloads require a full page reload to change downloads. Already loaded modules stay loaded. Core frontend bundles and unrelated extra frontend modules remain untouched. Resource-list filtering does not block direct asset requests or provide a security boundary, and fewer modules do not guarantee faster visible-card rendering.

## Visible-first graphs

Turn on **Visible-first graphs** on the Loona device and reload a selected dashboard using a targeted account. Loona registers its frontend module automatically; no resource entry, card wrapper, or duplicate dashboard is required. Saved dashboard configuration remains unchanged. The feature supports native sensor cards with `graph: line`, `custom:mini-graph-card`, and `custom:apexcharts-card` created through Home Assistant's native card container, including native stacks. Other cards and panel layouts use ordinary creation.

A graph already visible, or scrolled into view while earlier cards are still loading, starts immediately. Off-screen graphs wait for observable visible rendering and Home Assistant requests to settle, followed by a 750 ms quiet interval, then start one at a time during idle time. Custom cards have no universal finished-loading event, so this is a completion heuristic. Slow or continuous activity can delay background work; scrolling a graph into view still takes priority. This schedules card creation rather than filtering history requests or JavaScript resources.

Queued graphs use temporary placeholders with estimated sizes until the native card replaces them. Dashboard preview and editing create real cards immediately. Turning the graph switch or Enabled off releases pending graphs and restores ordinary creation; cards already created remain loaded. Turning it on affects subsequent card creation, so reload the view for a comparison. Initial installation, integration reloads, and upgrades require a browser page reload.

For troubleshooting, `window.loonaGraphLoadingReport()` shows queued and created graphs, and `console.table(window.loonaGraphLoadingTrace())` shows a bounded creation trace. These browser diagnostics do not measure total dashboard load time.

## Pause animations during loading

Turn on **Pause animations during loading** on the Loona device and reload a selected dashboard using a targeted account. This switch works independently of visible-first graphs and both filters. Loona pauses running, infinitely repeating CSS and Web Animations inside native dashboard cards while initial rendering and data requests settle. Live values and native controls continue updating. Finite transitions, already-paused animations, identifiable loading indicators, editing, previews, and panel layouts keep their ordinary behavior.

Motion resumes at an idle opportunity after a 750 ms quiet interval, immediately when you scroll, press a key, or touch the dashboard, or after at most 10 seconds. Turning this switch or Enabled off also resumes animations. When both performance switches are enabled, motion resumes before off-screen graphs begin their background loading. Later state updates and background graph creation do not restart the pause on a settled view. There is no universal custom-card loaded signal, so Loona uses visible render promises, DOM changes, images/fonts, resource activity, and outstanding Home Assistant requests as a completion heuristic. A stalled request cannot leave animations paused indefinitely.

This feature changes browser animations, not saved card styles or configuration. Animations implemented through JavaScript drawing loops, SVG SMIL, or inaccessible shadow roots are outside its scope. Reducing animation work during startup does not guarantee faster card completion; compare the same dashboard with this switch on and off. For troubleshooting, `window.loonaStartupMotionReport()` shows the pause phase, animation count, and restoration time.

## Performance measurements

The reproducible synthetic benchmark uses 10,000 sensor states and registry entries, 1,000 devices, 100 areas, 10 floors, and 100 labels. Its selected scope contains the first 200 sensors with their metadata relationships. Each state has a name, power unit/class, and a 64-byte padding attribute. A burst changes 1,000 evenly spaced sensors, including 20 in the selected scope.

Measurements below were taken with Loona 0.3.1, Core 2026.9.4, Python 3.14.6, and stock JS websocket client 9.6.0 on Node 22.23.2, running on an Apple M2 Ultra with 64 GiB RAM and macOS. Timings are medians of five samples after one warmup; Core serialization caches are warm. The full snapshot baseline uses Loona's disabled policy, and the live-update baseline uses an explicitly unfiltered native subscription.

| Measurement | Full data | Filtered data |
| --- | ---: | ---: |
| State snapshot entities | 10,000 | 200 |
| State snapshot JSON bytes | 2,640,912 | 52,860 |
| Full entity registry JSON bytes | 5,305,763 | 105,877 |
| Compact entity registry JSON bytes | 1,269,116 | 25,496 |
| Logical state events in the update burst | 1,000 | 20 |
| Update burst JSON bytes | 143,178 | 2,865 |
| Stock client snapshot processing | 12.45 ms | 0.23 ms |
| Stock client update burst processing | 2,263.44 ms | 0.74 ms |

JSON sizes include each logical event/result envelope before transport compression; they exclude websocket framing and grouped-message separators. Client timings cover JSON decoding and stock state collection updates on Node. They exclude network time, dashboard rendering, and tablet interaction. The approximately 98% reduction in these payloads is specific to this fixture, and is not a measured reduction in compressed network traffic or total CPU usage.

Registry filtering still parses the complete native list before selecting rows. In this fixture, a full entity-registry request took 2.86 ms with filtering bypassed and 13.19 ms with filtering active. Loona 0.3.1 uses Core's JSON decoder to reduce that filtering cost; the preceding decoder measured 28.24 ms on the same fixture. Smaller responses trade additional server processing for less data to transfer and process on the client.

To reproduce from a checkout with uv and Node.js installed, install the pinned development dependencies and run:

```sh
uv venv --python 3.14 venv
uv pip install --python venv/bin/python -r pyproject.toml --extra test
npm ci
LOONA_BENCHMARK=1 LOONA_BENCHMARK_OUTPUT=/tmp/loona-benchmark.json venv/bin/python -m pytest tests/test_benchmark.py -q -s
```

The benchmark creates an isolated in-memory Home Assistant fixture and writes aggregate results. It requires no Home Assistant login or running server. The ordinary test suite runs a smaller fixture to verify the measurements and final stock-client state.

For a real-browser comparison, use the same dashboard, account, network, and browser with a warm cache. Compare several page loads and normal card interactions with Loona's Enabled switch on and off, then restore it to on. Check that values update and service buttons work in both modes. Record the device model, browser/app version, and observed load times separately from the protocol measurements above. Real-browser rendering and interaction measurements remain outstanding.

## Troubleshooting

**A card is missing data:** turn off Enabled to check whether filtering is responsible. Verify that its dashboard is selected, then add any dependencies calculated by the card under Extra entities. Check advanced exclusions and press Rescan dashboards if needed.

**Entity filtering appears inactive:** ensure Enabled and Entity filtering are on, the account is selected, and Filtered subscriptions is greater than zero. Registry filtering has its own switch and does not contribute to the entity subscription count. Reload the page if it was open before setup or an integration reload. Check the Compatibility problem and Scope problem sensors and **Settings > Repairs**.

**Scope problem is on:** save the selected dashboards, remove deleted dashboard or account selections, and check for unsupported templates, strategies, or auto-entities filters. Both filters pass through full data while this sensor is on, even when their switches are enabled. Unresolved entity counts alone do not cause a bypass.

**Compatibility problem is on:** use a supported Home Assistant version and check for another integration replacing entity subscriptions, registry commands or resource-list commands. Turn off Loona while investigating. The affected filter returns to native handling; diagnostics identify registry and resource compatibility failures separately.

**Settings or another dashboard shows fewer entities:** that session uses a filtered account and shares its selected dashboard union. Add the needed entities, choose an unfiltered account, or turn off Loona's master switch.

Download diagnostics from the integration menu when reporting a problem at [Loona issues](https://github.com/leecaochang/Loona/issues). Include your Home Assistant version and the affected card type. Diagnostics redact account IDs, entity IDs, dashboard paths, resource URLs and dependency locations.

## License

[MIT](LICENSE).


## Compatibility testing

The native backend acceptance runner is `tests/core_compatibility.py`. It exercises real Core setup and unload, storage and YAML dashboard loading, inherited area/floor/label discovery, all six native registry lists and refetch notifications, native options and switch services, selected accounts, permissions, live state updates, scope replacement, bypass and persisted controls. The GitHub Actions compatibility matrix installs each admitted Core with its shipped package constraints and matching frontend, then runs this test with the appropriate Python version. The regular test suite also runs the acceptance runner on the development Core. Frontend scheduling and animation tests remain tied to the verified current frontend.

To reproduce a matrix entry, install its Core and matching frontend in an isolated environment using `.github/workflows/compatibility.yml`, then run `python tests/core_compatibility.py` from the repository. The development test extra pins Core 2026.9.4 and therefore requires Python 3.14.2 or newer; the integration itself supports Python 3.12 on its admitted older releases.
