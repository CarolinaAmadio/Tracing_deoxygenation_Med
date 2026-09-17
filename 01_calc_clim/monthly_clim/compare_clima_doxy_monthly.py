import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from bitsea.commons.layer import Layer
from bitsea.basins import V2 as OGS
from netCDF4 import Dataset
from bitsea.static.climatology import DatasetInfo, QualityCheck, TI as STATIC_TI, get_climatology
from bitsea.commons.mask import Mask
from bitsea.commons.utils import addsep
import shutil


def argument():
    parser = argparse.ArgumentParser(
        description='Compare monthly vertical climatologies from SUPERFLOAT and CORIOLIS_OGS against EMODNET and optional CORIOLIS noQC monthly files.',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--indir', '-i',
                        type=str,
                        required=True,
                        help='root input directory containing SUPERFLOAT/ and CORIOLIS/ monthly outputs')
    parser.add_argument('--outdir', '-o',
                        type=str,
                        required=True,
                        help='output directory for PNG plots')
    parser.add_argument('--variable', '-v',
                        type=str,
                        required=True,
                        help='variable to plot')
    parser.add_argument('--coriolis', '-c',
                        type=str,
                        default='/g100_scratch/userexternal/camadio0/ARGOPY_TESTS/Climatologies_Argopy/NO_QC/__CANYON_MED_NO_QC/Monthly_Clim/',
                        help='optional CORIOLIS noQC monthly directory with <sub>_mm_clim.nc files')
    parser.add_argument('--months', '-m',
                        type=str,
                        default=None,
                        help='comma-separated months to plot, e.g. 1,4,7; default is 1..12')
    parser.add_argument('--noqc',
                        action='store_true',
                        help='plot CORIOLIS noQC monthly files if available')
    return parser.parse_args()


def get_variable_from_nc(nc, varname):
    if varname in nc.variables:
        return nc.variables[varname][:]
    for candidate in ('DOXY', 'O2o', 'O2', 'do', 'doxy'):
        if candidate in nc.variables:
            return nc.variables[candidate][:]
    raise KeyError(f'Variable {varname} not found in {nc.filepath()}')


def parse_months(months_arg):
    if months_arg is None:
        return list(range(1, 13))
    months = []
    for token in months_arg.split(','):
        token = token.strip()
        if not token:
            continue
        months.append(int(token))
    return months


def format_period(year_min, month_min, year_max, month_max):
    year_min = int(year_min)
    month_min = int(month_min)
    year_max = int(year_max)
    month_max = int(month_max)
    if min(year_min, month_min, year_max, month_max) < 0:
        return None
    return f'{year_min:04d}-{month_min:02d} to {year_max:04d}-{month_max:02d}'


def get_emodnet_metadata(var, subbasins, layers, has_insitu_climatology):
    if not has_insitu_climatology:
        return [(None, None, None) for _ in subbasins]

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
            nobs += sum(
                ((pres >= layer.top) & (pres < layer.bottom)).sum()
                for layer in layers
            )

        period = None
        if profile_dates:
            period = format_period(
                min(profile_dates).year, min(profile_dates).month,
                max(profile_dates).year, max(profile_dates).month,
            )
        metadata.append((len(profile_list), nobs, period))
    return metadata


