# EC Tower Data Merging

Reproducible workflows for harmonising overlapping **eddy-covariance (EC) tower** releases from FLUXNET2015, ICOS and ICOS ETC for ecosystem modelling. Includes half-hourly timestamp alignment, per-variable source priorities, release provenance, gap audits and companion ERA5 checks.

This repository focuses on **EC data release reconciliation**, not model spin-up. The companion model workflows remain in [CLM-FATES-single-site-workflows](https://github.com/lyanyeung/CLM-FATES-single-site-workflows).

## Site examples

| Workflow | Sites | Candidate years | Run status |
|---|---|---|---|
| [`FLUXNET_BE-Bra`](examples/FLUXNET_BE-Bra/) | BE-Bra | 1996–2025 | merge completed; ERA5 coverage verified 100% |
| [`FLUXNET_MultiSource_3Sites`](examples/FLUXNET_MultiSource_3Sites/) | DK-Sor | 1996–2025 | merge completed; met no missing |
| ↳ same batch workflow | FR-Fon | 2005–2025 | merge completed; met no missing |
| ↳ same batch workflow | IT-Noe | 2004–2025 | merge completed; met no missing |

See [the recorded run summary](docs/MERGE_RESULTS_2026-10-13.md) for counts and known limitations.

## Method and safety

1. Transfer original downloaded packages to IRIDIS (files stay outside GitHub).
2. Extract nested ZIP packages without silently overwriting source data.
3. Convert timestamps to interval starts; **verify timestamp semantics per release**.
4. Resolve overlapping product releases by configurable **per-period, per-variable priorities** and preserve `*_SOURCE` (product provenance, *not* tower-measured versus gap-filled provenance).
5. Audit completeness, overlap differences, and companion site-downscaled `ERA5_HH` coverage.
6. Only after separate physical QC, BIF/ZBOT verification, NO_LEAP conversion and DATM audits should candidate meteorology be considered for CLM-FATES experiments.

The `.gitignore` excludes original FLUXNET/ICOS source data, generated forcing, model files and logs. Source-data terms must be respected. An apparently complete `*_F` series can include network gap filling; this repository does **not** certify scientific quality or convergence.

## Reproduction

Each example contains its own README and tested/staged scripts. They currently reflect work on University of Southampton IRIDIS6 under `/iridisfs/scratch/ly3n24/CLM_FATES/`. Change filesystem paths and site priorities before reuse elsewhere.

**Status: 13 October 2026.** The DK-Sor, FR-Fon and IT-Noe results are from completed candidate merge runs; their ERA5 audits, physical QC, DATM generation and new spin-ups have not been reported as completed here. The BE-Bra scripts are copied directly from the `main` branch of the original GitHub repository during migration, not from an older ZIP.
