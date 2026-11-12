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
from bitsea.commons.season import season
from bitsea.commons import timerequestors
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
    if int(year_min) == 0:
        return "no data"
    return f"{int(year_min):04d}-{int(month_min):02d} to {int(year_max):04d}-{int(month_max):02d}"


seasonObj = season(BGC=True)
SEASONS = [(i, seasonObj.get_season_dates(i)[1]) for i in range(seasonObj.get_seasons_number())]

HAS_INSITU_CLIMATOLOGY = "IN SITU" in DATASETS_TO_PLOT
_emodnet = {}
emodnet_metadata = {}


def get_emodnet_metadata(var, subbasins, layers, season_req):
    if not HAS_INSITU_CLIMATOLOGY: return [(None, None, None) for _ in subbasins]
    static_var, static_dataset = DatasetInfo(var)
    metadata = []

    for sub in subbasins:
        if not QualityCheck(var, sub):
            metadata.append((None, None, None))
            continue

        profile_list = static_dataset.Selector(static_var, STATIC_TI, sub)
        profile_list = [profile for profile in profile_list if STATIC_TI.contains(profile.time) and season_req.contains(profile.time)]
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
    for iseas, seasname in SEASONS:
        _emodnet[seasname] = get_climatology(VAR, SUBLIST, LayerList, basin_expand=True, QC=True, climseason=iseas)
        emodnet_metadata[seasname] = get_emodnet_metadata(VAR, SUBLIST, LayerList, timerequestors.Clim_season(iseas, seasonObj))


# Per POC esistono due climatologie (conversione bbp700->POC di Bellacicco e di Gali')
POC_VARIANTS = [("POC_bellacicco", "Bellacicco"), ("POC_gali", "Gali")]
VARIANTS = POC_VARIANTS if VAR == "POC" else [(VAR, None)]


def load_clim(subdir, source, filevar, seasname):
    ncavg = Dataset(INDIR + '/' + subdir + '/' + seasname + '_Avg_' + filevar + '_' + source + '.nc')
    ncstd = Dataset(INDIR + '/' + subdir + '/' + seasname + '_Std_' + filevar + '_' + source + '.nc')
    return {
        "avg": ncavg.variables[filevar][:],
        "std": ncstd.variables[filevar][:],
        "nprofiles": ncavg.variables["NPROFILES"][:],
        "nwmo": ncavg.variables["NWMO"][:],
        "year_min": ncavg.variables["YEAR_MIN"][:],
        "month_min": ncavg.variables["MONTH_MIN"][:],
        "year_max": ncavg.variables["YEAR_MAX"][:],
        "month_max": ncavg.variables["MONTH_MAX"][:],
    }


# {tag: {season: data}}, tag e' None se la variabile non ha varianti
superfloat_data = {}
if "BGC-ARGO" in DATASETS_TO_PLOT:
    for filevar, tag in VARIANTS:
        superfloat_data[tag] = {seasname: load_clim('SUPERFLOAT', 'superfloat', filevar, seasname) for _, seasname in SEASONS}


ppcon_data = {}
if "PPCON" in DATASETS_TO_PLOT:
    for filevar, tag in VARIANTS:
        ppcon_data[tag] = {seasname: load_clim('PPCON', 'ppcon', filevar, seasname) for _, seasname in SEASONS}


canyon_data = {}
if "CANYON" in DATASETS_TO_PLOT:
    canyon_data = {seasname: load_clim('CANYONMED', 'canyonmed', VAR, seasname) for _, seasname in SEASONS}


COLORS = {
    "SUPERFLOAT": "tab:red",
    "IN SITU": "tab:blue",
    "PPCON": "tab:green",
    "CANYON": "tab:purple",
    "SAT": "tab:brown",
}

summary_rows = []
rows_600m = []

plot_depth_limit = 200 if VAR == "P_l" else 801
plot_depth_mask = z_lev <= plot_depth_limit
layer_depth_plot = np.asarray(LayerDepth, dtype=float)
layer_depth_mask = layer_depth_plot <= plot_depth_limit


LINESTYLES = {None: '-', "Bellacicco": ':', "Gali": '-'}


def label_suffix(tag):
    return '' if tag is None else f' ({tag})'


def column_prefix(name, tag):
    return name if tag is None else f'{name}_{tag.upper()}'


