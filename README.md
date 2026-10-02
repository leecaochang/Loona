# Loona

Loona reduces the entity data Home Assistant sends to your dashboards. It can also skip unused card files, load visible graphs first and pause animations briefly during startup. Your dashboards, login and Home Assistant address stay the same.

Loona is experimental. Smaller responses can help slower devices, but do not guarantee faster card loading.

## Supported Home Assistant versions

| Core version | Features |
| --- | --- |
| **2024.5.5, 2024.12.5, 2025.6.3, 2026.1.3, 2026.8.3** | Entity, registry and resource filtering; settings; diagnostics; statistics. |
| **2026.9.3, 2026.9.4** | All of the above, plus visible-first graphs and animation pausing. |

Only these releases have been tested and enabled. Loona shows only features available on your version. An older supported release does not show the graph or animation controls. On an unlisted release, Loona reports a compatibility issue and leaves entity updates to Home Assistant. HACS requires at least **2024.5.5**.

Loona also checks the Home Assistant functions it uses before enabling a feature. If a check fails or another integration replaces those functions, the affected feature stops filtering.

## Install and set up

For manual installation, copy `custom_components/loona` into the `custom_components` folder in your Home Assistant configuration directory, then restart Home Assistant.

For HACS, add `https://github.com/leecaochang/Loona` as a custom repository with category **Integration**, download Loona, then restart Home Assistant. You need access to the repository to download it.

1. Open **Settings > Devices & services > Add integration** and choose **Loona**. Only one instance can be installed.
2. Select the dashboards the filtered accounts will use. Storage and YAML dashboards are supported. Save an automatically generated Overview dashboard before selecting it.
3. Choose **Selected accounts** or **All accounts**. Administrators can be filtered too.
4. Reload any browser pages that were already open.

Loona creates an administrator-only **Loona** dashboard with statistics and settings cards. It does not edit your existing dashboards.

Entity, registry and resource filtering applies only while a selected account is viewing a selected dashboard. Settings, Developer Tools, other panels and unselected dashboards receive normal Home Assistant data. Each browser tab reports its own panel automatically; clients without panel context receive normal data. If the report arrives after startup, Loona applies filtering to the existing updates. Reload browser pages after upgrading so they load the panel reporter. Home Assistant permissions still apply.

Home Assistant permissions still apply. Loona does not restrict access: an authorized app can still request other entities through Home Assistant's APIs. Requests that already specify their own entity list or filters are left unchanged.

## Controls

Use the **Loona settings** card, or open the Loona device under **Settings > Devices & services**. The switches and buttons can also be used in automations.

| Control | What it does |
| --- | --- |
| Enabled | Master switch. Off restores ordinary updates and lists, starts waiting graphs and resumes paused animations. Reload the browser to load previously skipped card files. |
| Entity filtering | Sends only entities needed by the selected dashboards and your include/exclude rules. On by default. |
| Registry filtering | Shortens entity, device, area, floor and label lists to the items your dashboards need. Off by default. Turn it off if an editor is missing choices. |
| Resource filtering | Loads required card files and any additional files you checked under **Card files**. Other optional files are skipped. Off by default. Reload after changing file choices. |
| Visible-first graphs | Starts on-screen graphs immediately. Off-screen graphs start later, or immediately when you scroll to them. Off by default. |
| Pause animations during loading | Pauses repeating card animations during startup and resumes them automatically. Off by default. |
| Rescan dashboards | Checks dashboard changes now. Ordinary changes are detected automatically; YAML files are checked about once a minute. |
| Reset live statistics | Clears live update totals, rates and page-load records. Entity counts, settings and recorded Home Assistant history are unchanged. |

All features need **Enabled** on. Registry, resource, graph and animation options work independently of Entity filtering. Switch states survive restarts. Changes to entity and registry filtering apply to existing updates; graph scheduling affects cards created afterward. Reload a view to compare graph loading. Resource changes need a browser reload because files already loaded cannot be unloaded.

After reloading Loona itself, reload browser pages so their updates use the new instance. Removing Loona restores ordinary updates for the connections it managed.

