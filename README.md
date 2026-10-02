# Loona

Loona transparently reduces the weight of Home Assistant Lovelace dashboards by removing unnecessary resources and reducing websocket updates. No extra software is required, only this integration. Your dashboards, login and Home Assistant address stay the same. You just set it and forget it.

Loona is experimental. Smaller responses can help slower devices, but do not guarantee faster card loading.

Entity, registry and resource filtering applies only while a selected account is viewing a selected dashboard. Settings, Developer Tools, other panels and unselected dashboards receive normal Home Assistant data. Each browser tab reports its own panel automatically; clients without panel context receive normal data. If the report arrives after startup, Loona applies filtering to the existing updates. Reload browser pages after upgrading so they load the panel reporter. Home Assistant permissions still apply.

## Supported Home Assistant versions

| Core version | Features |
| --- | --- |
| **2024.6 +** | Entity, registry and resource filtering; settings; diagnostics; statistics. |
| **2026.9 +** | All of the above, plus graph optimizations and animation pausing. |

Loona checks the Home Assistant functions it uses before enabling a feature. If a check fails or another integration replaces those functions, the affected feature stops filtering.

## Install and set up

For manual installation, copy `custom_components/loona` into the `custom_components` folder in your Home Assistant configuration directory, then restart Home Assistant.

For HACS, add `https://github.com/leecaochang/Loona` as a custom repository with category **Integration**, download Loona, then restart Home Assistant. You need access to the repository to download it.

1. Open **Settings > Devices & services > Add integration** and choose **Loona**. Only one instance can be installed.
2. Select the dashboards you want to filter.
3. Choose **Selected accounts** or **All accounts**. Dashboards for accounts you do not select will not be filtered. Home Assistant permissions still apply, Loona does not restrict access.
4. Optionally add the **Loona settings** card, the **Loona statistics** card, or both. Loona creates an administrator-only **Loona** dashboard containing your choices. Choose neither to skip creating this dashboard.
5. If you selected a card, the final setup step reminds you to refresh your browser before viewing it.

## Controls

Use the **Loona settings** card, or open the Loona device under **Settings > Devices & services**. You can enable or disable any of these controls, as needed. Enable all for maximal resource filtering. Resource changes require a browser reload.

| Control | What it does |
| --- | --- |
| Enabled | Master switch. `Off` restores standard dashboard behavior. Works instantly, no restart or refresh required. On by default. |
| Entity filtering | **Entity filtering is automatic.** Loona reads your selected dashboards and finds the entities their cards use. Use **Entity rules** to add individual entities, broader groups or patterns, or to exclude entities. On by default. |
| Pause animations during loading | Pauses repeating card animations during startup and resumes them automatically. Off by default. |
| Registry filtering | Reduces the information HA sends about entities and devices, such as their names, icons, device relationships, areas and other details. Off by default. |
| Resource filtering | Always loads the card resources for any cards you selected under **Cards**. Refresh the Home Assistant page after making changes. Off by default.|
| Delay graph loading | Off-screen graphs will load only after the dashboard has completely loaded, or immediately when you scroll to them. On-screen graphs always display immediately. Off by default. |
| Rescan dashboards | Check for any dashboard changes now. Normally, dashboard changes are automatically scanned about once a minute. |
| Reset live statistics | Clears live update totals, rates and page-load records. Entity counts, settings and recorded Home Assistant history remain unchanged. |

## Change settings

Use the **Loona settings** card or Loona's **Configure** menu under **Settings > Devices & services**.

| Section | Purpose |
| --- | --- |
| Dashboards | Choose which dashboards you want to filter. |
| Accounts | Choose which user accounts receive filtered data. |
| Filters and performance | Turn the available features on or off. |
| Entity rules | Use these rules to add anything Loona missed, or exclude entities you don’t need. Exclusions always override inclusions. |
| Cards | Choose additional card resource files to load when Resource filtering is on. Required files can not be disabled. |
## Cards

