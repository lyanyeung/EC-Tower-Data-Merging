#!/usr/bin/env bash
# Stage 04: adapts FLUXNET_MultiSite_6 02_make_6_surfaces.sh to BE-Bra.
# Surface generation is independent of meteorological forcing QC.
set -euo pipefail

ROOT="${CLM_ROOT:-/iridisfs/scratch/ly3n24/CLM_FATES}"
CTSM="$ROOT/CTSM"
INPUTDATA="$ROOT/inputdata"
SITE="BE-Bra"
SITE_ROOT="$ROOT/sites/MY_EC_SITE/$SITE"
OUT="$SITE_ROOT/subset_data"
CFG="$SITE_ROOT/${SITE}_data.cfg"

if [[ -d "$OUT/user_mods" ]] || compgen -G "$OUT/surfdata_${SITE}*" > /dev/null; then
  echo "Existing surface detected: $OUT. Skipping to avoid overwrite."
  exit 0
fi
BIF="$(find "$SITE_ROOT/forcing/raw/ICOS" -type f \
  -name 'ICOS_BE-Bra_FLUXNET_BIF_*.csv' -print -quit)"
[[ -n "$BIF" ]] || { echo 'ERROR: ICOS BIF metadata not found.' >&2; exit 1; }
echo "BIF: $BIF"
COORDS="$(python3 - "$BIF" <<'PY'
import csv, sys
values = {'LOCATION_LAT': [], 'LOCATION_LONG': []}
with open(sys.argv[1], encoding='latin-1', newline='') as f:
    for row in csv.DictReader(f):
        key = (row.get('VARIABLE') or '').strip().upper()
        if key in values:
            try:
                values[key].append(float(row['DATAVALUE']))
            except (KeyError, ValueError, TypeError):
                pass
results = {}
for key, vals in values.items():
    unique = sorted(set(vals))
    if len(unique) != 1:
        raise RuntimeError(f'{key}: expected one unique coordinate, got {unique}')
    results[key] = unique[0]
lat, lon = results['LOCATION_LAT'], results['LOCATION_LONG']
if not (-90 <= lat <= 90 and -180 <= lon <= 180):
    raise ValueError(f'Invalid coordinates: {lat}, {lon}')
print(lat, lon)
PY
)"
read -r LAT LON <<< "$COORDS"
echo "Latitude: $LAT; longitude: $LON"

[[ -d "$CTSM" ]] || { echo "Missing CTSM checkout: $CTSM" >&2; exit 1; }
[[ -d "$INPUTDATA" ]] || { echo "Missing CTSM inputdata: $INPUTDATA" >&2; exit 1; }
mkdir -p "$OUT"
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
find "$OUT" -maxdepth 3 -type f | sort