for isub, sub in enumerate(SUBLIST):
    print(sub)
    fig, axes = plt.subplots(1, len(SEASONS), figsize=[7 * len(SEASONS), 15], sharey=True)
    periods = {}

    for ax, (iseas, seasname) in zip(axes, SEASONS):
        for tag, by_season in superfloat_data.items():
            data = by_season[seasname]
            periods[("SUPERFLOAT", tag, seasname)] = format_period(data["year_min"][isub], data["month_min"][isub], data["year_max"][isub], data["month_max"][isub])
            ax.plot(data["avg"][isub, plot_depth_mask], z_lev[plot_depth_mask], color=COLORS["SUPERFLOAT"], linewidth=3, linestyle=LINESTYLES[tag], label=f'Superfloat{label_suffix(tag)}: {periods[("SUPERFLOAT", tag, seasname)]}')

        if HAS_INSITU_CLIMATOLOGY:
            emodnet_mean = _emodnet[seasname][0][isub, layer_depth_mask]
            emodnet_std = _emodnet[seasname][1][isub, layer_depth_mask]
            emodnet_depths = layer_depth_plot[layer_depth_mask]
            emodnet_nprofiles, emodnet_nobs, emodnet_period = emodnet_metadata[seasname][isub]
            periods[("EMODNET", None, seasname)] = emodnet_period
            ax.plot(emodnet_mean, emodnet_depths, 'ko', markersize=6, label=f'EMODnet: {emodnet_period}')
            ax.plot(emodnet_mean + emodnet_std, emodnet_depths, 'k--', linewidth=1.5)
            ax.plot(emodnet_mean - emodnet_std, emodnet_depths, 'k--', linewidth=1.5)
            ax.fill_betweenx(emodnet_depths, emodnet_mean - emodnet_std, emodnet_mean + emodnet_std, color='gray', alpha=0.15)

        for tag, by_season in ppcon_data.items():
            data = by_season[seasname]
            periods[("PPCON", tag, seasname)] = format_period(data["year_min"][isub], data["month_min"][isub], data["year_max"][isub], data["month_max"][isub])
            ax.plot(data["avg"][isub, plot_depth_mask], z_lev[plot_depth_mask], color=COLORS["PPCON"], linewidth=3, linestyle=LINESTYLES[tag], label=f'PPCON{label_suffix(tag)}: {periods[("PPCON", tag, seasname)]}')

        if canyon_data:
            data = canyon_data[seasname]
            periods[("CANYON", None, seasname)] = format_period(data["year_min"][isub], data["month_min"][isub], data["year_max"][isub], data["month_max"][isub])
            ax.plot(data["avg"][isub, plot_depth_mask], z_lev[plot_depth_mask], color=COLORS["CANYON"], linewidth=3, label=f'CANYON: {periods[("CANYON", None, seasname)]}')

        ax.grid()
        ax.tick_params(axis='both', labelsize=18)
        ax.set_ylim(plot_depth_limit, 0)
        ax.set_title(f"{seasname}", fontsize=20)
        ax.legend(fontsize=11)
        ax.set_xlabel(_units, fontsize=18)

    axes[0].set_ylabel("Depth (m)", fontsize=18)
    fig.suptitle(f"{sub.name}", fontsize=24)
    fig.savefig(OUTDIR + '/' + sub.name + '_' + VAR + '_climatologies.png', bbox_inches='tight')
    plt.close(fig)

    if VAR in {"O2o", "N3n"} and superfloat_data:
        row600 = {"BASIN": sub.name}
        for _, seasname in SEASONS:
            profile = np.asarray(superfloat_data[None][seasname]["avg"][isub, :], dtype=float)
            depth = np.asarray(z_lev, dtype=float)
            valid = np.isfinite(profile) & np.isfinite(depth)
            if valid.sum() >= 2: value_600m = np.interp(600.0, depth[valid], profile[valid])
            elif valid.sum() == 1: value_600m = profile[valid][0]
            else: value_600m = np.nan
            row600[seasname] = value_600m
        rows_600m.append(row600)

    row = {"BASIN": sub.name}

    for _, seasname in SEASONS:
        if HAS_INSITU_CLIMATOLOGY:
            emodnet_nprofiles, emodnet_nobs, emodnet_period = emodnet_metadata[seasname][isub]
            row.update({f"EMODNET_{seasname}_NPROFILES": emodnet_nprofiles, f"EMODNET_{seasname}_NOBS": emodnet_nobs, f"EMODNET_{seasname}_DATARANGE": emodnet_period})

        for tag, by_season in superfloat_data.items():
            data = by_season[seasname]
            col = column_prefix("SUPERFLOAT", tag) + f"_{seasname}"
            row.update({col + "_NPROFILES": int(data["nprofiles"][isub]), col + "_NWMO": int(data["nwmo"][isub]), col + "_DATARANGE": periods[("SUPERFLOAT", tag, seasname)]})

        for tag, by_season in ppcon_data.items():
            data = by_season[seasname]
            col = column_prefix("PPCON", tag) + f"_{seasname}"
            row.update({col + "_NPROFILES": int(data["nprofiles"][isub]), col + "_NWMO": int(data["nwmo"][isub]), col + "_DATARANGE": periods[("PPCON", tag, seasname)]})

        if canyon_data:
            data = canyon_data[seasname]
            row.update({f"CANYON_{seasname}_NPROFILES": int(data["nprofiles"][isub]), f"CANYON_{seasname}_NWMO": int(data["nwmo"][isub]), f"CANYON_{seasname}_DATARANGE": periods[("CANYON", None, seasname)]})
    summary_rows.append(row)

pd.DataFrame(summary_rows).to_csv(OUTDIR + "/climatology_sample_summary.csv", index=False)

if rows_600m:
    pd.DataFrame(rows_600m).to_csv(OUTDIR + f"/{VAR}_600m_by_basin.csv", index=False)

try:
    shutil.copy(__file__, OUTDIR)
except NameError:
    pass

