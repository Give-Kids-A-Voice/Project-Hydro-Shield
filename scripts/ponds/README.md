# Aerial pond detector (ponds no other map has)

Retention and neighborhood ponds are where most children with autism drown, and many are missing from OpenStreetMap
and USGS. This finds standing water in USDA NAIP photos and keeps only ponds that are not already on the map.

1. `build_ds.py`: candidate blobs = dark-in-near-infrared areas (NDWI > 0.15, NIR < 70), 200 m2 to 30 ha, with 29
   shape/colour/context features and a 48x48 4-band patch. Labelled by mapped water: >= 50% inside a mapped water
   area = 1, no mapped water within 30 m = 0.
2. `train.py`: gradient boosting on the features + 3 small CNNs on the patches (`pcnn.py`), averaged.
   Trained on 8 Florida areas (Tampa, Orlando, Jacksonville, Port St. Lucie, Lakeland, Sarasota, Ocala, Fort Myers;
   2025 imagery). Held out on Port St. Lucie at 0.7: 82% of hits were already-mapped water, and when the rest were
   looked at by eye almost all were real unmapped ponds.
3. `pond_run.py <name> x0 y0 x1 y1 year`: scores every candidate, keeps >= 0.7 with no mapped water within 30 m +
   the pond's radius, drops artificial turf (bright green, dark NIR). Outlines simplified to ~1.5 m.
4. `psheet.py`: 48-sample review sheet (random.seed(7)) with outlines. Every area is reviewed by eye.
5. `pond_write.py <workdir> [bad sheet indices]`: writes docs/data/ponds/<y>_<x>.json ({"i", "g": [ring]}).
   The page shows them as "Pond (aerial estimate)" with a "may be wrong; please verify" note.
