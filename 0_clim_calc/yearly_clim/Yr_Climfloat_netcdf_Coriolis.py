import argparse

def argument():
    parser = argparse.ArgumentParser(description = '''
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
from bitsea.instruments import bio_float
from bitsea.instruments import bio_float as bio_float
from bitsea.instruments.var_conversions import FLOATVARS
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
import sys
import seawater as sw
import xarray as xr
import matplotlib.pyplot as plt


def plot_line_profiles(df, z_interp, namesub, varmod):
    fig, axs = plt.subplots(1, 1, figsize=(10, 6))
    plt.plot(df.values, z_interp, alpha=0.3)
    plt.gca().invert_yaxis()  # Inverte l'asse y per simulare la profondità crescente verso il basso
    plt.ylabel(varmod)
    plt.xlabel("depth (m)")
    plt.title("All profiles " + namesub)

    plt.tight_layout()
    plt.savefig(OUTDIR + '/' + namesub+ '_' + varmod + '_coriolis_ogs.png'  )
    df.to_csv(OUTDIR   + '/' + namesub+ '_' + varmod + '_coriolis_ogs.csv')

def convert_umolkg_to_mmolm3(new_ds,Pres,Profile,VARNAME='DOXY'):
    """
    Convert DOXY from µmol/kg to mmol/m3 using TEOS-10 density.
    Works with both 1D and 2D (N_PROF, N_LEVELS) inputs.
    """
    density = sw.dens(new_ds['PSAL'], new_ds['TEMP'], new_ds['PRES'])
    # --- Compute density (kg/m3) ---
    density = np.squeeze(density)  # remove possible extra dims
    Pres_phy= np.squeeze(new_ds['PRES'])
    if len(density) != len(Pres):
       density  = np.interp( Pres,  Pres_phy, density, left=np.nan, right=np.nan)
    # --- Conversione  ---
    Profile = np.squeeze(Profile  * density / 1000.0)
    return(Pres,Profile)

OUTDIR     = addsep(args.outdir)
varmod     = args.variable

# INIT
TheMask=Mask.from_file("/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc")
z_interp= TheMask.zlevels

if OGS.atl in OGS.Pred.basin_list:
  OGS.Pred.basin_list.remove(OGS.atl) # tolgo Atlantic buffer
else: pass

SUBS    = OGS.Pred.basin_list[:]
CLIM    = np.zeros((len(SUBS),  len(z_interp) ), np.float32)*np.nan
STD     = np.zeros((len(SUBS),  len(z_interp) ), np.float32)*np.nan
print('_________________start__________________', flush=True)

SUB_COUNT = 0
TI=timerequestors.TimeInterval(
    starttime='19500101',
    endtime='20280101',
    dateformat='%Y%m%d',
)
for ISUB in SUBS:
       print('_____________ '+ str(ISUB)  +' _____________' , flush=True)

       Profilelist     = bio_float.FloatSelector(FLOATVARS[varmod],TI, ISUB )

       if (ISUB.name == "ion1"):
           isub = ComposedBasin('ion4', [OGS.swm2, OGS.ion2, OGS.tyr2], 'Neighbors of ion1')
           Profilelist     = bio_float.FloatSelector(FLOATVARS[varmod],TI, isub )
       elif (ISUB.name == "tyr1"):
           isub = ComposedBasin('supertyr', [OGS.tyr2,OGS.tyr1], 'tyr1and2')
           Profilelist     = bio_float.FloatSelector(FLOATVARS[varmod],TI, isub)
       else:
           Profilelist     = bio_float.FloatSelector(FLOATVARS[varmod],TI, ISUB )
       if Profilelist:
         print("number of profiles used",flush=True)  
         print(len(Profilelist), flush=True)  
         
         SERV_VAR = np.full((len(Profilelist), len(z_interp)), np.nan, dtype=np.float32)
         ICONT=0
         for PROFILE in Profilelist:
             Pres, Profile, Qc = PROFILE.read(var=FLOATVARS[varmod])
             if len(Pres) <5: continue
             if varmod == 'O2o': # converto in units
                     new_ds = xr.open_dataset(PROFILE._my_float.filename)
                     Pres,Profile = convert_umolkg_to_mmolm3(new_ds, Pres,Profile)
             Profile_interp = np.interp(z_interp, Pres, Profile , left=np.nan,right=np.nan)
             SERV_VAR[ICONT, :] = Profile_interp
             ICONT+=1
              
       else:
         continue
       df =pd.DataFrame(SERV_VAR)
       df=df.T
       namesub=ISUB.name
       plot_line_profiles(df, z_interp, namesub ,FLOATVARS[varmod])


       serv_P =  np.nanmean(SERV_VAR,axis=0) # allprofiles | aLB [0] | ALL Z [:]
       serv_S =  np.nanstd(SERV_VAR,axis=0)
       CLIM[SUB_COUNT, :] = serv_P
       STD[SUB_COUNT, :]  = serv_S
       SUB_COUNT+=1

#mean
import netCDF4 
outfile=OUTDIR + '/yr_Avg_'+varmod+'_coriolis_ogs.nc'
ncOUT = netCDF4.Dataset(outfile,'w')
ncOUT.createDimension('nsub',len(SUBS) )
ncOUT.createDimension('nav_lev',  len(z_interp) )
ncvar=ncOUT.createVariable(varmod,'f',('nsub','nav_lev'))
ncvar[:]=(CLIM)
ncOUT.close()

#std
outfile=OUTDIR + '/yr_Std_'+varmod+'_coriolis_ogs.nc'
ncOUT = netCDF4.Dataset( outfile,'w')
ncOUT.createDimension('nsub',len(SUBS) )
ncOUT.createDimension('nav_lev',  len(z_interp) )
ncvar=ncOUT.createVariable(varmod,'f',('nsub','nav_lev'))
ncvar[:]=(STD)
ncOUT.close()

import shutil
shutil.copy('Yr_Climfloat_netcdf_Coriolis.py'  , OUTDIR)
