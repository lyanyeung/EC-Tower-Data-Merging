# Recorded merged half-hourly candidate results — 13 October 2026

These are **user-reported IRIDIS program outputs**, not files independently reanalysed in this repository. Counts include leap-day intervals; the seven meteorological `*_F` fields contain no missing values after release-priority merging. Full numerical coverage is **not** a physical-QC pass and does not prove direct observations.

| Site | Start–end | Years | HH records | Missing meteorological records (each of 7) | Missing NEE_VUT_REF | Missing GPP_NT_VUT_REF | Missing GPP_DT_VUT_REF |
|---|---|---:|---:|---:|---:|---:|---:|
| BE-Bra | 1996–2025 | 30 | 525,984 | 0 | 17,520 | 52,608 | 52,608 |
| DK-Sor | 1996–2025 | 30 | 525,984 | 0 | 10,395 | 10,395 | 10,395 |
| FR-Fon | 2005–2025 | 21 | 368,160 | 0 | 0 | 0 | 0 |
| IT-Noe | 2004–2025 | 22 | 385,728 | 0 | 93,863 | 6,215 | 6,215 |

## Input release priorities

- BE-Bra: FLX 1996–1998; ICOS 1999–2024; ICOSETC 2025.
- DK-Sor: ICOS 1996–2024; ICOSETC 2025.
- FR-Fon: FLX 2005–2018; ICOS 2019–2025.
- IT-Noe: FLX 2004–2021; ICOS 2022–2025.

## ERA5

- **BE-Bra:** the companion ICOS `ERA5_HH_1981-2025` file was checked over 1996–2025; all seven `*_ERA` fields had 525,984 valid values and zero missing.
- **DK-Sor, FR-Fon, IT-Noe:** script provided; no completed audit results were supplied at the time of this status entry.

## Limitations and next verification

- Source transition diagnostics near 1999/2025 (BE-Bra), 2024/2025 (DK-Sor), 2018/2019 (FR-Fon) and 2021/2022 (IT-Noe) remain to be interpreted. Overlap statistics do not automatically prove physical continuity.
- QC flags, extreme-value screens, station metadata, changing measurement heights and land cover/PFT suitability require scientific review.
- Current outputs are candidates, still including leap days; `NO_LEAP` and 17,520-record annual DATM files have **not** been generated from these merged candidates.
- For DK-Sor, the existing six-site CLM-FATES surface, DATM and spin-up must not be overwritten. New multi-source files are under separate versioned forcing directories.
- Do not use an unfinished 2026 calendar year as a fully observed forcing year.
