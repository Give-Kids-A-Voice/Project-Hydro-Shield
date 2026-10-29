# Project Hydro-Shield (Open Source Project)
### A Decentralized, Localized Geofencing Shield to Prevent Accidental Drowning in Autistic Individuals

## 1. The Proximity & Safety Emergency
Accidental drowning linked to wandering or elopement is one of the leading preventable causes of death among autistic children and adults. Due to unique sensory alignments, individuals on the spectrum are often drawn directly to bodies of water—retention ponds, swimming pools, drainage canals, and fountains. 

Commercial tracking solutions (like Apple AirTags) are entirely insufficient. They suffer from severe cloud lag, rely heavily on sparse mesh-networks, and only notify a parent minutes *after* an individual has left a generic boundary. When a child elopes toward water, minutes equal fatalities.

**Project Hydro-Shield is an enterprise-grade, localized perimeter shield engineered to act instantly.** 

## 2. The Architectural Framework: Under $100 Hardware Targets
To ensure absolute accessibility for low-income and vulnerable families, this platform is optimized to run locally on an affordable smart-home anchor (such as a Raspberry Pi Zero 2 W or standard low-cost Linux micro-board). 

The application works by listening to constant, high-frequency local **Bluetooth Low Energy (BLE) or Ultra-Wideband (UWB) beacons** woven into the individual's clothing or wristband. 

## 3. High-Level System Workflow
1.  **Automated Hazard Mapping:** The software utilizes the Google Maps API to instantly reverse-geocode the home address and automatically map every polygon categorized as a body of water within a 500-meter radius buffer zones.
2.  **Continuous Signal Radar:** The local home server monitors the exact raw signal strength (RSSI) of the individual's wearable tracking beacon. 
3.  **The House-Wide Alarm Storm:** The exact microsecond the signal degradation proves the boundary has been breached while intersecting a Google Maps water hazard sector, the software executes an instantaneous local webhook override. **It triggers a deafening audio alarm storm through every smart speaker, phone, TV screen, and monitor connected to the home network simultaneously.** 
4.  **Vector Tracking Output:** The system instantly pushes a live directional map to the caregiver's device with a clear directional tracking vector blasting a singular directive: **SEARCH TARGET WATER MATRIX FIRST**.

## 4. Part of a Holistic Vision
Project Hydro-Shield sits directly alongside our communication initiative (**Dynamic Horizon AAC**) under the Give Kids A Voice organization umbrella. Together, we are writing the missing infrastructure to support, protect, and liberate the massive, rapidly expanding population of non-verbal autistic children and adults whom traditional societal infrastructures have completely abandoned.

## 5. What works today
- **Water Hazard Map** (`docs/`, live on GitHub Pages): enter an address, see every pond, retention basin, canal, ditch, pool and fountain within 300 m to 1.2 km, outlined on a map and ranked by distance to the water's edge. Uses free OpenStreetMap data. No API key.
- **`scripts/hazard_scan.py`**: the same scan for the home hub. Outputs GeoJSON. `python3 scripts/hazard_scan.py "your address" > hazards.geojson`
- `scripts/hydro_shield_scanner.py` is the original Google Places prototype. Places only returns named points, so it misses most unnamed retention ponds, ditches and backyard pools; the OpenStreetMap scan replaces it.

### Design notes
- **Two layers.** Layer 1 is the exit alarm: a wearable BLE tag leaves range of the home hub, or a door sensor trips, and every speaker and phone alarms within seconds. Layer 2 is outdoor tracking: a GPS wearable streams position and the hub reports distance and heading to the nearest mapped water.
- **Fail loud.** Dead tag battery, a tag that stops reporting, or a hub that loses power must alarm, never go quiet.
- **Home Assistant** runs the alarm side on the Pi, since it already speaks to Sonos, Google, Alexa, TVs and phones.
- Not a substitute for supervision, door locks and alarms, or swim lessons.

## 6. Active Repositories Tasks
We need systems engineers, IoT developers, network specialists, and geospatial programmer experts to jump into our **Issues** tab to claim modular challenges:
- **Module A:** Local BLE/UWB RSSI signal tracking & distance approximation metrics.
- **Module B:** Google Maps API Integration scripts for automated local property hydrology scanning.
- **Module C:** Decentralized local network smart-home speaker audio webhook override modules.
