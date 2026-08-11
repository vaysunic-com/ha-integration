# VAYSUNIC Solar — Home Assistant Integration

[![HACS: Custom][hacs-badge]][hacs]
[![Release][release-badge]][releases]
![HA min version][ha-badge]
![IoT class: cloud polling][iot-badge]

English | [简体中文](README.zh-Hans.md)

Bring your VAYSUNIC photovoltaic system into Home Assistant — devices such as inverters and meters appear as native entities, and your generation and grid figures can drive the built-in **Energy dashboard**.

![The Energy dashboard, fed by VAYSUNIC microinverters](images/energy-dashboard.png)

*Generation from every microinverter feeds Home Assistant's built-in Energy dashboard — no template sensors, no YAML.*

![A device page listing its measurements](images/device.png)

*Each device gets its own page. Every measurement the device reports becomes a sensor with the right unit and device class.*

## How it works

This is a **cloud-polling** integration (`iot_class: cloud_polling`), not a local one. Home Assistant polls the VAYSUNIC cloud API every two minutes; it does not talk to your inverters directly. If the cloud or your internet connection is down, Home Assistant receives no data.

- **Two minute polling**, matched to how often devices actually report.
- **No account credentials.** You paste a dedicated token, never your username and password.
- **Can be disabled at any time.** Disabling a token cuts Home Assistant off immediately.
- **Read-only.** The integration cannot change anything on your system.

## Requirements

- Home Assistant **2024.1.0** or newer
- A VAYSUNIC account with at least one power station **you own**
- An **HA token**, generated in the VAYSUNIC app

> Treat the token like a password: anyone holding it can read all data from your stations.

## Installation

### HACS (recommended)

1. HACS → three-dot menu (top right) → **Custom repositories**
2. Paste this repository's URL, set category to **Integration**, click **Add**
3. Find **VAYSUNIC Solar** in HACS, install it, then **restart Home Assistant**

### Manual

Copy `custom_components/vaysunic` into your Home Assistant `config/custom_components/` directory, then restart Home Assistant.

## Configuration

**Settings → Devices & Services → Add Integration → VAYSUNIC Solar**

![The setup dialog](images/config-flow.png)

| Field | Value |
| --- | --- |
| **Gateway URL** | `https://application.vaysunic.com/ha` — already filled in for you |
| **HA token** | The token you generated in the app |

The token is validated immediately — a wrong or disabled token is rejected on the spot. If a working token is later disabled, Home Assistant raises a re-authentication prompt so you can paste a new one without losing your entity history.

One token equals one config entry, and it covers **every station you own** — there is no per-station selection. Stations shared with you by another account are not included.

## Setting up the Energy dashboard

This is what most people install the integration for. Go to **Settings → Dashboards → Energy** and fill in:

| Energy dashboard slot | Which entity to pick |
| --- | --- |
| **Solar panels** | The `energy` sensor of **each** microinverter — add them all, Home Assistant sums them |
| **Grid consumption** | `energy_p_all` — or `energy_p` on a single-phase meter |
| **Return to grid** | `energy_n_all` — or `energy_n` on a single-phase meter |

**Which one is my meter?** Look at its entity list. If there are entities ending in `_all`, it is a three-phase meter and those are the ones you want — they already cover all three phases. A single-phase meter has no `_all` entities.

> **Every slot accepts multiple entities and Home Assistant simply adds them up.** So everything you put in one slot must measure a *different* flow of electricity — adding the same energy twice inflates your generation figure and throws off the whole balance, including household consumption and self-consumption ratio.

Energy sensors are currently provided by **microinverters and meters**. Other device types report instantaneous values such as power. A storage-only system without a grid meter will therefore have no figures for *Grid consumption* and *Return to grid*; fitting a grid meter solves it.

### Per-phase entities on a three-phase meter

A three-phase meter also exposes each phase separately:

| Phase | Grid consumption | Return to grid |
| --- | --- | --- |
| A | `energy_p` | `energy_n` |
| B | `energy_p_pb` | `energy_n_pb` |
| C | `energy_p_pc` | `energy_n_pc` |

