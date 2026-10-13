# GL-ZaH audit reference — IRIDIS6, 13 October 2026

Audit source: user-reported successful `python ~/02_extract_audit_GL-ZaH_iridis.py` execution.

- Input FLX: `FLX_GL-ZaH_FLUXNET2015_FULLSET_2000-2014_2-4.zip`
- Input ICOS: `ICOS_GL-ZaH_FLUXNET_2020-2025_v1.3_r1.zip`
- Extracted FLX CSVs: **12**
- Extracted ICOS CSVs: **17** (including `!TOC.csv`)
- FLX FULLSET_HH: **262,992** rows (2000–2014)
- ICOS FLUXMET_HH: **105,216** rows (2020–2025)
- ICOS ERA5_HH: **806,448** rows (1981–2026), with **87,648** checked in 2015–2019
- FLX/ICOS/ERA bridge: **100% non-missing** for each of `TA`, `VPD`, `PA`, `SW_IN`, `LW_IN`, `WS`, and `P` (`_F` or `_ERA` as appropriate).
- BIF-matching files reported: **6**
- Final script status: **`BRIDGE_DATA_COMPLETE_QC_PENDING`**
- `physical_qc_performed`: **false**
- `merging_performed`: **false**

Outputs on IRIDIS under `forcing/audit_multisource_v1/`:

- `GL-ZaH_inventory.json`
- `GL-ZaH_source_coverage.csv`
- `GL-ZaH_ERA5_bridge_yearly.csv`
- `GL-ZaH_audit_status.json`

Only this compact reference is committed, never the actual CSV/ZIP/NetCDF source data. Availability is not an endorsement of physical quality or missing EC carbon-flux observations.
