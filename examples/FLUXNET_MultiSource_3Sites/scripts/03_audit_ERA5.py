#!/usr/bin/env python3
"""Check numerical coverage (not physical validity) of companion FLUXNET ERA5_HH files."""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path('/iridisfs/scratch/ly3n24/CLM_FATES/sites/MY_EC_SITE')
YEARS = {'DK-Sor': (1996, 2025), 'FR-Fon': (2005, 2025), 'IT-Noe': (2004, 2025)}
VARS = ['TA_ERA', 'VPD_ERA', 'PA_ERA', 'SW_IN_ERA', 'LW_IN_ERA', 'WS_ERA', 'P_ERA']


def one(site, end_override=None):
    start, end = YEARS[site]
    end = end_override or end
    base = ROOT / site / 'forcing'
    files = sorted((base / 'raw_multisource_v1').rglob('*ERA5_HH*.csv'))
    if not files:
        raise RuntimeError(f'{site}: No standalone ERA5_HH file in raw_multisource_v1. '
                           'This does NOT prove ERA5 is absent; examine extracted package names.')
    expected = pd.date_range(f'{start}-01-01 00:00', f'{end}-12-31 23:30', freq='30min')
    merged = pd.DataFrame(np.nan, index=expected, columns=VARS)
    # Prefer ICOS companion first; only fill its gaps from other ERA products.
    files.sort(key=lambda p: (0 if '/ICOS/' in str(p) else 1, str(p)))
    print(f'\n==== {site} companion ERA coverage {start}-{end} ====')
    print('Expected half-hours:', len(expected))
    for f in files:
        h = pd.read_csv(f, nrows=0).columns.tolist()
        if 'TIMESTAMP_START' in h:
            tc, offset = 'TIMESTAMP_START', pd.Timedelta(0)
        elif 'TIMESTAMP_END' in h:
            tc, offset = 'TIMESTAMP_END', pd.Timedelta(minutes=30)
        else:
            print('  SKIP no timestamp:', f)
            continue
        available = [v for v in VARS if v in h]
        if not available:
            continue
        d = pd.read_csv(f, usecols=[tc]+available, low_memory=False, dtype={tc:'string'})
        times = pd.to_datetime(d[tc].str.strip(), format='%Y%m%d%H%M', errors='coerce') - offset
        if times.isna().any() or times.duplicated().any():
            raise ValueError(f'Invalid ERA timestamps in {f}')
        print(' ', f.name, f'[{times.min()} to {times.max()}]')
        d.index = pd.DatetimeIndex(times)
        d.drop(columns=[tc], inplace=True)
        good = d.index[(d.index>=expected[0]) & (d.index<=expected[-1])]
        if not good.isin(expected).all():
            raise ValueError(f'Non-HH timestamps: {f}')
        d = d.reindex(expected)
        for v in available:
            x = pd.to_numeric(d[v], errors='coerce').mask(lambda q:q<=-9990)
            merged[v] = merged[v].combine_first(x)
    report = pd.DataFrame([{
        'site': site, 'variable': v, 'records': int(merged[v].notna().sum()),
        'missing': int(merged[v].isna().sum()),
        'coverage_pct': round(100*merged[v].notna().mean(), 4)
    } for v in VARS])
    yearly = merged.notna().groupby(merged.index.year).mean()*100
    yearly.index.name = 'year'
    out = base / 'merged_multisource_v1'
    out.mkdir(parents=True, exist_ok=True)
    report.to_csv(out / f'{site}_ERA5_coverage_{start}_{end}.csv', index=False)
    yearly.to_csv(out / f'{site}_ERA5_yearly_coverage_{start}_{end}.csv')
    print(report.to_string(index=False))
    print(yearly.round(2).to_string())
    print('ERA numerical coverage:', 'FULL' if merged.notna().all().all() else 'INCOMPLETE / REVIEW')
    print('NOTE: ERA numerical coverage is NOT a physical or scientific QC pass.')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sites', nargs='+', choices=list(YEARS), default=list(YEARS))
    p.add_argument('--include-2026', action='store_true')
    a = p.parse_args()
    failures=[]
    for site in a.sites:
        try:
            one(site, 2026 if a.include_2026 and site in ('DK-Sor','FR-Fon') else None)
        except Exception as e:
            failures.append(site)
            print(f'ERA AUDIT ERROR [{site}]: {e}')
    if failures:
        raise SystemExit('ERA audit incomplete for '+', '.join(failures))

if __name__=='__main__':
    main()