**Most installations should ignore these and use the `_all` pair.** Per-phase figures matter in one situation only: when the three phases do not all serve the same purpose — for instance when one phase carries generation rather than household load, so the combined figure is no longer pure grid exchange. If that describes your installation, add one **grid connection per phase** (each pairing that phase's consumption and return) instead of the `_all` pair.

Not sure which applies to you? Ask whoever installed the system.

> ⚠️ Use either the `_all` pair **or** the per-phase pairs — never both. Mixing them counts the same electricity more than once, and the error propagates into household consumption and self-consumption ratio.

## Entities

Devices are grouped by serial number and placed in an area named after their power station.

Each numeric measurement becomes one `sensor`, carrying `device_class`, `state_class` and unit. Energy readings are cumulative counters marked `total_increasing`, so Home Assistant derives hourly, daily and monthly figures on its own.

The power, voltage and current of **each individual string** are separate entities, so a single underperforming panel shows up instead of being averaged away.

Entity IDs are built from the power station, the device serial and the measurement — a device with serial `A1B2C3D4E5F6` in a station named *My Plant* gets `sensor.my_plant_a1b2c3d4e5f6_energy`. **The serial is always in there**, so every entity maps back to exactly one device.

The energy readings available today:

| Device | Measurement | Meaning |
| --- | --- | --- |
| Microinverter | `energy` | Lifetime generation of that inverter |
| Meter (single-phase) | `energy_p` / `energy_n` | Imported from grid / exported to grid |
| Meter (three-phase) | `energy_p_all` / `energy_n_all` | Imported / exported, all phases combined |
| Meter (three-phase) | `energy_p_pb` / `energy_n_pb`, `energy_p_pc` / `energy_n_pc` | The same, broken down per phase — see [Per-phase entities](#per-phase-entities-on-a-three-phase-meter) |

New measurements and new devices are picked up automatically on later polls — no reinstall needed. Removing a device on the platform stops its entities from updating, but Home Assistant keeps the entity until you delete it.

## Data freshness

- Home Assistant polls every **two minutes**. Devices report roughly every three minutes, so polling faster would only fetch the same reading repeatedly.
- A device that stops reporting is shown as offline and its entities become **unavailable**. The same happens to every entity if the gateway becomes unreachable or the token is disabled — readings are never left frozen at their last value.
- **Microinverters go unavailable overnight.** They stop reporting after dark and come back in the morning. This is normal and does **not** corrupt your Energy dashboard: `total_increasing` treats an unavailable gap as a pause, not a counter reset, and there is no generation overnight to lose. Grid meters stay online around the clock, so import and export figures are unaffected.

## Privacy and data handling

- The integration only makes **outbound** HTTPS requests from your Home Assistant. Nothing connects inward, and no message broker is involved.
- It never asks for your account password — only the dedicated token.
- The API is read-only. Nothing in Home Assistant can change your system's settings.
- Disable the token and data stops immediately. Remove the integration and no traffic is sent at all.

## Troubleshooting

Enable debug logging in `configuration.yaml`, then restart:

```yaml
logger:
  logs:
    custom_components.vaysunic: debug
```

| Symptom | Likely cause |
| --- | --- |
| Setup succeeds but no entities appear | All your devices are currently offline. Entities are created from the first poll that returns readings — check back during daylight, or confirm in the app that a device is online |
| Entities show *unavailable* at night | Expected for microinverters, see [Data freshness](#data-freshness) |
| *Invalid or disabled token* | The token was disabled or mistyped. Home Assistant will prompt for re-authentication — paste a fresh one |
| *Failed to connect to the gateway* | Wrong gateway URL, or your Home Assistant cannot reach the internet. Check the URL against the table above |
| An energy sensor is missing from the Energy dashboard dropdown | Home Assistant only offers entities that have accumulated statistics. A newly added device can take up to two hours to appear |
| A measurement you expect is not there | Only what the device actually reports is exposed |

## Contributing

Bug reports and feature requests: [open an issue][issues]. Please include your Home Assistant version, the integration version, and the debug log described above.

## License

Licensed under the [Apache License 2.0](LICENSE). Note that the license does not grant
permission to use the VAYSUNIC name or logo — see section 6.

[hacs]: https://github.com/hacs/integration
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[release-badge]: https://img.shields.io/github/v/release/vaysunic-com/ha-integration
[releases]: https://github.com/vaysunic-com/ha-integration/releases
[ha-badge]: https://img.shields.io/badge/Home%20Assistant-2024.1.0%2B-41BDF5.svg
[iot-badge]: https://img.shields.io/badge/IoT%20class-cloud%20polling-orange.svg
[issues]: https://github.com/vaysunic-com/ha-integration/issues
