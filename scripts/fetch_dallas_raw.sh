#!/bin/bash
# Download Dallas Central Appraisal District's public data products into $1 (no login):
#   cur.zip   DCAD<year>_CURRENT.ZIP (RES_DETAIL.CSV has POOL_IND) from https://www.dallascad.org/DataProducts.aspx
#   PARCEL*/  PARCEL<year>.zip parcel shapefile from https://www.dallascad.org/GISDataProducts.aspx
# Tries this year, then last year. dallascad.org often resets connections, so curl retries.
set -euo pipefail
out=$1; mkdir -p "$out"; cd "$out"
UA="Mozilla/5.0 (ProjectHydroShield; givekidsavoice.org)"
B=https://www.dallascad.org
get() { curl -sSfL --retry 5 --retry-all-errors --retry-delay 10 -m 1800 -A "$UA" "$@"; }
link() {  # $1 page, $2 file-name regex -> URL-encoded download link from that page
  get "$B/$1" | grep -oiE "ViewPDFs\.aspx\?type=3&(amp;)?id=[^\"]*$2\"" | head -1 | sed -e 's/"$//' -e 's/&amp;/\&/g' -e 's/ /%20/g' -e 's/\\/%5C/g'
}
y=$(date -u +%Y)
for yr in $y $((y - 1)); do
  u=$(link DataProducts.aspx "DCAD${yr}_CURRENT\.zip") || true
  [ -n "$u" ] || continue
  get -o cur.zip "$B/$u" && unzip -l cur.zip | grep -q RES_DETAIL.CSV && break
  rm -f cur.zip
done
[ -f cur.zip ] || { echo "no DCAD current file"; exit 1; }
for yr in $y $((y - 1)); do
  u=$(link GISDataProducts.aspx "PARCEL${yr}\.zip") || true
  [ -n "$u" ] || continue
  get -o parcel.zip "$B/$u" && unzip -oq parcel.zip -d parcel && rm parcel.zip && break
  rm -rf parcel.zip parcel
done
find parcel -iname 'PARCEL20*.shp' | grep -q . || { echo "no DCAD parcel shapefile"; exit 1; }
