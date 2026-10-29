# Hydro-Shield Hub: exit alarm prototype

**Goal:** the moment a child leaves the house (tag out of range or a door opens), every phone, speaker and TV in the home sounds an alarm within seconds, and keeps sounding until someone taps "Found". If the tag goes silent, that alarms too.

Untested on real hardware yet. Build it, time it, and report what happened in the repo's Issues.

## Parts (about $90–130)

| Part | Why | Rough price |
|---|---|---|
| Raspberry Pi 4 (2 GB or more) + official power supply | Runs Home Assistant. A Pi Zero 2 W is too weak for Home Assistant OS. | $50–65 |
| 32 GB or larger microSD card (A2 rated) | Holds the system | $8–12 |
| 1–2 BLE beacon tags (iBeacon type, replaceable coin battery, 1-second or faster broadcast) | The child wears one: sewn into a shoe tongue, waistband or a sensory-friendly clip works better than a wristband many kids pull off | $15–25 each |
| Optional: Zigbee USB dongle (e.g. SONOFF ZBDongle-E) + 2–3 Zigbee door/window contact sensors | Door and pool-gate alarms. Fastest and most reliable trigger | $25 + $10–15 each |

Prices move; check current listings. Already own a Home Assistant box (HA Green, Yellow, or a mini PC)? Use that and skip the Pi.

## Setup (one step at a time)

1. **Flash Home Assistant OS.** On a computer, install Raspberry Pi Imager, choose *Other specific-purpose OS → Home assistants and home automation → Home Assistant*, write it to the SD card.
2. **Boot the Pi** wired to your router with an Ethernet cable. After about 5 minutes open `http://homeassistant.local:8123` and create the owner account.
3. **Install the phone app.** Home Assistant Companion app on each caregiver's phone, log in, allow notifications. On iPhone allow **Critical Alerts**.
4. **Add the tag.** Settings → Devices & services → Add integration → **iBeacon Tracker**. Put the tag next to the Pi; it appears as a device. Rename its entities to `device_tracker.child_tag` and `sensor.child_tag_estimated_distance` (or edit the YAML to match).
5. **Speakers.** Add your Google/Nest, Sonos, Alexa or smart TV integrations (Home Assistant usually finds them on its own).
6. **Doors (optional).** Plug in the Zigbee dongle, add the **ZHA** integration, pair each contact sensor, and name them in the YAML.
7. **Install the package.** Copy `homeassistant/hydroshield.yaml` into `config/packages/`, fill in the CHANGE ME lines, restart.
8. **Tune the distance.** Walk the tag to each outside door and note `estimated distance`. Set *Hydro-Shield distance limit* just above the largest indoor reading.
9. **Arm it** (toggle *Hydro-Shield armed*) and test: walk the tag out a door with a stopwatch running. Record seconds-to-alarm.

## Honest limits
- Bluetooth distance is noisy; walls and bodies change it. Door sensors are the most reliable trigger; the tag is the backup that also catches open windows and a door left open.
- This is an alarm, not a locator. Outdoor tracking (Layer 2) needs a GPS wearable and is a later module.
- Never a substitute for supervision, door locks set high, pool fences and swim lessons.

## Keeping false alarms rare without ever pausing protection
- **Exits always alarm at once and cannot be paused:** a door opening while the child's tag is near it, or the tag leaving without a caregiver's phone beside it.
- **Door opens while the child is deep inside:** chime only (someone else leaving). Needs a small Bluetooth receiver at each door (ESP32 Bluetooth proxy + Bermuda integration) to know which room the tag is in; until then every watched door is treated as an exit.
- **Tag signal lost (lying on it):** quiet phone warning, siren after 12 seconds unless the signal returns or a caregiver taps "I'm with him" (that hush lasts 5 minutes and covers only this warning). Night mode skips straight to the siren.
- **Out together:** turn on the Home Assistant app's BLE transmitter on caregiver phones; if the child's tag leaves with a caregiver phone beside it, no alarm.
- **Practice week:** turn on *practice week* for the first 7 days; would-be alarms are logged, not sounded. Tune, then switch it off.
- **Offline alert:** a free healthchecks.io check receives a ping every 2 minutes and texts caregivers if the box stops (unplugged, power or internet out).
- **False-alarm count:** after every alarm the phone asks "real or false?"; more than one false alarm a week is a bug to fix.
