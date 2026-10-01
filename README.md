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
| Enabled | Master switch. Turn it off to restore full entity states to subscriptions managed by Loona. |
| Entity filtering | Turns entity state filtering on or off while keeping the master switch independent. Both switches must be on for filtering. |
| Rescan dashboards | Reloads the selected configurations and rebuilds the scope. Use this for troubleshooting; ordinary dashboard changes are handled automatically. |

Switch states survive Home Assistant restarts. Switching either control off updates existing subscriptions managed by Loona without requiring a page reload. Turning filtering back on also applies to those subscriptions automatically.

Dashboard edits, relevant registry changes, entity additions and removals, and group membership changes trigger automatic scans. Changes are grouped briefly before scanning. YAML file changes are checked about once a minute; the rescan button applies them sooner.

Options changes also update existing managed subscriptions. After reloading the integration itself, reload browser pages once so their subscriptions are managed by the new instance of Loona. Removing the integration restores full state subscriptions for connections it managed.

## Change settings

Use Loona's **Configure** menu under **Settings > Devices & services**.

| Menu | Use |
| --- | --- |
| Dashboards | Change which dashboards contribute to the shared scope. |
| Targets | Change the selected accounts or choose all accounts. |
| Filters | Change the same Entity filtering control shown on the Loona device. |
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

For `custom:auto-entities`, Loona supports include rules based on `entity_id` globs and `domain` patterns. It retains a conservative set of matches, including entities an auto-entities exclusion might hide. Other filters, runtime templates, and dashboard strategies can prevent a reliable scan.

When a selected dashboard fails to load or has an unsupported dynamic construct, or when the combined scope is empty, Loona passes through full entity states for the entire selected union and reports a scope problem. It resumes filtering automatically after a complete scan. Extra entities do not override an incomplete scan.

Unknown custom card types can still use their explicit references. Cards that calculate additional entity names or inspect `hass.states` may need extra entities or domain inclusions. Loona cannot infer every custom card's runtime dependencies.

This release filters entity state subscriptions. Registry metadata, dashboard JavaScript and CSS resources, history, services, themes, and other Home Assistant APIs remain available normally.

## Troubleshooting

**A card is missing data:** turn off Enabled to check whether filtering is responsible. Verify that its dashboard is selected, then add any dependencies calculated by the card under Extra entities. Check advanced exclusions and press Rescan dashboards if needed.

**Filtering appears inactive:** ensure both switches are on, the account is selected, and Filtered subscriptions is greater than zero. Reload the page if it was open before setup or an integration reload. Check the Compatibility problem and Scope problem sensors and **Settings > Repairs**.

**Scope problem is on:** save the selected dashboards, remove deleted dashboard or account selections, and check for templates, strategies, or unsupported auto-entities filters. Unresolved entity counts alone do not cause a bypass.

**Compatibility problem is on:** use a supported Home Assistant version and check for another integration replacing the same subscription command. Turn off Loona while investigating. A compatibility failure prevents Loona from installing or updating its filter.

**Settings or another dashboard shows fewer entities:** that session uses a filtered account and shares its selected dashboard union. Add the needed entities, choose an unfiltered account, or turn off Loona's master switch.

Download diagnostics from the integration menu when reporting a problem at [Loona issues](https://github.com/leecaochang/Loona/issues). Include your Home Assistant version and the affected card type. Diagnostics redact account IDs, entity IDs, dashboard paths, and dependency locations.

## License

[MIT](LICENSE).
