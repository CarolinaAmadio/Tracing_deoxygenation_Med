import argparse

def argument():
    parser = argparse.ArgumentParser(description = '''
    This script computes yearly vertical climatologies of a given BGC-Argo variable for different Mediterranean sub-basins.
    **Input**: BGC-Argo float profiles selected for a given variable (--variable) and time range.
    **Method**: For each sub-basin, profiles are interpolated on the model depth levels, and vertical averages and standard deviations are computed.
    **Output**:
     - PNG figures showing all vertical profiles per sub-basin.
     - CSV files with the interpolated profile data.
     - NetCDF files containing the vertical climatologies:
         - yr_Avg_<variable>.nc: mean values
         - yr_Std_<variable>.nc: standard deviations
    ''', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(   '--outdir','-o',
                                type = str,
                                required = True,
                                help = 'input dir validation tmp')


    parser.add_argument(   '--variable', '-v',
                                type = str,
                                default = None,
                                required = True,
                                help = '''model variable''')
    return parser.parse_args()


args = argument()

from bitsea.commons.utils import addsep
import numpy as np
import pandas as pd
import os
from bitsea.commons import timerequestors
from bitsea.instruments import superfloat
from bitsea.instruments import superfloat as bio_float
from bitsea.instruments.var_conversions import FLOATVARS
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import xarray as xr
import sys 
sys.exit()


SEASON_COLORS = {
  "Winter": "#2166ac",
  "Spring": "#66bd63",
  "Summer": "#d73027",
  "Autumn": "#d8a31a",
}

SEASON_MONTHS = {
  12: "Winter", 1: "Winter", 2: "Winter",
  3: "Spring", 4: "Spring", 5: "Spring",
  6: "Summer", 7: "Summer", 8: "Summer",
  9: "Autumn", 10: "Autumn", 11: "Autumn",
}


def plot_line_profiles(df, z_interp, namesub, varmod, profile_months):
  fig, ax = plt.subplots(1, 1, figsize=(10, 6))
  for profile_index, month in enumerate(profile_months):
    season = SEASON_MONTHS[month]
    ax.plot(
      df.iloc[:, profile_index],
      z_interp,
      color=SEASON_COLORS[season],
      alpha=0.25,
      linewidth=0.8,
    )

  legend_handles = [
    Line2D([0], [0], color=SEASON_COLORS[season], linewidth=3, label=season)
    for season in SEASON_COLORS
  ]
  ax.legend(handles=legend_handles, title="Season")
  ax.invert_yaxis()
  ax.set_ylabel(varmod)
  ax.set_xlabel("depth (m)")
  ax.set_title("All profiles " + namesub)

  plt.tight_layout()
  plt.savefig(OUTDIR + '/' + namesub + '_' + varmod + '_superfloat.png')
  df.to_csv(OUTDIR + '/' + namesub + '_' + varmod + '_superfloat.csv')
  plt.close(fig)


OUTDIR   = addsep(args.outdir)
varmod   = args.variable
TheMask = Mask.from_file(os.environ["MASKFILE"])
z_interp = TheMask.zlevels
MONTHS   = np.arange(1,13)

if OGS.atl in OGS.Pred.basin_list:
  OGS.Pred.basin_list.remove(OGS.atl) # tolgo Atlantic buffer
else: pass

SUBS    = OGS.Pred.basin_list[:]
CLIM    = np.zeros((len(SUBS),  len(z_interp) ), np.float32)*np.nan
STD     = np.zeros((len(SUBS),  len(z_interp) ), np.float32)*np.nan
NPROFILES = np.zeros(len(SUBS), dtype=np.int32)
NWMO = np.zeros(len(SUBS), dtype=np.int32)
YEAR_MIN = np.zeros(len(SUBS), dtype=np.int32)
MONTH_MIN = np.zeros(len(SUBS), dtype=np.int32)
YEAR_MAX = np.zeros(len(SUBS), dtype=np.int32)
MONTH_MAX = np.zeros(len(SUBS), dtype=np.int32)
print('_________________start__________________')

TI=timerequestors.TimeInterval(starttime='19500101',endtime='20280101',dateformat='%Y%m%d')

for isub_index, ISUB in enumerate(SUBS):
    print('_____________ ' + str(ISUB) + ' _____________')
    Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, ISUB)
    if ISUB.name == "ion1":
      isub = ComposedBasin('ion4', [OGS.swm2, OGS.ion2, OGS.tyr2], 'Neighbors of ion1')
      Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, isub)
    elif ISUB.name == "tyr1":
      isub = ComposedBasin('supertyr', [OGS.tyr2, OGS.tyr1], 'tyr1and2')
      Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, isub)
    else:
      Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, ISUB)

    if not Profilelist:
      continue 

    print('number of profiles used', flush=True)
    print(len(Profilelist), flush=True) 
    
    NPROFILES[isub_index] = len(Profilelist)
    NWMO[isub_index] = len(bio_float.get_wmo_list(Profilelist))
    profile_dates = [profile.time for profile in Profilelist]
    date_min = min(profile_dates)
    date_max = max(profile_dates)
    YEAR_MIN[isub_index] = date_min.year
    MONTH_MIN[isub_index] = date_min.month
    YEAR_MAX[isub_index] = date_max.year
    MONTH_MAX[isub_index] = date_max.month
    print("number of WMO used")
    print(NWMO[isub_index])
    SERV_VAR = np.full((len(Profilelist), len(z_interp)), np.nan, dtype=np.float32)
    profile_months = []
    ICONT = 0
    for PROFILE in Profilelist:
      profile_months.append(PROFILE.time.month)
      Pres, Profile, Qc = PROFILE.read(var=FLOATVARS[varmod])
      Profile_interp = np.interp(z_interp, Pres, Profile, left=np.nan, right=np.nan)
      SERV_VAR[ICONT, :] = Profile_interp
      ICONT += 1
    if not profile_months:
      print("no valid profiles after filtering; skipping basin")
      continue

    df = pd.DataFrame(SERV_VAR).T
    namesub = ISUB.name
    plot_line_profiles(df, z_interp, namesub, FLOATVARS[varmod], profile_months)
    serv_P = np.nanmean(SERV_VAR, axis=0)
    serv_S = np.nanstd(SERV_VAR, axis=0)
    CLIM[isub_index, :] = serv_P
    STD[isub_index, :] = serv_S

