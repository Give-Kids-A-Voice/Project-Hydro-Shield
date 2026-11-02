# Aerial pool estimates (USDA NAIP)

Where there are no county pool records, the map only has OpenStreetMap pools, and those miss most backyard pools.
This folder fills that gap with pools detected in public USDA NAIP aerial imagery. The detections are written into
the shared pool tiles as `[lat, lon, "air"]`. The page labels them **Pool (aerial estimate)**, counts them separately
in the status line, and drops any that lie within 30 m of a county or OpenStreetMap pool.

## Imagery

USDA NAIP (National Agriculture Imagery Program) is public domain: 4 bands (red, green, blue, near-infrared) at 0.6 m,
or 0.3 m in recent years in some states. It is flown in summer, about every 2 years per state. The scripts read it from
the Microsoft Planetary Computer STAC API (collection `naip`). The files are cloud-optimised GeoTIFFs on Azure, and
the free anonymous SAS token comes from `/api/sas/v1/token/naip`, so no account is needed. Only the window that is
needed is range-read (about 12 MB per km²), and it is held in memory. No imagery is written to disk. Imagery at 0.3 m
is averaged down to 0.6 m so one model fits every state.

Latest years on Planetary Computer when this was built: CA 2022, AZ 2023 (0.3 m), TX 2022.

## Detector (`detect.py`, `cnn.py`, `model/`)

1. **Scene normalisation.** Haze and colour balance vary a lot between flights. For example, Contra Costa 2022 has a
   strong blue cast, and Tracy 2022 has deep blue shadows. For each ~1 km chunk, the detector measures the median
   B−R, G−R and N−G over non-vegetated pixels and its median brightness. The thresholds are relative to those values.
2. **Candidates.** A *core* mask finds bright pixels where blue and green are well above red and NIR is below green,
   all relative to the scene: water reflects blue and green and absorbs NIR. A looser mask grows the core into the
   rest of the pool. Connected components of 6–2,500 m² that contain core pixels are kept.
3. **Features** (32 per candidate): mean bands and ratios (G/B, N/G, …), scene-relative colour, area, solidity,
   extent, elongation, perimeter²/area, and the surrounding ring's NDVI, brightness and colour.
4. **Two classifiers**, averaged:
   * gradient boosting (scikit-learn `HistGradientBoostingClassifier`) on the features;
   * a tiny CNN (about 130k parameters, 3 seeds, 4-rotation test-time augmentation) on a 40×40 px (24 m) patch
     centred on the candidate. The CNN is what learns to reject house shadows, solar panels and blue tarps.
   A candidate is kept when the average score is ≥ 0.7. Detections within 8 m of each other are merged (a pool split
   in two, a pool plus its spa).

## Labels and validation (`train/`)

Ground truth is the pool-flagged **parcel polygons** from the same public assessor layers the county pool builders use
(SanGIS, Riverside CREST, Pasadena, Contra Costa, San Joaquin, Solano, Maricopa, Collin CAD). Polygons are needed
because the committed county points are parcel centroids, often 15–40 m from the pool. A point-to-point test at 20 m
mostly measures lot size, not the detector.

* **Precision (GT):** a detection inside a pool-flagged parcel, or within 15 m of an OpenStreetMap pool. *Each pool
  parcel can confirm only one detection*, so a solar panel on the roof of a pool home does not count as correct.
* **Recall:** the share of pool-flagged parcels that hold at least one detection.
* **Chance:** the same precision test after shifting every detection 250 m. This is how often a random spot lands in
  a pool parcel, and it shows the metric is far from trivial.
* **Training labels:** the strongest candidate in each pool parcel is positive. Other candidates in that parcel are
  left out. Candidates outside pool parcels are negative.

The model was trained on six 2×2 km windows: four in San Diego County, plus Antioch (Contra Costa) and Stockton (San
Joaquin) for Central Valley imagery. It was **evaluated on eight held-out windows that it never saw**:

| held-out window (NAIP year) | detections | GT-confirmed | precision (GT) | chance | pool parcels | found | recall |
|---|---|---|---|---|---|---|---|
| Corona, Riverside Co. (2022) | 409 | 359 | 0.878 | 0.27 | 429 | 354 | 0.825 |
| Palm Desert, Riverside Co. (2022) | 1,258 | 1,205 | 0.958 | 0.36 | 1,379 | 1,195 | 0.867 |
| Pasadena / Altadena (2022) | 410 | 345 | 0.841 | 0.25 | 465 | 344 | 0.740 |
| Walnut Creek, Contra Costa (2022) | 525 | 516 | 0.983 | 0.30 | 689 | 512 | 0.743 |
| Tracy, San Joaquin Co. (2022) | 753 | 616 | 0.818 | 0.22 | 796 | 613 | 0.770 |
| Vacaville, Solano Co. (2022) | 518 | 477 | 0.921 | 0.15 | 561 | 470 | 0.838 |
| Scottsdale, Maricopa Co. AZ (2023) | 1,429 | 1,415 | 0.990 | 0.43 | 1,856 | 1,405 | 0.757 |
| Plano, Collin Co. TX (2022) | 831 | 817 | 0.983 | 0.36 | 1,139 | 814 | 0.715 |
| **pooled** | **6,133** | **5,750** | **0.938** | | **7,314** | **5,707** | **0.780** |

