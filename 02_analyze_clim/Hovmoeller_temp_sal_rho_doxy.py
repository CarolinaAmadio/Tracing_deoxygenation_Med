import argparse
import os
import sys

import cmcrameri as cmc
import gsw
import matplotlib.colors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from bitsea.basins import V2 as OGS
from bitsea.basins.region import Rectangle
from bitsea.commons import timerequestors
from bitsea.instruments import bio_float, superfloat
from bitsea.instruments.var_conversions import FLOATVARS

sys.path.append(os.path.abspath(".."))
from utils.basins_CA_new_bitsea import cross_Med_basins

from bitsea.commons.mask import Mask
TheMask=Mask.from_file("/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc")
z_interp= TheMask.zlevels


def parse_args():
    parser = argparse.ArgumentParser(
        description='Create Hovmoeller plots of temperature, salinity and density from floats.'
    )
    parser.add_argument(
        '--outdir', '-o',
        type=str,
        required=True,
        help='Output directory for plots.'
    )
    parser.add_argument(
        '--dataset', '-d',
        choices=['superfloat', 'coriolis', 'both'],
        default='superfloat',
        help='Float source to plot.'
    )
    parser.add_argument(
        '--basin', '-b',
        type=str,
        default=None,
        help='Optional basin name to restrict the plot.'
    )
    return parser.parse_args()


args = parse_args()

OUTDIR = args.outdir
os.makedirs(OUTDIR, exist_ok=True)

if OGS.atl in OGS.Pred.basin_list:
    OGS.Pred.basin_list.remove(OGS.atl)
SUBS = OGS.Pred.basin_list[:]
if args.basin is not None:
    SUBS = [sub for sub in SUBS if sub.name == args.basin]
    if not SUBS:
        raise ValueError(f"Basin '{args.basin}' not found.")

TI = timerequestors.TimeInterval(
    starttime='19500101',
    endtime='20280101',
    dateformat='%Y%m%d',
)

DEPTHS = z_interp[z_interp <= 1000]

CMAP_TEMP = cmc.cm.lipari
CMAP_SAL  = cmc.cm.lipari
CMAP_RHO  = cmc.cm.lipari
CMAP_OXY  = cmc.cm.navia_r


def get_density_600m(basin_name):
    df     = pd.read_csv('/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/02_analyze_clim/density_600m.csv',     index_col=0)
    dfstd  = pd.read_csv('/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/02_analyze_clim/density_std_600m.csv', index_col=0)
    try:
        val = df.loc[basin_name].values[0]
        std = dfstd.loc[basin_name].values[0]
        return val, std
    except KeyError:
        print(f"Basin '{basin_name}' not found in density CSV")
        return None, None


def read_temp_psal(p):
    pres_t, temp, _ = p.read('TEMP')
    pres_s, sal, _ = p.read('PSAL')
    if (pres_t is None or temp is None or pres_s is None or sal is None
            or len(pres_t) < 5 or len(pres_s) < 5):
        pres_t, temp, _ = p.read('TEMP', read_adjusted=False)
        pres_s, sal, _ = p.read('PSAL', read_adjusted=False)
    return pres_t, temp, pres_s, sal


def convert_oxygen(p, doxypres, doxyprofile):
    '''Convert DOXY from micromol/kg to mmol/m3 (needed for coriolis).'''
    if doxypres is None or doxypres.size == 0:
        return doxyprofile
    pres_t, temp, pres_s, sal = read_temp_psal(p)
    if temp is None or sal is None:
        return doxyprofile
    if len(pres_s) != len(pres_t):
        sal = np.interp(pres_t, pres_s, sal)
    SA = gsw.SA_from_SP(sal, pres_t, p.lon, p.lat)
    density = gsw.rho(SA, gsw.CT_from_t(SA, temp, pres_t), pres_t)
    density_on_zdoxy = np.interp(doxypres, pres_t, density)
    return doxyprofile * density_on_zdoxy / 1000.