HA sorts the native device page alphabetically. Loona cannot set the row order there. Its own settings card puts the master switch first, then filters, then loading options, with scan/reset buttons at the bottom. The statistics card groups status, live rates, totals and recent page loads.

## Change settings

Use the **Loona settings** card or Loona's **Configure** menu under **Settings > Devices & services**.

| Section | Purpose |
| --- | --- |
| Dashboards | Choose dashboards whose entities are included. All filtered accounts share this list. |
| Accounts | Choose which accounts receive filtered data. |
| Filters and performance | Turn the available features on or off. |
| Extra entities | Add entities a card needs but Loona did not find, or entities needed on other pages. |
| Advanced entity rules | Include entity types, individual entities or patterns. Exclusions override inclusions. |
| Card files | Choose additional files to load when Resource filtering is on. Required files stay enabled automatically. |
| Why entities are included | Inspect where an entity was found and which rules affect it. This read-only preview is in Configure. |

The settings card has searchable lists and a **Save** and **Cancel** button for each section. Search narrows existing choices; typing cannot add a new ID. Saved choices that no longer exist remain visible so you can remove them. If settings changed elsewhere, cancel your draft and refresh before editing again. The card does not poll for settings changes.

Advanced rules accept choices from current entities and the entity registry: types such as `light`, IDs such as `sensor.room_temperature`, and patterns such as `sensor.*`. Previously saved custom patterns remain available, even when they currently match nothing. New arbitrary text patterns cannot be entered. Excluding an entity used by a card can remove its data. Loona always includes its own controls and statistics.

## Card files

Resource filtering reads the saved configurations of all selected dashboards. It keeps files for recognized custom cards, shared styles and configured helpers. This is a catalog of known card packages, not a scanner that can understand every JavaScript file or template. A card may need additional files Loona cannot detect.

In **Card files**, required files have no checkbox. Check any other files you need. Unchecked optional files, including newly installed ones, are skipped while Resource filtering is on. Choices are saved without deleting Home Assistant's file registrations. With Resource filtering off, Home Assistant loads all registered files.

A warning means Loona is uncertain which files are needed, or a saved file is no longer registered. It does not prove anything is broken. If the dashboard works, you can keep your choices. If a card, icon or helper is missing, turn off Resource filtering and reload the browser page. Then check the needed file before turning filtering back on.

This filter covers registered dashboard files. It does not filter Home Assistant's own frontend files, extra frontend modules or direct requests for a file. Loona's bundled cards load separately and do not need resource registrations.

## Statistics

The **Loona statistics** card shows filtering status, live update rates, totals and each dashboard's latest browser reload. It refreshes visible statistics about every 30 seconds. The first rate reading after startup or reset appears at the next update.

An update feed is a subscription to live entity changes. A tab can have more than one, so feed counts are not browser counts. Each eligible update is counted once per selected-account feed; opening more tabs can increase totals. Initial snapshots, denied entities, explicitly filtered requests, unselected accounts and changes to Loona's own entities are excluded. When filtering is bypassed, counted updates are recorded as sent.

| Device sensor | Meaning |
| --- | --- |
| Entities included | IDs kept after dashboard discovery and your include/exclude rules. May include IDs that no longer exist. |
| Available included entities | Included IDs that currently have a Home Assistant state. |
| Estimated entity reduction | Percentage of current entities outside the included list. This estimate is shown even when filtering is off. |
| Tracked update feeds | Ordinary entity subscriptions Loona tracks, including unfiltered accounts. |
| Filtered update feeds | Tracked feeds currently receiving a reduced entity list. |
| Last successful scan | Time of the latest complete dashboard scan. |
| Scan duration | Time taken by the latest scan, in milliseconds. |
| Entity updates sent / filtered per second | Updates sent or skipped for selected-account feeds, averaged over the last measured interval. |
| Live update reduction | Filtered updates as a percentage of sent plus filtered updates in that interval. Zero if no updates were counted. |
| Entity updates sent / filtered | Running totals since startup or reset. |
| Compatibility | Supported when Loona's checks pass for the features offered on this HA version; Limited if a check fails. |
| Dashboard scan | Complete when Loona can safely build the entity list; Incomplete while entity and registry filtering are paused. |

