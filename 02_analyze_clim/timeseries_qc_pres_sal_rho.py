#!/usr/bin/env python3
import argparse
import os
import sys

import gsw
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from bitsea.basins import V2 as OGS
from bitsea.basins.region import Rectangle
from bitsea.basins.basin import ComposedBasin
from bitsea.commons import timerequestors
from bitsea.commons.mask import Mask
from bitsea.instruments import superfloat
from bitsea.instruments.var_conversions import FLOATVARS
sys.path.append(os.path.abspath(".."))
from utils.basins_CA_new_bitsea import cross_Med_basins


def argument():
    parser = argparse.ArgumentParser(
        description='Create timeseries CSV/plots with O2 at 600m, rho-based and max-salinity points.',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        '--outdir', '-o',
        required=True,
        help='Directory for CSV and PNG outputs.'
    )
    parser.add_argument(
        '--variable', '-v',
        default='O2o',
        help='Float variable name (default: O2o).'
    )
    return parser.parse_args()

args = argument()

OUTDIR = args.outdir
os.makedirs(OUTDIR, exist_ok=True)

MASKFILE = (
    "/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/"
    "Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc"
)
TheMask = Mask.from_file(MASKFILE)

if OGS.atl in OGS.Pred.basin_list:
    OGS.Pred.basin_list.remove(OGS.atl)

SUBS = OGS.Pred.basin_list[:]
TI = timerequestors.TimeInterval(
    starttime='19500101',
    endtime='20280101',
    dateformat='%Y%m%d',
)
COLUMNS = [
    'wmo', 'Cycle', 'DRIFT_CODE', 'offset', 'time',
    'value_at600m', 'value_at_rho_gsw', 'depth_at_rho_gsw',
    'value_at_maxsal', 'depth_at_maxsal',
    'value_at_maxsal_liw_50m', 'depth_at_maxsal_liw_50m'
]

LIW_DEPTH_300_1000M = True

def get_density_600m(NAME_BASIN):
    df = pd.read_csv(
        "/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/02_analyze_clim/density_600m.csv",
        index_col=0,
    )
    dfstd = pd.read_csv(
        "/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/02_analyze_clim/density_std_600m.csv",
        index_col=0,
    )
    try:
        val = df.loc[NAME_BASIN].values[0]
        std = dfstd.loc[NAME_BASIN].values[0]
        return val, std
    except KeyError:
        print(f"Colonna '{NAME_BASIN}' non trovata")
        return np.nan, np.nan

def read_temp_psal(p):
    PresT, Temp, QcT = p.read('TEMP')
    Pres, Sali, QcS = p.read('PSAL')
    if (Pres is None or PresT is None or Temp is None or Sali is None
            or len(Pres) < 5 or len(PresT) < 5):
        PresT, Temp, QcT = p.read('TEMP', read_adjusted=False)
        Pres, Sali, QcS = p.read('PSAL', read_adjusted=False)
    return PresT, Temp, QcT, Pres, Sali, QcS

def convert_oxygen(p, doxypres, doxyprofile):
    if doxypres.size == 0:
        return doxyprofile
    PresT, temp, _, Pres, sali, _ = read_temp_psal(p)
    if len(temp) != len(sali):
        temp = np.interp(Pres, PresT, temp)
    SA = gsw.SA_from_SP(sali, Pres, p.lon, p.lat)
    density = gsw.rho(SA, gsw.CT_from_t(SA, temp, Pres), Pres)
    density_on_zdoxy = np.interp(doxypres, Pres, density)
    return doxyprofile * density_on_zdoxy / 1000.0

def get_rho_layer(mask_rho, profile, pres, density_interp, rho_600m_per_sub, lat):
    if np.any(mask_rho):
        value_rho = profile[mask_rho].mean()
        pres_rho = pres[mask_rho].mean()
    else:
        idx = np.argmin(np.abs(density_interp - rho_600m_per_sub))
        if np.abs(density_interp[idx] - rho_600m_per_sub) <= 0.1:
            idx_sort = np.argsort(density_interp)
            rho_sorted = density_interp[idx_sort]
            pres_sorted = pres[idx_sort]
            prof_sorted = profile[idx_sort]
            value_rho = np.interp(rho_600m_per_sub, rho_sorted, prof_sorted)
            pres_rho = np.interp(rho_600m_per_sub, rho_sorted, pres_sorted)
        else:
            return np.nan, np.nan
    depth_rho = -gsw.z_from_p(pres_rho, lat)
    return value_rho, depth_rho

