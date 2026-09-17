import argparse
from datetime import datetime


def argument():
    parser = argparse.ArgumentParser(description='''
    ''', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--outdir', '-o',
                        type=str,
                        required=True,
                        help='input dir validation tmp')

    parser.add_argument('--variable', '-v',
                        type=str,
                        default=None,
                        required=True,
                        help='model variable')
    return parser.parse_args()


args = argument()

from bitsea.commons.utils import addsep
import numpy as np
import pandas as pd
import os
from bitsea.commons import timerequestors
from bitsea.instruments import bio_float
from bitsea.instruments.var_conversions import FLOATVARS
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
import gsw
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


SEASON_COLORS = {
    "Winter": "#2166ac",
    "Spring": "#66bd63",
    "Summer": "#d73027",
    "Autumn": "#d8a31a",
}

SEASON_MONTHS = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring", 4: "Spring", 5: "Spring",
    6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn",
}


def compute_density_teos10(sp, temp, pres, ds):
    """Compute density using TEOS-10 with gsw."""
    if 'LONGITUDE' in ds and 'LATITUDE' in ds:
        SA = gsw.SA_from_SP(sp, pres, ds['LONGITUDE'], ds['LATITUDE'])
    elif 'longitude' in ds and 'latitude' in ds:
        SA = gsw.SA_from_SP(sp, pres, ds['longitude'], ds['latitude'])
    elif 'lon' in ds and 'lat' in ds:
        SA = gsw.SA_from_SP(sp, pres, ds['lon'], ds['lat'])
    else:
        SA = sp

    CT = gsw.CT_from_t(SA, temp, pres)
    return gsw.rho(SA, CT, pres)


def plot_line_profiles(df, z_interp, namesub, varmod, profile_months):
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    for profile_index, month in enumerate(profile_months):
        season = SEASON_MONTHS[month]
        ax.plot(
            df.iloc[:, profile_index],
            z_interp,
            color=SEASON_COLORS[season],
            alpha=0.25,
            linewidth=0.8,
        )

    legend_handles = [
        Line2D([0], [0], color=SEASON_COLORS[season], linewidth=3, label=season)
        for season in SEASON_COLORS
    ]
    ax.legend(handles=legend_handles, title='Season')
    ax.invert_yaxis()
    ax.set_ylabel(varmod)
    ax.set_xlabel('depth (m)')
    ax.set_title('All profiles ' + namesub)

    plt.tight_layout()
    plt.savefig(OUTDIR + '/' + namesub + '_' + varmod + '_coriolis.png')
    df.to_csv(OUTDIR + '/' + namesub + '_' + varmod + '_coriolis.csv')
    plt.close(fig)


def convert_umolkg_to_mmolm3(new_ds, Pres, Profile, VARNAME='DOXY'):
    density = compute_density_teos10(new_ds['PSAL'], new_ds['TEMP'], new_ds['PRES'], new_ds)
    density = np.squeeze(density)
    Pres_phy = np.squeeze(new_ds['PRES'])
    if len(density) != len(Pres):
        density = np.interp(Pres, Pres_phy, density, left=np.nan, right=np.nan)
    Profile = np.squeeze(Profile * density / 1000.0)
    return Pres, Profile


OUTDIR = addsep(args.outdir)
varmod = args.variable

TheMask = Mask.from_file(os.environ["MASKFILE"])
z_interp = TheMask.zlevels

if OGS.atl in OGS.Pred.basin_list:
    OGS.Pred.basin_list.remove(OGS.atl)

SUBS = OGS.Pred.basin_list[:]
CLIM = np.zeros((len(SUBS), len(z_interp)), np.float32) * np.nan
STD = np.zeros((len(SUBS), len(z_interp)), np.float32) * np.nan
NPROFILES = np.zeros(len(SUBS), dtype=np.int32)
NWMO = np.zeros(len(SUBS), dtype=np.int32)
YEAR_MIN = np.zeros(len(SUBS), dtype=np.int32)
MONTH_MIN = np.zeros(len(SUBS), dtype=np.int32)
YEAR_MAX = np.zeros(len(SUBS), dtype=np.int32)
MONTH_MAX = np.zeros(len(SUBS), dtype=np.int32)
print('_________________start__________________', flush=True)

