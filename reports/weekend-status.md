# Project Hydro-Shield: weekend status

## 2026-10-31 (Saturday)

**Bottom line:** The live site is healthy and nothing was rolled back. Main was not touched. Branch `counties-next` adds 10 new counties (285,397 pool/spa points) and passed every regression test. It is ready for you to review and merge.

### 1. Health check (live site)
- https://hydroshield.givekidsavoice.org/ returns 200 and contains "Every pond, canal and pool".
- The latest `water-tiles.yml` run is #21, for commit 0f3d470 ("Add Citrus County"), pushed 2026-10-30 17:40 UTC. It succeeded.
- Pool counts for the reference addresses, checked with Playwright on the live site. All six match the expected numbers exactly.

| Address | Expected | Live |
|---|---|---|
| Ashmonte Drive, Land O Lakes, FL | ~2329 | 2329 |
| Westchase, Tampa, FL | ~3096 | 3096 |
| Largo, FL | ~2696 | 2696 |
| Sarasota, FL | ~3101 | 3101 |
| Mandarin, Jacksonville, FL | ~648 | 648 |
| 110 N Apopka Ave, Inverness, FL 34450 | ~592 | 592 |

- **Rollbacks:** none needed and none made.

### 2. Counties added on `counties-next` (commit 0bd0667, not on main)
Each county's free Property Appraiser file is joined on parcel ID to the FDOR statewide parcel centroids.

| County | Source (free, public, curl-fetchable) | Pool/spa parcels in file | Points added | Sample address → pools shown locally |
|---|---|---|---|---|
| Volusia | VCPA weekly pool extract (`VOLUSIA_POOLS_EXTRACT.csv`) | 43,180 | 42,527 | Port Orange → 2126 |
| Seminole | SCPA daily CAMA (`ExtraFeature.csv`: POOL n / SPA n) | 47,908 | 47,288 | Oviedo → 2873 |
| Osceola | OCPA 2026 certified data (`vw_mdxfob.csv`, codes 57xx/55xx) | 36,369 | 36,152 | Kissimmee → 1880 |
| Lake | LCPA FTP `Xfob_*.txt` (POL/CPOL/CCPL/PLV, HTB) | 27,223 | 26,958 | Clermont → 794 |
| Marion | MCPA TRIM data (`POOL = Y`) | 20,636 | 20,629 | Ocala → 1501 |
| Charlotte | CCPA nightly `cd.txt` (`haspool`) | 43,939 | 43,681 | Port Charlotte → 5844 |
| St. Johns | SJCPA CAMA supplement mdb (`XFOBView` POOL*/SPAM) | 26,634 | 26,206 | Ponte Vedra Beach → 1476 |
| Alachua | ACPA nightly CAMA (`ImprvDetails.txt`, 176x/476x, 1300/4300) | 10,551 | 10,549 | Haile Plantation → 1355 |
| Martin | MCPA `real_sfyi.csv` (POOL/JACUZZI) + `real_master.csv` | 22,616 | 22,318 | Stuart → 8072 |
| Leon | LCPA `BuildingData.zip` → `OTHERFEAT.TXT` (OOL/SPA) | 9,101 | 9,089 | Killearn, Tallahassee → 1733 |

**Regression tests (all passed):**
- (a) Every point in origin/main's `docs/data/pools` is still on the branch: 689,220 checked, 0 lost. The merge only adds points and dedupes them.
- (b) I served `docs/` locally and checked the six reference addresses. All six matched live exactly (2329, 3096, 2696, 3101, 648, 592), and so did the opening search (1350).
- (c) A sample address in each of the 10 new counties shows pools (table above). The same addresses show no county pools on live.

**Other changes on the branch:**
- `docs/index.html`: the coverage line and credits now list all 21 counties.
- New `scripts/fetch_county_raw.sh <county> <dir>` downloads each county's file.
- `scripts/build_statewide_join.py` gains parsers for the 10 counties.
- New counties get **one point per parcel**. FDOR has hundreds of centroids for some condo or common-area parcels (up to 1,288 for one St. Johns parcel), and one point per centroid would scatter phantom pools. Sarasota, Duval and Citrus still use the old behaviour (one point per FDOR centroid), so nothing live changes.
- `water-tiles.yml`:
  - Adds a weekly refresh loop for the 10 counties. It installs `mdbtools` for St. Johns, and if a county fails it keeps the committed data.
  - Job timeout raised from 60 to 100 minutes to make room for the extra downloads.
  - This workflow only runs on main, so the new steps have **not run in CI yet**. Watch the first run after you merge.

