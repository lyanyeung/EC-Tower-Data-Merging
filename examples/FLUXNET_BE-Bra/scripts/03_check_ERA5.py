from pathlib import Path
import pandas as pd
import numpy as np

root = Path(
    "/iridisfs/scratch/ly3n24/CLM_FATES/"
    "sites/MY_EC_SITE/BE-Bra/forcing/raw"
)

files = sorted(root.rglob("*ERA5_HH*.csv"))

variables = [
    "TA_ERA", "VPD_ERA", "PA_ERA",
    "SW_IN_ERA", "LW_IN_ERA", "WS_ERA", "P_ERA"
]

expected = pd.date_range(
    "1996-01-01", "2025-12-31 23:30",
    freq="30min"
)

merged = pd.DataFrame(index=expected)

for v in variables:
    merged[v] = np.nan

print("ERA5_HH files found:", len(files))

if not files:
    print("No standalone ERA5_HH CSV found.")
    print("Check package contents before assuming ERA5 availability.")
    raise SystemExit(1)

for path in files:
    print("\nReading:", path)

    header = pd.read_csv(path, nrows=0).columns.tolist()

    if "TIMESTAMP_START" in header:
        tc = "TIMESTAMP_START"
        shift = False
    elif "TIMESTAMP_END" in header:
        tc = "TIMESTAMP_END"
        shift = True
    else:
        print("No recognized timestamp column; skipping")
        continue

    available = [v for v in variables if v in header]
    print("Variables:", available)

    df = pd.read_csv(
        path, usecols=[tc] + available,
        low_memory=False
    )

    time = pd.to_datetime(
        df[tc].astype("string").str.strip(),
        format="%Y%m%d%H%M",
        errors="coerce"
    )

    if time.isna().any():
        raise RuntimeError(f"Invalid timestamps: {path}")

    if shift:
        time -= pd.Timedelta(minutes=30)

    df.index = pd.DatetimeIndex(time)

    if df.index.has_duplicates:
        raise RuntimeError(f"Duplicate timestamps: {path}")

    print("Period:", df.index.min(), "to", df.index.max())

    df = df.reindex(expected)

    for v in available:
        values = pd.to_numeric(df[v], errors="coerce")
        values = values.mask(values <= -9990)
        merged[v] = merged[v].combine_first(values)

print("\n=== ERA5 COVERAGE: 1996-2025 ===")

for v in variables:
    count = int(merged[v].notna().sum())
    missing = len(expected) - count

    print(
        f"{v:12s} "
        f"available={count:7d} "
        f"missing={missing:7d} "
        f"coverage={100*count/len(expected):7.3f}%"
    )

print("\n=== YEARLY COVERAGE (%) ===")
yearly = merged.notna().groupby(merged.index.year).mean() * 100
print(yearly.round(2).to_string())

if merged.notna().all().all():
    print("\nPASS: All seven ERA5 variables cover the full period.")
else:
    print("\nREVIEW: ERA5 gaps or missing variables remain.")