SUB_COUNT = 0
TI = timerequestors.TimeInterval(
    starttime='19500101',
    endtime='20280101',
    dateformat='%Y%m%d',
)
for ISUB in SUBS:
    print('_____________ ' + str(ISUB) + ' _____________', flush=True)

    Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, ISUB)

    if ISUB.name == 'ion1':
        isub = ComposedBasin('ion4', [OGS.swm2, OGS.ion2, OGS.tyr2], 'Neighbors of ion1')
        Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, isub)
    elif ISUB.name == 'tyr1':
        isub = ComposedBasin('supertyr', [OGS.tyr2, OGS.tyr1], 'tyr1and2')
        Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, isub)
    else:
        Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, ISUB)

    if not Profilelist:
        continue

    print('number of profiles used', flush=True)
    print(len(Profilelist), flush=True)

    SERV_VAR = np.full((len(Profilelist), len(z_interp)), np.nan, dtype=np.float32)
    profile_months = []
    valid_profiles = []
    ICONT = 0

    for PROFILE in Profilelist:
        Pres, Profile, Qc = PROFILE.read(var=FLOATVARS[varmod])
        if len(Pres) < 5:
            continue
        if varmod == 'O2o':
            new_ds = xr.open_dataset(PROFILE._my_float.filename)
            Pres, Profile = convert_umolkg_to_mmolm3(new_ds, Pres, Profile)
        Profile_interp = np.interp(z_interp, Pres, Profile, left=np.nan, right=np.nan)
        SERV_VAR[ICONT, :] = Profile_interp
        profile_months.append(PROFILE.time.month)
        valid_profiles.append(PROFILE)
        ICONT += 1

    if not valid_profiles:
        print('no valid profiles after filtering; skipping basin', flush=True)
        continue

    df = pd.DataFrame(SERV_VAR).T
    namesub = ISUB.name
    plot_line_profiles(df, z_interp, namesub, FLOATVARS[varmod], profile_months)
    NPROFILES[SUB_COUNT] = len(valid_profiles)
    NWMO[SUB_COUNT] = len(bio_float.get_wmo_list(valid_profiles))
    profile_dates = [profile.time for profile in valid_profiles]
    date_min = min(profile_dates)
    date_max = max(profile_dates)
    YEAR_MIN[SUB_COUNT] = date_min.year
    MONTH_MIN[SUB_COUNT] = date_min.month
    YEAR_MAX[SUB_COUNT] = date_max.year
    MONTH_MAX[SUB_COUNT] = date_max.month

    serv_P = np.nanmean(SERV_VAR, axis=0)
    serv_S = np.nanstd(SERV_VAR, axis=0)
    CLIM[SUB_COUNT, :] = serv_P
    STD[SUB_COUNT, :] = serv_S
    SUB_COUNT += 1

import netCDF4
outfile = OUTDIR + '/yr_Avg_' + varmod + '_coriolis.nc'
ncOUT = netCDF4.Dataset(outfile, 'w')
ncOUT.createDimension('nsub', len(SUBS))
ncOUT.createDimension('nav_lev', len(z_interp))
ncvar = ncOUT.createVariable(varmod, 'f', ('nsub', 'nav_lev'))
ncvar[:] = CLIM
ncvar = ncOUT.createVariable('NPROFILES', 'i4', ('nsub',))
ncvar.long_name = 'number of profiles used'
ncvar[:] = NPROFILES
ncvar = ncOUT.createVariable('NWMO', 'i4', ('nsub',))
ncvar.long_name = 'number of distinct WMO used'
ncvar[:] = NWMO
for name, long_name, values in [
    ('YEAR_MIN', 'year of earliest profile', YEAR_MIN),
    ('MONTH_MIN', 'month of earliest profile', MONTH_MIN),
    ('YEAR_MAX', 'year of latest profile', YEAR_MAX),
    ('MONTH_MAX', 'month of latest profile', MONTH_MAX),
]:
    ncvar = ncOUT.createVariable(name, 'i4', ('nsub',))
    ncvar.long_name = long_name
    ncvar[:] = values
ncOUT.close()

outfile = OUTDIR + '/yr_Std_' + varmod + '_coriolis.nc'
ncOUT = netCDF4.Dataset(outfile, 'w')
ncOUT.createDimension('nsub', len(SUBS))
ncOUT.createDimension('nav_lev', len(z_interp))
ncvar = ncOUT.createVariable(varmod, 'f', ('nsub', 'nav_lev'))
ncvar[:] = STD
ncOUT.close()

import shutil
shutil.copy('Yr_Climfloat_netcdf_Coriolis.py', OUTDIR)
