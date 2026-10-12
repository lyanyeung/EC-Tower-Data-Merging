#!/usr/bin/env bash
# Optional: apply the existing six-site surface procedure to new sites only.
# DK-Sor already belongs to FLUXNET_MultiSite_6; never regenerate its surface here.
set -euo pipefail
ROOT="${CLM_ROOT:-/iridisfs/scratch/ly3n24/CLM_FATES}"
CTSM="$ROOT/CTSM"
INPUTDATA="$ROOT/inputdata"
[[ -d "$CTSM" && -d "$INPUTDATA" ]] || { echo 'ERROR: CTSM or inputdata directory missing' >&2; exit 1; }
if (( $# == 0 )); then set -- FR-Fon IT-Noe; fi
for SITE in "$@"; do
  if [[ "$SITE" == DK-Sor ]]; then
    echo 'SKIP DK-Sor: existing six-site surface must remain unchanged'
    continue
  fi
  if [[ "$SITE" != FR-Fon && "$SITE" != IT-Noe ]]; then
    echo "ERROR: unsupported new site $SITE" >&2
    exit 1
  fi
  SITE_ROOT="$ROOT/sites/MY_EC_SITE/$SITE"
  OUT="$SITE_ROOT/subset_data"
  CFG="$SITE_ROOT/${SITE}_data.cfg"
  if [[ -e "$CFG" || -e "$OUT" ]]; then
    echo "SKIP $SITE: existing config/surface directory detected; inspect before any new generation"
    continue
  fi
  mapfile -d '' BIFS < <(find "$SITE_ROOT/forcing/raw_multisource_v1/ICOS" -type f \
    -name "ICOS_${SITE}_FLUXNET_BIF_*.csv" -print0)
  if (( ${#BIFS[@]} != 1 )); then
    echo "ERROR $SITE: expected exactly one ICOS BIF, found ${#BIFS[@]}" >&2
    exit 1
  fi
  COORDS="$(python3 - "${BIFS[0]}" <<'PY'
import csv,sys
lat=[];lon=[]
with open(sys.argv[1],encoding='latin-1',newline='') as f:
 for r in csv.DictReader(f):
  key=(r.get('VARIABLE') or '').strip().upper()
  if key in ('LOCATION_LAT','LOCATION_LONG'):
   try:
    val=float(r['DATAVALUE'])
    (lat if key=='LOCATION_LAT' else lon).append(val)
   except (KeyError,ValueError,TypeError): pass
lat=list(set(lat)); lon=list(set(lon))
if len(lat)!=1 or len(lon)!=1 or not(-90<=lat[0]<=90 and -180<=lon[0]<=180):
 raise SystemExit(f'Invalid/multiple coordinates: {lat}, {lon}')
print(lat[0],lon[0])
PY
)"
  read -r LAT LON <<< "$COORDS"
  echo "Create $SITE surface at ($LAT, $LON)"
  cd "$CTSM"
  cp tools/site_and_regional/default_data_2000.cfg "$CFG"
  sed -i 's|dir = lnd/clm2/surfdata_esmf/ctsm5.4.0|dir = lnd/clm2/surfdata_esmf/ctsm5.3.0|g' "$CFG"
  sed -i 's|surfdat_16pft = .*|surfdat_16pft = surfdata_0.9x1.25_hist_2000_16pfts_c240908.nc|' "$CFG"
  sed -i 's|mesh_surf = .*|mesh_surf = fv0.9x1.25_141008_ESMFmesh.nc|' "$CFG"
  tools/site_and_regional/subset_data point \
    --lat "$LAT" --lon "$LON" --lon-type 180 --site "$SITE" \
    --surf-year 2000 --create-surface --create-user-mods \
    --inputdata-dir "$INPUTDATA" --cfg-file "$CFG" --outdir "$OUT"
  echo "SURFACE COMPLETED: $SITE"
done
