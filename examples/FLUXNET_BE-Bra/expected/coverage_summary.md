# BE-Bra observed execution snapshot (12 October 2026)

These values were copied from the successful IRIDIS terminal output. They are **not** synthetic test results. The scripts in this GitHub example represent the same scientific workflow; for exact source-code provenance, copy the as-run scripts from the IRIDIS home directory using the commands in `README.md`.

- Three input packages: FLUXNET2015 FULLSET 1996–2020; ICOS FLUXNET 1999–2024; ICOSETC FLUXMET HH 2020–2025.
- Merged period: 1996-01-01 00:00 to 2025-12-31 23:30 (30-minute intervals), **525,984 rows including leap days**.
- All seven consolidated meteorological columns (`TA_F`, `VPD_F`, `PA_F`, `SW_IN_F`, `LW_IN_F`, `WS_F`, `P_F`) have zero NA/sentinel missing values after merging.
- For each of the seven meteorological columns, retained records: FLX **52,608** (1996–1998); ICOS **455,856** (1999–2024); ICOSETC **17,520** (2025).
- EC fluxes are not uniformly complete: `NEE_VUT_REF` 17,520 missing rows; `GPP_NT_VUT_REF` and `GPP_DT_VUT_REF` 52,608 missing rows. Do not treat the flux comparison as 30 complete years.
- One ERA5_HH companion identified: `ICOS_BE-Bra_FLUXNET_ERA5_HH_1981-2025_v1.3_r1.csv`.
- Verified **1996–2025** ERA5 coverage: **525,984 / 525,984 (100%)** for all seven `*_ERA` meteorological variables, after filtering missing-value sentinels.
- The ERA5 file is the **FLUXNET/ICOS companion site-downscaled ERA5 product**, not independently downloaded ERA5-Land.
- Removing leap days for the CLM `NO_LEAP` DATM forcing produces **525,600** expected half-hour rows (17,520 per year). That transformation has **not** yet been executed in this BE-Bra example.
- The surface script was prepared, but no successful BE-Bra surface-generation output has been supplied yet. Do not report it as complete until run and validated.

Data coverage does not imply physical QC, raw-observation coverage, consistency at inter-product boundaries, or correct FATES PFT representation.
