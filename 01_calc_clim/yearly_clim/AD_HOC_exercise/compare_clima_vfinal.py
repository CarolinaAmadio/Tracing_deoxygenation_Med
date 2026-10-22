import argparse
import pandas as pd

def argument():
    parser = argparse.ArgumentParser(description='counts the available BGC-Argo float profiles per basin and plots their monthly distribution.', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--indir','-i', type=str, required=True, help='netcdf inputs')
    parser.add_argument('--outdir','-o', type=str, required=True, help='output to save png')
    parser.add_argument('--variable','-v', type=str, default=None, required=True, help='model variable')
    return parser.parse_args()

args = argument()

import numpy as np
from bitsea.commons.layer import Layer
from bitsea.basins import V2 as OGS
from netCDF4 import Dataset
from bitsea.static.climatology import DatasetInfo, QualityCheck, get_climatology
from bitsea.commons.time_interval import TimeInterval
import matplotlib.pylab as plt
from bitsea.commons.mask import Mask
import os
from bitsea.commons.utils import addsep

INDIR = addsep(args.indir)
OUTDIR = addsep(args.outdir)
OUTDIR = OUTDIR + '/' + args.variable
VAR = args.variable

UNITS = {"O2o": r"$mmol\,m^{-3}$", "N3n": r"$mmol\,m^{-3}$", "P_l": r"$mg\,m^{-3}$", "vosaline": "PSU", "votemper": r"$^\circ C$", "PAR": r"$\mu E\,m^{-2}\,s^{-1}$", "pH": "-"}
_units = UNITS.get(VAR, VAR)

meshmask = os.environ["MASKFILE"]
TheMask = Mask.from_file(meshmask)
z_lev = TheMask.zlevels
PresDOWN = np.array([0,25,50,75,100,125,150,200,400,600,800])
LayerList = [Layer(PresDOWN[k], PresDOWN[k+1]) for k in range(len(PresDOWN)-1)]
LayerDepth = [.5*(ll.bottom+ll.top) for ll in LayerList]
z_interp = np.arange(0,200,10)
z_interp = np.append(z_interp, np.arange(200,801,40))

SUBLIST = []
for sub in OGS.Pred.basin_list:
    if 'atl' in sub.name:
        continue
    SUBLIST.append(sub)
DATESTART = '20130101'
DATEEND = '20261231'
HAS_INSITU_CLIMATOLOGY = VAR not in {"votemper", "vosaline", "PAR", "POC", "CDOM", "Ed_490"}
EMODNET_TI = TimeInterval(DATESTART, DATEEND, "%Y%m%d")
if HAS_INSITU_CLIMATOLOGY:
    _emodnet = get_climatology(VAR, SUBLIST, LayerList, basin_expand=False, QC=True)
os.makedirs(OUTDIR, exist_ok=True)

import matplotlib.cm as cm
colors_blue = cm.Blues(np.linspace(0.4, 0.9, 5))
colors_gray = cm.Greys(np.linspace(0.4, 0.8, 5))
colors_red = cm.Reds(np.linspace(0.4, 0.9, 4))

# ============================================================
# READ SUPERFLOAT YEARLY CLIMATOLOGY
# ============================================================
ncs_avg = Dataset(INDIR + '/yr_Avg_' + VAR + '_superfloat.nc')
years = ncs_avg.variables["year"][:]
sub_names = ncs_avg.variables["sub"][:]
z_lev = ncs_avg.variables["nav_lev"][:]
vs_avg = ncs_avg.variables[VAR][:]
nprofiles = ncs_avg.variables["NPROFILES"][:]
nwmo = ncs_avg.variables["NWMO"][:]
print('Years:', years)
print('Number of years:', len(years))
print('Number of sub-basins:', len(sub_names))
print('Number of depth levels:', len(z_lev))

# ============================================================
# EMODNET METADATA
# ============================================================
def get_emodnet_metadata(var, subbasins, layers):
    if not HAS_INSITU_CLIMATOLOGY:
        return [(None, None, None) for _ in subbasins]
    static_var, static_dataset = DatasetInfo(var)
    metadata = []
    for sub in subbasins:
        if not QualityCheck(var, sub):
            metadata.append((None, None, None))
            continue
        profile_list = static_dataset.Selector(static_var, EMODNET_TI, sub)
        profile_list = [profile for profile in profile_list if EMODNET_TI.contains(profile.time)]
        profile_dates = [profile.time for profile in profile_list]
        nobs = 0
        for profile in profile_list:
            pres, _, _ = profile.read(static_var)
            nobs += sum(((pres >= layer.top) & (pres < layer.bottom)).sum() for layer in layers)
        period = None
        if profile_dates:
            period = f"{min(profile_dates).year}-{max(profile_dates).year}"
        metadata.append((len(profile_list), nobs, period))
    return metadata
emodnet_metadata = get_emodnet_metadata(VAR, SUBLIST, LayerList)
# ============================================================
# PLOT
# ============================================================
periods = {'2013-2015': [2013, 2014, 2015], '2018-2019': [2018, 2019], '2024-2025': [2024, 2025]}
period_colors = {'2013-2015': colors_blue[2], '2018-2019': colors_gray[2], '2024-2025': colors_red[1]}

for isub, sub in enumerate(SUBLIST):
    print('Processing:', sub.name)
    fig, ax = plt.subplots(1, 1, figsize=[7, 15])
    # --------------------------------------------------------
    # SUPERFLOAT YEARLY PROFILES
    # --------------------------------------------------------
    valid_years = 0
    for iyear, year in enumerate(years):
        profile = vs_avg[iyear, isub, :]
        nprof = int(nprofiles[iyear, isub])
        if nprof == 0:
            continue
        if np.all(np.isnan(profile)):
            continue

        if 2013 <= year <= 2017:
            color = colors_blue[year - 2013]
        elif 2018 <= year <= 2022:
            color = colors_gray[year - 2018]
        elif 2023 <= year <= 2026:
            color = colors_red[year - 2023]
        else:
            color = 'black'
 
        ax.plot(profile, z_lev, color=color, linewidth=2, label=f'Superfloat {year} ({nprof})')
        valid_years += 1
    # --------------------------------------------------------
    # EMODNET CLIMATOLOGY
    # --------------------------------------------------------
    if HAS_INSITU_CLIMATOLOGY:
        emodnet_mean = _emodnet[0][isub, :]
        emodnet_std = _emodnet[1][isub, :]
        emodnet_nprofiles, emodnet_nobs, emodnet_period = emodnet_metadata[isub]
        ax.plot(emodnet_mean, LayerDepth, 'ko', linewidth=2, markersize=6, label=f'EMODNET: {emodnet_period}')
        ax.plot(emodnet_mean + emodnet_std, LayerDepth, 'k--', linewidth=1.5)
        ax.plot(emodnet_mean - emodnet_std, LayerDepth, 'k--', linewidth=1.5)
        ax.fill_betweenx(LayerDepth, emodnet_mean - emodnet_std, emodnet_mean + emodnet_std, color='gray', alpha=0.15)
    # --------------------------------------------------------
    # FIGURE SETTINGS
    # --------------------------------------------------------
    ax.grid()
    ax.tick_params(axis='both', labelsize=20)
    ax.set_ylim(801, 0)
    ax.set_title(f'{sub.name}\nSuperfloat: {valid_years} years', fontsize=20)
    ax.legend(fontsize=12)
    ax.set_xlabel(_units, fontsize=20)
    ax.set_ylabel('Depth (m)', fontsize=20)
    plt.subplots_adjust(top=0.95, bottom=0.05)
    outfile = OUTDIR + '/' + sub.name + '_' + VAR + '_yearly_clim_superfloat.png'
    print('Saving:', outfile)
    plt.savefig(outfile, bbox_inches='tight', pad_inches=0.05)
    plt.close()

    # ========================================================
    # FIGURE 2: PERIOD AVERAGES + EMODNET
    # ========================================================
    fig, ax = plt.subplots(1, 1, figsize=[7, 15])

    for period_name, period_years in periods.items():
        idx = np.isin(years, period_years)
        profiles_period = vs_avg[idx, isub, :]
        nprof_period = nprofiles[idx, isub]

        valid = nprof_period > 0
        if not np.any(valid):
            continue

        profile = np.nanmean(profiles_period[valid, :], axis=0)
        nprof_total = int(np.sum(nprof_period[valid]))

        if np.all(np.isnan(profile)):
            continue

        ax.plot(profile, z_lev, color=period_colors[period_name], linewidth=3, label=f'Superfloat {period_name} (N={nprof_total})')

    if HAS_INSITU_CLIMATOLOGY:
        ax.plot(emodnet_mean, LayerDepth, 'ko', linewidth=2, markersize=6, label=f'EMODNET: {emodnet_period}')
        ax.plot(emodnet_mean + emodnet_std, LayerDepth, 'k--', linewidth=1.5)
        ax.plot(emodnet_mean - emodnet_std, LayerDepth, 'k--', linewidth=1.5)
        ax.fill_betweenx(LayerDepth, emodnet_mean - emodnet_std, emodnet_mean + emodnet_std, color='gray', alpha=0.15)

    ax.grid()
    ax.tick_params(axis='both', labelsize=20)
    ax.set_ylim(801, 0)
    ax.set_title(f'{sub.name}\nSuperfloat period averages', fontsize=20)
    ax.legend(fontsize=12)
    ax.set_xlabel(_units, fontsize=20)
    ax.set_ylabel('Depth (m)', fontsize=20)
    plt.subplots_adjust(top=0.95, bottom=0.05)

    outfile = OUTDIR + '/' + sub.name + '_' + VAR + '_period_clim_superfloat.png'
    print('Saving:', outfile)
    plt.savefig(outfile, bbox_inches='tight', pad_inches=0.05)
    plt.close()

# ============================================================
# CLOSE NETCDF
# ============================================================
ncs_avg.close()
