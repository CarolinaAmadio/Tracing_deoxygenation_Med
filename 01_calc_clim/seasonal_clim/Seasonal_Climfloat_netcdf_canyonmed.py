import argparse


def argument():
    parser = argparse.ArgumentParser(description='''
    This script computes seasonal vertical climatologies of a given CANYON-MED variable for different Mediterranean sub-basins.
    **Input**: CANYON-MED profiles selected for a given variable (--variable) and seasonal climatology (bitsea season with BGC=True: MAM, JJA, SON, DJF).
    **Method**: For each sub-basin and season, profiles are interpolated on the model depth levels, and vertical averages and standard deviations are computed.
    **Output**:
     - PNG figures showing all vertical profiles per sub-basin.
     - CSV files with the interpolated profile data.
     - NetCDF files containing the vertical climatologies:
         - <season>_Avg_<variable>_canyonmed.nc: mean values
         - <season>_Std_<variable>_canyonmed.nc: standard deviations
         - <season>_Pct_<variable>_canyonmed.nc: median (MEDIAN) and percentiles P01, P05, P95, P99
    ''', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--outdir','-o',
                        type=str,
                        required=True,
                        help='input dir validation tmp')

    parser.add_argument('--variable', '-v',
                        type=str,
                        default=None,
                        required=True,
                        help='model variable')
    parser.add_argument('--workers', '-w',
                        type=int,
                        default=1,
                        help='parallel processes (one task per season and sub-basin)')
    args = parser.parse_args()
    if args.workers < 1:
        parser.error('--workers must be at least 1')
    return args


args = argument()

from bitsea.commons.utils import addsep
import numpy as np
import pandas as pd
import os
from bitsea.commons import timerequestors
from bitsea.commons.season import season
from bitsea.instruments import float_canyonmed as bio_float
from bitsea.instruments.var_conversions import CANYONVAR
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot_line_profiles(df, z_interp, namesub, varmod, seasname):
    fig, axs = plt.subplots(1, 1, figsize=(10, 6))
    plt.plot(df.values, z_interp, alpha=0.3)
    plt.gca().invert_yaxis()
    plt.ylabel(varmod)
    plt.xlabel('depth (m)')
    plt.title(f'All profiles {namesub} season {seasname}')

    plt.tight_layout()
    plt.savefig(OUTDIR + f'/{namesub}_{varmod}_{seasname}_canyonmed.png')
    plt.close()
    df.to_csv(OUTDIR + f'/{namesub}_{varmod}_{seasname}_canyonmed.csv')


OUTDIR = addsep(args.outdir)
varmod = args.variable

CANYON_VARS = {"N3n", "N1p", "DIC", "N5s", "ALK", "pH"}
if varmod not in CANYON_VARS:
    raise ValueError(f"This script only supports CanyonMED variables: {sorted(CANYON_VARS)}")

TheMask = Mask.from_file(os.environ["MASKFILE"])
z_interp = TheMask.zlevels

if OGS.atl in OGS.Pred.basin_list:
    OGS.Pred.basin_list.remove(OGS.atl)

SUBS = OGS.Pred.basin_list[:]
print('_________________start__________________', flush=True)

canyon_key = CANYONVAR[varmod]
seasonObj = season(BGC=True)
NSEASONS = seasonObj.get_seasons_number()
PCT_LIST = [1, 5, 95, 99]


def process_basin(mm, isub_index):
    ISUB = SUBS[isub_index]
    _, seasname = seasonObj.get_season_dates(mm)
    print(f'_____________ {ISUB} {seasname} _____________', flush=True)
    TI = timerequestors.Clim_season(mm, seasonObj)

    isub = ISUB
    if ISUB.name == 'ion1':
        isub = ComposedBasin('ion4', [OGS.swm2, OGS.ion2, OGS.tyr2], 'Neighbors of ion1')
    elif ISUB.name == 'tyr1':
        isub = ComposedBasin('supertyr', [OGS.tyr2, OGS.tyr1], 'tyr1and2')

    Profilelist = bio_float.FloatSelector(canyon_key, TI, isub)
    Profilelist = [P for P in Profilelist if P._my_float.has_canyonmed(canyon_key)]
    if not Profilelist:
        return None

    print('number of profiles used', flush=True)
    print(len(Profilelist), flush=True)

    sub_profile_times = [pd.to_datetime(P.time).to_pydatetime() for P in Profilelist]
    date_min, date_max = min(sub_profile_times), max(sub_profile_times)

    SERV_VAR = np.full((len(Profilelist), len(z_interp)), np.nan, dtype=np.float32)
    for ICONT, PROFILE in enumerate(Profilelist):
        Pres, Profile, Qc = PROFILE.read(var=canyon_key, var_mod=None, sourcedata='canyon_med')
        if np.all(Qc > 0):
            raise ValueError("No canyonmed was read")
        SERV_VAR[ICONT, :] = np.interp(z_interp, Pres, Profile, left=np.nan, right=np.nan)

    df = pd.DataFrame(SERV_VAR).T
    plot_line_profiles(df, z_interp, ISUB.name, varmod, seasname)

    return {
        'NPROFILES': len(Profilelist),
        'NWMO': len(bio_float.get_wmo_list(Profilelist)),
        'YEAR_MIN': date_min.year, 'MONTH_MIN': date_min.month,
        'YEAR_MAX': date_max.year, 'MONTH_MAX': date_max.month,
        'CLIM': np.nanmean(SERV_VAR, axis=0),
        'STD': np.nanstd(SERV_VAR, axis=0),
        'MEDIAN': np.nanmedian(SERV_VAR, axis=0),
        'PCT': np.nanpercentile(SERV_VAR, PCT_LIST, axis=0),
    }


