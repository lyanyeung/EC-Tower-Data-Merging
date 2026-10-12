from pathlib import Path
from zipfile import ZipFile
import pandas as pd
import numpy as np
import shutil
import tempfile

ROOT = Path(
    "/iridisfs/scratch/ly3n24/CLM_FATES/"
    "sites/MY_EC_SITE/BE-Bra/forcing"
)

PKG = ROOT / "packages"
RAW = ROOT / "raw"
OUT = ROOT / "merged"

OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "FLX": (
        "FLX_BE-Bra_FLUXNET2015_FULLSET_"
        "1996-2020_beta-3"
    ),
    "ICOS": (
        "ICOS_BE-Bra_FLUXNET_"
        "1999-2024_v1.3_r1"
    ),
    "ICOSETC": (
        "ICOSETC_BE-Bra_FLUXNET_FLUXMET_HH_"
        "2020-2025_v1.3_r1"
    ),
}

VARIABLES = [
    "TA_F", "VPD_F", "PA_F",
    "SW_IN_F", "LW_IN_F", "WS_F", "P_F",
    "NEE_VUT_REF",
    "GPP_NT_VUT_REF",
    "GPP_DT_VUT_REF",
]

MET_VARS = VARIABLES[:7]


# --------------------------------------------------
# 1. Recursive ZIP extraction
# --------------------------------------------------

def extract_zip(zip_path, destination, depth=0):
    if depth > 5:
        raise RuntimeError("Too many nested ZIP levels")

    with ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue

            name = Path(
                info.filename.replace("\\", "/")
            ).name

            if not name:
                continue

            suffix = Path(name).suffix.lower()

            if suffix == ".zip":
                with tempfile.NamedTemporaryFile(
                    suffix=".zip",
                    dir=destination,
                    delete=False
                ) as tmp:
                    with zf.open(info) as src:
                        shutil.copyfileobj(src, tmp)
                    nested = Path(tmp.name)

                try:
                    extract_zip(
                        nested, destination, depth + 1
                    )
                finally:
                    nested.unlink(missing_ok=True)

            elif suffix == ".csv":
                target = destination / name

                if target.exists():
                    if target.stat().st_size != info.file_size:
                        raise RuntimeError(
                            f"Existing CSV differs: {target}"
                        )
                    continue

                temporary = destination / (name + ".partial")

                with zf.open(info) as src:
                    with open(temporary, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                if temporary.stat().st_size != info.file_size:
                    raise RuntimeError(
                        f"Incomplete extraction: {name}"
                    )

                temporary.replace(target)


def find_hh_file(label, folder):
    files = sorted(folder.rglob("*.csv"))

    if label == "FLX":
        matches = [
            f for f in files
            if "_FULLSET_HH_" in f.name
        ]
    else:
        matches = [
            f for f in files
            if "FLUXMET_HH" in f.name
        ]

    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: Expected one HH file, "
            f"found {len(matches)}: {matches}"
        )

    return matches[0]


# --------------------------------------------------
# 2. Timestamp parsing
# --------------------------------------------------

def parse_time(series):
    s = series.astype("string").str.strip()

    if s.str.fullmatch(r"\d{12}").fillna(False).all():
        return pd.to_datetime(
            s, format="%Y%m%d%H%M", errors="coerce"
        )

    return pd.to_datetime(s, errors="coerce")


# --------------------------------------------------
# 3. Read three sources
# --------------------------------------------------

full_index = pd.date_range(
    "1996-01-01 00:00",
    "2025-12-31 23:30",
    freq="30min"
)

data = {}

