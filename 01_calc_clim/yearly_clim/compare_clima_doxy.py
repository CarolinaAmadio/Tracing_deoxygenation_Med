import argparse
import pandas as pd
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
from bitsea.static.climatology import DatasetInfo, QualityCheck, TI as STATIC_TI, get_climatology
import matplotlib.pylab as plt
from bitsea.commons.mask import Mask
import os
from bitsea.commons.utils import addsep

INDIR       = addsep(args.indir)
OUTDIR      = addsep(args.outdir)
OUTDIR      = OUTDIR + '/' + args.variable
VAR         = args.variable

UNITS = {
    "O2o": r"$mmol\,m^{-3}$",
    "N3n": r"$mmol\,m^{-3}$",
    "P_l": r"$mg\,m^{-3}$",
    "vosaline": "PSU",
    "votemper": r"$^\circ C$",
    "PAR": r"$\mu E\,m^{-2}\,s^{-1}$",
    "pH": "-",
}
_units = UNITS.get(VAR, VAR)

meshmask = os.environ["MASKFILE"]
TheMask = Mask.from_file(meshmask)
z_lev= TheMask.zlevels
#CORIOLIS='/g100_scratch/userexternal/camadio0/ARGOPY_TESTS/Climatologies_Argopy/NO_QC/__CANYON_MED_NO_QC/Yearly_Clim/'

#PresDOWN = np.array([0,25,50,75,100,125,150,200,400,600,800,1000,1500,2000,2500,3000,4000,5000])
PresDOWN = np.array([0,25,50,75,100,125,150,200,400,600,800])
LayerList = [ Layer(PresDOWN[k], PresDOWN[k+1])  for k in range(len(PresDOWN)-1) ]
LayerDepth = [ .5*(ll.bottom+ll.top) for ll in LayerList ]

z_interp=np.arange(0,200,10)
z_interp = np.append(z_interp , np.arange(200, 801, 40))
#z_interp = np.append(z_interp , np.arange(600,1001, 50))

LayerFloatDepth = [.5*(z_interp[il]+z_interp[il+1]) for il in range(len(z_interp)-1)]

SUBLIST = []
for sub in OGS.Pred.basin_list:
    if 'atl' in sub.name: continue
    SUBLIST.append(sub)

HAS_INSITU_CLIMATOLOGY = VAR not in {"votemper", "vosaline","PAR"}
if HAS_INSITU_CLIMATOLOGY:
    _emodnet = get_climatology(VAR, SUBLIST, LayerList, basin_expand=True, QC=True)
os.makedirs(OUTDIR , exist_ok=True)

# create parsing superfloat 
ncs_avg = Dataset( INDIR + '/SUPERFLOAT/yr_Avg_'+VAR+'_superfloat.nc')
ncs_std = Dataset( INDIR + '/SUPERFLOAT/yr_Std_'+VAR+'_superfloat.nc')

vs_avg = ncs_avg.variables[VAR][:]
vs_std = ncs_std.variables[VAR][:]
nprofiles = ncs_avg.variables["NPROFILES"][:]
nwmo = ncs_avg.variables["NWMO"][:]
superfloat_year_min = ncs_avg.variables["YEAR_MIN"][:]
superfloat_month_min = ncs_avg.variables["MONTH_MIN"][:]
superfloat_year_max = ncs_avg.variables["YEAR_MAX"][:]
superfloat_month_max = ncs_avg.variables["MONTH_MAX"][:]

# create parsing coriolis biofloat
ncc_avg = Dataset(  INDIR + '/CORIOLIS/yr_Avg_'+VAR+'_coriolis.nc')
ncc_std = Dataset(  INDIR + '/CORIOLIS/yr_Std_'+VAR+'_coriolis.nc')

vc_avg = ncc_avg.variables[VAR][:]
vc_std = ncc_std.variables[VAR][:]
coriolis_nprofiles = ncc_avg.variables["NPROFILES"][:]
coriolis_nwmo = ncc_avg.variables["NWMO"][:]
coriolis_year_min = ncc_avg.variables["YEAR_MIN"][:]
coriolis_month_min = ncc_avg.variables["MONTH_MIN"][:]
coriolis_year_max = ncc_avg.variables["YEAR_MAX"][:]
coriolis_month_max = ncc_avg.variables["MONTH_MAX"][:]


