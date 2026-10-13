#!/usr/bin/env python3
"""Read-only audit of GL-ZaH FLX/ICOS/ERA5 time coverage; only unpacks source packages.

Creates separate raw_multisource_v1 and audit_multisource_v1 directories.
Does NOT interpolate, fill, write DATM, or change other experiment inputs.
"""
from __future__ import annotations
import argparse
import csv
import json
import shutil
import tempfile
import zlib
from collections import defaultdict
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import numpy as np
import pandas as pd

STEMS = {
    'FLX': 'FLX_GL-ZaH_FLUXNET2015_FULLSET_2000-2014_2-4',
    'ICOS': 'ICOS_GL-ZaH_FLUXNET_2020-2025_v1.3_r1',
}
MET = ['TA_F', 'VPD_F', 'PA_F', 'SW_IN_F', 'LW_IN_F', 'WS_F', 'P_F']
ERA = [k[:-2] + '_ERA' for k in MET]
GAP_START = '2015-01-01 00:00'
GAP_END = '2019-12-31 23:30'


def file_crc32(path):
    acc = 0
    with path.open('rb') as f:
        for b in iter(lambda: f.read(2 * 1024 * 1024), b''):
            acc = zlib.crc32(b, acc)
    return acc & 0xFFFFFFFF


def unpack(archive, dest, depth=0):
    if depth > 5:
        raise RuntimeError(f'Nested ZIP level >5 in {archive}')
    with ZipFile(archive) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = PurePosixPath(info.filename.replace('\\', '/')).name
            if not name:
                continue
            ext = Path(name).suffix.lower()
            if ext == '.zip':
                with tempfile.NamedTemporaryFile(suffix='.zip', dir=str(dest), delete=False) as fh:
                    nested = Path(fh.name)
                    with z.open(info) as src:
                        shutil.copyfileobj(src, fh)
                try:
                    unpack(nested, dest, depth + 1)
                finally:
                    nested.unlink(missing_ok=True)
            elif ext == '.csv':
                output = dest / name
                if output.exists():
                    if output.stat().st_size != info.file_size or file_crc32(output) != info.CRC:
                        raise RuntimeError(f'Existing CSV conflicts with source ZIP: {output}')
                    continue
                partial = dest / (name + '.partial')
                if partial.exists():
                    raise RuntimeError(f'Stale extraction partial: {partial}')
                with z.open(info) as src, partial.open('wb') as out:
                    shutil.copyfileobj(src, out)
                if partial.stat().st_size != info.file_size or file_crc32(partial) != info.CRC:
                    partial.unlink(missing_ok=True)
                    raise RuntimeError(f'Failed ZIP CRC/size verification: {name}')
                partial.replace(output)
                print('  Extracted', output.name, flush=True)


def unpack_source(pkg_dir, raw_dir, stem):
    raw_dir.mkdir(parents=True, exist_ok=True)
    archives = sorted(p for p in pkg_dir.glob(stem + '.*') if p.suffix.lower() == '.zip')
    folder = pkg_dir / stem
    csvs = sorted(p for p in pkg_dir.glob(stem + '.*') if p.suffix.lower() == '.csv')
    if len(archives) == 1:
        print('Source ZIP:', archives[0], flush=True)
        unpack(archives[0], raw_dir)
    elif len(archives) > 1:
        raise RuntimeError(f'Multiple archives found for {stem}: {archives}')
    elif folder.is_dir():
        print('Source extracted directory:', folder, flush=True)
        # First expand all ZIP files (including outer/inner archives), then standalone CSV files.
        for z in sorted(folder.rglob('*')):
            if z.is_file() and z.suffix.lower() == '.zip':
                unpack(z, raw_dir)
        for src in sorted(folder.rglob('*')):
            if not src.is_file() or src.suffix.lower() != '.csv':
                continue
            output = raw_dir / src.name
            if output.exists():
                if output.stat().st_size != src.stat().st_size or file_crc32(output) != file_crc32(src):
                    raise RuntimeError(f'CSV name collision, differing contents: {src}')
            else:
                shutil.copy2(src, output)
                print('  Copied', output.name, flush=True)
    elif len(csvs) == 1:
        # A standalone CSV is supported for inventory but full source packages are preferred.
        src = csvs[0]; dest = raw_dir / src.name
        if not dest.exists():
            shutil.copy2(src, dest)
    else:
        raise FileNotFoundError(f'Missing package: {stem} in {pkg_dir}')
    return sorted(raw_dir.rglob('*.csv'))


def find_one(files, test, label):
    selected = [x for x in files if test(x.name.upper())]
    if len(selected) != 1:
        print(f'  {label}: expected 1 file, found {len(selected)}', flush=True)
        for x in selected:
            print('   -', x, flush=True)
        return None
    print(f'  {label}: {selected[0].name}', flush=True)
    return selected[0]


def parse_time_column(df, col, path):
    raw = df[col].astype('string').str.strip().str.replace(r'\.0$', '', regex=True)
    stamp = pd.to_datetime(raw, format='%Y%m%d%H%M', errors='coerce')
    if stamp.isna().any():
        raise ValueError(f'{path}: {int(stamp.isna().sum())} unparseable timestamps')
    if col == 'TIMESTAMP_END':
        stamp -= pd.Timedelta(minutes=30)
    idx = pd.DatetimeIndex(stamp)
    if idx.has_duplicates:
        raise ValueError(f'{path}: duplicate timestamps')
    if not idx.is_monotonic_increasing:
        raise ValueError(f'{path}: timestamps are not sorted')
    if (idx.minute % 30 != 0).any() or (idx.second != 0).any():
        raise ValueError(f'{path}: non half-hour-aligned timestamp')
    return idx


