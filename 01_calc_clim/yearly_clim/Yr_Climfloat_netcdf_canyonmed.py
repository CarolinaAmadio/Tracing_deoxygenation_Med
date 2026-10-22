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
from bitsea.commons import timerequestors
from bitsea.instruments import float_canyonmed
from bitsea.instruments import float_canyonmed as bio_float
from bitsea.instruments.var_conversions import CANYONVAR
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


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
    fig, axs = plt.subplots(1, 1, figsize=(10, 6))
    for profile_index, month in enumerate(profile_months):
        season = SEASON_MONTHS[month]
        plt.plot(
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
    plt.legend(handles=legend_handles, title="Season")
    plt.gca().invert_yaxis()  # Inverte l'asse y per simulare la profondità crescente verso il basso
    plt.ylabel( varmod )
    plt.xlabel("depth (m)")
    plt.title("All profiles " + namesub)

    plt.tight_layout()
    plt.savefig(OUTDIR + '/' + namesub + '_' + varmod + '_canyonmed.png')
    df.to_csv(OUTDIR + '/' + namesub + '_' + varmod + '_canyonmed.csv')

OUTDIR     = addsep(args.outdir)
varmod     = args.variable

CANYON_VARS = {"N3n", "N1p", "DIC", "N5s", "ALK", "pH"}
if varmod not in CANYON_VARS:
    raise ValueError(f"This script only supports CanyonMED variables: {sorted(CANYON_VARS)}")

# INIT
TheMask = Mask.from_file(os.environ["MASKFILE"])
z_interp= TheMask.zlevels

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

SUB_COUNT = 0
TI=timerequestors.TimeInterval(
    starttime='19500101',
    endtime='20280101',
    dateformat='%Y%m%d',
)

for ISUB in SUBS:
       #if ISUB.name != "nwm": continue
       print('_____________ '+ str(ISUB)  +' _____________')
       Profilelist     = float_canyonmed.FloatSelector(CANYONVAR[varmod],TI, ISUB ) 
        
       if (ISUB.name == "ion1"):
           isub = ComposedBasin('ion4', [OGS.swm2, OGS.ion2, OGS.tyr2], 'Neighbors of ion1')
           Profilelist     = float_canyonmed.FloatSelector(CANYONVAR[varmod],TI, ISUB )

       elif (ISUB.name == "tyr1"):
           isub = ComposedBasin('supertyr', [OGS.tyr2, OGS.tyr1], 'tyr1and2')
           Profilelist     = float_canyonmed.FloatSelector(CANYONVAR[varmod],TI, ISUB )
       else:
           Profilelist     = float_canyonmed.FloatSelector(CANYONVAR[varmod],TI, ISUB )

       if Profilelist:
           print("number of profiles used")
           print(len(Profilelist))

           SERV_VAR = np.full((len(Profilelist), len(z_interp)), np.nan, dtype=np.float32)
           ICONT = 0
           profile_months = []
           for PROFILE in Profilelist:
               if not PROFILE._my_float.has_canyonmed(CANYONVAR[varmod] ):
                   continue
               #print (PROFILE._my_float.filename)
               profile_months.append(PROFILE.time.month)

               Pres, Profile, Qc = PROFILE.read(var=CANYONVAR[varmod] , var_mod=None, sourcedata='canyon_med')
               if np.all(Qc > 0):
                   raise ValueError("No canyonmed was read")
               Profile_interp = np.interp(z_interp, Pres, Profile)

               SERV_VAR[ICONT, :] = Profile_interp
               ICONT += 1

           df = pd.DataFrame(SERV_VAR).T
           namesub = ISUB.name
           plot_line_profiles(df, z_interp, namesub, CANYONVAR[varmod], profile_months)

           serv_P = np.nanmean(SERV_VAR, axis=0)  # allprofiles | aLB | ALL Z [:]
           serv_S = np.nanstd(SERV_VAR, axis=0)
           CLIM[SUB_COUNT, :] = serv_P
           STD[SUB_COUNT, :] = serv_S
           SUB_COUNT += 1

       else:
           continue

#mean
import netCDF4 
outfile=OUTDIR+ '/yr_Avg_'+varmod+'_canyonmed.nc' 

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
outfile=OUTDIR + '/yr_Std_'+varmod+'_canyonmed.nc'

ncOUT = netCDF4.Dataset( outfile,'w')
ncOUT.createDimension('nsub',len(SUBS) )
ncOUT.createDimension('nav_lev',  len(z_interp) )
ncvar=ncOUT.createVariable(varmod,'f',('nsub','nav_lev'))
ncvar[:]=(STD)
ncOUT.close()

import shutil
shutil.copy('Yr_Climfloat_netcdf_canyonmed.py'  , OUTDIR)
