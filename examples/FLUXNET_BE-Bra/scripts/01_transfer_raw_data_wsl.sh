#!/usr/bin/env bash
# Run from WSL. Transfers source archives (never to GitHub).
set -euo pipefail

LOCAL_ROOT="${LOCAL_ROOT:-/mnt/d}"
IRIDIS_USER="${IRIDIS_USER:-ly3n24}"
IRIDIS_HOST="${IRIDIS_HOST:-iridis6.soton.ac.uk}"
REMOTE="/iridisfs/scratch/${IRIDIS_USER}/CLM_FATES/sites/MY_EC_SITE/BE-Bra/forcing/packages"

sources=(
  FLX_BE-Bra_FLUXNET2015_FULLSET_1996-2020_beta-3
  ICOS_BE-Bra_FLUXNET_1999-2024_v1.3_r1
  ICOSETC_BE-Bra_FLUXNET_FLUXMET_HH_2020-2025_v1.3_r1
)
files=()
for stem in "${sources[@]}"; do
  echo "Looking for $stem under $LOCAL_ROOT"
  mapfile -d '' matches < <(find "$LOCAL_ROOT" -type f \
    \( -name "${stem}.zip" -o -name "${stem}.csv" \) -print0)
  if (( ${#matches[@]} != 1 )); then
    printf 'ERROR: expected exactly one source file, got %d for %s\n' "${#matches[@]}" "$stem" >&2
    printf 'Matches: %s\n' "${matches[@]:-none}" >&2
    exit 1
  fi
  files+=("${matches[0]}")
  echo "Found: ${matches[0]}"
done

ssh "${IRIDIS_USER}@${IRIDIS_HOST}" "mkdir -p '$REMOTE'"
for f in "${files[@]}"; do
  rsync -avh --progress -- "$f" "${IRIDIS_USER}@${IRIDIS_HOST}:${REMOTE}/"
done
ssh "${IRIDIS_USER}@${IRIDIS_HOST}" "ls -lh '$REMOTE'"
echo 'Transfer complete. Original archives remain on WSL and IRIDIS.'