def load_values(path, variables):
    header = pd.read_csv(path, nrows=0).columns.tolist()
    if 'TIMESTAMP_START' in header:
        tc = 'TIMESTAMP_START'
    elif 'TIMESTAMP_END' in header:
        tc = 'TIMESTAMP_END'
    else:
        raise ValueError(f'No TIMESTAMP_START/END found: {path.name}')
    have = [v for v in variables if v in header]
    df = pd.read_csv(path, usecols=[tc] + have, dtype={tc: 'string'}, low_memory=False)
    dtidx = parse_time_column(df, tc, path)
    df = df.drop(columns=[tc]); df.index = dtidx
    for v in have:
        df[v] = pd.to_numeric(df[v], errors='coerce')
        df.loc[df[v] <= -9990, v] = np.nan
    return df, have, {'file': str(path), 'time_column': tc,
                      'start': str(df.index.min()), 'end': str(df.index.max()),
                      'nrows': len(df), 'columns_available': have}


def coverage(df, cols, start, end, source):
    expected = pd.date_range(start, end, freq='30min')
    part = df.reindex(expected)
    rows = []
    for v in cols:
        series = part[v] if v in part else pd.Series(np.nan, index=expected)
        valid = int(series.notna().sum()); n = len(expected)
        rows.append({'source': source, 'variable': v, 'expected_rows': n,
                     'valid_rows': valid, 'missing_rows': n - valid,
                     'coverage_pct': round(100 * valid / n, 5)})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=Path(
        '/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE/GL-ZaH'))
    args = ap.parse_args()
    base = args.root / 'forcing'
    pkgs = base / 'packages_multisource_v1'
    raws = base / 'raw_multisource_v1'
    reports = base / 'audit_multisource_v1'
    reports.mkdir(parents=True, exist_ok=True)
    inventory = {}
    files_by = {}
    print('GL-ZaH source audit (no forcing files are written)')

    for src, stem in STEMS.items():
        print('\n=== SOURCE', src, '===', flush=True)
        files = unpack_source(pkgs, raws / src, stem)
        files_by[src] = files
        print('Total extracted CSV files:', len(files))
        for f in files:
            if ('ERA5_HH' in f.name.upper() or 'BIF' in f.name.upper()
                    or 'FLUXMET_HH' in f.name.upper() or 'FULLSET_HH' in f.name.upper()):
                print(' ', f.name, flush=True)
        inventory[src] = {'stem': stem, 'csv_count': len(files),
                          'bif_files': [str(p) for p in files if 'BIF' in p.name.upper()]}

    specs = [
        ('FLX', 'FLX', lambda n: '_FULLSET_HH_' in n, MET,
         '2000-01-01', '2014-12-31 23:30'),
        ('ICOS', 'ICOS', lambda n: 'FLUXMET_HH' in n, MET,
         '2020-01-01', '2025-12-31 23:30'),
        ('ERA5_HH', 'ICOS', lambda n: 'ERA5_HH' in n, ERA, GAP_START, GAP_END),
    ]
    inventory['audits'] = {}
    results = []
    year_rows = []
    missing_required_file = []
    for name, source, predicate, vars_, first, last in specs:
        print('\n=== AUDITING', name, '===', flush=True)
        path = find_one(files_by[source], predicate, name)
        if path is None:
            missing_required_file.append(name)
            inventory['audits'][name] = {'status': 'MISSING_OR_AMBIGUOUS'}
            continue
        data, have, meta = load_values(path, vars_)
        inventory['audits'][name] = meta
        print('Actual period:', meta['start'], 'to', meta['end'], flush=True)
        print('Original rows:', meta['nrows'], flush=True)
        print('Required columns present:', have, flush=True)
        cv = coverage(data, vars_, first, last, name)
        results.extend(cv)
        for item in cv:
            print('  {variable:12} {valid_rows:7}/{expected_rows:7} valid  ({coverage_pct:.3f}%)'.format(**item))
        if name == 'ERA5_HH':
            for y in range(2015, 2020):
                yr = coverage(data, vars_, f'{y}-01-01', f'{y}-12-31 23:30', name)
                for it in yr:
                    year_rows.append({'year': y, **it})

    report = pd.DataFrame(results, columns=[
        'source', 'variable', 'expected_rows', 'valid_rows', 'missing_rows', 'coverage_pct'])
    yearly = pd.DataFrame(year_rows)
    report.to_csv(reports / 'GL-ZaH_source_coverage.csv', index=False)
    yearly.to_csv(reports / 'GL-ZaH_ERA5_bridge_yearly.csv', index=False)
    (reports / 'GL-ZaH_inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf-8')

    good = (not missing_required_file and len(results) == 21
            and all(x['missing_rows'] == 0 for x in results))
    state = 'BRIDGE_DATA_COMPLETE_QC_PENDING' if good else 'REVIEW_MISSING_DATA'
    status = {'status': state, 'period': [2000, 2025],
              'bridge_years': [2015, 2019], 'bridge_rows_expected': 87648,
              'missing_required_files': missing_required_file,
              'physical_qc_performed': False, 'merging_performed': False,
              'report_dir': str(reports)}
    (reports / 'GL-ZaH_audit_status.json').write_text(json.dumps(status, indent=2))
    print('\n=== FINAL AUDIT ===')
    print(report.to_string(index=False) if not report.empty else '(no audit data)')
    print('BIF count:', sum(len(inventory[s]['bif_files']) for s in STEMS))
    print('Status:', state)
    print('Reports:', reports)
    if good:
        print('ALL required time/variable records are present. NEXT: source transition QC and candidate merge.')
    else:
        print('GAPS detected. Inspect coverage CSV before any gap filling or model run.')

if __name__ == '__main__':
    main()
