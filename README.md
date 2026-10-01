# Loona

Loona reduces the entity states sent to Home Assistant dashboards. Select the dashboards and accounts to filter, then continue using your existing dashboards at your normal Home Assistant address.

Loona is experimental. This release supports Home Assistant Core **2026.9.3 and 2026.9.4**. On other versions, Loona reports a compatibility problem and leaves native subscriptions unchanged. Support for earlier versions has not yet been established.

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

Open the **Loona** device under **Settings > Devices & services** to find these controls. They can also be used in normal Home Assistant automations.

| Control | What it does |
| --- | --- |
| Enabled | Master switch. Turn it off to restore full entity states and registry lists to subscriptions managed by Loona. |
| Entity filtering | Turns entity state filtering on or off while keeping the master switch independent. Both switches must be on for filtering. |
| Registry filtering | Limits entity, device, area, floor, and label lists to dashboard dependencies and related metadata. Off by default. The Enabled switch must also be on. |
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
| Filters | Change the Entity filtering and Registry filtering controls shown on the Loona device. |
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

Subscription counts refresh about every 30 seconds. Each selected dashboard also has a child device with **Discovered entities** and **Unresolved entities** sensors. These count that dashboard's dependencies before advanced rules; unresolved IDs have neither a registry entry nor a current state. They do not measure traffic for an individual dashboard.

## Supported dashboards and limitations

Loona discovers explicit entity references in nested cards, sections, badges, conditions, picture elements, camera fields, and action targets. It expands groups and supported device, area, floor, and label targets. Referenced entity IDs that are currently missing remain in the scope so their states can appear later.

Loona scans supported templates without executing them. Jinja display and style templates can use literal entity references in `states`, `is_state`, `is_state_attr`, `state_attr`, and `has_value`, including conditions, local values, common numeric/text filters, and clock formatting. For `custom:button-card`, supported JavaScript includes the card's explicit `entity`, literal `states['sensor.example']` or `hass.states['sensor.example']` lookups, scalar calculations, conditions, and common number/string formatting. Every branch contributes dependencies, even when it is currently inactive.

Computed entity IDs, state enumeration, unknown helpers or filters, templated entity/target fields, and code outside the supported subset prevent a complete scan. Loona passes through full data for those cases. Extra entities do not make an unsupported template complete.

For `custom:auto-entities`, Loona supports include rules based on `entity_id` globs and `domain` patterns. It retains a conservative set of matches, including entities an auto-entities exclusion might hide. Other filters, template-generated entity lists, and dashboard strategies can prevent a reliable scan.

When a selected dashboard fails to load or has an unsupported dynamic construct, or when the combined scope is empty, Loona passes through full entity states and registry lists for the entire selected union and reports a scope problem. It resumes filtering automatically after a complete scan. Extra entities do not override an incomplete scan.

Unknown custom card types can still use their explicit references. Cards that calculate additional entity names or inspect `hass.states` may need extra entities or domain inclusions. Loona cannot infer every custom card's runtime dependencies.

This release filters entity state subscriptions and optionally registry lists. Dashboard JavaScript and CSS resources, history, services, themes, and other Home Assistant APIs remain available normally.

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

**Compatibility problem is on:** use a supported Home Assistant version and check for another integration replacing entity subscriptions or registry commands. Turn off Loona while investigating. The affected filter returns to native handling; diagnostics identify a registry compatibility failure separately.

**Settings or another dashboard shows fewer entities:** that session uses a filtered account and shares its selected dashboard union. Add the needed entities, choose an unfiltered account, or turn off Loona's master switch.

Download diagnostics from the integration menu when reporting a problem at [Loona issues](https://github.com/leecaochang/Loona/issues). Include your Home Assistant version and the affected card type. Diagnostics redact account IDs, entity IDs, dashboard paths, and dependency locations.

## License

[MIT](LICENSE).