Automatic resource filtering reads the saved configurations of all selected dashboards and allows resources for recognized custom cards, shared styles and configured helpers. Automatic scanning is not perfect, it may still miss a some JavaScript files or templates, so a card may require additional files Loona cannot detect.

Required resource files will have no checkbox, as they must always be included. Unchecked resource files, including newly installed ones, are skipped while Resource filtering is on. For resources you need, find their filename and check them to be included.

If a card, icon or helper is missing, turn off Resource filtering and reload the browser page. Then check the needed file before turning filtering back on.

This filter covers only registered dashboard files. It does not filter Home Assistant's own frontend files, extra frontend modules or direct requests for a file. Home Assistant's file registrations are not affected.

 With Resource filtering off, Home Assistant loads all registered files.

## Diagnostics

The **Loona statistics** dashboard card shows filtering status, live update rates, totals and each dashboard's latest browser reload. It refreshes visible statistics about every 30 seconds. The first rate reading after startup or reset appears at the next update.

Initial snapshots, denied entities, explicitly filtered requests, unselected accounts and changes to Loona's own entities are excluded. When filtering is bypassed, counted updates are recorded as sent.

| Device sensor | Meaning |
| --- | --- |
| Available included entities | IDs kept after dashboard discovery and your include/exclude rules, that currently are available in Home Assistant. |
| Compatibility | `Supported` when Loona's compatibility checks pass; `Limited` when a feature is unavailable. |
| Dashboard scan | `Complete` when Loona can safely build the entity list; `Incomplete` while entity and registry filtering are paused. |
| Entity updates filtered (per second) | Entities skipped, averaged over the last measured interval. |
| Entity updates sent (per second) | Entities included, averaged over the last measured interval. |
| Estimated entity reduction | Percentage of current entities outside the included list. This estimate is shown even when filtering is off. |
| Filtered update feeds | Feeds are an ongoing connection through which Home Assistant sends entity changes to a browser tab or app. This tracks feeds currently receiving a reduced entity list. |
| Included entities | IDs kept after dashboard discovery and your include/exclude rules. May include IDs that no longer exist. |
| Last successful scan | Time of the latest complete dashboard scan. |
| Live update reduction | Measures ongoing entity changes, rather than the initial page load. It fluctuates depending on which entities are changing, and shows 0% when no updates occurred during the update interval. |
| Scan duration | Time taken by the latest scan, in milliseconds. |
| Version | Installed Loona version. |
| Warnings | Number of current warnings. Informational checks are not counted. |
| Tracked update feeds | Feeds are an ongoing connection through which Home Assistant sends entity changes to a browser tab or app. This tracks ordinary entity feeds Loona tracks, including unfiltered accounts. |

Each selected dashboard has a related device with **Entities not found** and **Referenced entities** sensors. They count references before entity rules. An entity is not found when it has neither a current state nor an entity registry entry. It may be a deleted entity, a typo or a temporary entity. Missing entities alone do not stop filtering. These counts do not measure traffic for an individual dashboard.

**Reset live statistics** clears the live counters and page-load records. Statistics also reset when Loona reloads or HA restarts. They are not saved between restarts. Home Assistant's recorded history and the current entity counts are unaffected.

The cards show update rates with one decimal place. **Entity rules** combines individual entities, entity types and patterns in separate **Included** and **Excluded** groups, with one Save action.

## Warnings

Both Loona cards show **Warnings and checks** with an explanation and recovery steps. Warnings cover unavailable features, failed dashboard creation, incomplete scans, missing entity references, exclusions affecting cards, and saved card files that are no longer registered. They clear when the condition is resolved.

Informational checks cover custom cards and files Loona cannot fully inspect, including template-driven dependencies and unchecked files with unknown usage. If everything works, no action is needed. These checks do not increase the Warnings sensor count.

Loona does not create Home Assistant Repairs notifications. Existing Loona Repairs are removed when the updated integration loads. Statistics and warnings refresh about every 30 seconds in the statistics card; use Refresh or Rescan dashboards in the settings card to check again.

