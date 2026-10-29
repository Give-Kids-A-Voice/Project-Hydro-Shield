# First build: the parts in the October 2026 order

For the kit: Raspberry Pi 4 (4 GB) + CanaKit power supply, SanDisk 64 GB microSD, PiSugar S Plus battery, SONOFF ZBDongle-E (Zigbee stick), Aqara door/window sensors (3), SONOFF SNZB-09P siren, DX-CP27 beacon tags (3).
Follow `README.md` for the general steps; these are the part-specific details. About 2 hours the first time.

## 1. Before power: assemble
- Mount the Pi on the PiSugar S Plus (spring pins touch the pads under the Pi; screws included). Charge the PiSugar fully once.
- The Miuzei case likely won't close over the PiSugar. Leave the case off for testing; the enclosure is a later job.
- Plug the Zigbee stick into a USB **2.0** (black) port, ideally on a short USB extension cable, away from the Pi's USB 3 (blue) ports, which interfere with Zigbee.

## 2. Software
1. Flash Home Assistant OS to the SD card (Raspberry Pi Imager → Other specific-purpose OS → Home assistants → Home Assistant → Raspberry Pi 4).
2. Ethernet to the router, power on, wait ~10 minutes, open `http://homeassistant.local:8123`, create the owner account.
3. Settings → Devices & services: Home Assistant usually offers **ZHA** for the Zigbee stick automatically. Accept it (radio type: EZSP).

## 3. Pair the Zigbee devices (ZHA → Add device, then)
- **Aqara door sensors:** hold the small button with a pin for ~5 seconds until the blue light blinks. Keep tapping the button every ~2 seconds until Home Assistant shows it (Aqara sensors go to sleep fast). Name them `front_door`, `back_door`, `pool_gate`/`slider`.
- **SONOFF siren:** power it from any USB-C phone charger near the bedrooms. Hold its button ~5 seconds until it flashes. Name it `hydroshield_siren`.
- Pair the siren **first**: it's mains powered and becomes a relay that strengthens the door sensors' signal.

## 4. The tag
- Install the beacon's setup app (scan the QR code on the tag) and set the **advertising interval to 500 ms–1 s** and transmit power to medium. Faster = quicker alarm, shorter battery.
- Home Assistant → Add integration → **iBeacon Tracker**. Hold the tag near the Pi; it appears within a minute. Rename to `child_tag`.

## 5. Install the alarm
Copy `homeassistant/hydroshield.yaml` into `config/packages/` (File editor or Samba add-on), set the child's name and the entity names, restart.

## 6. Test (stopwatch)
1. Arm it. Walk the tag out each door at a child's pace. Write down seconds-to-siren for each door.
2. Open each door with the tag inside: siren should start within ~2 seconds.
3. Pull the tag's battery: alarm within ~30 seconds ("tag stopped reporting").
4. Unplug the Pi's power: the PiSugar should keep it running; open a door, siren still sounds.
Post the numbers in the repo's Issues so we can tune the defaults.
