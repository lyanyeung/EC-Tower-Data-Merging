#!/usr/bin/env bash
# Run on WSL. Copy two original network packages per site to protected multi-source package folders.
set -euo pipefail
LOCAL_BASE="${LOCAL_BASE:-/mnt/d/Fluxes_Tower_Experiment/ICOS}"
IRIDIS_USER="${IRIDIS_USER:-ly3n24}"
IRIDIS_HOST="${IRIDIS_HOST:-iridis6.soton.ac.uk}"
REMOTE_BASE="/iridisfs/scratch/${IRIDIS_USER}/CLM_FATES/sites/MY_EC_SITE"
SITES=(DK-Sor FR-Fon IT-Noe)
STEMS=(
  'ICOS_DK-Sor_FLUXNET_1996-2024_v1.3_r1'
  'ICOSETC_DK-Sor_FLUXNET_FLUXMET_HH_2021-2026_v1.3_r1'
  'FLX_FR-Fon_FLUXNET2015_FULLSET_2005-2020_beta-3'
  'ICOS_FR-Fon_FLUXNET_2019-2026_v1.3_r1'
  'FLX_IT-Noe_FLUXNET2015_FULLSET_2004-2023_1-3'
  'ICOS_IT-Noe_FLUXNET_2022-2025_v1.3_r1'
)
FILES=()
for i in "${!STEMS[@]}"; do
  site="${SITES[$((i/2))]}"; stem="${STEMS[$i]}"; dir="$LOCAL_BASE/$site"
  [[ -d "$dir" ]] || { echo "ERROR: folder not found: $dir" >&2; exit 1; }
  candidates=()
  # Search up to 3 levels down; package may be in one nested download folder.
  mapfile -d '' candidates < <(find "$dir" -maxdepth 3 -type f \
      \( -iname "${stem}.zip" -o -iname "${stem}.csv" \) -print0)
  [[ -d "$dir/$stem" ]] && candidates+=("$dir/$stem")
  if (( ${#candidates[@]} != 1 )); then
    echo "ERROR: expected exactly one package file (.zip/.csv) or extracted directory for $stem" >&2
    echo "Checked under $dir; matches: ${candidates[*]:-none}" >&2
    echo 'Available files:' >&2; find "$dir" -maxdepth 2 -type f | head -40 >&2
    exit 1
  fi
  FILES+=("${candidates[0]}")
  printf 'FOUND %s: %s\n' "$site" "${candidates[0]}"
done
for i in "${!STEMS[@]}"; do
  site="${SITES[$((i/2))]}"; src="${FILES[$i]}"
  remote="$REMOTE_BASE/$site/forcing/packages_multisource_v1"
  ssh "${IRIDIS_USER}@${IRIDIS_HOST}" "mkdir -p '$remote'"
  echo "Transferring $site $(basename "$src")"
  # rsync skips byte-identical data, and preserves existing unrelated files.
  # Do not use --delete.
  if [[ -d "$src" ]]; then
    rsync -avh --progress -- "$src/" "${IRIDIS_USER}@${IRIDIS_HOST}:${remote}/$(basename "$src")/"
  else
    rsync -avh --progress -- "$src" "${IRIDIS_USER}@${IRIDIS_HOST}:${remote}/"
  fi
done
echo 'SUCCESS: all 6 source packages transferred (or synced).'