def fill_nans_along_time(matrix):
    '''Interpolate NaNs along the time axis (axis=1) for each depth level.'''
    filled = matrix.copy()
    x = np.arange(matrix.shape[1])
    for d in range(matrix.shape[0]):
        row = matrix[d, :]
        finite = np.isfinite(row)
        if finite.sum() >= 2:
            filled[d, :] = np.interp(x, x[finite], row[finite])
    return filled


def make_hovmoeller(profile_list, doxy_convert=False):
    times = []
    temp_mat = []
    sal_mat = []
    rho_mat = []
    oxy_mat = []

    for p in profile_list:
        #if p._my_float.cycle == 337 and p._my_float.wmo=='6903266':
        #import sys
        #sys.exit('carol')
        pres_t, temp_prof, pres_s, sal_prof = read_temp_psal(p)
        if pres_t is None or temp_prof is None or pres_s is None or sal_prof is None:
            continue

        if len(pres_t) < 5 or len(pres_s) < 5:
            continue
        if p.lat is None or p.lon is None or np.isnan(p.lat) or np.isnan(p.lon):
            continue

        if len(pres_s) != len(pres_t) or not np.allclose(pres_s, pres_t):
            sal_prof = np.interp(pres_t, pres_s, sal_prof)

        pres = np.asarray(pres_t, dtype=float)
        temp_prof = np.asarray(temp_prof, dtype=float)
        sal_prof = np.asarray(sal_prof, dtype=float)

        valid = np.isfinite(pres) & np.isfinite(temp_prof) & np.isfinite(sal_prof)
        if np.count_nonzero(valid) < 5:
            continue

        pres = pres[valid]
        temp_prof = temp_prof[valid]
        sal_prof = sal_prof[valid]
        if np.nanmin(sal_prof) < 32.0:
          raise RuntimeError(f'Salinity below 32 psu detected in float {p._my_float.wmo}, cycle {p._my_float.cycle}')

        order = np.argsort(pres)
        pres = pres[order]
        temp_prof = temp_prof[order]
        sal_prof = sal_prof[order]

        if pres.size < 5 or np.nanmax(pres) < 5:
            continue

        try:
            sa = gsw.SA_from_SP(sal_prof, pres, p.lon, p.lat)
            ct = gsw.CT_from_t(sa, temp_prof, pres)
            rho_prof = gsw.rho(sa, ct, pres)
        except Exception:
            continue

        temp_grid = np.interp(DEPTHS, pres, temp_prof, left=np.nan, right=np.nan)
        sal_grid  = np.interp(DEPTHS, pres, sal_prof,  left=np.nan, right=np.nan)
        rho_grid  = np.interp(DEPTHS, pres, rho_prof,  left=np.nan, right=np.nan)

        # oxygen
        try:
            pres_o, oxy_prof, _ = p.read(FLOATVARS['O2o'])
            if pres_o is None or oxy_prof is None or len(oxy_prof) < 3:
                raise ValueError
            pres_o   = np.asarray(pres_o,   dtype=float)
            oxy_prof = np.asarray(oxy_prof,  dtype=float)
            if doxy_convert:
                oxy_prof = convert_oxygen(p, pres_o, oxy_prof)
            ord_o    = np.argsort(pres_o)
            oxy_grid = np.interp(DEPTHS, pres_o[ord_o], oxy_prof[ord_o],
                                 left=np.nan, right=np.nan)
        except Exception:
            oxy_grid = np.full(len(DEPTHS), np.nan)

        if np.all(np.isnan(temp_grid)) and np.all(np.isnan(sal_grid)) and np.all(np.isnan(rho_grid)):
            continue

        times.append(p.time)
        temp_mat.append(temp_grid)
        sal_mat.append(sal_grid)
        rho_mat.append(rho_grid)
        oxy_mat.append(oxy_grid)

    if len(times) == 0:
        return None

    times = pd.to_datetime(times)
    sort_idx = np.argsort(times.values)
    times = times[sort_idx]

    temp_mat = np.vstack(temp_mat)[sort_idx, :].T
    sal_mat  = np.vstack(sal_mat) [sort_idx, :].T
    rho_mat  = np.vstack(rho_mat) [sort_idx, :].T
    oxy_mat  = np.vstack(oxy_mat) [sort_idx, :].T

    return times, temp_mat, sal_mat, rho_mat, oxy_mat


