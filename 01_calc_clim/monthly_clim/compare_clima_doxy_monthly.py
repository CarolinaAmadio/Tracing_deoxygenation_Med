import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from bitsea.commons.layer import Layer
from bitsea.basins import V2 as OGS
from netCDF4 import Dataset
from bitsea.static.climatology import get_climatology
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


def main():
    args = argument()
    INDIR = addsep(args.indir)
    OUTDIR = addsep(args.outdir)
    CORIOLIS_NOQC = addsep(args.coriolis)
    VAR = args.variable
    MONTHS = parse_months(args.months)
    os.makedirs(OUTDIR, exist_ok=True)

    TheMask = Mask.from_file(
        '/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc')
    z_lev = TheMask.zlevels

    PresDOWN = np.array([0, 25, 50, 75, 100, 125, 150, 200, 400, 600, 800])
    LayerList = [Layer(PresDOWN[k], PresDOWN[k + 1]) for k in range(len(PresDOWN) - 1)]
    LayerDepth = [0.5 * (ll.bottom + ll.top) for ll in LayerList]

    SUBLIST = []
    for sub in OGS.Pred.basin_list:
        if 'atl' in sub.name:
            continue
        SUBLIST.append(sub)

    _emodnet = get_climatology(VAR, SUBLIST, LayerList, basin_expand=True, QC=True)

    for mm in MONTHS:
        super_dir = os.path.join(INDIR, 'SUPERFLOAT')
        coriolis_dir = os.path.join(INDIR, 'CORIOLIS')

        file_sf_avg = os.path.join(super_dir, f'{mm:02d}_Avg_superfloat_dataset_{VAR}.nc')
        file_sf_std = os.path.join(super_dir, f'{mm:02d}_Std_superfloat_dataset_{VAR}.nc')
        file_co_avg = os.path.join(coriolis_dir, f'{mm:02d}_Avg_{VAR}_coriolis_ogs.nc')
        file_co_std = os.path.join(coriolis_dir, f'{mm:02d}_Std_{VAR}_coriolis_ogs.nc')

        if not os.path.exists(file_sf_avg) or not os.path.exists(file_sf_std):
            raise FileNotFoundError(f'Missing SUPERFLOAT monthly files for month {mm}: {file_sf_avg} or {file_sf_std}')
        if not os.path.exists(file_co_avg) or not os.path.exists(file_co_std):
            raise FileNotFoundError(f'Missing CORIOLIS monthly files for month {mm}: {file_co_avg} or {file_co_std}')

        with Dataset(file_sf_avg) as ncs_avg, Dataset(file_sf_std) as ncs_std, Dataset(file_co_avg) as ncc_avg, Dataset(file_co_std) as ncc_std:
            vs_avg = get_variable_from_nc(ncs_avg, VAR)
            vs_std = get_variable_from_nc(ncs_std, VAR)
            vc_avg = get_variable_from_nc(ncc_avg, VAR)
            vc_std = get_variable_from_nc(ncc_std, VAR)

            for isub, sub in enumerate(SUBLIST):
                fig, ax = plt.subplots(1, 1, figsize=(7, 15))

                ax.plot(vs_avg[isub, :], z_lev, color='tab:red', linewidth=3, label='Superfloat')
                ax.plot(vs_avg[isub, :] + vs_std[isub, :], z_lev, color='tab:red', linestyle=':')
                ax.plot(vs_avg[isub, :] - vs_std[isub, :], z_lev, color='tab:red', linestyle=':')

                ax.plot(vc_avg[isub, :], z_lev, color='k', linewidth=2, label='Coriolis_ogs')
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

                ax.plot(_emodnet[0][isub, :], LayerDepth, 'bo', label='Insitu')
                ax.plot(_emodnet[0][isub, :] + _emodnet[1][isub, :], LayerDepth, 'b-.')
                ax.plot(_emodnet[0][isub, :] - _emodnet[1][isub, :], LayerDepth, 'b-.')
                ax.grid()
                ax.set_ylim(801, 0)
                ax.set_title(f'{sub.name} month {mm:02d}')
                ax.legend()
                ax.set_xlabel(r'mmol m$^{-3}$')
                fig_name = os.path.join(OUTDIR, f'{sub.name}_{VAR}_month_{mm:02d}_clima_float_emodnet.png')
                fig.savefig(fig_name, dpi=150)
                plt.close(fig)

    shutil.copy(__file__, OUTDIR)


if __name__ == '__main__':
    main()
