# Nationwide water layer: feasibility and build plan

Branch `uswater` (draft, not merged, live site unchanged). Measured 2026-11-01 in the build sandbox (2 vCPU, 7 GB RAM).

## Summary

- **Feasible. Recommend Cloudflare R2 behind a custom domain (`water.givekidsavoice.org`).** GitHub Pages can't hold it: the US is roughly 5.5–12 GB in today's tile format and about 300–450k files. The Pages limits are 1 GB and a 10-minute deploy.
- **The new packed format is about 10x smaller with no measurable loss of accuracy.** It uses 3–5 m Douglas-Peucker simplification, delta-encoded integer coordinates and gzip. National storage drops to about 0.5–0.9 GB (about 1–2 GB counting each state's own copy).
- **Expected cost: about $0 a month.** Storage and a 500k-visitor TV day both fit R2's free tier, and R2 charges nothing for egress. Even with no free tier the bill would stay under $5 a month.
- **CI:** two states a day from Geofabrik, refreshing the whole country each month. Build jobs run in parallel and a single sync job uploads one state at a time. A failed state keeps last month's tiles.
- **Interim:** the Overpass fallback no longer asks all four servers at once. It caches answers for 7 days, tries at most two servers, and pauses for 2 minutes after a 429/503/504. When it gives up it shows a clear message.

## 1. Measurements

Michigan has dense water: the Great Lakes coast and about 11k inland lakes. Georgia is a mid state with heavy stream and pond mapping. The extracts came from download.openstreetmap.fr because Geofabrik is blocked in the sandbox. That mirror has no Minnesota, Louisiana or Arizona state files. For a dry region I used the committed `docs/data/water` tiles, which turned out to be Southern California (lat 32.8–35.9, lon -120.2 to -114.2). Statewide Arizona was not built.

Pipeline: `scripts/build_osm_state.py filter` (pyosmium) → `export` → `build_water_tiles.py` → `pack_tiles.py`.

| | Michigan | Georgia | SoCal (committed, v1) |
|---|---|---|---|
| Source .osm.pbf | 348 MB | 391 MB | – |
| Download time | 18 s | 23 s | – |
| Filter (pyosmium; CI uses osmium-tool, ~10x faster) | 321 s | 346 s | – |
| Filtered pbf | 41.6 MB | 66.6 MB | – |
| Export → geojsonseq | 125 s (226 MB) | 171 s (310 MB) | – |
| Features (water areas / lines / pools) | 85,270 / 167,357 / 9,988 | 102,712 / 197,472 / 12,651 | – |
| Tiling time | 79 s | 101 s | – |
| Tiles | 7,283 | 5,919 | 2,163 |
| **v1 as today** raw total | 145.2 MB | 200.5 MB | 33.6 MB |
| v1 gzip / brotli total | 31.3 / 29.8 MB | 44.0 / 42.0 MB | 7.1 / 6.7 MB |
| v1 tile mean / median / p99 / max | 19.9 / 14.2 / 124 / 308 KB | 33.9 / 27.8 / 114 / 174 KB | 15.5 / 7.7 / 90 / 157 KB |
| v1 + DP 2 m raw / gzip | 112.9 / 24.7 MB | – | – |
| v1 + DP 5 m raw / gzip | 87.9 / 19.2 MB | 90.3 / 19.7 MB | – |
| **v2 packed (DP 5 m + delta ints + gzip-9)** total | **13.2 MB** | **14.1 MB** | – |
| v2 tile mean / median / p99 / max (bytes on the wire) | 1.8 / 1.5 / 7.4 / 14.7 KB | 2.4 / 2.4 / 6.6 / 15.3 KB | – |
| Pack time | 7 s | ~8 s | – |

### Does simplification hurt accuracy within 1.2 km of a home?

I picked random points in tiles and compared distance-to-edge for every hazard within 1.2 km, original against simplified, loading the 3x3 tiles around each point (`acc.py` in the measurement scratch).

| | points / hazards | per-hazard distance change p99 / max | nearest-hazard change max | hazards lost / gained |
|---|---|---|---|---|
| MI, DP 2 m | 300 / 2,872 | 0.92 / 2.05 m | 1.62 m | 0 / 0 |
| MI, DP 5 m | 300 / 2,872 | 2.72 / 4.75 m | 4.75 m | 0 / 0 |
| GA, DP 5 m | 200 / 2,113 | 3.41 / 5.89 m | 3.78 m | 0 / 0 |

A pond smaller than the tolerance keeps its original outline, so nothing disappears. Distances are shown rounded to metres and feet. A 3–5 m shift is smaller than OSM's own mapping error. **The draft CI uses 3 m.** Dropping tiny features far from homes isn't needed: once the geometry is simplified, the pond count no longer drives tile size. I also didn't want to judge "far from homes" without address data.

Delta-int encoding halves the raw size (88 → 45 MB for MI) and cuts gzip by about 30% (19.2 → 13.2 MB). The decoder is a 1-line function, verified against the v1 coordinates in node.

### National extrapolation (by land area; MI 146k km², GA 149k km², US 9.15M km²)

- **Tiles:** MI and GA have 0.040–0.050 tiles per km² (about 100% of land cells are non-empty). Applied to the US that gives 365–455k. Arid western cells are sparser, so **about 300–450k tiles** is a reasonable range. Alaska (about 100k cells) is the biggest unknown.
- **Today's v1 format:** 0.6 (SoCal) to 1.35 (GA) KB per km², so **about 5.5–12 GB raw** (about 1.3–2.7 GB gzipped).
- **v2 packed:** 0.090–0.095 KB per km² on MI and GA, so **about 0.5–0.9 GB** public, plus a second per-state `src/` copy: **about 1–2 GB in the bucket**.

## 2. Hosting

| | GitHub Pages | Cloudflare R2 + custom domain |
|---|---|---|
| Size limit | 1 GB published site: **fails** (v1 is 5.5–12 GB; Pages stores files uncompressed) | none that matters (10 GB free) |
| File count / deploy | ~400k files in one artifact, 10-min deploy timeout: **impractical** | upload only changed objects |
| Bandwidth | soft 100 GB/month, no hard SLA under a spike | egress free; Cloudflare edge cache in front |
| Precompressed tiles | no (Pages gzips on the fly) | yes (`Content-Encoding: gzip` stored) |

**Recommendation: R2.** Keep the site, county pool tiles and the current FL/SoCal/AZ/NV/TX water on Pages as they are. Serve national tiles from `https://water.givekidsavoice.org/v2/<key>.json`.

**Cost.** R2 list prices (verify at signup): storage $0.015/GB-month with 10 GB free; Class A (writes) $4.50/M with 1M/month free; Class B (reads) $0.36/M with 10M/month free; egress $0.

- Storage, 2 GB: **$0** (worst case $0.03).
- Monthly refresh: about 30–60k changed tiles in a typical month. The initial backfill is about 0.8M writes, which fits the free 1M.
- **TV spike:** 500k visitors × 4–8 tiles = 2–4M tile requests, plus 500k for `coverage.json`. That is about 4–10 GB transferred at 1.8–2.4 KB per tile. With an edge cache rule most requests never reach R2. Even with no caching at all, 4.5M Class B reads sit inside the free 10M. **Expected $0; ceiling under $5/month.**
- A `r2.dev` public URL is rate-limited and not meant for production. A custom domain needs givekidsavoice.org's DNS on Cloudflare (free plan). Alternative if he won't move DNS: a Worker on workers.dev reading the bucket. The free Workers plan stops at 100k requests a day, so that route needs Workers Paid at $5/month.

**Front end** (`docs/index.html` on this branch):

- `WATER_CDN = 'https://water.givekidsavoice.org/v2/'`. An empty string switches the layer off.
- `coverage.json` (about 1k one-degree cells, a few KB) is loaded once. If every tile key around the home falls in covered cells, tiles come from R2. **A 404 there means "no mapped water in this tile"**, so homes with no water nearby still get an instant answer and nothing falls through to Overpass. The current loader can't do this.
- If R2 is unreachable (network error or 5xx), the loader falls back to this site's own v1 `data/water` tiles and then to guarded Overpass. Florida and the other current regions keep working either way.
- Reads both formats (`g` for v1, `d` for v2).
- **CORS:** a plain GET with no custom headers, so the bucket only needs `Access-Control-Allow-Origin`. The owner pastes this into the bucket's CORS policy: `[{"AllowedOrigins":["https://hydroshield.givekidsavoice.org"],"AllowedMethods":["GET","HEAD"],"MaxAgeSeconds":86400}]`.
- **Cache headers** are set at upload: `Cache-Control: public, max-age=86400, stale-while-revalidate=604800`, and 1 h for `coverage.json`. Cloudflare doesn't edge-cache `.json` by default, so add a Cache Rule: hostname `water.givekidsavoice.org` → Eligible for cache, edge TTL 1 day.

## 3. CI (draft: `.github/workflows/us-water.yml`)

- **Schedule** (`scripts/us_states.json`): days 1–23 rebuild two states each, pairing one big state with one small one. Days 24–28 rebuild one each (AZ, KY, SC, MD, AK). Total 51 = 50 states + DC.
- **Manual run:** `workflow_dispatch` with `states=all` (backfill: 51 jobs, 4 in parallel, about 3–4 h) or a list such as `GA MI`.
- **Build job**, one matrix job per state, 90-minute limit:
  - Geofabrik `<slug>-latest.osm.pbf` and `<slug>.poly`
  - `osmium tags-filter` (same tags as Florida, pools as `nwr`)
  - `build_osm_state.py export`, which outputs pools as points
  - `build_water_tiles.py --simplify 3`
  - `pack_tiles.py --pools docs/data/pools`, which drops OSM pools within about 30 m of a county record
  - Uploads the result as an artifact. Estimated 10–25 min per state; California, about 1.2 GB, is the long one.
- **Sync job**, one job, states processed one after another — `sync_tiles_r2.py`:
  - **Sanity guard:** if a state comes back with fewer than 80% of last month's tiles, nothing is written.
  - **Change detection:** md5 comparison, so only changed tiles are uploaded and tiles that vanished are removed.
  - **Border tiles:** each state keeps its own `src/<ST>/<key>.json`. The public `v2/<key>.json` is the deduplicated union of every state's src copy for that key, so rebuilding Georgia never deletes Florida's features on the line. Tested with moto (a mocked S3): two states share a tile, one is then rebuilt without that tile, and the neighbour's features survive.
  - Writes `manifests/<ST>.json` and rebuilds `v2/coverage.json`.
- A failed build means no artifact, so that state's old tiles stay live. A failed upload is reported as a warning.
- This workflow only runs once it is on the default branch. On `uswater` it is inert.
- **Secrets:** `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.

## 4. Interim protection (in this branch's `index.html`, ready to ship on its own)

- Overpass answers are cached in localStorage for 7 days, keyed by home rounded to about 100 m plus radius.
- Servers are asked **one at a time, starting at a random one, at most two**. Before, the page asked all four at once, which multiplies load four times exactly when servers are struggling.
- After a 429/503/504 the browser pauses Overpass for 2 minutes.
- On failure the message is plain: prebuilt data doesn't cover the area yet, the public servers are busy, try again in a few minutes, and meanwhile walk the street.
- Optional extra: a `data/config.json` kill-switch so the owner can turn off live Overpass with one commit during the broadcast.

**Other spike risks outside water tiles:**

- Nominatim (geocoder fallback): its policy is at most 1 request per second, so it will block a spike.
- Esri's keyless geocoder and basemap: throttling limits unknown.
- Pages' soft 100 GB/month: 500k visitors × page weight could reach it.
- Once DNS is on Cloudflare, proxying `hydroshield` through Cloudflare (orange cloud) shields Pages.
- An Esri developer key or a paid geocoder is worth considering before air date.

## Owner actions (Mark does these; we never handle passwords)

1. Create a Cloudflare account and **add a payment method**. R2 requires one even on the free tier.
2. Add the `givekidsavoice.org` site to Cloudflare (free plan) and change the nameservers at the registrar. **Before switching, check that the imported DNS records include the existing `hydroshield` CNAME and any email/MX records.**
3. In R2, create a bucket (e.g. `hydroshield-water`) and connect the custom domain `water.givekidsavoice.org`.
4. Paste the CORS JSON above into the bucket's CORS policy. Add the Cache Rule described in section 2.
5. Create an R2 API token with **Object Read & Write, limited to that bucket**.
6. In GitHub (repo → Settings → Secrets and variables → Actions), add `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` and `R2_BUCKET`.
7. Then: merge, run the workflow with `states=all`, check a few addresses, and only then let the front end use `WATER_CDN` (it can ship with `''` until the backfill is done).

## Unverified / open

- **No real upload yet** (no credentials). The sync logic was tested only against moto. R2's handling of stored `Content-Encoding: gzip` through a custom domain, including CF re-compression, needs one live check.
- **CI timings are estimates.** `osmium tags-filter` speed and the California/Texas/Alaska export memory and time weren't measured here.
- The draft workflow has never run on Actions, and the edited `index.html` was only syntax-checked. Nobody has clicked through it in a browser against a real bucket.
- **The national figures are extrapolated from 2 states plus SoCal.** Alaska (bulk-imported lakes and streams) could be much larger than the area-based estimate. Geofabrik state extracts may differ slightly from the openstreetmap.fr ones used here.
- **Coverage before backfill:** a 1° cell counts as covered once every state *built so far* touching it is built. Until all states exist, a border cell can be marked covered while its unbuilt neighbour's part is missing. Fix: precompute `cell_states` from all 51 `.poly` files (hook already in `sync_tiles_r2.py`), or enable the front end only after the full backfill (recommended).
- R2 and Workers prices and free tiers are from list prices; confirm at signup.
- Not changed: the existing Pages workflow, county pool tiles, and the v1 regional builds.
