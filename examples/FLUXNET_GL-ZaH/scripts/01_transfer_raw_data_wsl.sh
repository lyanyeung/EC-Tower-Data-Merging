#!/usr/bin/env bash
# Run in WSL. Transfer original packages only; never modify other IRIDIS sites.
set -euo pipefail

LOCAL_ROOT="${LOCAL_ROOT:-/mnt/d/Fluxes_Tower_Experiment/ICOS/GL-ZaH}"
IRIDIS_USER="${IRIDIS_USER:-ly3n24}"
IRIDIS_HOST="${IRIDIS_HOST:-iridis6.soton.ac.uk}"
REMOTE="/iridisfs/scratch/${IRIDIS_USER}/CLM_FATES/sites/MY_EC_SITE/GL-ZaH/forcing/packages_multisource_v1"

STEMS=(
  'FLX_GL-ZaH_FLUXNET2015_FULLSET_2000-2014_2-4'
  'ICOS_GL-ZaH_FLUXNET_2020-2025_v1.3_r1'
)

[[ -d "$LOCAL_ROOT" ]] || { echo "ERROR: Windows/WSL folder not found: $LOCAL_ROOT" >&2; exit 1; }
declare -a MODES PATHS
for stem in "${STEMS[@]}"; do
  mapfile -d '' archives < <(
    find "$LOCAL_ROOT" -maxdepth 4 -type f \
      \( -name "${stem}.zip" -o -name "${stem}.ZIP" \) -print0
  )
  if (( ${#archives[@]} > 1 )); then
    echo "ERROR: Multiple ZIP archives found for $stem; choose one manually:" >&2
    printf '  %s\n' "${archives[@]}" >&2
    exit 1
  fi
  if (( ${#archives[@]} == 1 )); then
    MODES+=(archive); PATHS+=("${archives[0]}")
    echo "FOUND archive: ${archives[0]}"
  elif [[ -d "$LOCAL_ROOT/$stem" ]]; then
    MODES+=(folder); PATHS+=("$LOCAL_ROOT/$stem")
    echo "FOUND extracted folder: $LOCAL_ROOT/$stem"
  else
    mapfile -d '' csvs < <(
      find "$LOCAL_ROOT" -maxdepth 4 -type f \
        \( -name "${stem}.csv" -o -name "${stem}.CSV" \) -print0
    )
    if (( ${#csvs[@]} != 1 )); then
      echo "ERROR: Did not find unique ZIP, folder, or CSV for $stem" >&2
      exit 1
    fi
    MODES+=(csv); PATHS+=("${csvs[0]}")
    echo "FOUND CSV: ${csvs[0]}"
  fi
done

ssh "${IRIDIS_USER}@${IRIDIS_HOST}" "mkdir -p '$REMOTE'"

for i in "${!STEMS[@]}"; do
  stem="${STEMS[$i]}"; mode="${MODES[$i]}"; path="${PATHS[$i]}"
  if [[ "$mode" == folder ]]; then
    ssh "${IRIDIS_USER}@${IRIDIS_HOST}" "mkdir -p '$REMOTE/$stem'"
    rsync -avh --partial --progress "$path/" "${IRIDIS_USER}@${IRIDIS_HOST}:$REMOTE/$stem/"
  else
    rsync -avh --partial --progress "$path" "${IRIDIS_USER}@${IRIDIS_HOST}:$REMOTE/"
  fi
done

echo "TRANSFER COMPLETE: $REMOTE"
ssh "${IRIDIS_USER}@${IRIDIS_HOST}" "find '$REMOTE' -maxdepth 2 -type f -printf '%p %s bytes\\n' | head -40"