#mean
import netCDF4 
outfile=OUTDIR + '/yr_Avg_'+varmod+'_superfloat.nc'
ncOUT = netCDF4.Dataset(outfile,'w')
ncOUT.createDimension('nsub',len(SUBS) )
ncOUT.createDimension('nav_lev',  len(z_interp) )
ncvar=ncOUT.createVariable(varmod,'f',('nsub','nav_lev'))
ncvar[:]=(CLIM)
ncvar=ncOUT.createVariable('NPROFILES','i4',('nsub',))
ncvar.long_name = 'number of profiles'
ncvar[:] = NPROFILES
ncvar=ncOUT.createVariable('NWMO','i4',('nsub',))
ncvar.long_name = 'number of distinct WMO'
ncvar[:] = NWMO
for name, long_name, values in [
    ('YEAR_MIN', 'year of earliest profile', YEAR_MIN),
    ('MONTH_MIN', 'month of earliest profile', MONTH_MIN),
    ('YEAR_MAX', 'year of latest profile', YEAR_MAX),
    ('MONTH_MAX', 'month of latest profile', MONTH_MAX),
]:
  ncvar = ncOUT.createVariable(name, 'i4', ('nsub',))
  ncvar.long_name = long_name
  ncvar[:] = values
ncOUT.close()

#std
outfile=OUTDIR + '/yr_Std_'+varmod+'_superfloat.nc'
ncOUT = netCDF4.Dataset( outfile,'w')
ncOUT.createDimension('nsub',len(SUBS) )
ncOUT.createDimension('nav_lev',  len(z_interp) )
ncvar=ncOUT.createVariable(varmod,'f',('nsub','nav_lev'))
ncvar[:]=(STD)
ncOUT.close()

import shutil
shutil.copy('Yr_Climfloat_netcdf_superfloat.py'  , OUTDIR)
