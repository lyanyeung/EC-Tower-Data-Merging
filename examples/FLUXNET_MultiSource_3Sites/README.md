# Multi-source FLUXNET/ICOS harmonisation — DK-Sor, FR-Fon and IT-Noe

This workflow extends [FLUXNET_BE-Bra](../FLUXNET_BE-Bra/) and protects the older [FLUXNET_MultiSite_6](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/FLUXNET_MultiSite_6) outputs for DK-Sor.

**Scientific status: PROVISIONAL.** The scripts preserve product provenance but do not validate physical plausibility, metadata `ZBOT`, land cover, tower measurement origin or EC flux consistency. No original source data are committed to GitHub.

| Site | Input products | Primary source per period | Default candidate period |
|---|---|---|---|
| DK-Sor | `ICOS_DK-Sor_FLUXNET_1996-2024_v1.3_r1` + `ICOSETC_DK-Sor_FLUXNET_FLUXMET_HH_2021-2026_v1.3_r1` | ICOS 1996–2024; ICOSETC 2025 | 1996–2025 |
| FR-Fon | `FLX_FR-Fon_FLUXNET2015_FULLSET_2005-2020_beta-3` + `ICOS_FR-Fon_FLUXNET_2019-2026_v1.3_r1` | FLX 2005–2018; ICOS 2019–2025 | 2005–2025 |
| IT-Noe | `FLX_IT-Noe_FLUXNET2015_FULLSET_2004-2023_1-3` + `ICOS_IT-Noe_FLUXNET_2022-2025_v1.3_r1` | FLX 2004–2021; ICOS 2022–2025 | 2004–2025 |

**2026 caution:** It is currently October 2026. The DK-Sor and FR-Fon packages are labelled through 2026, but 2026 cannot yet be a fully observed calendar year. The default merged candidate stops at 2025. You can inspect 2026 separately with `--include-2026`, but do **not** feed it into a 500-year cycle until independently validated.

## Folder layout (IRIDIS6)

For each `SITE` under `/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/`:

```
SITE/
  forcing/
    packages_multisource_v1/  # source ZIP/CSV or extracted package directory
    raw_multisource_v1/       # extracted, source-labelled copies (not prior raw/)
      ICOS/
      FLX/                   # where applicable
      ICOSETC/               # where applicable
    merged_multisource_v1/    # candidate merge and non-sensitive audit reports
  subset_data/                # separately generated surface (not changed for DK-Sor)
```

This intentionally avoids writing to prior `forcing/raw`, `forcing/processed_v5`, `forcing/datm_v5_candidate_timevarying_zbot`, `subset_data`, cases, model run directories, or archives for DK-Sor.

## Execute

Upload package files (.zip or .csv) from `D:\Fluxes_Tower_Experiment\ICOS\SITE`, or an exactly named extracted package directory. On WSL:

```bash
bash scripts/01_transfer_wsl.sh
```

Upload these **scripts only** to IRIDIS, for example:

```bash
scp scripts/02_merge_three_sites.py scripts/03_audit_ERA5.py scripts/04_make_surfaces.sh \
  ly3n24@iridis6.soton.ac.uk:~/
```

On IRIDIS:

```bash
conda activate clm_fates_env
python ~/02_merge_three_sites.py 2>&1 | tee ~/multisource_3sites_merge.log
python ~/03_audit_ERA5.py 2>&1 | tee ~/multisource_3sites_ERA5.log
# Optional only after inspecting merged/ERA output:
bash ~/04_make_surfaces.sh FR-Fon IT-Noe 2>&1 | tee ~/multisource_3sites_surface.log
```

Do not run `04_make_surfaces.sh` on DK-Sor; it already appears in six-site surface generation. Source availability, latitude/longitude and BIF naming are checked for each new surface.

The merger creates `${SITE}_multisource_HH_${START}_${END}_candidate.csv` containing every merged meteorological and available EC flux variable, `*_SOURCE` provenance and `*_QC` for selected meteorological records where available. The `*_SOURCE` field identifies **which release supplied a value**, *not* whether it was directly measured by a tower or gap-filled. Other reports provide per-variable source counts, yearly completeness, and quantitative differences in overlapping valid records.

The companion ERA5 audit checks actual non-missing coverage of all seven meteorological `*_ERA` variables. If no ERA5_HH CSV is in either package, it reports missing coverage; do not assume all sites match BE-Bra.

**Timestamp rule:** Prefer `TIMESTAMP_START` for FLX/ICOS. For ICOSETC, prefer `TIMESTAMP_END` shifted backwards by 30 minutes (check release metadata; this mirrors BE-Bra). We treat dates as local standard time, not daylight-saving timestamps. All 2025 candidate years remain provisional pending QC. No 29 February removal is performed at this stage.

## Later workflow

1. Validate cross-source joins, discontinuities, periods with anomalous non-missing placeholders and source-specific QC flags.
2. Inspect ERA companion data and justify any physical QC substitutions (never blindly replace tower extremes with ERA).
3. Extract dated TA_F and WS_F measurement heights from BIF, verify `ZBOT` and site canopy height.
4. Create 17,520-row NO_LEAP annual DATM netCDFs, audit PFT/surface suitability and forcing before any new spin-up.
5. For DK-Sor, decide whether scientifically supported 2025 data warrant a new experiment; never overwrite the existing 1996–2024 six-site case or archive.

`--overwrite-candidate` must be passed explicitly to regenerate a pre-existing candidate merged CSV. Raw source material is never overwritten when conflicting.
