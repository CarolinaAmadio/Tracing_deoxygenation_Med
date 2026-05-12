import argparse


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
from bitsea.commons import timerequestors
from bitsea.instruments import bio_float
from bitsea.instruments.var_conversions import FLOATVARS
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
import gsw 
import xarray as xr
import matplotlib.pyplot as plt


def compute_density_teos10(sp, temp, pres, ds):
    """Compute density using TEOS-10 with gsw."""
    if 'LONGITUDE' in ds and 'LATITUDE' in ds:
        SA = gsw.SA_from_SP(sp, pres, ds['LONGITUDE'], ds['LATITUDE'])
    elif 'longitude' in ds and 'latitude' in ds:
        SA = gsw.SA_from_SP(sp, pres, ds['longitude'], ds['latitude'])
    elif 'lon' in ds and 'lat' in ds:
        SA = sgw.SA_from_SP(sp, pres, ds['lon'], ds['lat'])
    else:
        SA = sp

    CT = gsw.CT_from_t(SA, temp, pres)
    return gsw.rho(SA, CT, pres)


def plot_line_profiles(df, z_interp, namesub, varmod, mm):
    fig, axs = plt.subplots(1, 1, figsize=(10, 6))
    plt.plot(df.values, z_interp, alpha=0.3)
    plt.gca().invert_yaxis()
    plt.ylabel(varmod)
    plt.xlabel('depth (m)')
    plt.title(f'All profiles {namesub} month {mm:02d}')

    plt.tight_layout()
    plt.savefig(OUTDIR + f'/{namesub}_{varmod}_{mm:02d}_coriolis_ogs.png')
    df.to_csv(OUTDIR + f'/{namesub}_{varmod}_{mm:02d}_coriolis_ogs.csv')


def convert_umolkg_to_mmolm3(new_ds, Pres, Profile, VARNAME='DOXY'):
    """Convert DOXY from µmol/kg to mmol/m3 using TEOS-10 density."""
    density = compute_density_teos10(new_ds['PSAL'], new_ds['TEMP'], new_ds['PRES'], new_ds)
    density = np.squeeze(density)
    Pres_phy = np.squeeze(new_ds['PRES'])
    if len(density) != len(Pres):
        density = np.interp(Pres, Pres_phy, density, left=np.nan, right=np.nan)
    Profile = np.squeeze(Profile * density / 1000.0)
    return Pres, Profile


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
            if len(Pres) < 5:
                continue
            if varmod == 'O2o':
                new_ds = xr.open_dataset(PROFILE._my_float.filename)
                Pres, Profile = convert_umolkg_to_mmolm3(new_ds, Pres, Profile)
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

    outfile = OUTDIR + f'/{mm:02d}_Avg_{varmod}_coriolis_ogs.nc'
    ncOUT = netCDF4.Dataset(outfile, 'w')
    ncOUT.createDimension('nsub', len(SUBS))
    ncOUT.createDimension('nav_lev', len(z_interp))
    ncvar = ncOUT.createVariable(varmod, 'f', ('nsub', 'nav_lev'))
    ncvar[:] = CLIM
    ncOUT.close()

    outfile = OUTDIR + f'/{mm:02d}_Std_{varmod}_coriolis_ogs.nc'
    ncOUT = netCDF4.Dataset(outfile, 'w')
    ncOUT.createDimension('nsub', len(SUBS))
    ncOUT.createDimension('nav_lev', len(z_interp))
    ncvar = ncOUT.createVariable(varmod, 'f', ('nsub', 'nav_lev'))
    ncvar[:] = STD
    ncOUT.close()