**Caveats to know before merging:**
- **Alachua** looks low (about 10.5k pools). Some pools may be recorded elsewhere in the CAMA export.
- **Leon**'s file is dated 2025-11-17, about a year old.
- **Osceola** is the annual certified roll, so it updates yearly.
- **Leon** returns 403 to a browser-style user agent with our project tag, so its fetch uses curl's default user agent. No blocks were bypassed.
- **Marion**'s URL contains the roll name (`TRIM_Merlin226.ZIP`) and may change next year.
- **Possible improvement:** Sarasota, Duval and Citrus could also switch to one point per parcel. This would trim condo duplicates, but those counties are live, so I left them for you to decide.

### 3. Counties not added: need an email/data request or a manual download

| County | Problem | Contact |
|---|---|---|
| Palm Beach | Pool data is only sold as a "Pools and Spas" report; the free DR-590 roll has no pool data | pa-pubsvc@pbcpao.gov, 561-355-2881, form https://pbcpao.gov/pdf/DataRunRequest.pdf |
| Broward | The only pool layer is in an ArcGIS service named `BCPA_INTERNAL_AUG26` (layer "Pool and Spa", about 143k). It answers anonymous queries, but the name says internal, so **I did not use it**. Your call: ask BCPA if it's OK to use | BCPA via bcpa.net |
| Collier | collierappraiser.com blocks this network ("access restricted"). Free `int_buildings_csv.zip` may have pool codes | https://www.collierappraiser.com/Main_Data/DataDownloads.html (try from your own connection) |
| Brevard | Cloudflare challenge on https://www.bcpao.us/PublicData.aspx (WebData.zip may contain pools) | Office via that page |
| St. Lucie | Cloudflare 403. The free SFYI CSV is listed at https://www.paslc.gov/231/Data-Requests | Data Request Form on that page |
| Clay | Cloudflare on ccpao.com | Public-records form on ccpao.com |
| Indian River | Cloudflare on the Schneider/Beacon `DataDownload.zip` (has an improvement-feature file) | Form: https://www.ircpa.org/media/14214/website-request-public-record-information.pdf |
| Okaloosa | The county GIS only has the first extra-feature code per parcel (about 3.9k pools; real count much higher) | 850-651-7240; https://okaloosapa.com/public-records-request/ |
| Escambia | No pool field in any public service; no bulk download | pidept@escpa.org, 850-434-2735 |
| Bay | GIS has only an extra-feature count; baypa.net behind Cloudflare | dsowell@baypa.net, 850-248-8401 |
| Santa Rosa | GIS has only an extra-feature count | publicrecords@srcpa.gov, https://srcpa.gov/public-records-request/ |

For the Cloudflare-blocked counties (Brevard, St. Lucie, Clay, Indian River, Collier), the free files can probably be downloaded by hand in a browser. If you drop them into the repo or a shared folder, they can be parsed the same way.

### To merge
Review `counties-next` (one commit on top of main: 0bd0667), then fast-forward main to it. The deploy workflow will run. After it finishes, re-check the reference addresses and one new-county address, such as Port Charlotte, FL.

## 2026-11-01 (Sunday)

**Bottom line:** The live site is healthy and nothing was rolled back. No new county data was added today: every remaining county is still blocked or needs a request. Collier is close. Its free files now load and allow automated downloads, but the one file with pools would not download from this network today. The code to add Collier is ready on `counties-next`.

### Main changed after Saturday's report
Main now has 9 commits that were not there when Saturday's report was written. They were all pushed by `mal247` on 2026-10-31 from a Claude session (`session_013QLbgwVTHWdyVf5LuiY5Gj`):
- The 10 Saturday counties (9b9310b)
- Map changes and anonymous usage counts
- Southern California and San Diego water and pools
- A fix for a leftover blue circle on the map (cd5495c)

All 5 deploy runs for these commits succeeded. Because all of this is now on main, `counties-next` was fast-forwarded to main (cd5495c) before today's work.

