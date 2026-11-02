# Metros status (Arizona, Nevada, Texas) - 2026-11-01

Branch `metros`, based on main 5505203. Not merged or deployed.

## Pool records (committed in docs/data/pools, coordinates only)

| County | Source (publisher) | Filter | Pools placed |
|---|---|---|---|
| Maricopa AZ | Maricopa County Enterprise GIS, Parcel_Data_View | Pool='YES', Latitude_DD/Longitude_DD | 416,330 |
| Clark NV | Clark County Assessor AORES extract + CC_PARCELS_SHP centroids (republished by City of Las Vegas Office of GIS) | POOL>=1, joined on PARCEL | 135,760 (136,093 distinct parcels in AORES) |
| Harris TX | Harris Central Appraisal District, Real_building_land.zip extra_features + GIS Parcels.zip | cd RRP1-RRP7, joined on acct | 122,826 |
| Tarrant TX | Tarrant Appraisal District PropertyData(Delimited)_R.ZIP + TAD OD_Parcels MapServer | Swimming_Pool_Ind='Y', GIS_Link=TAXPIN | 78,451 |
| Dallas TX | Dallas Central Appraisal District DCAD2026_CURRENT.ZIP RES_DETAIL.CSV + DCAD PARCEL2026 shapefile (both official DCAD; the unofficial AGOL layer is not used) | POOL_IND='Y', joined on account | 64,055 |
| Collin TX | Collin Central Appraisal District CCAD_Parcel_Feature_Set/4 | imprvPoolFlag='T' | 63,860 |

Total county points: 881,282. OSM pools merged after a ~30 m dedupe against county points:
Arizona +7,040 (146,728 dropped), Nevada +968 (1,705 dropped), Texas +3,513 (7,712 dropped).
903 new tiles plus 1 changed shared tile (712_-2308, Primm, on the CA/NV line); 21 MB of new tiles.

## Water (not committed; Actions cache per region)
OSM water from openstreetmap.fr extracts locally (Geofabrik in CI), clipped by build_osm_region.py:
Arizona 18,602 features / 1,006 tiles; Nevada 10,260 / 572; Texas 29,754 / 625.
25 water tiles are shared between regions (CA/NV line); scripts/merge_tiles.py concatenates them at assembly.

## Workflow slots
22 az-water, 23 nv-water, 24 tx-water, 25 az-nv-pools (Maricopa + Clark), 26 harris, 27 tarrant-collin, 28 dallas.
Water slots also merge fresh OSM pool points into the committed tiles (build_osm_region.py merge), no county download needed.
Southern California's pool step now uses the same merge instead of `cp`, so it can no longer overwrite the shared Clark tile.

## Regression
FL and CA baselines: identical to live (pool counts and hazard counts) using the live FL water tiles.
New metros: see the main session report.

## Unverified
- The new workflow steps have not run on GitHub (Geofabrik downloads, the Texas filter time, the DCAD fetch script end to end, HCAD year fallback).
- The first push after merge has no AZ/NV/TX water cache, so all three regions build in that run (estimated 25-40 min extra).