Each selected dashboard has a related device with **Referenced entities** and **Entities not found** sensors. They count references before advanced rules. An ID is not found when it has neither a current state nor an entity registry entry. It may be a deleted entity, a typo or a temporary entity. Missing IDs alone do not stop filtering. These counts do not measure traffic for an individual dashboard.

Page-load counts include the selected dashboards' combined entities. File counts cover registered card files, not Home Assistant's own files or extra modules. Reloads are recorded; switching views without reloading does not add a new record. Neither these counts nor update rates measure loading time, CPU savings or network bandwidth.

**Reset live statistics** clears the live counters and page-load records. Statistics also reset when Loona reloads or HA restarts. They are not saved between restarts. Home Assistant's recorded history and the current entity counts are unaffected.

## Cards and language

You can add `type: custom:loona-statistics-card` and `type: custom:loona-settings-card` to your own dashboards. Both cards require an administrator account. Detailed entity explanations remain in Configure.

The cards, setup forms and messages support English and Simplified Chinese. Chinese UI locales, including Traditional Chinese, use Simplified Chinese; other locales use English. The cards follow your profile language while open. Native device-page entity names use HA's backend language instead. Set that with HA's system settings or `homeassistant.language` in YAML, then reload Loona. Profile language does not rename those entities. Your dashboard titles, account names, IDs and custom card titles are preserved.

Upgrades add the settings card to an unedited generated Loona dashboard. Edited dashboards are preserved; add the card manually if wanted. Uninstalling removes Loona's modules and its unedited generated dashboard. Remove Loona cards from your own dashboards before uninstalling. Already loaded files stay in an open page until you reload it.

## Graph loading and animations

Visible-first graphs supports native sensor cards with `graph: line`, Mini Graph Card and ApexCharts Card, including native stacks. Other cards and panel layouts load normally. Dashboard editing and previews load real cards immediately.

Visible graphs start immediately, including when you scroll to them. Off-screen graphs wait until visible rendering and HA requests settle, followed by 750 ms without activity. They then start one at a time when the browser is idle. Custom cards have no common finished-loading signal, so Loona estimates when it can start background work. Temporary placeholders reserve space for waiting graphs. Turning the feature off starts any waiting graphs; already loaded graphs stay loaded.

Animation pausing applies to repeating CSS and Web Animations inside dashboard cards. Animations resume when the browser is idle after 750 ms without activity, when you scroll or interact, or after at most 10 seconds. Live data keeps updating. Loading indicators, finite transitions, editing and previews are left alone. JavaScript drawing loops, SVG SMIL and inaccessible shadow roots are not covered. Later updates do not restart the pause on a settled page. When both features are enabled, animations resume before background graphs start.

These features do not change saved dashboards. Neither guarantees faster loading. Compare the same dashboard with each feature on and off. Browser reports for troubleshooting are `window.loonaGraphLoadingReport()`, `window.loonaGraphLoadingTrace()` and `window.loonaStartupMotionReport()`; they do not measure total dashboard loading time.

## Performance measurements

The reproducible synthetic benchmark uses 10,000 sensor states and registry entries, 1,000 devices, 100 areas, 10 floors, and 100 labels. Its selected entity list contains the first 200 sensors with their metadata relationships. Each state has a name, power unit/class, and a 64-byte padding attribute. A burst changes 1,000 evenly spaced sensors, including 20 in the selected entity list.

Measurements below were taken with Loona 0.3.1, Core 2026.9.4, Python 3.14.6, and stock JS websocket client 9.6.0 on Node 22.23.2, running on an Apple M2 Ultra with 64 GiB RAM and macOS. Timings are medians of five samples after one warmup; Core serialization caches are warm. The full snapshot baseline uses Loona's disabled policy, and the live-update baseline uses an explicitly unfiltered native subscription.

