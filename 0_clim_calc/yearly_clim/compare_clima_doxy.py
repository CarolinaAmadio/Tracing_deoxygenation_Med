import argparse
def argument():
    parser = argparse.ArgumentParser(description = '''
    counts the available BGC-Argo float profiles per basin and plots their monthly distribution.
    ''', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(   '--indir','-i',
                                type = str,
                                required = True,
                                help = ' netcdf inputs')

    parser.add_argument(   '--outdir','-o',
                                type = str,
                                required = True,
                                help = 'output to save png')



    parser.add_argument(   '--variable', '-v', type = str,
                                default = None,
                                required = True,
                                help = '''model variable''')
    return parser.parse_args()


args = argument()

import numpy as np
from bitsea.commons.layer import Layer
from bitsea.basins import V2 as OGS
from netCDF4 import Dataset
from bitsea.static.climatology import get_climatology
import matplotlib.pylab as plt
from bitsea.commons.mask import Mask
import os
from bitsea.commons.utils import addsep

INDIR       = addsep(args.indir)
OUTDIR      = addsep(args.outdir)
OUTDIR      = OUTDIR + '/' + args.variable
VAR         = args.variable
TheMask=Mask.from_file("/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc")
z_lev= TheMask.zlevels
CORIOLIS='/g100_scratch/userexternal/camadio0/ARGOPY_TESTS/Climatologies_Argopy/NO_QC/__CANYON_MED_NO_QC/Yearly_Clim/'

PresDOWN = np.array([0,25,50,75,100,125,150,200,400,600,800,1000,1500,2000,2500,3000,4000,5000])
LayerList = [ Layer(PresDOWN[k], PresDOWN[k+1])  for k in range(len(PresDOWN)-1) ]
LayerDepth = [ .5*(ll.bottom+ll.top) for ll in LayerList ]

z_interp=np.arange(0,200,10)
z_interp = np.append(z_interp , np.arange(200, 600, 40))
z_interp = np.append(z_interp , np.arange(600,1001, 50))

LayerFloatDepth = [.5*(z_interp[il]+z_interp[il+1]) for il in range(len(z_interp)-1)]

SUBLIST = []
for sub in OGS.Pred.basin_list:
    if 'atl' in sub.name: continue
    SUBLIST.append(sub)

_emodnet = get_climatology( VAR,SUBLIST, LayerList, basin_expand=True, QC=True)
os.makedirs(OUTDIR , exist_ok=True)
_units = r"mmol\,m^{-3}"

# create parsing superfloat 
ncs_avg = Dataset( INDIR + '/SUPERFLOAT/yr_Avg_superfloat_dataset_O2o.nc')
ncs_std = Dataset( INDIR + '/SUPERFLOAT/yr_Std_superfloat_dataset_O2o.nc') #VAR

vs_avg = ncs_avg.variables[VAR][:]
vs_std = ncs_std.variables[VAR][:]

# create parsing coriolis biofloat
ncc_avg = Dataset(  INDIR + '/CORIOLIS/yr_Avg_O2o_coriolis_ogs.nc')
ncc_std = Dataset(  INDIR + '/CORIOLIS/yr_Std_O2o_coriolis_ogs.nc')

vc_avg = ncc_avg.variables[VAR][:]
vc_std = ncc_std.variables[VAR][:]

for isub,sub in enumerate(SUBLIST):
    print(sub)
    fig,axs = plt.subplots(2,1,sharex=True,figsize=[7,15])
    for ii in range(2):
        plt.sca(axs[ii])
        # superfloat QC 
        plt.plot(vs_avg[isub,:], z_lev, color='tab:red', linewidth=3, label='Superfloat')
        #plt.plot(vs_std[isub,:] + vs_std[isub,:], z_lev, color='tab:red', linestyle=':')
        #plt.plot(vs_std[isub,:] - vs_std[isub,:], z_lev, color='tab:red', linestyle=':')

        # Coriolis biofloat
        plt.plot(vc_avg[isub,:], z_lev, color='k', linewidth=2, label='Corilis_ogs')
        #plt.plot(vc_std[isub,:] + vc_std[isub,:], z_lev, color='silver', linestyle=':')
        #plt.plot(vc_std[isub,:] - vc_std[isub,:], z_lev, color='silver', linestyle=':')

        # Coriolis standard Mode
        #file_no_qc = Dataset(CORIOLIS+'/'+sub.name+'_annual_clim.nc')
        #std_no_qc  = Dataset(CORIOLIS+'/'+ sub.name+'_annual_clim_std.nc')
        #v_coriolis = file_no_qc.variables['DOXY'][:]
        #st_coriolis= std_no_qc.variables['DOXY'][:]
        #plt.plot(v_coriolis, z_lev, color='dodgerblue', linewidth=3, label='STD.M_Coriolis')
        #plt.plot(v_coriolis + st_coriolis, z_lev, color='tab:pink', linestyle=':')
        #plt.plot(v_coriolis - st_coriolis, z_lev, color='tab:pink', linestyle=':')
            
        plt.plot(_emodnet[0][isub,:], LayerDepth,  'bo', label='Insitu')
        plt.plot(_emodnet[0][isub,:] + _emodnet[1][isub,:], LayerDepth, 'b-.')
        plt.plot(_emodnet[0][isub,:] - _emodnet[1][isub,:], LayerDepth, 'b-.')
        plt.grid()

    plt.sca(axs[0])
    plt.ylim(200,0)
    plt.title(sub.name)
    plt.legend()
    plt.sca(axs[1])
    plt.ylim(2000,200)
    units = _units
    plt.xlabel( units)

    plt.savefig(OUTDIR +'/'+  sub.name +'_'+ VAR+'_clima_float_emodnet.png')
    plt.close()


import shutil 
shutil.copy('compare_clima_doxy.py'  , OUTDIR   )

