# GL-ZaH — FLUXNET2015 / ICOS meteorological gap audit

**Status (13 October 2026): SOURCE AUDIT PASSED; MERGE AND SCIENTIFIC QC NOT YET PERFORMED.**

GL-ZaH (Zackenberg Heath, Greenland) has two disjoint published EC-tower meteorological products. This example documents the confirmed availability of a complete site-downscaled ERA5_HH meteorological bridge for 2015–2019 and preserves the as-run audit scripts. It does **not** reconstruct flux measurements for those missing years.

## Source packages and proposed forcing priority

| Period | Product | Status |
|---|---|---|
| 2000–2014 | `FLX_GL-ZaH_FLUXNET2015_FULLSET_2000-2014_2-4` | Seven `_F` meteorological variables have full numerical coverage |
| 2015–2019 | `ICOS_GL-ZaH_FLUXNET_ERA5_HH_1981-2026_v1.3_r1.csv`, delivered inside `ICOS_GL-ZaH_FLUXNET_2020-2025_v1.3_r1` | Seven `_ERA` meteorological variables have full numerical coverage in bridge window |
| 2020–2025 | `ICOS_GL-ZaH_FLUXNET_2020-2025_v1.3_r1` | Seven `_F` meteorological variables have full numerical coverage |

These are separate inputs **not yet merged**. Source `_F` products may already be gap-filled by their providers. ERA5_HH is a site-downscaled reanalysis companion, *not* an independent ERA5-Land download or missing tower measurements. The 2026 part of the ERA product is not included in the planned 2000–2025 candidate.

## Confirmed audit results on IRIDIS6

On 13 October 2026, `02_extract_audit_ERA5_bridge.py` completed successfully using the two original ZIPs. Numerical coverage of seven meteorological variables:

| Source | Period | Half-hour rows | Missing records per variable |
|---|---|---:|---:|
| FLX FULLSET_HH | 2000–2014 | 262,992 | 0 |
| ICOS ERA5_HH | 2015–2019 | 87,648 | 0 |
| ICOS FLUXMET_HH | 2020–2025 | 105,216 | 0 |
| **Total proposed period** | **2000–2025** | **455,856** | **0 availability gaps** |

Actual program result: `BRIDGE_DATA_COMPLETE_QC_PENDING`. The audit creates an inventory, source-coverage table, five-year ERA bridge table, and audit status JSON. See [expected/audit_summary.md](expected/audit_summary.md).

## Directory layout on IRIDIS

```text
/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/GL-ZaH/
└── forcing/
    ├── packages_multisource_v1/  # FLX and ICOS original packages; not committed
    ├── raw_multisource_v1/       # extracted originals; not committed
    │   ├── FLX/
    │   └── ICOS/
    └── audit_multisource_v1/     # generated audit reports; not committed
```

## Reproduction

Run the upload script in WSL when the original packages are at `/mnt/d/Fluxes_Tower_Experiment/ICOS/GL-ZaH`:

```bash
bash scripts/01_transfer_raw_data_wsl.sh
scp scripts/02_extract_audit_ERA5_bridge.py ly3n24@iridis6.soton.ac.uk:~/02_extract_audit_GL-ZaH_iridis.py
```

Then on IRIDIS:

```bash
conda activate clm_fates_env
set -o pipefail
python ~/02_extract_audit_GL-ZaH_iridis.py 2>&1 | tee ~/GL-ZaH_source_ERA5_audit.log
```

The audit re-extracts nested ZIPs in source-labelled directories with CRC verification and does not alter previous modelling cases. A complete audit is **not equivalent to a final CLM forcing file**.

## Outstanding work

1. Merge the 26-year interval by meteorological variable with explicit `FLX`, `ICOS_ERA5_BRIDGE`, and `ICOS` source provenance; do not invent 2015–2019 GPP or NEE.
2. Verify time-stamp convention, source transitions at 2014/2015 and 2019/2020, physical range constraints, precipitation and radiation continuity, and any provider gap-fill / QC flags.
3. Assess Arctic tundra surface/PFT suitability, snow and freeze-thaw representation, BIF measurement height and `ZBOT` before constructing `NO_LEAP` annual DATM inputs or performing a FATES experiment.
4. Follow the model input and spin-up workflow separately in [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows). No original EC tower or reanalysis datasets are distributed here.
