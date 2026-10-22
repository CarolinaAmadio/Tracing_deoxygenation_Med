import argparse
import os
import shutil
import numpy as np
import pandas as pd
import matplotlib.pylab as plt
from netCDF4 import Dataset
from bitsea.commons.layer import Layer
from bitsea.basins import V2 as OGS
from bitsea.static.climatology import DatasetInfo, QualityCheck, TI as STATIC_TI, get_climatology
from bitsea.commons.mask import Mask
from bitsea.commons.utils import addsep


def argument():
    parser = argparse.ArgumentParser(description='Compares the available climatologies for a given variable and plots their vertical profiles by basin.', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--indir', '-i', type=str, required=True, help='netcdf input directory')
    parser.add_argument('--outdir', '-o', type=str, required=True, help='output directory for png')
    parser.add_argument('--variable', '-v', type=str, required=True, help='model variable')
    return parser.parse_args()


args = argument()
INDIR = addsep(args.indir)
OUTDIR = addsep(args.outdir)
VAR = args.variable
OUTDIR = OUTDIR + '/' + VAR
os.makedirs(OUTDIR, exist_ok=True)


UNITS = {
    "O2o": r"$mmol\,m^{-3}$",
    "N3n": r"$mmol\,m^{-3}$",
    "P_l": r"$mg\,m^{-3}$",
    "vosaline": "PSU",
    "votemper": r"$^\circ C$",
    "PAR": r"$\mu E\,m^{-2}\,s^{-1}$",
    "POC": r"$mg\,m^{-3}$",
    "pH": "-",
    "N1p": r"$mmol\,m^{-3}$",
    "N5s": r"$mmol\,m^{-3}$",
    "DIC": r"$\mu mol\,kg^{-1}$",
    "ALK": r"$\mu mol\,kg^{-1}$",
}
_units = UNITS.get(VAR, VAR)


FLOATVARS = {
    'O2o': 'DOXY',
    'N3n': 'NITRATE',
    'P_l': 'CHLA',
    'vosaline': 'PSAL',
    'votemper': 'TEMP',
    'PAR': 'DOWNWELLING_PAR',
    'POC': 'BBP700',
    'pH': 'PH_IN_SITU_TOTAL',
}

PPCONVAR = {
    'N3n': 'NITRATE',
    'P_l': 'CHLA',
    'POC': 'BBP700',
}

CANYONVAR = {
    'O2o': 'DOXY',
    'P_l': 'CHLA',
    'N3n': 'NITRATE',
    'N1p': 'PO4',
    'DIC': 'DIC',
    'N5s': 'SiOH4',
    'ALK': 'AT',
    'pH': 'PH_IN_SITU_TOTAL',
}


AVAILABLE_DATASETS = {
    "votemper": ["BGC-ARGO"],
    "vosaline": ["BGC-ARGO"],
    "POC": ["BGC-ARGO", "PPCON"],
    "P_l": ["SAT", "BGC-ARGO", "IN SITU", "PPCON"],
    "O2o": ["BGC-ARGO", "IN SITU"],
    "Ed_490": ["BGC-ARGO"],
    "PAR": ["BGC-ARGO"],
    "N3n": ["BGC-ARGO", "IN SITU", "PPCON", "CANYON"],
    "N1p": ["IN SITU", "CANYON"],
    "NH4": ["IN SITU"],
    "CDOM": [],
    "pH": ["IN SITU", "CANYON"],
    "N5s": ["IN SITU", "CANYON"],
    "ALK": ["IN SITU", "CANYON"],
    "DIC": ["IN SITU", "CANYON"],
    "pCO2": ["IN SITU"],
}


if VAR not in AVAILABLE_DATASETS:
    raise ValueError(f"Variable '{VAR}' not recognized. Available variables: {', '.join(AVAILABLE_DATASETS.keys())}")

DATASETS_TO_PLOT = AVAILABLE_DATASETS[VAR]
print(f"\nVariable: {VAR}")
print(f"Available climatologies: {DATASETS_TO_PLOT}\n")


meshmask = os.environ["MASKFILE"]
TheMask = Mask.from_file(meshmask)
z_lev = TheMask.zlevels

PresDOWN = np.array([0, 25, 50, 75, 100, 125, 150, 200, 400, 600, 800])
LayerList = [Layer(PresDOWN[k], PresDOWN[k + 1]) for k in range(len(PresDOWN) - 1)]
LayerDepth = [.5 * (ll.bottom + ll.top) for ll in LayerList]


SUBLIST = []
for sub in OGS.Pred.basin_list:
    if 'atl' in sub.name: continue
    SUBLIST.append(sub)


def format_period(year_min, month_min, year_max, month_max):
    return f"{int(year_min):04d}-{int(month_min):02d} to {int(year_max):04d}-{int(month_max):02d}"


HAS_INSITU_CLIMATOLOGY = "IN SITU" in DATASETS_TO_PLOT
_emodnet = None
emodnet_metadata = [(None, None, None) for _ in SUBLIST]


def get_emodnet_metadata(var, subbasins, layers):
    if not HAS_INSITU_CLIMATOLOGY: return [(None, None, None) for _ in subbasins]
    static_var, static_dataset = DatasetInfo(var)
    metadata = []

    for sub in subbasins:
        if not QualityCheck(var, sub):
            metadata.append((None, None, None))
            continue

        profile_list = static_dataset.Selector(static_var, STATIC_TI, sub)
        profile_list = [profile for profile in profile_list if STATIC_TI.contains(profile.time)]
        profile_dates = [profile.time for profile in profile_list]
        nobs = 0

        for profile in profile_list:
            pres, _, _ = profile.read(static_var)
            for layer in layers:
                nobs += ((pres >= layer.top) & (pres < layer.bottom)).sum()

        period = None
        if profile_dates:
            period = format_period(min(profile_dates).year, min(profile_dates).month, max(profile_dates).year, max(profile_dates).month)

        metadata.append((len(profile_list), nobs, period))

    return metadata


if HAS_INSITU_CLIMATOLOGY:
    _emodnet = get_climatology(VAR, SUBLIST, LayerList, basin_expand=True, QC=True)
    emodnet_metadata = get_emodnet_metadata(VAR, SUBLIST, LayerList)


superfloat_data = None
if "BGC-ARGO" in DATASETS_TO_PLOT:
    ncs_avg = Dataset(INDIR + '/SUPERFLOAT/yr_Avg_' + VAR + '_superfloat.nc')
    ncs_std = Dataset(INDIR + '/SUPERFLOAT/yr_Std_' + VAR + '_superfloat.nc')
    superfloat_data = {
        "avg": ncs_avg.variables[VAR][:],
        "std": ncs_std.variables[VAR][:],
        "nprofiles": ncs_avg.variables["NPROFILES"][:],
        "nwmo": ncs_avg.variables["NWMO"][:],
        "year_min": ncs_avg.variables["YEAR_MIN"][:],
        "month_min": ncs_avg.variables["MONTH_MIN"][:],
        "year_max": ncs_avg.variables["YEAR_MAX"][:],
        "month_max": ncs_avg.variables["MONTH_MAX"][:],
    }


coriolis_data = None
if "BGC-ARGO" in DATASETS_TO_PLOT:
    ncc_avg = Dataset(INDIR + '/CORIOLIS/yr_Avg_' + VAR + '_coriolis.nc')
    ncc_std = Dataset(INDIR + '/CORIOLIS/yr_Std_' + VAR + '_coriolis.nc')
    coriolis_data = {
        "avg": ncc_avg.variables[VAR][:],
        "std": ncc_std.variables[VAR][:],
        "nprofiles": ncc_avg.variables["NPROFILES"][:],
        "nwmo": ncc_avg.variables["NWMO"][:],
        "year_min": ncc_avg.variables["YEAR_MIN"][:],
        "month_min": ncc_avg.variables["MONTH_MIN"][:],
        "year_max": ncc_avg.variables["YEAR_MAX"][:],
        "month_max": ncc_avg.variables["MONTH_MAX"][:],
    }


ppcon_data = None
if "PPCON" in DATASETS_TO_PLOT:
    ppcon_avg_nc = Dataset(INDIR + '/PPCON/yr_Avg_' + VAR + '_ppcon.nc')
    ppcon_std_nc = Dataset(INDIR + '/PPCON/yr_Std_' + VAR + '_ppcon.nc')
    ppcon_data = {
        "avg": ppcon_avg_nc.variables[VAR][:],
        "std": ppcon_std_nc.variables[VAR][:],
        "nprofiles": ppcon_avg_nc.variables["NPROFILES"][:],
        "nwmo": ppcon_avg_nc.variables["NWMO"][:],
        "year_min": ppcon_avg_nc.variables["YEAR_MIN"][:],
        "month_min": ppcon_avg_nc.variables["MONTH_MIN"][:],
        "year_max": ppcon_avg_nc.variables["YEAR_MAX"][:],
        "month_max": ppcon_avg_nc.variables["MONTH_MAX"][:],
    }


canyon_data = None
if "CANYON" in DATASETS_TO_PLOT:
    canyon_avg_nc = Dataset(INDIR + '/CANYONMED/yr_Avg_' + VAR + '_canyonmed.nc')
    canyon_std_nc = Dataset(INDIR + '/CANYONMED/yr_Std_' + VAR + '_canyonmed.nc')
    canyon_data = {
        "avg": canyon_avg_nc.variables[VAR][:],
        "std": canyon_std_nc.variables[VAR][:],
        "nprofiles": canyon_avg_nc.variables["NPROFILES"][:],
        "nwmo": canyon_avg_nc.variables["NWMO"][:],
        "year_min": canyon_avg_nc.variables["YEAR_MIN"][:],
        "month_min": canyon_avg_nc.variables["MONTH_MIN"][:],
        "year_max": canyon_avg_nc.variables["YEAR_MAX"][:],
        "month_max": canyon_avg_nc.variables["MONTH_MAX"][:],
    }


COLORS = {
    "SUPERFLOAT": "tab:red",
    "CORIOLIS": "tab:orange",
    "IN SITU": "tab:blue",
    "PPCON": "tab:green",
    "CANYON": "tab:purple",
    "SAT": "tab:brown",
}


summary_rows = []
values_600m = []
basin_names = []

plot_depth_limit = 200 if VAR == "P_l" else 801
plot_depth_mask = z_lev <= plot_depth_limit
layer_depth_plot = np.asarray(LayerDepth, dtype=float)
layer_depth_mask = layer_depth_plot <= plot_depth_limit


for isub, sub in enumerate(SUBLIST):
    print(sub)
    fig, ax = plt.subplots(1, 1, figsize=[7, 15])

    superfloat_period = None
    if superfloat_data is not None:
        superfloat_period = format_period(superfloat_data["year_min"][isub], superfloat_data["month_min"][isub], superfloat_data["year_max"][isub], superfloat_data["month_max"][isub])
        ax.plot(superfloat_data["avg"][isub, plot_depth_mask], z_lev[plot_depth_mask], color=COLORS["SUPERFLOAT"], linewidth=3, label=f'Superfloat: {superfloat_period}')

    coriolis_period = None
    if coriolis_data is not None:
        coriolis_period = format_period(coriolis_data["year_min"][isub], coriolis_data["month_min"][isub], coriolis_data["year_max"][isub], coriolis_data["month_max"][isub])
        ax.plot(coriolis_data["avg"][isub, plot_depth_mask], z_lev[plot_depth_mask], color=COLORS["CORIOLIS"], linewidth=2, linestyle='--', alpha=0.6, label=f'Coriolis: {coriolis_period}')

    emodnet_nprofiles, emodnet_nobs, emodnet_period = emodnet_metadata[isub]
    #if HAS_INSITU_CLIMATOLOGY:
    #    ax.plot(_emodnet[0][isub, :], LayerDepth, 'bo', label=f'In situ: {emodnet_period}')
    #    ax.plot(_emodnet[0][isub, :] + _emodnet[1][isub, :], LayerDepth, 'b-.')
    #    ax.plot(_emodnet[0][isub, :] - _emodnet[1][isub, :], LayerDepth, 'b-.')

    if HAS_INSITU_CLIMATOLOGY:
        emodnet_mean = _emodnet[0][isub, layer_depth_mask]
        emodnet_std = _emodnet[1][isub, layer_depth_mask]
        emodnet_depths = layer_depth_plot[layer_depth_mask]
        emodnet_nprofiles, emodnet_nobs, emodnet_period = emodnet_metadata[isub]
        ax.plot(emodnet_mean, emodnet_depths, 'ko', markersize=6, label=f'EMODnet: {emodnet_period}')
        ax.plot(emodnet_mean + emodnet_std, emodnet_depths, 'k--', linewidth=1.5)
        ax.plot(emodnet_mean - emodnet_std, emodnet_depths, 'k--', linewidth=1.5)
        ax.fill_betweenx(emodnet_depths, emodnet_mean - emodnet_std, emodnet_mean + emodnet_std, color='gray', alpha=0.15)


    ppcon_period = None
    if ppcon_data is not None:
        ppcon_period = format_period(ppcon_data["year_min"][isub], ppcon_data["month_min"][isub], ppcon_data["year_max"][isub], ppcon_data["month_max"][isub])
        ax.plot(ppcon_data["avg"][isub, plot_depth_mask], z_lev[plot_depth_mask], color=COLORS["PPCON"], linewidth=3, label=f'PPCON: {ppcon_period}')

    canyon_period = None
    if canyon_data is not None:
        canyon_period = format_period(canyon_data["year_min"][isub], canyon_data["month_min"][isub], canyon_data["year_max"][isub], canyon_data["month_max"][isub])
        ax.plot(canyon_data["avg"][isub, plot_depth_mask], z_lev[plot_depth_mask], color=COLORS["CANYON"], linewidth=3, label=f'CANYON: {canyon_period}')

    ax.grid()
    ax.tick_params(axis='both', labelsize=20)
    ax.set_ylim(plot_depth_limit, 0)
    ax.set_title(f"{sub.name}", fontsize=20)
    ax.legend(fontsize=15)
    ax.set_xlabel(_units, fontsize=20)
    ax.set_ylabel("Depth (m)", fontsize=20)
    ax.figure.savefig(OUTDIR + '/' + sub.name + '_' + VAR + '_climatologies.png', bbox_inches='tight')
    plt.close(fig)

    if VAR in {"O2o", "N3n"} and superfloat_data is not None:
        profile = np.asarray(superfloat_data["avg"][isub, :], dtype=float)
        depth = np.asarray(z_lev, dtype=float)
        valid = np.isfinite(profile) & np.isfinite(depth)
        if valid.sum() >= 2: value_600m = np.interp(600.0, depth[valid], profile[valid])
        elif valid.sum() == 1: value_600m = profile[valid][0]
        else: value_600m = np.nan
        basin_names.append(sub.name)
        values_600m.append(value_600m)

    row = {"BASIN": sub.name}

    if HAS_INSITU_CLIMATOLOGY:
        row.update({"EMODNET_NPROFILES": emodnet_nprofiles, "EMODNET_NOBS": emodnet_nobs, "EMODNET_DATARANGE": emodnet_period})

    if superfloat_data is not None:
        row.update({"SUPERFLOAT_NPROFILES": int(superfloat_data["nprofiles"][isub]), "SUPERFLOAT_NWMO": int(superfloat_data["nwmo"][isub]), "SUPERFLOAT_DATARANGE": superfloat_period})

    if coriolis_data is not None:
        row.update({"CORIOLIS_NPROFILES": int(coriolis_data["nprofiles"][isub]), "CORIOLIS_NWMO": int(coriolis_data["nwmo"][isub]), "CORIOLIS_DATARANGE": coriolis_period})

    if ppcon_data is not None:
        row.update({"PPCON_NPROFILES": int(ppcon_data["nprofiles"][isub]), "PPCON_NWMO": int(ppcon_data["nwmo"][isub]), "PPCON_DATARANGE": ppcon_period})

    if canyon_data is not None:
        row.update({"CANYON_NPROFILES": int(canyon_data["nprofiles"][isub]), "CANYON_NWMO": int(canyon_data["nwmo"][isub]), "CANYON_DATARANGE": canyon_period})

    summary_rows.append(row)


pd.DataFrame(summary_rows).to_csv(OUTDIR + "/climatology_sample_summary.csv", index=False)

if VAR in {"O2o", "N3n"} and basin_names:
    df_600m = pd.DataFrame({"value_600m": values_600m}, index=basin_names)
    df_600m.index.name = "BASIN"
    df_600m.to_csv(OUTDIR + f"/{VAR}_600m_by_basin.csv")


try:
    shutil.copy(__file__, OUTDIR)
except NameError:
    pass

