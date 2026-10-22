import argparse
import os
import numpy as np
import pandas as pd
import xarray as xr
import netCDF4

from bitsea.commons.utils import addsep
from bitsea.instruments import superfloat as bio_float
from bitsea.instruments.var_conversions import FLOATVARS
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
from bitsea.commons import timerequestors


# ============================================================
# ARGUMENTS
# ============================================================

def argument():
    parser = argparse.ArgumentParser(
        description='''
        This script computes yearly vertical climatologies of a given
        BGC-Argo variable for a Mediterranean sub-basin.

        Years: 2013-2026

        For each year:
          - profiles are selected for the sub-basin
          - profiles are interpolated on model depth levels
          - vertical mean and standard deviation are calculated

        If no profiles are available for a given year, the climatology
        is set to NaN.
        ''',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        '--outdir', '-o',
        type=str,
        required=True,
        help='output directory'
    )

    parser.add_argument(
        '--variable', '-v',
        type=str,
        required=True,
        help='model variable'
    )

    parser.add_argument(
        '--sub',
        type=str,
        required=True,
        help='sub-basin name to process'
    )

    return parser.parse_args()


args = argument()


# ============================================================
# SETTINGS
# ============================================================

OUTDIR = addsep(args.outdir)
varmod = args.variable
subname = args.sub

# Hardcoded years
YEARS = np.arange(2013, 2027)

# Model variable -> BGC-Argo variable
LOCAL_FLOATVARS = {
    'O2o': 'DOXY',
    'N3n': 'NITRATE',
    'P_l': 'CHLA',
    'P_i': 'CHLA',
    'Chla': 'CHLA',
    'vosaline': 'PSAL',
    'votemper': 'TEMP',
    'PAR': 'DOWNWELLING_PAR',
    'POC': 'BBP700',
    'P_c': 'BBP700',
    'Ed_490': 'DOWN_IRRADIANCE490',
    'CDOM': 'CDOM',
    'BBP532': 'BBP532',
    'pH': 'PH_IN_SITU_TOTAL'}

# Use FLOATVARS as in the original script
floatvar = FLOATVARS[varmod]
TheMask = Mask.from_file(os.environ["MASKFILE"])
z_interp = TheMask.zlevels
os.makedirs(OUTDIR, exist_ok=True)

# ============================================================
# BASINS
# ===========================================================
if OGS.atl in OGS.Pred.basin_list:
    OGS.Pred.basin_list.remove(OGS.atl)
SUBS    = OGS.Pred.basin_list[:]
print('_________________ start __________________')
print('Variable:', varmod)
print('Float variable:', floatvar)
print('Sub-basin:', subname)
print('Years:', YEARS)
print('Number of depth levels:', len(z_interp))

# ============================================================
# OUTPUT ARRAYS
# ============================================================
nsub = len(SUBS)
nyear = len(YEARS)
nz = len(z_interp)

# Dimensions:
#   year, sub, depth
CLIM = np.full((nyear, nsub, nz),np.nan,dtype=np.float32)
STD = np.full((nyear, nsub, nz),np.nan,dtype=np.float32)

# Number of profiles per year/sub
NPROFILES = np.zeros((nyear, nsub),dtype=np.int32)
# Number of distinct WMO per year/sub
NWMO = np.zeros( (nyear, nsub),dtype=np.int32)
# ============================================================
# LOOP OVER YEARS AND SUB-BASINS
# ============================================================
for iyear, year in enumerate(YEARS):
    print('')
    print('================================================')
    print('YEAR:', year)
    print('================================================')
    # Time interval for the year
    datestart = f'{year}0101'
    dateend = f'{year}1231'
    TI = timerequestors.TimeInterval(starttime=datestart,endtime=dateend,dateformat='%Y%m%d')
    # Loop over sub-basins
    for isub_index, ISUB in enumerate(SUBS):
        print('')
        print('-------------', ISUB.name, '-------------')
        # Select profiles
        if ISUB.name == "ion1":
            isub = ComposedBasin('ion4',[OGS.swm2, OGS.ion2, OGS.tyr2],'Neighbors of ion1')
            Profilelist = bio_float.FloatSelector(floatvar,TI,isub)
        elif ISUB.name == "tyr1":
            isub = ComposedBasin('supertyr', [OGS.tyr2, OGS.tyr1],'tyr1and2')
            Profilelist = bio_float.FloatSelector(floatvar,TI,isub)
        else:
            Profilelist = bio_float.FloatSelector(floatvar,TI,ISUB)
        # ----------------------------------------------------
        # No profiles
        # ----------------------------------------------------
        if not Profilelist:
            print(f'No profiles for {ISUB.name} in {year} -> NaN')
            # CLIM and STD are already NaN
            # NPROFILES and NWMO are already 0
            continue
        # ----------------------------------------------------
        # Number of profiles / WMO
        # ----------------------------------------------------
        NPROFILES[iyear, isub_index] = len(Profilelist)
        NWMO[iyear, isub_index] = len(
            bio_float.get_wmo_list(Profilelist))
        print('Number of profiles:',NPROFILES[iyear, isub_index])
        print('Number of WMO:',NWMO[iyear, isub_index])
        # ----------------------------------------------------
        # Read and interpolate profiles
        # ----------------------------------------------------
        SERV_VAR = np.full((len(Profilelist), nz),np.nan, dtype=np.float32)
        valid_profiles = 0
        for PROFILE in Profilelist:
            try:
                Pres, Profile, Qc = PROFILE.read(var=floatvar)
                # Remove invalid values
                valid = (np.isfinite(Pres) & np.isfinite(Profile))
                Pres = np.asarray(Pres)[valid]
                Profile = np.asarray(Profile)[valid]
                if len(Pres) < 2:continue
                # Make sure pressure/depth is sorted
                order = np.argsort(Pres)
                Pres = Pres[order]
                Profile = Profile[order]
                Profile_interp = np.interp(z_interp,Pres, Profile,left=np.nan,right=np.nan)
                SERV_VAR[valid_profiles, :] = Profile_interp
                valid_profiles += 1
            except Exception as e:
                print(f'Warning: could not read profile: {e}')
        # ----------------------------------------------------
        # No valid profiles after reading
        # ----------------------------------------------------
        if valid_profiles == 0:
            print( f'No valid profiles for {ISUB.name}'f'in {year} -> NaN')
            NPROFILES[iyear, isub_index] = 0
            NWMO[iyear, isub_index] = 0
            continue
        # ----------------------------------------------------
        # Keep only valid profiles
        # ----------------------------------------------------
        SERV_VAR = SERV_VAR[:valid_profiles, :]
        NPROFILES[iyear, isub_index] = valid_profiles
        # ----------------------------------------------------
        # Climatology
        # ----------------------------------------------------
        CLIM[iyear, isub_index, :] = np.nanmean(SERV_VAR,axis=0)
        STD[iyear, isub_index, :] = np.nanstd(SERV_VAR,axis=0)
        print(f'Valid profiles used: {valid_profiles}')

