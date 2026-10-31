#!/usr/bin/env bash
# Download the free public Property Appraiser file(s) build_statewide_join.py needs for one county.
#   scripts/fetch_county_raw.sh <county> <raw_dir>
# Exits non-zero if the download fails (the workflow then keeps the committed data).
set -euo pipefail
county=$1; raw=$2; mkdir -p "$raw"; cd "$raw"
UA="Mozilla/5.0 (ProjectHydroShield; givekidsavoice.org)"
get() { curl -sfL --retry 3 -A "$UA" -o "$1" "$2"; }
case "$county" in
  volusia)   # Volusia County Property Appraiser countywide pool extract (rebuilt weekly)
    get VOLUSIA_POOLS_EXTRACT.csv https://vcpa.vcgov.org/files/extracts/pools/VOLUSIA_POOLS_EXTRACT.csv ;;
  seminole)  # Seminole County Property Appraiser daily CAMA export
    get cama.zip https://files.scpafl.org/data/cama/SeminoleCounty.zip && unzip -joq cama.zip '*ExtraFeature.csv' && rm cama.zip ;;
  osceola)   # Osceola County Property Appraiser certified data (annual; link is scraped from the data page)
    u=$(curl -sf -A "$UA" https://www.property-appraiser.org/data/ | grep -oE 'https://www\.dropbox\.com/[^"]+CertifiedData_OCPA\.zip[^"]+' | head -1 | sed 's/&#038;/\&/g; s/&amp;/\&/g')
    [ -n "$u" ] && get ocpa.zip "$u" && unzip -joq ocpa.zip '*vw_mdxfob.csv' && rm ocpa.zip ;;
  lake)      # Lake County Property Appraiser extra-features file (newest Xfob_*.txt in the public FTP folder)
    f=$(curl -sf -A "$UA" https://c.lakecountyfl.gov/FTP/PA_office/Data/ | grep -oiE 'Xfob_[0-9]+\.txt' | sort -u | tail -1)
    [ -n "$f" ] && get xfob.txt "https://c.lakecountyfl.gov/FTP/PA_office/Data/$f" ;;
  marion)    # Marion County Property Appraiser TRIM data (POOL = Y)
    get trim.zip https://www.pa.marion.fl.us/data/TRIM_Merlin226.ZIP && unzip -joq trim.zip '*.csv' && rm trim.zip ;;
  charlotte) # Charlotte County Property Appraiser nightly cd.txt (haspool)
    get c.zip https://www.ccappraiser.com/downloads/charlotte.zip && unzip -joq c.zip '*cd.txt' && rm c.zip ;;
  stjohns)   # St. Johns County Property Appraiser CAMA supplement (Access db; needs mdbtools)
    get sup.zip https://sftp.sjcpa.us/CAMADataSup.zip && unzip -joq sup.zip '*.mdb' && rm sup.zip \
      && mdb-export CAMADataSup.mdb XFOBView > xfob.csv && rm -f CAMADataSup.mdb ;;
  alachua)   # Alachua County Property Appraiser nightly CAMA export
    get a.zip https://s3.amazonaws.com/acpa.cama/ACPA_CAMAData.zip && unzip -joq a.zip '*ImprvDetails.txt' && rm a.zip ;;
  martin)    # Martin County Property Appraiser data downloads (special features + master for parcel IDs)
    get sfyi.zip https://www.pamartinfl.gov/tools-resources/data-downloads/1168-real-sfyi/download && unzip -joq sfyi.zip && rm sfyi.zip
    get master.zip https://www.pamartinfl.gov/tools-resources/data-downloads/46-real-master/download && unzip -joq master.zip && rm master.zip ;;
  leon)      # Leon County Property Appraiser building data (OTHERFEAT.TXT)
    curl -sfL --retry 3 -o b.zip https://search.leonpa.gov/Downloads/BuildingData.zip && unzip -joq b.zip '*OTHERFEAT.TXT' && rm b.zip ;;
  *) echo "unknown county $county" >&2; exit 2 ;;
esac
# `a && b` chains do not trip set -e, so check the expected outputs explicitly
need() { for f in "$@"; do [ -s "$f" ] || { echo "$county: missing $f" >&2; exit 1; }; done; }
case "$county" in
  volusia) need VOLUSIA_POOLS_EXTRACT.csv ;; seminole) need ExtraFeature.csv ;; osceola) need vw_mdxfob.csv ;;
  lake) need xfob.txt ;; marion) need TRIM*MCPA*Data.csv ;; charlotte) need cd.txt ;; stjohns) need xfob.csv ;;
  alachua) need ImprvDetails.txt ;; martin) need real_sfyi.csv real_master.csv ;; leon) need OTHERFEAT.TXT ;;
esac
ls -la
