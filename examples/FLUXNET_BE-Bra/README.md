# BE-Bra — three-source FLUXNET/ICOS reconciliation for CLM-FATES

**Status (12 October 2026):** Multisource meteorology consolidation and companion ERA5_HH coverage audit **ran successfully on IRIDIS6**; the surface-generation script has been prepared but **not confirmed executed**. The merged CSV is a **candidate**, not final QC-approved model input.

This example extends [`../FLUXNET_MultiSite_6/`](https://github.com/lyanyeung/CLM-FATES-single-site-workflows/tree/main/examples/FLUXNET_MultiSite_6) to a site with overlapping flux-tower releases. It deliberately separates source reconciliation from meteorological QC, measurement-height verification, annual DATM NetCDF production and case submission.

## Inputs and priority rules

| Package | Nominal years | Main use |
| --- | --- | --- |
| `FLX_BE-Bra_FLUXNET2015_FULLSET_1996-2020_beta-3` | 1996–2020 | Main source for 1996–1998; later years possible fallback |
| `ICOS_BE-Bra_FLUXNET_1999-2024_v1.3_r1` | 1999–2024 | Main source for 1999–2024 |
| `ICOSETC_BE-Bra_FLUXNET_FLUXMET_HH_2020-2025_v1.3_r1` | 2020–2025 | Main source for 2025; earlier years possible fallback |

**Merger rule:** For *each variable and timestamp*, take the first non-missing value according to priority within its year group. The code writes the chosen product to an adjacent `*_SOURCE` field; no interpolation or ERA5 replacements are performed in this step. ICOS/FLX `TIMESTAMP_START` is used when available. ICOSETC `TIMESTAMP_END` is shifted **back by 30 minutes** to align half-hour **interval starts** in local standard (non-DST) time. The timestamp convention must be rechecked for other sites/releases; it is not a universal rule.

Variables: `TA_F`, `VPD_F`, `PA_F`, `SW_IN_F`, `LW_IN_F`, `WS_F`, `P_F`; EC reference columns `NEE_VUT_REF`, `GPP_NT_VUT_REF`, `GPP_DT_VUT_REF` when present. Sentinels `<= -9990` are missing.

## IRIDIS structure

```text
/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/BE-Bra/
├── forcing/
│   ├── packages/          # Original downloaded ZIP or CSV: never commit
│   ├── raw/
│   │   ├── FLX/
│   │   ├── ICOS/
│   │   └── ICOSETC/
│   └── merged/
│       ├── BE-Bra_multisource_HH_1996_2025_candidate.csv
│       └── BE-Bra_source_summary.csv
└── subset_data/           # Created only after surface command succeeds
```

## Scripts and execution

The example's scripts are reconstructed and hardened from the documented BE-Bra session (e.g. extraction CRC checks and no-overwrite guard). To publish the **exact files actually run** on IRIDIS, replace scripts 02 and 03 with copies from the IRIDIS home directory before committing:

```bash
# In local WSL repo root, after extracting this example:
rsync -av ly3n24@iridis6.soton.ac.uk:~/prepare_BE-Bra_multisource.py \
  examples/FLUXNET_BE-Bra/scripts/02_prepare_multisource.py
rsync -av ly3n24@iridis6.soton.ac.uk:~/check_BE-Bra_ERA5.py \
  examples/FLUXNET_BE-Bra/scripts/03_check_ERA5.py
# If/when the surface script has been used, capture its precise revision too:
rsync -av ly3n24@iridis6.soton.ac.uk:~/make_BE-Bra_surface.sh \
  examples/FLUXNET_BE-Bra/scripts/04_make_surface.sh
```

If these `rsync` commands are used, the scripts' options may differ slightly from those described below because the **as-run** copy takes precedence.

Run the scripts from their appropriate environment:

```bash
# WSL, only when transferring original packages is necessary:
LOCAL_ROOT=/mnt/d/Site_Level_Experiment/BE-Bra \
  bash scripts/01_transfer_raw_data_wsl.sh

# IRIDIS6 (conda activate clm_fates_env):
python scripts/02_prepare_multisource.py 2>&1 | tee ~/BE-Bra_multisource_preparation.log
python scripts/03_check_ERA5.py 2>&1 | tee ~/BE-Bra_ERA5_coverage.log
bash scripts/04_make_surface.sh 2>&1 | tee ~/BE-Bra_surface.log
```

Run paths above assume this example directory has been copied/cloned to IRIDIS; the original successful execution instead used scripts under `~/`. The prebuilt `02_prepare_multisource.py` **refuses to overwrite an existing candidate CSV** to prevent accidental loss. When reproducing from scratch, use a new empty output directory or explicitly archive the old candidate before rerunning.

## Validated results

See [`expected/coverage_summary.md`](expected/coverage_summary.md). In brief, the merged file has **525,984** half-hour rows for 1996–2025 including leap days, with no missing values in the seven meteorological columns. All seven companion `*_ERA` series likewise have **100% numerical coverage** across that window. The EC GPP/NEE columns are less complete; the reported full meteorological coverage does **not** establish complete measured-only flux records.

## Limitations and follow-up work

1. **Cross-product breakpoints:** Compare overlapping records around 1999 and 2025 and investigate systematic biases, changed variable definitions, QC labels, and any abrupt changes. Do not assume values are consistent simply because the time axis is complete.
2. **Official FLUXNET `_F` values:** They can already include gap-filling or downscaled reanalysis. Source provenance `*_SOURCE` indicates the *release*, **not** whether a record was measured or filled. Future QC should preserve each source's `*_F_QC` metadata as available.
3. **ERA5:** Companion site-downscaled ERA5 is a backup/reference, not a mandate to replace site observations. Use physical screening and documented, reproducible human review as in six-site QC v5; avoid applying unrelated site-specific thresholds without review.
4. **Surface:** [`04_make_surface.sh`](scripts/04_make_surface.sh) mirrors the six-site CTSM point-surface procedure. Check BIF coordinates, validate surface `PCT_NATVEG`/`PCT_CROP`/natural PFT fractions against actual site vegetation, and distinguish generated successfully from scientifically suitable.
5. **Measurement height and DATM:** Extract `TA_F` and `WS_F` heights and dates from BIF, select/justify `ZBOT`, remove leap days for `NO_LEAP`, generate 30 annual DATM NetCDFs, and perform structural + scientific QC before using them for any 500-year spin-up.
6. **Do not commit raw tower data, proprietary files, login tokens, downloaded ZIP archives, candidate forcing CSVs or NetCDF files.** The repository contains code and a compact execution summary only.

For future multi-source sites, generalize source IDs, expected years, timestamp semantics and priority rules in a separate configuration; **do not blindly reuse BE-Bra's metadata or year boundaries**.