"Unconfirmed" is not the same as "wrong". Assessor records lag new pools, leave out above-ground pools and HOA or
apartment pools, and the Pasadena window spills into Altadena and San Marino, which have no city pool flag. A random
sample of 36 unconfirmed detections per window was inspected by eye:

| window | unconfirmed | real pools in sample of 36 | estimated precision after inspection |
|---|---|---|---|
| Pasadena / Altadena | 65 | ~32 | ~0.98 |
| Vacaville | 41 | ~22 | ~0.97 |
| Corona | 50 | ~16 (rest: rooftop solar, blue roofs and tarps, sport courts) | ~0.93 |
| Tracy | 137 | ~5 (rest: deep blue house shadows) | **~0.84** |

The pooled precision clears the 0.85 bar, and so does every window except Tracy after inspection. **Tracy is below
it**: that flight has long, very blue shadows. For Central Valley counties, inspect a sample before publishing, use a
higher threshold (0.8 gives Tracy 0.89 GT-confirmed, recall 0.74), or add a local training window.

Recall misses are mostly pools under tree canopy, covered or green pools, very small spas, and pools built after the
imagery date (the GT is current; the imagery is from 2022).

To retrain or re-evaluate (from a scratch work directory; it writes `cand/`, `parcels/` and the models there):

    cd /tmp/aerial-work && for f in /path/to/repo/scripts/aerial/train/*.py; do ln -sf $f .; done
    python3 -c "import subprocess,sys; from areas import AREAS; [subprocess.run([sys.executable,'run_area.py',n,*map(str,b),str(y)]) for n,(s,b,y,r) in AREAS.items()]"
    python3 train2.py && python3 evalscores.py avg 0.6,0.7,0.8
    python3 audit.py <window> 0.7 36 fp     # contact sheet of unconfirmed detections -> crops/

## Running a region

    python3 scripts/aerial/run_region.py <name> <lon0> <lat0> <lon1> <lat1> <naip-year> --write docs/data/pools

It needs `numpy scipy scikit-image scikit-learn rasterio pyproj` and CPU-only `torch`. It works in 0.01-degree chunks,
checkpoints to `/tmp/aerial-<name>/chunks.jsonl` (so a re-run resumes), merges the detections, and then replaces the
`air` points inside the box. It never writes air points into a tile that has county records, and it skips points
within 30 m of a county or OSM point. `build_osm_region.py` and `pack_tiles.py` ignore `air` points when they
de-duplicate OSM pools, so an OSM pool is never dropped because of an estimate.

## Pilot: San Fernando Valley (Los Angeles), NAIP 2022

    python3 scripts/aerial/run_region.py sfv -118.67 34.15 -118.35 34.33 2022 --write docs/data/pools

* Box 34.15–34.33 N, 118.67–118.35 W (~590 km²): 576 chunks, 24 NAIP items. It took about 1 hour on a 2 vCPU /
  8 GB box (5.5–6 s per chunk, about 0.9 GB peak memory).
* 62,252 pools after merging. 59,918 were written as `air` points and 2,334 were skipped as duplicates of OSM pools
  already in the tiles. That is 26 tiles and +1.7 MB of JSON.
* A random sample of 48 pilot detections was inspected by eye: 45–47 were pools. The others were a tennis court, a
  blue sport court, and two uncertain cases.
* Page, hazards within 500 m (before → after): Sherman Oaks 24 → 64, Northridge 0 → 26, Woodland Hills 4 → 33.

## Scaling to the other gap metros

Measured cost on this 2 vCPU box: **~600 km² per hour** (about 10 CPU-seconds and 12 MB of imagery read per km²).

Rough urbanised areas: rest of LA County ~3,500 km², Orange ~1,000, Sacramento metro ~1,300, Tucson ~900, San Antonio
(Bexar) ~1,300, Austin (Travis) ~900, Atlanta core counties ~4,000, Charlotte ~1,500, Salt Lake ~700, and others
~2,000. That totals **~17,000 km²**.

* **This box:** ~28–30 hours of wall time, run one county at a time (each run resumes if stopped). About 200 GB is
  read from Planetary Computer, which is free, and nothing is stored.
* **AWS (nonprofit credits):** ~47 CPU-hours in total. For example, one c7i.4xlarge (16 vCPU, about $0.7/h on demand)
  running 8 two-thread workers on different counties finishes in about 3–4 hours, for **under $5 of compute**. Even
  with generous overhead it is under $25. Reading from Azure costs nothing on either side. AWS's own NAIP bucket
  (`naip-analytic`, requester-pays) is an alternative that adds S3 request fees.
* **GitHub Actions (no credits needed):** a hosted runner manages about the same rate as this box. A county of
  ≤1,500 km² fits in one 6-hour job, so a yearly "aerial" slot in `water-tiles.yml` can rotate through the gap
  counties.

Refresh: NAIP is reflown about every 2 years per state, so once a year is plenty. Check the STAC for a newer
`naip:year`, re-run that state's boxes with the new year (the run replaces the box's `air` points), and before
committing, inspect a random contact sheet of ~50 detections (`train/audit.py`-style). Where a flight looks like
Tracy 2022 (long blue shadows), raise `--threshold` to 0.8 or add a local training window. When a county later gets
assessor pool records, the county builders rewrite those tiles and the `air` points there go away.
