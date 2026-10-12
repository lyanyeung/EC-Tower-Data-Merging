#!/usr/bin/env python3
"""Merge FLUXNET2015/ICOS/ICOSETC releases to provenance-rich candidate HH data.

Read-only for raw source ZIPs; does NOT make forcing physical-QC approved.
Usage: python 02_merge_three_sites.py [--sites DK-Sor FR-Fon IT-Noe] [--include-2026]
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import shutil
import tempfile
import zlib
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

BASE = Path('/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE')
CONFIG = {
    'DK-Sor': {
        'start': 1996, 'end': 2025,
        'sources': {
            'ICOS': 'ICOS_DK-Sor_FLUXNET_1996-2024_v1.3_r1',
            'ICOSETC': 'ICOSETC_DK-Sor_FLUXNET_FLUXMET_HH_2021-2026_v1.3_r1',
        },
        'priorities': [(1996, 2024, ['ICOS', 'ICOSETC']), (2025, 2026, ['ICOSETC', 'ICOS'])],
    },
    'FR-Fon': {
        'start': 2005, 'end': 2025,
        'sources': {
            'FLX': 'FLX_FR-Fon_FLUXNET2015_FULLSET_2005-2020_beta-3',
            'ICOS': 'ICOS_FR-Fon_FLUXNET_2019-2026_v1.3_r1',
        },
        'priorities': [(2005, 2018, ['FLX', 'ICOS']), (2019, 2026, ['ICOS', 'FLX'])],
    },
    'IT-Noe': {
        'start': 2004, 'end': 2025,
        'sources': {
            'FLX': 'FLX_IT-Noe_FLUXNET2015_FULLSET_2004-2023_1-3',
            'ICOS': 'ICOS_IT-Noe_FLUXNET_2022-2025_v1.3_r1',
        },
        'priorities': [(2004, 2021, ['FLX', 'ICOS']), (2022, 2025, ['ICOS', 'FLX'])],
    },
}
MET = ['TA_F', 'VPD_F', 'PA_F', 'SW_IN_F', 'LW_IN_F', 'WS_F', 'P_F']
EC = ['NEE_VUT_REF', 'GPP_NT_VUT_REF', 'GPP_DT_VUT_REF']
VARIABLES = MET + EC


def crc32(path):
    crc = 0
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            crc = zlib.crc32(block, crc)
    return crc & 0xffffffff


def extract_archive(archive: Path, destination: Path, depth=0):
    if depth > 6:
        raise ValueError('Nested ZIP depth too large')
    with ZipFile(archive) as z:
        bad = z.testzip()
        if bad:
            raise ValueError(f'ZIP checksum error {archive}: {bad}')
        for info in z.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename.replace('\\', '/')).name
            if not name:
                continue
            suffix = Path(name).suffix.lower()
            if suffix not in ('.csv', '.zip'):
                continue
            if suffix == '.zip':
                with tempfile.NamedTemporaryFile(dir=destination, suffix='.zip', delete=False) as tmp:
                    with z.open(info) as inp:
                        shutil.copyfileobj(inp, tmp)
                    nested = Path(tmp.name)
                try:
                    extract_archive(nested, destination, depth+1)
                finally:
                    nested.unlink(missing_ok=True)
                continue
            target = destination / name
            if target.exists():
                if target.stat().st_size != info.file_size or crc32(target) != info.CRC:
                    raise ValueError(f'Conflicting existing CSV, refused overwrite: {target}')
                continue
            with tempfile.NamedTemporaryFile(dir=destination, prefix='extract_', suffix='.partial', delete=False) as tmp:
                with z.open(info) as inp:
                    shutil.copyfileobj(inp, tmp)
                part = Path(tmp.name)
            if part.stat().st_size != info.file_size or crc32(part) != info.CRC:
                part.unlink(missing_ok=True)
                raise ValueError(f'Incomplete extraction: {name}')
            part.replace(target)


def stage_package(folder: Path, stem: str, destination: Path):
    paths = [p for p in folder.iterdir() if p.stem.lower() == stem.lower() and p.suffix.lower() in ('.zip', '.csv')]
    dirs = [p for p in folder.iterdir() if p.name.lower() == stem.lower() and p.is_dir()]
    candidates = paths + dirs
    if len(candidates) != 1:
        raise ValueError(f'Exactly one package expected for {stem} in {folder}; got {candidates}')
    pkg = candidates[0]
    destination.mkdir(parents=True, exist_ok=True)
    if pkg.is_dir():
        items = list(pkg.rglob('*.csv')) + list(pkg.rglob('*.zip'))
        if not items:
            raise ValueError(f'No CSV/ZIP inside {pkg}')
        for f in items:
            if f.suffix.lower() == '.zip':
                extract_archive(f, destination)
            else:
                target = destination / f.name
                if target.exists():
                    if target.stat().st_size != f.stat().st_size or crc32(target) != crc32(f):
                        raise ValueError(f'Conflicting existing CSV: {target}')
                else:
                    shutil.copy2(f, target)
    elif pkg.suffix.lower() == '.zip':
        extract_archive(pkg, destination)
    else:
        target = destination / pkg.name
        if target.exists():
            if target.stat().st_size != pkg.stat().st_size or crc32(target) != crc32(pkg):
                raise ValueError(f'Conflicting existing CSV: {target}')
        else:
            shutil.copy2(pkg, target)


def read_source(label: str, raw_dir: Path, requested_cols, idx: pd.DatetimeIndex):
    files = list(raw_dir.rglob('*.csv'))
    if label == 'FLX':
        matches = [f for f in files if '_FULLSET_HH_' in f.name.upper()]
    else:
        matches = [f for f in files if 'FLUXMET_HH' in f.name.upper()]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly 1 {label} HH CSV, found {matches}')
    path = matches[0]
    header = pd.read_csv(path, nrows=0).columns.tolist()
    if label == 'ICOSETC' and 'TIMESTAMP_END' in header:
        stamp = 'TIMESTAMP_END'
        delta = pd.Timedelta(minutes=30)
    elif 'TIMESTAMP_START' in header:
        stamp = 'TIMESTAMP_START'
        delta = pd.Timedelta(0)
    elif 'TIMESTAMP_END' in header:
        stamp = 'TIMESTAMP_END'
        delta = pd.Timedelta(minutes=30)
    else:
        raise ValueError(f'Timestamp column missing: {path}')
    extras = [v + '_QC' for v in MET]
    use = [stamp] + [c for c in requested_cols + extras if c in header and c != stamp]
    d = pd.read_csv(path, usecols=use, low_memory=False, dtype={stamp: 'string'})
    raw_ts = d[stamp].astype('string').str.strip()
    t = pd.to_datetime(raw_ts, format='%Y%m%d%H%M', errors='coerce')
    if t.isna().any():
        raise ValueError(f'Unparseable time in {path}')
    t = pd.DatetimeIndex(t - delta)
    if t.has_duplicates:
        raise ValueError(f'Duplicate interval starts in {path}')
    if len(t) > 1 and (t[1:] <= t[:-1]).any():
        raise ValueError(f'Unsorted timestamps in {path}')
    d.index = t
    d.drop(columns=[stamp], inplace=True)
    for v in requested_cols + extras:
        if v in d:
            d[v] = pd.to_numeric(d[v], errors='coerce').mask(lambda x: x <= -9990)
        else:
            d[v] = np.nan
    print(f'  {label}: {path.name} [{t.min()} .. {t.max()}], {len(t):,} rows', flush=True)
    # Reindex catches non-half-hour or off-clock timestamps; no silent discarding.
    valid = t[(t >= idx[0]) & (t <= idx[-1])]
    if len(valid) and not valid.isin(idx).all():
        raise ValueError(f'{label}: unexpected half-hour alignment')
    return d[requested_cols + extras].reindex(idx)


def save_csv_no_overwrite(df, path: Path, overwrite: bool):
    if path.exists() and not overwrite:
        raise FileExistsError(f'Output exists: {path}; use --overwrite-candidate to replace candidates only')
    tmp = path.with_name(path.name + '.partial')
    if tmp.exists():
        raise FileExistsError(f'Abandoned partial output {tmp}; inspect before retry')
    try:
        df.to_csv(tmp, index=True)
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def one_site(site, args):
    conf = CONFIG[site]
    start, end = conf['start'], (2026 if args.include_2026 and site in ('DK-Sor', 'FR-Fon') else conf['end'])
    idx = pd.date_range(f'{start}-01-01', f'{end}-12-31 23:30', freq='30min')
    site_root = args.root / site / 'forcing'
    pkg_dir = site_root / 'packages_multisource_v1'
    raw_dir = site_root / 'raw_multisource_v1'
    output = site_root / 'merged_multisource_v1'
    output.mkdir(parents=True, exist_ok=True)
    print(f'\n========== {site} {start}-{end} ==========', flush=True)
    data = {}
    for label, stem in conf['sources'].items():
        subdir = raw_dir / label
        stage_package(pkg_dir, stem, subdir)
        data[label] = read_source(label, subdir, VARIABLES, idx)
    years = idx.year
    merged = pd.DataFrame(index=idx)
    chosen = {}
    for v in VARIABLES:
        values = pd.Series(np.nan, index=idx, dtype='float64')
        from_label = pd.Series(pd.NA, index=idx, dtype='string')
        for first, last, priority in conf['priorities']:
            subset = (years >= first) & (years <= last)
            for label in priority:
                take = subset & values.isna() & data[label][v].notna()
                values.loc[take] = data[label][v].loc[take]
                from_label.loc[take] = label
        merged[v] = values
        merged[v+'_SOURCE'] = from_label
        chosen[v] = from_label
        if v in MET:
            qc = pd.Series(np.nan, index=idx, dtype='float64')
            for label in data:
                take = from_label.eq(label).fillna(False).to_numpy(dtype=bool)
                qc.loc[take] = data[label].loc[take, v+'_QC']
            merged[v+'_QC'] = qc
    merged.index.name = 'time'
    prefix = f'{site}_multisource_HH_{start}_{end}_candidate'
    out = output / (prefix + '.csv')
    if out.exists() and not args.overwrite_candidate:
        raise FileExistsError(f'{out} exists; refused to overwrite (use --overwrite-candidate)')
    # Atomic commit of the largest product first.
    save_csv_no_overwrite(merged, out, args.overwrite_candidate)
    summary = pd.DataFrame([
        {'variable': v, **{f'{label}_records': int(chosen[v].eq(label).sum()) for label in data},
         'missing_records': int(merged[v].isna().sum())} for v in VARIABLES
    ])
    summary.to_csv(output / f'{site}_source_summary_{start}_{end}.csv', index=False)
    yearly = merged[MET].notna().groupby(years).mean()
    yearly.index.name = 'year'
    yearly.to_csv(output / f'{site}_yearly_met_coverage_{start}_{end}.csv')
    differences = []
    labels = list(data)
    if len(labels) == 2:
        left, right = labels
        for v in MET:
            a = data[left][v]
            b = data[right][v]
            valid = a.notna() & b.notna()
            diff = (a[valid] - b[valid]).abs()
            differences.append({'variable': v, 'source_a': left, 'source_b': right,
                                'overlapping_valid_rows': int(valid.sum()),
                                'median_absolute_difference': float(diff.median()) if len(diff) else np.nan,
                                'p95_absolute_difference': float(diff.quantile(.95)) if len(diff) else np.nan})
    pd.DataFrame(differences).to_csv(output / f'{site}_overlap_differences.csv', index=False)
    summary_info = {
        'site': site, 'years': [start, end], 'rows': len(idx),
        'met_all_complete': bool(merged[MET].notna().all().all()),
        'minimum_yearly_met_fraction': float(yearly.min().min()),
        'no_leap_expected_rows': (end-start+1) * 17520,
        'notes': ['Candidate only; physical QC and ERA analysis not yet performed.',
                  'Source provenance is product provenance, not measured-vs-gapfilled provenance.',
                  '2026 is provisional and must not be treated as a complete observed model year.'],
    }
    (output / f'{site}_merge_status.json').write_text(json.dumps(summary_info, indent=2))
    print(summary.to_string(index=False))
    print('Yearly meteorological coverage:')
    print(yearly.round(4).to_string())
    print('Merged:', out)
    print('NOTICE: noleap, physical QC, ZBOT, DATM and spin-up are NOT performed.')
    return summary_info


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sites', nargs='+', choices=CONFIG.keys(), default=list(CONFIG))
    p.add_argument('--root', type=Path, default=BASE)
    p.add_argument('--include-2026', action='store_true', help='Diagnostic only: include unfinished 2026 for DK-Sor/FR-Fon')
    p.add_argument('--overwrite-candidate', action='store_true', help='Explicitly overwrite previously generated candidate outputs')
    args = p.parse_args()
    failed = []
    for site in args.sites:
        try:
            one_site(site, args)
        except Exception as e:
            print(f'ERROR [{site}] {type(e).__name__}: {e}', flush=True)
            failed.append(site)
    if failed:
        raise SystemExit(f'Failed sites: {", ".join(failed)}')
    print('\nSUCCESS: all selected multisource candidate merges completed.')


if __name__ == '__main__':
    main()