def format_period(year_min, month_min, year_max, month_max):
    return f"{int(year_min):04d}-{int(month_min):02d} to {int(year_max):04d}-{int(month_max):02d}"


def get_emodnet_metadata(var, subbasins, layers):
    if not HAS_INSITU_CLIMATOLOGY:
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


emodnet_metadata = get_emodnet_metadata(VAR, SUBLIST, LayerList)
summary_rows = []
for isub,sub in enumerate(SUBLIST):
    print(sub)
    fig,axs = plt.subplots(1,1,sharex=True,figsize=[7,15])
    for ii in range(1):
        #plt.sca(axs)
        # superfloat QC 
        superfloat_period = format_period(
            superfloat_year_min[isub], superfloat_month_min[isub],
            superfloat_year_max[isub], superfloat_month_max[isub]
        )
        coriolis_period = format_period(
            coriolis_year_min[isub], coriolis_month_min[isub],
            coriolis_year_max[isub], coriolis_month_max[isub]
        )
        plt.plot(
            vs_avg[isub,:], z_lev, color='tab:red', linewidth=3,
            label=f'Superfloat: {superfloat_period}'
        )
        #plt.plot(vs_std[isub,:] + vs_std[isub,:], z_lev, color='tab:red', linestyle=':')
        #plt.plot(vs_std[isub,:] - vs_std[isub,:], z_lev, color='tab:red', linestyle=':')

        # Coriolis biofloat
        plt.plot(
            vc_avg[isub,:], z_lev, color='k', linewidth=2,
            label=f'Coriolis: {coriolis_period}'
        )
        #plt.plot(vc_std[isub,:] + vc_std[isub,:], z_lev, color='silver', linestyle=':')
        #plt.plot(vc_std[isub,:] - vc_std[isub,:], z_lev, color='silver', linestyle=':')

        if HAS_INSITU_CLIMATOLOGY:
            emodnet_nprofiles, emodnet_nobs, emodnet_period = emodnet_metadata[isub]
            plt.plot(_emodnet[0][isub,:], LayerDepth, 'bo', label=f'Insitu: {emodnet_period}')
            plt.plot(_emodnet[0][isub,:] + _emodnet[1][isub,:], LayerDepth, 'b-.')
            plt.plot(_emodnet[0][isub,:] - _emodnet[1][isub,:], LayerDepth, 'b-.')
        plt.grid()

    #plt.sca(axs[0])
    plt.ylim(801,0)
    plt.title(
        f"{sub.name}\n"
        f"Superfloat: {int(nprofiles[isub])} profiles, "
        f"{int(nwmo[isub])} WMO"
    )
    plt.legend()
    #plt.sca(axs[1])
    #plt.ylim(2000,200)
    units = _units
    plt.xlabel( units)

    plt.savefig(OUTDIR +'/'+  sub.name +'_'+ VAR+'_clima_float_emodnet.png')
    plt.close()

    emodnet_nprofiles, emodnet_nobs, emodnet_period = emodnet_metadata[isub]
    summary_rows.append({
        "BASIN": sub.name,
        "EMODNET_NPROFILES": emodnet_nprofiles,
        "EMODNET_NOBS": emodnet_nobs,
        "EMODNET_DATARANGE": emodnet_period,
        "SUPERFLOAT_NPROFILES": int(nprofiles[isub]),
        "SUPERFLOAT_NWMO": int(nwmo[isub]),
        "SUPERFLOAT_DATARANGE": superfloat_period,
        "CORIOLIS_NPROFILES": int(coriolis_nprofiles[isub]),
        "CORIOLIS_NWMO": int(coriolis_nwmo[isub]),
        "CORIOLIS_DATARANGE": coriolis_period,
    })

pd.DataFrame(summary_rows).to_csv(
    OUTDIR + "/climatology_sample_summary.csv", index=False
)

import shutil 
shutil.copy('compare_clima_doxy.py'  , OUTDIR   )