## Custom Dashboard Cards

You can add `type: custom:loona-statistics-card` and `type: custom:loona-settings-card` to your own dashboards. Both cards require an administrator account. The bundled cards are available even if you skipped the generated dashboard during setup.

## Supported languages

This integration and the custom dashboard cards support English and Simplified Chinese. The cards follow your profile language.

Uninstalling removes Loona's modules and its unedited generated dashboard. Remove Loona cards from your own dashboards before uninstalling.

## Delayed graph loading

Delayed graphs loading supports native sensor cards with `graph: line`, Mini Graph Card and ApexCharts Card, including native stacks. Other cards and panel layouts load normally. Dashboard editing and previews load real cards immediately.

Visible graphs start immediately, including when you scroll to them. Off-screen graphs wait until visible rendering and HA requests settle, followed by 750 ms without activity. They then load one at a time when the browser is idle.

Custom cards have no common finished-loading signal, so Loona estimates when it can start background work.

Temporary placeholders reserve space for waiting graphs. Turning this feature off immediately starts any waiting graphs; already loaded graphs stay loaded.

Enabling this feature does not guarantee faster loading.

## Animations

Animation pausing applies to repeating CSS and web animations inside dashboard cards. Animations resume when the browser is idle after 750 ms without activity, when you scroll or interact, or after at most 10 seconds. Live data keeps updating.

Loading indicators, transitions, editing and previews remain untouched. JavaScript drawing loops, SVG SMIL and inaccessible shadow roots are also not covered.

When delayed graph loading is also enabled, animations resume before background graphs start.

Enabling this feature does not guarantee faster loading.

## Troubleshooting

Compare the same dashboard with each feature on and off. Reports for troubleshooting are available from your browser console:

`window.loonaGraphLoadingReport()`
`window.loonaGraphLoadingTrace()`
`window.loonaStartupMotionReport()`

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

**A card has missing or incorrect data:** turn off Enabled and compare. If that fixes it, check the selected dashboards and entity rules. Press Rescan dashboards after correcting them.

**A card or icon does not appear:** turn off Resource filtering and reload the browser. Check the needed file in **Cards**  before enabling the filter again.

**Entity filtering is not active:** check Enabled, Entity filtering and the selected accounts. Filtered update feeds should be greater than zero. Reload pages opened before setup or an integration reload. Check Compatibility, Dashboard scan and **Warnings and checks** in either Loona card.

**Dashboard scan says Incomplete:** check for removed dashboards/accounts and save automatically generated dashboards. Unsupported templates, strategies or auto-entities rules can prevent a complete scan. Loona sends all entity data while this condition remains. Missing entity IDs alone do not cause this condition.

**Compatibility says Limited:** check your HA version and Loona diagnostics. Another integration may also have replaced a function Loona requires. The affected feature leaves its requests to HA.

**A panel is missing choices:** reload the browser after upgrading Loona. Non-dashboard panels and unselected dashboards receive normal data. Selectors opened within a filtered dashboard still use its scope; add needed entities under **Entity rules** or disable filtering while editing.

When reporting a problem at [Loona issues](https://github.com/leecaochang/Loona/issues), include your HA version, affected card type and integration diagnostics. Diagnostics hide account and entity IDs, dashboard paths, file URLs and reference locations.

## Development tests

The GitHub Actions compatibility matrix runs `tests/core_compatibility.py` against each supported HA release with its matching dependencies and frontend. It checks setup/unload, native storage and YAML dashboards, entity discovery, registry lists, options, controls, permissions, live updates, bypass and restoration. Graph and animation tests cover the verified current frontends.

To reproduce a compatibility test, follow `.github/workflows/compatibility.yml` in an isolated environment and run `python tests/core_compatibility.py`. Development dependencies in `pyproject.toml` pin HA 2026.9.4 and require Python 3.14.2 or newer. Supported older HA releases use Python 3.12.

## License

[MIT](LICENSE).
