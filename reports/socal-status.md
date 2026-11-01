# Project Hydro-Shield: Southern California status

## 2026-10-31 (Saturday)

**Bottom line:** Branch `socal` (not merged, main and the live site untouched) adds water hazards and OpenStreetMap pool points for Los Angeles, Orange, Ventura, Riverside and San Bernardino counties. Florida pool counts are unchanged in the regression test. California pool coverage is partial and the site says so.

### 1. What was added
- `scripts/build_osm_region.py` (pyosmium + shapely, no osmium CLI needed): keeps the same water tags as the Florida build (natural=water, landuse=basin/reservoir, leisure=water_park, waterway=canal/ditch/drain/stream/river/riverbank, amenity=fountain), clips to the five county boundaries (+~500 m) taken from the same extract, and writes
  - a GeoJSON sequence fed to the unchanged `scripts/build_water_tiles.py` (same 0.05-degree tile scheme, same classification in `hazards.js`). Flood-control channels, debris/retention basins and reservoirs come through as canal/drain/basin/reservoir tags, as mapped in OSM.
  - pool points (`leisure=swimming_pool` nodes, ways and multipolygons) as `[lat, lon, "osm"]` in `docs/data/pools/<floor(lat*20)>_<floor(lon*20)>.json`, deduplicated on a ~4 m grid. Pools are left out of the water tiles so a pool is never counted twice.
- Workflow `water-tiles.yml`: new step downloads Geofabrik `socal-latest.osm.pbf`, builds SoCal water tiles into the same `water-tiles` dir (built in CI, not committed, like Florida) and refreshes SoCal pool points over the committed copy. The step is `continue-on-error` so it can never block the Florida deploy; cache key now also hashes `build_osm_region.py`.
- Front end: default view unchanged (Florida). Coverage line and credits mention Southern California and "Pool coverage in California is partial (OpenStreetMap)". OSM pools are labelled "Pool (OpenStreetMap)" (not "county record"), and the status line counts them separately. Geocoding was already national (Esri `countryCode=USA`, Nominatim `countrycodes=us`, no Florida bbox or "FL" suffix), so no change needed. No geolocation, no new tracking.

### 2. Counts (OSM data of 2026-10-30)
- Water: 54,708 features, 2,163 tiles, 38 MB (CI-built, not committed).
- Pools: 108,925 raw pool objects in the extract → 46,777 after clip and dedupe, 645 tiles, 3.4 MB committed.

| County | OSM pool points |
|---|---|
| Los Angeles | 29,385 |
| Orange | 5,727 |
| Riverside | 5,940 |
| San Bernardino | 3,773 |
| Ventura | 1,931 |
| Just outside a county line (500 m buffer) | 21 |

### 3. Regression test (Playwright, docs/ served locally, radius 500 m)
Live numbers were checked first and matched last weekend's.

| Address | Live pools | Local pools |
|---|---|---|
| Ashmonte Drive, Land O Lakes, FL | 2329 | 2329 |
| Westchase, Tampa, FL | 3096 | 3096 |
| Largo, FL | 2696 | 2696 |
| Sarasota, FL | 3101 | 3101 |
| Mandarin, Jacksonville, FL | 648 | 648 |
| 110 N Apopka Ave, Inverness, FL 34450 | 592 | 592 |

Florida water tiles are CI-built and Overpass is unreachable from the test sandbox, so local Florida *water* counts were not comparable; only pool counts were tested for Florida.

| SoCal address | Water tiles loaded | Hazards within 500 m | OSM pools loaded (tiles around the point) |
|---|---|---|---|
| Santa Monica, CA | 1/1 | 7 | 47 |
| Pasadena, CA | 2/2 | 4 | 1938 |
| Irvine, CA | 1/1 | 16 | 176 |
| Thousand Oaks, CA | 2/2 | 7 | 73 |
| Riverside, CA | 1/1 | 7 | 70 |
| Rancho Cucamonga, CA | 1/1 | 7 | 145 |
| Long Beach, CA | 1/1 | 0 | 24 |

City-name searches land on a downtown point, so few hazards inside 500 m is expected (Long Beach downtown: none mapped within 500 m). The "pools" number is what the existing status line shows: all pool points in the loaded tiles, not only those inside the radius.