# ============================================================
# SAVE MEAN NETCDF
# ============================================================
outfile = (OUTDIR +'/yr_Avg_' + varmod +'_superfloat.nc')
print('')
print('Saving:', outfile)
ncOUT = netCDF4.Dataset(outfile, 'w')
# Dimensions
ncOUT.createDimension('year',len(YEARS))
ncOUT.createDimension('nsub',len(SUBS))
ncOUT.createDimension('nav_lev',len(z_interp))
# Year
ncvar = ncOUT.createVariable('year','i4',('year',))
ncvar.long_name = 'year'
ncvar[:] = YEARS
# Sub-basin names
ncvar = ncOUT.createVariable('sub',str,('nsub',))
for i, sub in enumerate(SUBS):
    ncvar[i] = sub.name
# Depth
ncvar = ncOUT.createVariable('nav_lev','f4',('nav_lev',))
ncvar.long_name = 'model depth'
ncvar.units = 'm'
ncvar[:] = z_interp
# Climatology
ncvar = ncOUT.createVariable(varmod,'f4',('year', 'nsub', 'nav_lev'), fill_value=np.nan)
ncvar.long_name = (f'yearly vertical climatology of {varmod}')
ncvar[:] = CLIM
# Number profiles
ncvar = ncOUT.createVariable('NPROFILES','i4',('year', 'nsub'))
ncvar.long_name = 'number of profiles'
ncvar[:] = NPROFILES
# Number WMO
ncvar = ncOUT.createVariable('NWMO','i4', ('year', 'nsub'))
ncvar.long_name = 'number of distinct WMO'
ncvar[:] = NWMO
ncOUT.close()

# ============================================================
# SAVE STD NETCDF
# ============================================================
outfile = OUTDIR + '/yr_Std_' + varmod + '_superfloat.nc'
print('Saving:', outfile)
ncOUT = netCDF4.Dataset(outfile,'w')
# Dimensions
ncOUT.createDimension('year',len(YEARS))
ncOUT.createDimension('nsub',len(SUBS))
ncOUT.createDimension('nav_lev',len(z_interp))
# Year
ncvar = ncOUT.createVariable('year', 'i4',('year',))
ncvar.long_name = 'year'
ncvar[:] = YEARS
# Sub-basin
ncvar = ncOUT.createVariable('sub', str,('nsub',))
for i, sub in enumerate(SUBS):
    ncvar[i] = sub.name
# Depth
ncvar = ncOUT.createVariable('nav_lev','f4', ('nav_lev',))
ncvar.long_name = 'model depth'
ncvar.units = 'm'
ncvar[:] = z_interp
# Standard deviation
ncvar = ncOUT.createVariable(varmod, 'f4',('year', 'nsub', 'nav_lev'),fill_value=np.nan)
ncvar.long_name = (
    f'yearly vertical standard deviation of {varmod}')
ncvar[:] = STD
# Number profiles
ncvar = ncOUT.createVariable('NPROFILES','i4',('year', 'nsub'))
ncvar.long_name = 'number of profiles'
ncvar[:] = NPROFILES
# Number WMO
ncvar = ncOUT.createVariable( 'NWMO','i4',('year', 'nsub'))
ncvar.long_name = 'number of distinct WMO'
ncvar[:] = NWMO
ncOUT.close()

