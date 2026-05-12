import argparse


def argument():
    parser = argparse.ArgumentParser(description='''
    This script computes monthly vertical climatologies of a given SUPERFLOAT variable for different Mediterranean sub-basins.
    **Input**: SUPERFLOAT profiles selected for a given variable (--variable) and monthly climatology.
    **Method**: For each sub-basin and month, profiles are interpolated on the model depth levels, and vertical averages and standard deviations are computed.
    **Output**:
     - PNG figures showing all vertical profiles per sub-basin.
     - CSV files with the interpolated profile data.
     - NetCDF files containing the vertical climatologies:
         - mm_Avg_superfloat_dataset_<variable>.nc: mean values
         - mm_Std_superfloat_dataset_<variable>.nc: standard deviations
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
    return parser.parse_args()


args = argument()

from bitsea.commons.utils import addsep
import numpy as np
import pandas as pd
from bitsea.commons import timerequestors
from bitsea.instruments import superfloat
from bitsea.instruments import superfloat as bio_float
from bitsea.instruments.var_conversions import FLOATVARS
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
import matplotlib.pyplot as plt


def plot_line_profiles(df, z_interp, namesub, varmod, mm):
    fig, axs = plt.subplots(1, 1, figsize=(10, 6))
    plt.plot(df.values, z_interp, alpha=0.3)
    plt.gca().invert_yaxis()
    plt.ylabel(varmod)
    plt.xlabel('depth (m)')
    plt.title(f'All profiles {namesub} month {mm:02d}')

    plt.tight_layout()
    plt.savefig(OUTDIR + f'/{namesub}_{varmod}_{mm:02d}_superfloat.png')
    plt.close()
    df.to_csv(OUTDIR + f'/{namesub}_{varmod}_{mm:02d}_superfloat.csv')


OUTDIR = addsep(args.outdir)
varmod = args.variable

TheMask = Mask.from_file(
    '/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc')
z_interp = TheMask.zlevels

if OGS.atl in OGS.Pred.basin_list:
    OGS.Pred.basin_list.remove(OGS.atl)

SUBS = OGS.Pred.basin_list[:]
print('_________________start__________________', flush=True)

MONTHS = np.arange(1, 13)

for mm in MONTHS:
    CLIM = np.full((len(SUBS), len(z_interp)), np.nan, dtype=np.float32)
    STD = np.full((len(SUBS), len(z_interp)), np.nan, dtype=np.float32)
    SUB_COUNT = 0

    TI = timerequestors.Clim_month(mm)

    for ISUB in SUBS:
        print(f'_____________ {ISUB} _____________', flush=True)

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
        ICONT = 0

        for PROFILE in Profilelist:
            Pres, Profile, Qc = PROFILE.read(var=FLOATVARS[varmod])
            Profile_interp = np.interp(z_interp, Pres, Profile, left=np.nan, right=np.nan)
            SERV_VAR[ICONT, :] = Profile_interp
            ICONT += 1

        df = pd.DataFrame(SERV_VAR).T
        plot_line_profiles(df, z_interp, ISUB.name, FLOATVARS[varmod], mm)

        serv_P = np.nanmean(SERV_VAR, axis=0)
        serv_S = np.nanstd(SERV_VAR, axis=0)
        CLIM[SUB_COUNT, :] = serv_P
        STD[SUB_COUNT, :] = serv_S
        SUB_COUNT += 1

    import netCDF4

    outfile = OUTDIR + f'/{mm:02d}_Avg_superfloat_dataset_{varmod}.nc'
    ncOUT = netCDF4.Dataset(outfile, 'w')
    ncOUT.createDimension('nsub', len(SUBS))
    ncOUT.createDimension('nav_lev', len(z_interp))
    ncvar = ncOUT.createVariable(varmod, 'f', ('nsub', 'nav_lev'))
    ncvar[:] = CLIM
    ncOUT.close()

    outfile = OUTDIR + f'/{mm:02d}_Std_superfloat_dataset_{varmod}.nc'
    ncOUT = netCDF4.Dataset(outfile, 'w')
    ncOUT.createDimension('nsub', len(SUBS))
    ncOUT.createDimension('nav_lev', len(z_interp))
    ncvar = ncOUT.createVariable(varmod, 'f', ('nsub', 'nav_lev'))
    ncvar[:] = STD
    ncOUT.close()