| Measurement | Full data | Filtered data |
| --- | ---: | ---: |
| State snapshot entities | 10,000 | 200 |
| State snapshot JSON bytes | 2,640,912 | 52,860 |
| Full entity registry JSON bytes | 5,305,763 | 105,877 |
| Compact entity registry JSON bytes | 1,269,116 | 25,496 |
| Logical state events in the update burst | 1,000 | 20 |
| Update burst JSON bytes | 143,178 | 2,865 |
| Standard client snapshot processing | 12.45 ms | 0.23 ms |
| Standard client update burst processing | 2,263.44 ms | 0.74 ms |

JSON sizes include each logical event/result envelope before transport compression; they exclude websocket framing and grouped-message separators. Client timings cover JSON decoding and the standard client's state updates on Node. They exclude network time, dashboard rendering, and tablet interaction. The approximately 98% reduction in these payloads is specific to this fixture, and is not a measured reduction in compressed network traffic or total CPU usage.

Registry filtering still parses the complete native list before selecting rows. In this fixture, a full entity-registry request took 2.86 ms with filtering bypassed and 13.19 ms with filtering active. Loona 0.3.1 uses Core's JSON decoder to reduce that filtering cost; the preceding decoder measured 28.24 ms on the same fixture. Smaller responses trade additional server processing for less data to transfer and process on the client.

To reproduce from a checkout with uv and Node.js installed, install the pinned development dependencies and run:

```sh
uv venv --python 3.14 venv
uv pip install --python venv/bin/python -r pyproject.toml --extra test
npm ci
LOONA_BENCHMARK=1 LOONA_BENCHMARK_OUTPUT=/tmp/loona-benchmark.json venv/bin/python -m pytest tests/test_benchmark.py -q -s
```

The benchmark creates an isolated in-memory Home Assistant fixture and writes aggregate results. It requires no Home Assistant login or running server. The ordinary test suite runs a smaller fixture to verify the measurements and final stock-client state.

For a real-browser comparison, use the same dashboard, account, network, and browser with a warm cache. Compare several page loads and normal card interactions with Loona's Enabled switch on and off, then restore it to on. Check that values update and service buttons work in both modes. Record the device model, browser/app version, and observed load times separately from the protocol measurements above. These benchmark numbers do not measure how fast your cards finish loading.

## Troubleshooting

**A card has missing or incorrect data:** turn off Enabled and compare. If that fixes it, check the selected dashboards, Extra entities and exclusion rules. Press Rescan dashboards after correcting them.

**A card or icon does not appear:** turn off Resource filtering and reload the browser. Check the needed file in Card files before enabling the filter again.

**Entity filtering is not active:** check Enabled, Entity filtering and the selected accounts. Filtered update feeds should be greater than zero. Reload pages opened before setup or an integration reload. Check Compatibility, Dashboard scan and **Settings > Repairs**.

**Dashboard scan says Incomplete:** check for removed dashboards/accounts and save automatically generated dashboards. Unsupported templates, strategies or auto-entities rules can prevent a complete scan. Loona sends all entity data while this condition remains. Missing entity IDs alone do not cause this condition.

**Compatibility says Limited:** check your HA version and Loona diagnostics. Another integration may have replaced a function Loona uses. The affected feature leaves its requests to HA.

**A panel is missing choices:** reload the browser after upgrading Loona. Non-dashboard panels and unselected dashboards receive normal data. Selectors opened within a filtered dashboard still use its scope; add needed entities with Extra entities or disable filtering while editing.

When reporting a problem at [Loona issues](https://github.com/leecaochang/Loona/issues), include your HA version, affected card type and integration diagnostics. Diagnostics hide account and entity IDs, dashboard paths, file URLs and reference locations.

## Development tests

The GitHub Actions compatibility matrix runs `tests/core_compatibility.py` against each supported HA release with its matching dependencies and frontend. It checks setup/unload, native storage and YAML dashboards, entity discovery, registry lists, options, controls, permissions, live updates, bypass and restoration. Graph and animation tests cover the verified current frontends.

To reproduce a compatibility test, follow `.github/workflows/compatibility.yml` in an isolated environment and run `python tests/core_compatibility.py`. Development dependencies in `pyproject.toml` pin HA 2026.9.4 and require Python 3.14.2 or newer. Supported older HA releases use Python 3.12.

## License

[MIT](LICENSE).