for label, stem in SOURCES.items():
    print(f"\n========== {label} ==========", flush=True)

    folder = RAW / label
    folder.mkdir(parents=True, exist_ok=True)

    zip_path = PKG / (stem + ".zip")
    csv_path = PKG / (stem + ".csv")

    if zip_path.exists():
        extract_zip(zip_path, folder)
    elif csv_path.exists():
        target = folder / csv_path.name
        if not target.exists():
            shutil.copy2(csv_path, target)
    else:
        raise FileNotFoundError(
            f"Missing input package: {stem}"
        )

    hh = find_hh_file(label, folder)
    print("HH file:", hh, flush=True)

    header = pd.read_csv(hh, nrows=0).columns.tolist()

    # ICOSETC uses local non-DST interval end.
    if label == "ICOSETC" and "TIMESTAMP_END" in header:
        time_col = "TIMESTAMP_END"
        subtract_minutes = 30
    elif "TIMESTAMP_START" in header:
        time_col = "TIMESTAMP_START"
        subtract_minutes = 0
    elif "TIMESTAMP_END" in header:
        time_col = "TIMESTAMP_END"
        subtract_minutes = 30
    else:
        raise RuntimeError(
            f"No compatible local timestamp in {hh}"
        )

    wanted = set(VARIABLES + [time_col])

    df = pd.read_csv(
        hh,
        usecols=lambda c: c in wanted,
        low_memory=False,
        dtype={time_col: "string"}
    )

    times = parse_time(df[time_col])

    if times.isna().any():
        raise RuntimeError(
            f"{label}: Unparseable timestamps"
        )

    if subtract_minutes:
        times = times - pd.Timedelta(
            minutes=subtract_minutes
        )

    df = df.drop(columns=[time_col])
    df.index = pd.DatetimeIndex(times)

    if df.index.has_duplicates:
        raise RuntimeError(
            f"{label}: Duplicate timestamps"
        )

    for var in VARIABLES:
        if var not in df.columns:
            df[var] = np.nan

        df[var] = pd.to_numeric(
            df[var], errors="coerce"
        )

        df.loc[df[var] <= -9990, var] = np.nan

    df = df[VARIABLES].sort_index()

    print(
        "Actual time range:",
        df.index.min(), "to", df.index.max()
    )
    print("Original rows:", len(df))
    print(
        "Available forcing columns:",
        [v for v in MET_VARS
         if df[v].notna().any()]
    )

    data[label] = df.reindex(full_index)


# --------------------------------------------------
# 4. Priority by period
# --------------------------------------------------

periods = [
    (1996, 1998, ["FLX", "ICOS", "ICOSETC"]),
    (1999, 2024, ["ICOS", "ICOSETC", "FLX"]),
    (2025, 2025, ["ICOSETC", "ICOS", "FLX"]),
]

result = pd.DataFrame(index=full_index)
years = full_index.year

for var in VARIABLES:
    values = pd.Series(
        np.nan, index=full_index, dtype="float64"
    )
    provenance = pd.Series(
        pd.NA, index=full_index, dtype="string"
    )

    for start, end, priority in periods:
        year_mask = (years >= start) & (years <= end)

        for label in priority:
            candidate = data[label][var]

            choose = (
                year_mask
                & values.isna()
                & candidate.notna()
            )

            values.loc[choose] = candidate.loc[choose]
            provenance.loc[choose] = label

    result[var] = values
    result[var + "_SOURCE"] = provenance


# --------------------------------------------------
# 5. Save candidate merged data and audit
# --------------------------------------------------

result.index.name = "time"

output = OUT / (
    "BE-Bra_multisource_HH_"
    "1996_2025_candidate.csv"
)

result.to_csv(output)

records = []

for var in VARIABLES:
    counts = result[var + "_SOURCE"].value_counts()

    records.append({
        "variable": var,
        "FLX_records": int(counts.get("FLX", 0)),
        "ICOS_records": int(counts.get("ICOS", 0)),
        "ICOSETC_records": int(counts.get("ICOSETC", 0)),
        "missing_records": int(result[var].isna().sum()),
    })

summary = pd.DataFrame(records)

summary_path = OUT / "BE-Bra_source_summary.csv"
summary.to_csv(summary_path, index=False)

print("\n========== FINAL SUMMARY ==========")
print("Output:", output)
print("Total rows:", len(result))
print(summary.to_string(index=False))

print("\nYearly meteorological completeness:")
yearly = result[MET_VARS].notna().groupby(years).mean()
print(yearly.round(4).to_string())

print("\nBE-Bra candidate merging completed.")
print("Scientific QC and DATM generation remain pending.")