def get_maxsal_layer(p, profile, pres, pres_sali, sali, liw_depth_300_1000m=False):
    value_at_maxsal = np.nan
    depth_at_maxsal = np.nan
    value_at_maxsal_liw_50m = np.nan
    depth_at_maxsal_liw_50m = np.nan
    if len(sali) > 0 and np.any(np.isfinite(sali)):
        if liw_depth_300_1000m:
            mask_depth = (
                (pres_sali >= 300.0) &
                (pres_sali <= 1000.0) &
                np.isfinite(sali)
            )
            if not np.any(mask_depth):
                return (
                    np.nan, np.nan,
                    np.nan, np.nan,
                )
            sali_sel = sali[mask_depth]
            pres_sali_sel = pres_sali[mask_depth]
            idx_max = np.nanargmax(sali_sel)
            maxsal_pres = pres_sali_sel[idx_max]
        else:
            idx_max = np.nanargmax(sali)
            maxsal_pres = pres_sali[idx_max]
        depth_at_maxsal = -gsw.z_from_p(maxsal_pres, p.lat)
        if len(pres) > 0 and len(profile) > 0:
            value_at_maxsal = np.interp(maxsal_pres, pres, profile, left=np.nan, right=np.nan)
            target_pres = maxsal_pres + 50.0
            depth_at_maxsal_liw_50m = -gsw.z_from_p(target_pres, p.lat)
            value_at_maxsal_liw_50m = np.interp(target_pres, pres, profile, left=np.nan, right=np.nan)
    return (
        value_at_maxsal, depth_at_maxsal,
        value_at_maxsal_liw_50m, depth_at_maxsal_liw_50m,
    )

def collect_data_from_profiles(Profilelist, DOXY_convert=False):
    rows = []
    for p in Profilelist:
        pres, profile, qc = p.read(FLOATVARS[args.variable])
        if DOXY_convert:
            profile = convert_oxygen(p, pres, profile)

        if len(profile) < 5 or len(pres) < 5 or pres.max() < 600:
            continue

        with xr.open_dataset(p._my_float.filename) as ds:
            doxy_qc = ds.get("DOXY_QC")
            offset = np.nan
            drift_code = np.nan
            if doxy_qc is not None:
                offset = doxy_qc.attrs.get("offset", np.nan)
                drift_code = doxy_qc.attrs.get("drift_code", np.nan)

        mask = (pres >= 550) & (pres <= 650)
        value_at600m = profile[mask].mean() if np.any(mask) else np.nan

        PresT, temp, _, Pres, sali, _ = read_temp_psal(p)
        pos = Rectangle(np.float64(p.lon), np.float64(p.lon), np.float64(p.lat), np.float64(p.lat))
        NAME_BASIN, BORDER_BASIN = cross_Med_basins(pos)
        rho_600m_per_sub, stdev = get_density_600m(NAME_BASIN)
        stdev = stdev * 2.0

        value_rho_gsw = np.nan
        depth_at_rho_gsw = np.nan
        if (len(temp) > 0 and len(sali) > 0 and len(PresT) > 0 and len(Pres) > 0
                and not np.isnan(p.lat) and not np.isnan(p.lon)):
            if len(Pres) != len(PresT):
                sali = np.interp(PresT, Pres, sali)
            sa = gsw.SA_from_SP(sali, PresT, p.lon, p.lat)
            ct = gsw.CT_from_t(sa, temp, PresT)
            rho_gsw = gsw.rho(sa, ct, PresT)
            density_interp = np.interp(pres, PresT, rho_gsw)
            mask_rho = ((density_interp >= rho_600m_per_sub - stdev)
                        & (density_interp <= rho_600m_per_sub + stdev))
            value_rho_gsw, depth_at_rho_gsw = get_rho_layer(
                mask_rho, profile, pres, density_interp, rho_600m_per_sub, p.lat
            )

        value_at_maxsal, depth_at_maxsal, value_at_maxsal_liw_50m, depth_at_maxsal_liw_50m = get_maxsal_layer(
            p, profile, pres, Pres, sali, LIW_DEPTH_300_1000M
        )

        rows.append({
            'wmo': p._my_float.wmo,
            'Cycle': p._my_float.cycle,
            'DRIFT_CODE': drift_code,
            'offset': offset,
            'time': p.time.strftime('%Y%m%d'),
            'value_at600m': value_at600m,
            'value_at_rho_gsw': value_rho_gsw,
            'depth_at_rho_gsw': depth_at_rho_gsw,
            'value_at_maxsal': value_at_maxsal,
            'depth_at_maxsal': depth_at_maxsal,
            'value_at_maxsal_liw_50m': value_at_maxsal_liw_50m,
            'depth_at_maxsal_liw_50m': depth_at_maxsal_liw_50m,
        })

    df_local = pd.DataFrame(rows, columns=COLUMNS)
    if not df_local.empty:
        df_local['time'] = pd.to_datetime(df_local['time'], format='%Y%m%d')
    return df_local