tasks = [(mm, SUB_COUNT) for mm in range(NSEASONS) for SUB_COUNT in range(len(SUBS))]

nworkers = min(args.workers, max(1, len(tasks)))
print(f'Processing {len(tasks)} season-basin tasks with {nworkers} worker(s)', flush=True)
if nworkers == 1:
    results = {t: process_basin(*t) for t in tasks}
else:
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=nworkers, mp_context=mp.get_context("fork")) as pool:
        futures = {t: pool.submit(process_basin, *t) for t in tasks}
        results = {t: f.result() for t, f in futures.items()}

for mm in range(NSEASONS):
    _, seasname = seasonObj.get_season_dates(mm)
    CLIM = np.full((len(SUBS), len(z_interp)), np.nan, dtype=np.float32)
    STD = np.full((len(SUBS), len(z_interp)), np.nan, dtype=np.float32)
    MEDIAN = np.full((len(SUBS), len(z_interp)), np.nan, dtype=np.float32)
    PCT = np.full((len(PCT_LIST), len(SUBS), len(z_interp)), np.nan, dtype=np.float32)
    NPROFILES = np.zeros(len(SUBS), dtype=np.int32)
    NWMO = np.zeros(len(SUBS), dtype=np.int32)
    YEAR_MIN = np.zeros(len(SUBS), dtype=np.int32)
    MONTH_MIN = np.zeros(len(SUBS), dtype=np.int32)
    YEAR_MAX = np.zeros(len(SUBS), dtype=np.int32)
    MONTH_MAX = np.zeros(len(SUBS), dtype=np.int32)

    for SUB_COUNT in range(len(SUBS)):
        r = results.get((mm, SUB_COUNT))
        if r is None:
            continue
        CLIM[SUB_COUNT, :] = r['CLIM']
        STD[SUB_COUNT, :] = r['STD']
        MEDIAN[SUB_COUNT, :] = r['MEDIAN']
        PCT[:, SUB_COUNT, :] = r['PCT']
        NPROFILES[SUB_COUNT] = r['NPROFILES']
        NWMO[SUB_COUNT] = r['NWMO']
        YEAR_MIN[SUB_COUNT], MONTH_MIN[SUB_COUNT] = r['YEAR_MIN'], r['MONTH_MIN']
        YEAR_MAX[SUB_COUNT], MONTH_MAX[SUB_COUNT] = r['YEAR_MAX'], r['MONTH_MAX']

    import netCDF4

    outfile = OUTDIR + f'/{seasname}_Avg_{varmod}_canyonmed.nc'
    ncOUT = netCDF4.Dataset(outfile, 'w')
    ncOUT.createDimension('nsub', len(SUBS))
    ncOUT.createDimension('nav_lev', len(z_interp))
    ncvar = ncOUT.createVariable(varmod, 'f', ('nsub', 'nav_lev'))
    ncvar[:] = CLIM
    for name, long_name, values in [
        ('NPROFILES', 'number of profiles', NPROFILES),
        ('NWMO', 'number of distinct WMO', NWMO),
        ('YEAR_MIN', 'year of earliest profile', YEAR_MIN),
        ('MONTH_MIN', 'month of earliest profile', MONTH_MIN),
        ('YEAR_MAX', 'year of latest profile', YEAR_MAX),
        ('MONTH_MAX', 'month of latest profile', MONTH_MAX),
    ]:
        ncvar = ncOUT.createVariable(name, 'i4', ('nsub',))
        ncvar.long_name = long_name
        ncvar[:] = values
    ncOUT.close()

    outfile = OUTDIR + f'/{seasname}_Std_{varmod}_canyonmed.nc'
    ncOUT = netCDF4.Dataset(outfile, 'w')
    ncOUT.createDimension('nsub', len(SUBS))
    ncOUT.createDimension('nav_lev', len(z_interp))
    ncvar = ncOUT.createVariable(varmod, 'f', ('nsub', 'nav_lev'))
    ncvar[:] = STD
    ncOUT.close()

    outfile = OUTDIR + f'/{seasname}_Pct_{varmod}_canyonmed.nc'
    ncOUT = netCDF4.Dataset(outfile, 'w')
    ncOUT.createDimension('nsub', len(SUBS))
    ncOUT.createDimension('nav_lev', len(z_interp))
    ncvar = ncOUT.createVariable('MEDIAN', 'f', ('nsub', 'nav_lev'))
    ncvar.long_name = 'median of ' + varmod
    ncvar[:] = MEDIAN
    for ip, pct in enumerate(PCT_LIST):
        ncvar = ncOUT.createVariable('P%02d' % pct, 'f', ('nsub', 'nav_lev'))
        ncvar.long_name = '%d-th percentile of %s' % (pct, varmod)
        ncvar[:] = PCT[ip]
    ncOUT.close()