def main():
    args = argument()
    INDIR = addsep(args.indir)
    OUTDIR = addsep(args.outdir)
    CORIOLIS_NOQC = addsep(args.coriolis)
    VAR = args.variable
    MONTHS = parse_months(args.months)
    os.makedirs(OUTDIR, exist_ok=True)

    TheMask = Mask.from_file(os.environ["MASKFILE"])
    z_lev = TheMask.zlevels

    PresDOWN = np.array([0, 25, 50, 75, 100, 125, 150, 200, 400, 600, 800])
    LayerList = [Layer(PresDOWN[k], PresDOWN[k + 1]) for k in range(len(PresDOWN) - 1)]
    LayerDepth = [0.5 * (ll.bottom + ll.top) for ll in LayerList]

    SUBLIST = []
    for sub in OGS.Pred.basin_list:
        if 'atl' in sub.name:
            continue
        SUBLIST.append(sub)

    HAS_INSITU_CLIMATOLOGY = VAR not in {"votemper", "vosaline"}
    if HAS_INSITU_CLIMATOLOGY:
        _emodnet = get_climatology(VAR, SUBLIST, LayerList, basin_expand=True, QC=True)
    emodnet_metadata = get_emodnet_metadata(VAR, SUBLIST, LayerList, HAS_INSITU_CLIMATOLOGY)
    summary_rows = []

    for mm in MONTHS:
        super_dir = os.path.join(INDIR, 'SUPERFLOAT')
        coriolis_dir = os.path.join(INDIR, 'CORIOLIS')

        file_sf_avg = os.path.join(super_dir, f'{mm:02d}_Avg_{VAR}_superfloat.nc')
        file_sf_std = os.path.join(super_dir, f'{mm:02d}_Std_{VAR}_superfloat.nc')
        file_co_avg = os.path.join(coriolis_dir, f'{mm:02d}_Avg_{VAR}_coriolis.nc')
        file_co_std = os.path.join(coriolis_dir, f'{mm:02d}_Std_{VAR}_coriolis.nc')

        if not os.path.exists(file_sf_avg) or not os.path.exists(file_sf_std):
            raise FileNotFoundError(f'Missing SUPERFLOAT monthly files for month {mm}: {file_sf_avg} or {file_sf_std}')
        if not os.path.exists(file_co_avg) or not os.path.exists(file_co_std):
            raise FileNotFoundError(f'Missing CORIOLIS monthly files for month {mm}: {file_co_avg} or {file_co_std}')

        with Dataset(file_sf_avg) as ncs_avg, Dataset(file_sf_std) as ncs_std, Dataset(file_co_avg) as ncc_avg, Dataset(file_co_std) as ncc_std:
            vs_avg = get_variable_from_nc(ncs_avg, VAR)
            vs_std = get_variable_from_nc(ncs_std, VAR)
            vc_avg = get_variable_from_nc(ncc_avg, VAR)
            vc_std = get_variable_from_nc(ncc_std, VAR)

            sf_nprofiles = getattr(ncs_avg, 'NPROFILES', None)
            sf_nwmo = getattr(ncs_avg, 'NWMO', None)
            sf_ymin = getattr(ncs_avg, 'YEAR_MIN', None)
            sf_mmin = getattr(ncs_avg, 'MONTH_MIN', None)
            sf_ymax = getattr(ncs_avg, 'YEAR_MAX', None)
            sf_mmax = getattr(ncs_avg, 'MONTH_MAX', None)
            co_nprofiles = getattr(ncc_avg, 'NPROFILES', None)
            co_nwmo = getattr(ncc_avg, 'NWMO', None)
            co_ymin = getattr(ncc_avg, 'YEAR_MIN', None)
            co_mmin = getattr(ncc_avg, 'MONTH_MIN', None)
            co_ymax = getattr(ncc_avg, 'YEAR_MAX', None)
            co_mmax = getattr(ncc_avg, 'MONTH_MAX', None)
            sf_period = None
            co_period = None
            if None not in (sf_ymin, sf_mmin, sf_ymax, sf_mmax):
                sf_period = format_period(sf_ymin, sf_mmin, sf_ymax, sf_mmax)
            if None not in (co_ymin, co_mmin, co_ymax, co_mmax):
                co_period = format_period(co_ymin, co_mmin, co_ymax, co_mmax)

            for isub, sub in enumerate(SUBLIST):
                fig, ax = plt.subplots(1, 1, figsize=(7, 15))

                sf_label = 'Superfloat' if sf_period is None else f'Superfloat: {sf_period}'
                ax.plot(vs_avg[isub, :], z_lev, color='tab:red', linewidth=3, label=sf_label)
                ax.plot(vs_avg[isub, :] + vs_std[isub, :], z_lev, color='tab:red', linestyle=':')
                ax.plot(vs_avg[isub, :] - vs_std[isub, :], z_lev, color='tab:red', linestyle=':')

                co_label = 'Coriolis' if co_period is None else f'Coriolis: {co_period}'
                ax.plot(vc_avg[isub, :], z_lev, color='k', linewidth=2, label=co_label)
                ax.plot(vc_avg[isub, :] + vc_std[isub, :], z_lev, color='k', linestyle=':')
                ax.plot(vc_avg[isub, :] - vc_std[isub, :], z_lev, color='k', linestyle=':')

                if args.noqc:
                    file_noqc = os.path.join(CORIOLIS_NOQC, f'{sub.name}_{mm:02d}_clim.nc')
                    file_noqc_std = os.path.join(CORIOLIS_NOQC, f'{sub.name}_{mm:02d}_clim_std.nc')
                    if os.path.exists(file_noqc):
                        with Dataset(file_noqc) as nc_noqc:
                            v_noqc = get_variable_from_nc(nc_noqc, VAR)
                        if os.path.exists(file_noqc_std):
                            with Dataset(file_noqc_std) as nc_noqc_std:
                                s_noqc = get_variable_from_nc(nc_noqc_std, VAR)
                        else:
                            s_noqc = None
                        ax.plot(v_noqc, z_lev, color='dodgerblue', linewidth=2, label='Coriolis_noQC')
                        if s_noqc is not None:
                            ax.plot(v_noqc + s_noqc, z_lev, color='dodgerblue', linestyle=':')
                            ax.plot(v_noqc - s_noqc, z_lev, color='dodgerblue', linestyle=':')

                if HAS_INSITU_CLIMATOLOGY:
                    emodnet_nprofiles, emodnet_nobs, emodnet_period = emodnet_metadata[isub]
                    emodnet_label = 'Insitu' if emodnet_period is None else f'Insitu: {emodnet_period}'
                    ax.plot(_emodnet[0][isub, :], LayerDepth, 'bo', label=emodnet_label)
                    ax.plot(_emodnet[0][isub, :] + _emodnet[1][isub, :], LayerDepth, 'b-.')
                    ax.plot(_emodnet[0][isub, :] - _emodnet[1][isub, :], LayerDepth, 'b-.')
                else:
                    emodnet_nprofiles, emodnet_nobs, emodnet_period = (None, None, None)
                ax.grid()
                ax.set_ylim(801, 0)
                title_parts = [f'{sub.name} month {mm:02d}']
                if sf_nprofiles is not None and sf_nwmo is not None:
                    title_parts.append(f'SF nprof={int(sf_nprofiles)} nwmo={int(sf_nwmo)}')
                if co_nprofiles is not None and co_nwmo is not None:
                    title_parts.append(f'CO nprof={int(co_nprofiles)} nwmo={int(co_nwmo)}')
                ax.set_title(' | '.join(title_parts))
                ax.legend()
                ax.set_xlabel(VAR)
                fig_name = os.path.join(OUTDIR, f'{sub.name}_{VAR}_month_{mm:02d}_clima_float_emodnet.png')
                fig.savefig(fig_name, dpi=150)
                plt.close(fig)

                summary_rows.append({
                    'MONTH': mm,
                    'BASIN': sub.name,
                    'EMODNET_NPROFILES': emodnet_nprofiles,
                    'EMODNET_NOBS': emodnet_nobs,
                    'EMODNET_DATARANGE': emodnet_period,
                    'SUPERFLOAT_NPROFILES': int(sf_nprofiles) if sf_nprofiles is not None else None,
                    'SUPERFLOAT_NWMO': int(sf_nwmo) if sf_nwmo is not None else None,
                    'SUPERFLOAT_DATARANGE': sf_period,
                    'CORIOLIS_NPROFILES': int(co_nprofiles) if co_nprofiles is not None else None,
                    'CORIOLIS_NWMO': int(co_nwmo) if co_nwmo is not None else None,
                    'CORIOLIS_DATARANGE': co_period,
                })

    pd.DataFrame(summary_rows).to_csv(
        os.path.join(OUTDIR, 'climatology_sample_summary.csv'), index=False
    )
    shutil.copy(__file__, OUTDIR)


if __name__ == '__main__':
    main()