for ISUB in SUBS:
    print(ISUB.name)
    _super_Profilelist = superfloat.FloatSelector(FLOATVARS[args.variable], TI, ISUB)
    df_super = collect_data_from_profiles(_super_Profilelist, DOXY_convert=False)

    if df_super.empty:
        print(f"Skipping {ISUB.name}: df_super.empty={df_super.empty}")
        continue

    df_super = df_super.sort_values('time')
    df_super.to_csv(os.path.join(OUTDIR, f'{ISUB.name}_superfloat_oxy_at600m.csv'), index=False)

    fig, axs = plt.subplots(1, 2, figsize=(16, 6), sharex=True)

    ax_left = axs[0]
    shallow_600 = (df_super['depth_at_maxsal_liw_50m'] > 600.0).fillna(False)
    rho_shallow = (df_super['depth_at_rho_gsw'] < df_super['depth_at_maxsal_liw_50m']).fillna(False)

    ax_left.plot(
        df_super['time'][~shallow_600], df_super['value_at600m'][~shallow_600],
        linestyle='None', marker='o', markersize=8,
        markerfacecolor='dodgerblue', markeredgecolor='black',
        alpha=0.5, label='value_at600m'
    )
    ax_left.plot(
        df_super['time'][shallow_600], df_super['value_at600m'][shallow_600],
        linestyle='None', marker='o', markersize=8,
        markerfacecolor='black', markeredgecolor='black',
        alpha=0.9, label='value_at600m (< maxsal_liw_50m)'
    )

    ax_left.plot(
        df_super['time'][~rho_shallow], df_super['value_at_rho_gsw'][~rho_shallow],
        linestyle='None', marker='o', markersize=6,
        markerfacecolor='gray', markeredgecolor='black',
        alpha=0.9, label='value_at_rho_gsw'
    )
    ax_left.plot(
        df_super['time'][rho_shallow], df_super['value_at_rho_gsw'][rho_shallow],
        linestyle='None', marker='o', markersize=6,
        markerfacecolor='black', markeredgecolor='black',
        alpha=0.9, label='value_at_rho_gsw (< maxsal_liw_50m)'
    )

    ax_left.plot(
        df_super['time'], df_super['value_at_maxsal'],
        linestyle='None', marker='D', markersize=6,
        markerfacecolor='#fff0f5', markeredgecolor='black',
        alpha=0.7, label='value_at_maxsal'
    )
    ax_left.plot(
        df_super['time'], df_super['value_at_maxsal_liw_50m'],
        linestyle='None', marker='D', markersize=6,
        markerfacecolor='magenta', markeredgecolor='black',
        alpha=0.9, label='maxsal_liw_50m'
    )
    ax_left.set_title(f'{ISUB.name} Superfloat')
    ax_left.set_ylabel('Oxygen')
    ax_left.grid(True)
    ax_left.legend(loc='best')

    ax_right = axs[1]
    ax_right.plot(
        df_super['time'],
        np.full(df_super['time'].shape, 600.0),
        color='black', linestyle='--', linewidth=1.5,
        label='depth reference 600 m'
    )
    ax_right.plot(
        df_super['time'], df_super['depth_at_rho_gsw'],
        color='goldenrod', linestyle='--', linewidth=1.8,
        label='depth_at_rho_gsw'
    )
    ax_right.plot(
        df_super['time'], df_super['depth_at_maxsal'],
        color='darkred', linestyle='-.', linewidth=1.8,
        label='depth_at_maxsal'
    )
    ax_right.plot(
        df_super['time'], df_super['depth_at_maxsal_liw_50m'],
        color='purple', linestyle=':', linewidth=1.8,
        label='depth_at_maxsal_liw_50m'
    )
    ax_right.set_xlabel('Time')
    ax_right.set_ylabel('Depth (m)')
    ax_right.invert_yaxis()
    ax_right.grid(True)
    ax_right.tick_params(axis='x', rotation=45)

    lines_left, labels_left = ax_left.get_legend_handles_labels()
    lines_right, labels_right = ax_right.get_legend_handles_labels()
    ax_left.legend(lines_left, labels_left, loc='best')
    ax_right.legend(lines_right, labels_right, loc='best')

    fig.tight_layout()
    fig.savefig(os.path.join(OUTDIR, f'{ISUB.name}_superfloat.png'))
    plt.close(fig)