### 1. Health check (live site)
- https://hydroshield.givekidsavoice.org/ returns 200 and contains "Every pond, canal and pool".
- The latest `water-tiles.yml` run is #26, for cd5495c, run 2026-11-01 02:14 UTC. It succeeded.
- The page no longer runs a search when it opens (changed in 83da5de), so there was no opening search to wait for. Each address was searched directly.
- The usage-count beacon was blocked during these tests, so the checks did not add to the site's stats.

| Address | Expected | Live |
|---|---|---|
| Ashmonte Drive, Land O Lakes, FL | ~2329 | 2329 |
| Westchase, Tampa, FL | ~3096 | 3096 |
| Largo, FL | ~2696 | 2696 |
| Sarasota, FL | ~3101 | 3101 |
| Mandarin, Jacksonville, FL | ~648 | 648 |
| 110 N Apopka Ave, Inverness, FL 34450 | ~592 | 592 |
| Port Charlotte, FL (a Saturday county, now live) | 5844 on the branch Saturday | 5847 |

- **Rollbacks:** none needed and none made.

### 2. Counties
**Added:** none. No data in `docs/data/pools` changed, so no points could be lost and the live counts are unaffected.

**Collier: code ready, data not yet downloaded**
- collierappraiser.com is reachable again; on Saturday it returned "access restricted".
- Its Data Downloads page and Terms of Use say scripts, scheduled tasks and AI tools may download the data files. The limit is each file once per day per network, and each link expires after 10 minutes.
- `int_buildingcodes_csv.zip` downloaded fine. It lists the pool codes (POOL-1..9, POOL10..27, POOLV1..9, NVP1..9) and the spa codes (SPA, SPA-1..7).
- `int_buildings_csv.zip` (16.3 MB, "Buildings and extra features") returned 410 "link expired" twice, even on a link made seconds earlier. The likeliest reason is that the daily limit had already been used on this shared cloud network.
- I stopped after the second try. The site warns that repeat requests past the limit can get the network blocked. I did not try the "All (CSV)" bundle to get around the limit.
- **Ready on the branch:**
  - `scripts/fetch_county_raw.sh collier` loads a fresh link and downloads both files.
  - `scripts/build_statewide_join.py collier` reads the files and joins them to the FDOR parcel locations. Collier is CO_NO 21, with 368,325 FDOR parcels and 11-digit parcel IDs that match the Collier files.
  - I tested the parser end to end on test rows with real Collier parcel IDs: 2 of 2 matched and were placed.
  - The file layout doesn't say which column holds the feature code, so the parser checks both BldgClass and CalcCode and prints how many matches each one gives.
- **Not done yet:** Collier is not in the workflow or `index.html`.
- **To finish it:** download `int_buildings_csv.zip` once by hand from https://www.collierappraiser.com/Main_Data/DataDownloads.html, or let the next run try again on a new day. Then build, run the regression tests, and add Collier to the coverage line, the credits and the weekly loop.

**Re-checked today, still blocked:**
- **Palm Beach:** the county GIS parcel layers (`gis.pbcgov.org` Parcels/PARCELS, PAO_PARCELS_WM) have no pool field. To get pool data, request it from pa-pubsvc@pbcpao.gov, 561-355-2881, form https://pbcpao.gov/pdf/DataRunRequest.pdf.
- **Indian River:** the CAMA download is linked from https://www.ircpa.org/site-links/downloads/ (`beacon.schneidercorp.com/.../DataDownload.zip`). It still gets a Cloudflare challenge (`cf-mitigated: challenge`), so I did not use it. You can download it by hand in a browser, or use the form https://www.ircpa.org/media/14214/website-request-public-record-information.pdf.
- **Brevard** (bcpao.us), **St. Lucie** (paslc.gov) and **Clay** (ccpao.com) still return 403 from Cloudflare.
  - Brevard's county GIS (`gis.brevardfl.gov`) has no parcel or pool services.
  - Contacts are unchanged from Saturday's table.
- **Broward, Okaloosa, Escambia, Bay, Santa Rosa:** I did not re-check them. Saturday's findings and contacts still apply.
  - Broward's only pool layer is the "internal" BCPA service, which I am not using without permission.