def save_hovmoeller(times, temp_mat, sal_mat, rho_mat, oxy_mat, basin_name, source_name):
    rho_600m, rho_std = get_density_600m(basin_name)

    months = np.array([t.month for t in times])
    month_x = np.arange(1, 13)
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def monthly_clim(matrix):
        clim = np.full((matrix.shape[0], 12), np.nan)
        for m in range(1, 13):
            idx = np.where(months == m)[0]
            if len(idx) > 0:
                clim[:, m - 1] = np.nanmean(matrix[:, idx], axis=1)
        return clim

    temp_clim = monthly_clim(temp_mat)
    sal_clim  = monthly_clim(sal_mat)
    rho_clim  = monthly_clim(rho_mat)
    oxy_clim  = monthly_clim(oxy_mat)

    # depth of isopycnal rho_600m for each time step
    if rho_600m is not None:
        iso_depth = np.full(rho_mat.shape[1], np.nan)
        for t in range(rho_mat.shape[1]):
            col = rho_mat[:, t]
            valid = np.isfinite(col)
            if np.count_nonzero(valid) >= 2:
                idx_sort = np.argsort(col[valid])
                rho_sorted = col[valid][idx_sort]
                dep_sorted = DEPTHS[valid][idx_sort]
                if rho_600m >= rho_sorted[0] and rho_600m <= rho_sorted[-1]:
                    iso_depth[t] = np.interp(rho_600m, rho_sorted, dep_sorted)
        iso_depth_clim = np.array([
            np.nanmean(iso_depth[months == m]) if np.any(months == m) else np.nan
            for m in range(1, 13)
        ])
    else:
        iso_depth = None
        iso_depth_clim = np.full(12, np.nan)

    # depth of salinity maximum for each time step
    sal_max_depth = np.array([
        DEPTHS[np.nanargmax(sal_mat[:, t])] if np.any(np.isfinite(sal_mat[:, t])) else np.nan
        for t in range(sal_mat.shape[1])
    ])
    sal_max_clim = np.array([
        np.nanmean(sal_max_depth[months == m]) if np.any(months == m) else np.nan
        for m in range(1, 13)
    ])

    panels = [
        (temp_mat, temp_clim, CMAP_TEMP, 'Temperature', '°C',      None, None),
        (sal_mat,  sal_clim,  CMAP_SAL,  'Salinity',    'psu',      32.0, 40.0),
        (rho_mat,  rho_clim,  CMAP_RHO,  'Density',     'kg/m³',    None, None),
        (oxy_mat,  oxy_clim,  CMAP_OXY,  'Oxygen',      'mmol/m³',  None, None),
    ]

    fig, axs = plt.subplots(4, 3, figsize=(24, 16), sharey='row',
                             gridspec_kw={'width_ratios': [2, 1, 1], 'wspace': 0.02, 'hspace': 0.35})
    # share x within col 0 (time axis) and col 1 (month axis) only
    # col 2 (profiles) must stay independent — each variable has a different x range
    for col in (0, 1):
        for row in range(1, 4):
            axs[row, col].sharex(axs[0, col])

    for i, (matrix, clim, cmap, title, cbar_label, vmin_fix, vmax_fix) in enumerate(panels):
        ax_l = axs[i, 0]
        ax_r = axs[i, 1]
        ax_p = axs[i, 2]

        vmin = vmin_fix if vmin_fix is not None else np.nanmin(matrix)
        vmax = vmax_fix if vmax_fix is not None else np.nanmax(matrix)
        norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax, clip=True)

        # ---- left panel: full timeseries ----
        pcm = ax_l.pcolormesh(times, DEPTHS, matrix, shading='auto',
                              cmap=cmap, norm=norm)
        ax_l.set_ylabel('Depth (m)')
        ax_l.invert_yaxis()
        fig.colorbar(pcm, ax=ax_l, label=cbar_label)
        ax_l.grid(True, linestyle=':', alpha=0.4)

        # ---- centre panel: monthly climatology Hovmoeller ----
        pcm_r = ax_r.pcolormesh(month_x, DEPTHS, clim, shading='auto',
                                cmap=cmap, norm=norm)
        fig.colorbar(pcm_r, ax=ax_r, label=cbar_label)
        ax_r.grid(True, linestyle=':', alpha=0.4)
        ax_r.set_xticks(month_x)
        ax_r.set_xticklabels(month_labels, fontsize=8)

        # ---- right panel: 12 monthly + 1 annual mean profiles ----
        # hawaii: 0=deep blue (Jan) → 1=yellow-orange (Jul), Dec stays near blue
        for m in range(12):
            color_val = 0.5 * (1.0 - np.cos(2.0 * np.pi * m / 12.0))
            profile = clim[:, m]
            valid_p = np.isfinite(profile)
            if valid_p.any():
                ax_p.plot(profile[valid_p], DEPTHS[valid_p],
                          #color=cmc.cm.hawaii(color_val), linewidth=0.9, alpha=0.85,
                          color=cmc.cm.managua_r(color_val), linewidth=0.9,
                          label=month_labels[m])
        ann_profile = np.nanmean(clim, axis=1)
        valid_a = np.isfinite(ann_profile)
        if valid_a.any():
            ax_p.plot(ann_profile[valid_a], DEPTHS[valid_a],
                      color='k', linewidth=2.0, label='annual mean')
        ax_p.set_xlim(vmin, vmax)
        ax_p.set_xlabel(cbar_label)
        ax_p.grid(True, linestyle=':', alpha=0.4)

        # ---- overlay lines ----
        if i == 1:  # salinity
            ax_l.plot(times, sal_max_depth, color='k', linewidth=1.5,
                      linestyle=':', label='depth of sal max')
            ax_l.legend(loc='upper right', fontsize=8)
            ax_l.set_title(f'{basin_name} {source_name.capitalize()} — {title}')
            ax_r.plot(month_x, sal_max_clim, color='k', linewidth=1.5,
                      linestyle=':', label='depth of sal max')
            ax_r.legend(loc='upper right', fontsize=8)
            ax_r.set_title(f'{basin_name} — {title} (climatology)')
            ann_sal_max = np.nanmean(sal_max_depth)
            if np.isfinite(ann_sal_max):
                ax_p.axhline(ann_sal_max, color='k', linewidth=1.5, linestyle=':')
            ax_p.legend(loc='lower right', fontsize=6, ncol=2)
            ax_p.set_title(f'{basin_name} — {title} (profiles)')

        elif i == 2 and rho_600m is not None:  # density
            ax_l.plot(times, iso_depth, color='k', linewidth=1.5,
                      linestyle=':', label=f'ρ₆₀₀={rho_600m:.3f} kg/m³')
            ax_l.legend(loc='upper right', fontsize=8)
            ax_l.set_title(
                f'{basin_name} {source_name.capitalize()} — {title}'
                f'   [ρ₆₀₀ = {rho_600m:.3f} ± {rho_std:.3f} kg/m³]'
            )
            ax_r.plot(month_x, iso_depth_clim, color='k', linewidth=1.5,
                      linestyle=':', label=f'ρ₆₀₀={rho_600m:.3f} kg/m³')
            ax_r.legend(loc='upper right', fontsize=8)
            ax_r.set_title(f'{basin_name} — {title} (climatology)')
            ann_iso = np.nanmean(iso_depth)
            if np.isfinite(ann_iso):
                ax_p.axhline(ann_iso, color='k', linewidth=1.5, linestyle=':')
            ax_p.legend(loc='lower right', fontsize=6, ncol=2)
            ax_p.set_title(f'{basin_name} — {title} (profiles)')

        elif i == 3:  # oxygen
            if np.any(np.isfinite(sal_max_depth)):
                ax_l.plot(times, sal_max_depth, color='lightgray', linewidth=1.5,
                          linestyle=':', label='depth of sal max')
            if iso_depth is not None and np.any(np.isfinite(iso_depth)):
                ax_l.plot(times, iso_depth, color='k', linewidth=1.5,
                          linestyle=':', label=f'ρ₆₀₀={rho_600m:.3f} kg/m³')
            ax_l.legend(loc='upper right', fontsize=8)
            ax_l.set_title(f'{basin_name} {source_name.capitalize()} — {title}')
            if np.any(np.isfinite(sal_max_clim)):
                ax_r.plot(month_x, sal_max_clim, color='lightgray', linewidth=1.5,
                          linestyle=':', label='depth of sal max')
            if np.any(np.isfinite(iso_depth_clim)):
                ax_r.plot(month_x, iso_depth_clim, color='k', linewidth=1.5,
                          linestyle=':', label=f'ρ₆₀₀={rho_600m:.3f} kg/m³')
            ax_r.legend(loc='upper right', fontsize=8)
            ax_r.set_title(f'{basin_name} — {title} (climatology)')
            ann_sal_max = np.nanmean(sal_max_depth)
            if np.isfinite(ann_sal_max):
                ax_p.axhline(ann_sal_max, color='lightgray', linewidth=1.5, linestyle=':')
            if iso_depth is not None:
                ann_iso = np.nanmean(iso_depth)
                if np.isfinite(ann_iso):
                    ax_p.axhline(ann_iso, color='k', linewidth=1.5, linestyle=':')
            ax_p.legend(loc='lower right', fontsize=6, ncol=2)
            ax_p.set_title(f'{basin_name} — {title} (profiles)')

        else:  # temperature
            ax_l.set_title(f'{basin_name} {source_name.capitalize()} — {title}')
            ax_r.set_title(f'{basin_name} — {title} (climatology)')
            ax_p.legend(loc='lower right', fontsize=6, ncol=2)
            ax_p.set_title(f'{basin_name} — {title} (profiles)')

    axs[-1, 0].set_xlabel('Time')
    axs[-1, 1].set_xlabel('Month')
    axs[-1, 2].set_xlabel('')
    # rotate date labels only on the time axis (col 0, last row)
    plt.setp(axs[-1, 0].xaxis.get_majorticklabels(), rotation=30, ha='right')
    # restore x-tick labels on all profile panels (col 2) — autofmt_xdate would hide them
    for row in range(4):
        axs[row, 2].tick_params(axis='x', labelbottom=True)
    fig.tight_layout(h_pad=1.2, w_pad=0.2)

    outfile = os.path.join(OUTDIR, f'{basin_name}_{source_name}_hovmoeller.png')
    fig.savefig(outfile, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {outfile}')


for basin in SUBS:
    print(f'Processing basin {basin.name}')
    if args.dataset in ('superfloat', 'both'):
        super_profiles = superfloat.FloatSelector(FLOATVARS['votemper'], TI, basin)
        super_data = make_hovmoeller(super_profiles, doxy_convert=False)
        if super_data is not None:
            save_hovmoeller(*super_data, basin.name, 'superfloat')
        else:
            print(f'  No valid superfloat profiles for {basin.name}.')

    if args.dataset in ('coriolis', 'both'):
        cor_profiles = bio_float.FloatSelector(FLOATVARS['votemper'], TI, basin)
        cor_data = make_hovmoeller(cor_profiles, doxy_convert=True)
        if cor_data is not None:
            save_hovmoeller(*cor_data, basin.name, 'coriolis')
        else:
            print(f'  No valid coriolis profiles for {basin.name}.')