### 4. Caveats
- **OSM pool completeness is low.** Rough expectation for these five counties is several hundred thousand residential pools (order of 500k+; not verified against an authoritative source). 46,777 points suggests well under 10% coverage overall, with patches (e.g. Pasadena) much better than others. The site says coverage is partial.
- The local build used the openstreetmap.fr California extract because Geofabrik was not reachable from the sandbox; CI uses Geofabrik `socal-latest` as specified. Same OSM data, but the CI step itself has not run yet (it only runs on main / schedule).
- CI time: the pure-Python filter took ~12 min on all of California locally (2 cores); `socal` is smaller. The job timeout is 100 min.
- LA County's GIS service (behind Incapsula) was not used. No paid or licensed data.

### 5. Next: aerial-imagery pool detection (not implemented)
- Imagery: USDA NAIP (0.6 m, 4-band incl. near-infrared, public domain) via the AWS Open Data bucket `naip-analytic` / Microsoft Planetary Computer STAC (free, no key for reads); USGS/CA state orthos as backup.
- Approach: tile NAIP around residential parcels; first pass with a spectral rule (pool water is bright blue with low NIR: high blue/NIR ratio, NDWI) to get candidates; then a small CNN/segmentation model trained on the existing Florida county pool points as labels (Florida NAIP + county records = free training set); output points into the same pool tiles with kind `"ai"`, labelled "Pool (detected from aerial photo)"; dedupe against OSM points; spot-check precision on known neighbourhoods before publishing.

## San Diego County (2026-10-31, branch `sandiego`)

**Bottom line:** San Diego County added to the SoCal OSM water/pool build, plus real Assessor pool records for all of San Diego County (SanGIS/SANDAG parcels, POOL = 'Y') and for the City of Palm Desert (Riverside County CREST tax data published by the city). Florida pool counts unchanged.

### Sources
- **Used:** SanGIS/SANDAG regional parcel layer, public ArcGIS service `geo.sandag.org/server/rest/services/Hosted/Parcels/FeatureServer/0` (no login). 109,149 parcel records with POOL = 'Y' -> 108,619 distinct parcel polygons (stacked condo APNs counted once), placed at parcel centroids.
- **Used:** City of Palm Desert `Palm_Desert_Parcels_CREST` (public ArcGIS Online FeatureServer, HAS_POOL = '1'): 9,434 pool parcels.
- **Found, skipped:** LA County GIS (Incapsula bot protection, as before). No public pool flag found for Orange, Ventura, Riverside (county-wide) or San Bernardino assessor data in an ArcGIS Online search. User-uploaded AGOL snapshots of SanGIS parcels not used (the SANDAG-hosted copy is the official, current one). data.sandiegocounty.gov had no pool dataset.
- New script `scripts/build_ca_parcel_pools.py`; runs weekly in the workflow's Assemble step after the OSM pool copy (`|| echo` keeps committed tiles if the fetch fails or returns implausibly few records).

### OSM vs records
OSM pool points within ~30 m of a record point are dropped as duplicates (a parcel centroid sits 10-25 m from the pool, so a 4 m test would not catch them); others (hotel/public pools, unflagged parcels) are kept. San Diego: 3,308 OSM dropped, 2,106 kept in those tiles; Palm Desert: 65 dropped.

| County | Pool records | OSM pool points |
|---|---|---|
| San Diego | 108,619 | 2,129 |
| Riverside | 9,434 (Palm Desert only) | 5,875 |
| Los Angeles | - | 29,385 |
| Orange | - | 5,727 |
| San Bernardino | - | 3,773 |
| Ventura | - | 1,931 |
| County-line buffer | - | 24 |

Water: 60,956 features, 2,569 tiles (43 MB, CI-built, not committed) for the six counties.

### Regression (Playwright, local docs/ + locally built water tiles, 500 m)
Florida pools: Land O Lakes 2329, Westchase 3096, Largo 2696, Sarasota 3101, Mandarin 648, Inverness 592, identical to live (checked live first). SoCal OSM counts unchanged: Santa Monica 47, Pasadena 1938, Irvine 176, Thousand Oaks 73, Riverside 70, Rancho Cucamonga 145, Long Beach 24.

| Place | Hazards within 500 m | Pool records (loaded tiles) | OSM pools (loaded tiles) |
|---|---|---|---|
| Oceanside, CA 92056 | 54 | 2434 | 24 |
| Carlsbad | 62 | 1758 | 11 |
| Escondido | 10 | 1491 | 38 |
| Chula Vista | 15 | 1241 | 20 |
| La Mesa | 17 | 2255 | 18 |
| Downtown San Diego | 12 | 341 | 74 |
| Palm Desert (Riverside Co.) | 61 | 3490 | 45 |

Hazard counts include pool records inside the radius. Not verified: the CI step itself (Geofabrik socal-latest), which only runs on main.
