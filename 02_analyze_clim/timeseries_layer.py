import argparse

def argument():
    parser = argparse.ArgumentParser(description = '''
    Compute tseries of var in Superfloat and Coriolis profiles 
    Mediterranean sub-basin. For every profile, extracts the var 
concentration around depth m and at the isopycnal corresponding to the mean
basin density at depth m.
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

    parser.add_argument(   '--depth','-d',
                                type = float,
                                required = True,
                                help = 'layer')
    return parser.parse_args()


args = argument()

from bitsea.commons.utils import addsep
import numpy as np
import pandas as pd
from bitsea.commons import timerequestors
from bitsea.instruments import bio_float
from bitsea.instruments import superfloat 
from bitsea.instruments.var_conversions import FLOATVARS
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
import sys
import xarray as xr
import gsw
import matplotlib.pyplot as plt
import os 
from bitsea.basins.region import Region, Rectangle
sys.path.append(os.path.abspath(".."))
from utils.basins_CA_new_bitsea import cross_Med_basins

OUTDIR = args.outdir
DEPTH = args.depth
varmod = args.variable

if DEPTH <= 100:DMIN, DMAX = DEPTH - 25, DEPTH + 25
else: DMIN, DMAX = DEPTH - 50, DEPTH + 50

plot_col = f'value_at{DEPTH}m'

os.makedirs(OUTDIR, exist_ok=True)

UNITS = {"O2o": r"$mmol\,m^{-3}$", "N3n": r"$mmol\,m^{-3}$", "P_l": r"$mg\,m^{-3}$", "vosaline": "PSU", "votemper": r"$^\circ C$", "PAR": r"$\mu E\,m^{-2}\,s^{-1}$", "pH": "-"}
VAR_UNITS = UNITS.get(varmod, varmod)
CONVERT_CORIOLIS = varmod in {"O2o", "N3n"}


# INIT
TheMask = Mask.from_file(os.environ["MASKFILE"])
z_interp= TheMask.zlevels

if OGS.atl in OGS.Pred.basin_list:
  OGS.Pred.basin_list.remove(OGS.atl) # tolgo Atlantic buffer
else: pass

SUBS    = OGS.Pred.basin_list[:]
print('_________________start__________________')
print(f'Variable: {varmod}')
print(f'Depth: {DEPTH} m')
print(f'Depth interval: {DMIN} - {DMAX} m')
print(f'Output directory: {OUTDIR}')

SUB_COUNT = 0
TI=timerequestors.TimeInterval( starttime='19500101',endtime='20280101',dateformat='%Y%m%d',)
list_basin =[]
for ISUB in SUBS:
    list_basin.append(ISUB.name)

COLUMNS = ['wmo', 'Cycle', 'time', plot_col]


def read_temp_psal(p):
    PresT, Temp, QcT = p.read('TEMP')
    Pres, Sali, QcS = p.read('PSAL')
    if (Pres is None or PresT is None or Temp is None or Sali is None
            or len(Pres) < 5 or len(PresT) < 5):
        PresT, Temp, QcT = p.read('TEMP', read_adjusted=False)
        Pres, Sali, QcS = p.read('PSAL', read_adjusted=False)
    return PresT, Temp, QcT, Pres, Sali, QcS

def convert_to_mmmolm3(p, varpres, varprofile):
    ''' from micromol/Kg to  mmol/m3'''
    if varpres.size == 0: return varprofile
    PresT, temp, Qc, Pres, sali, QcS = read_temp_psal(p)
    if len(temp) != len(sali):
        temp = np.interp(Pres, PresT, temp)
    SA = gsw.SA_from_SP(sali, Pres, p.lon, p.lat)
    density = gsw.rho(SA, gsw.CT_from_t(SA, temp, Pres), Pres)
    density_on_zvar = np.interp(varpres, Pres, density)
    return varprofile * density_on_zvar / 1000.

def convert_coriolis_profile(p, pres, profile):
    if varmod == 'O2o':
        return convert_to_mmmolm3(p, pres, profile)
    if varmod == 'N3n':
        return convert_to_mmmolm3(p, pres, profile)
    return profile
           
def collect_data_from_profiles(Profilelist, varmod, VAR_convert=False):
    rows = []
    for p in Profilelist:
        pres, profile, qc = p.read(FLOATVARS[varmod])
        if varmod=='O2o' or varmod=='N3n':
            if VAR_convert:
                 profile = convert_coriolis_profile(p, pres, profile)

        if len (profile) <5: continue
        if len(pres)<5: continue
        if pres.max()< DMIN: continue

        # media tra  DMIN,DMAX
        mask = (pres >= DMIN) & (pres <= DMAX)
        if np.any(mask): 
            value = profile[mask].mean()
        else: 
            value = np.nan 
        if np.isnan(value): continue

        #pres_temp, temp, _, pres_sali, sali, _ = read_temp_psal(p)
        rows.append({'wmo': p._my_float.wmo, 'Cycle': p._my_float.cycle, 'time': p.time.strftime('%Y%m%d'), plot_col: value})
    df_local = pd.DataFrame(rows, columns=COLUMNS)
    if not df_local.empty:
        df_local['time'] = pd.to_datetime(df_local['time'], format='%Y%m%d')
    return df_local 

for isub_index, ISUB in enumerate(SUBS):
    #if ISUB.name != 'nwm': continue
    #if isub_index < 12: continue
    print('_____________ '+ str(ISUB)  +' _____________')
    _super_Profilelist = superfloat.FloatSelector(FLOATVARS[varmod],TI, ISUB)
    _cor_Profilelist    = bio_float.FloatSelector(FLOATVARS[varmod],TI, ISUB)

    df_super = collect_data_from_profiles(_super_Profilelist,varmod, VAR_convert=False)
    df_cor = collect_data_from_profiles(_cor_Profilelist, varmod, VAR_convert=True)

    if df_super is None or df_super.empty or df_cor is None or df_cor.empty:
        print(f"Skipping {ISUB.name}: df_super={None if df_super is None else len(df_super)}, df_cor={None if df_cor is None else len(df_cor)}")
        continue
    df_super = df_super.sort_values('time')
    df_cor = df_cor.sort_values('time')

    #df_super['time'] = pd.to_datetime(df_super['time'])
    #df_super['year'] = df_super['time'].dt.year
    #df_super['month'] = df_super['time'].dt.month
    #df_cor['time'] = pd.to_datetime(df_cor['time'])
    #df_cor['year'] = df_cor['time'].dt.year
    #df_cor['month'] = df_cor['time'].dt.month
    #df_cor.to_csv(OUTDIR +'/'+ ISUB.name  + '_'+varmod+'_coriolis_at600m.csv')
    #df_super.to_csv(OUTDIR +'/'+ ISUB.name+ '_'+varmod+'_superfloat_at600m.csv')

    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
    ax = axes[0]
    ax.plot(df_super['time'], df_super[plot_col], linestyle='None', marker='o', markersize=6, markerfacecolor='red', markeredgecolor='black', alpha=0.8)
    ax.set_title(f'{ISUB.name} - Superfloat')
    ax.set_ylabel(f'{VAR_UNITS} at {DEPTH} m')
    ax.grid(True)

    ax = axes[1]
    ax.plot(df_cor['time'], df_cor[plot_col], linestyle='None', marker='o', markersize=6, markerfacecolor='black', markeredgecolor='gray', alpha=0.8)
    ax.set_title(f'{ISUB.name} - Coriolis')
    ax.set_xlabel('Time')
    ax.set_ylabel(f'{VAR_UNITS} at {DEPTH} m')
    ax.grid(True)

    fig.suptitle(f'{ISUB.name} - {varmod} at {DEPTH} m', fontsize=14)
    fig.autofmt_xdate()
    fig.tight_layout()
    outfile = os.path.join(OUTDIR, f'{ISUB.name}_{varmod}_timeseries.png')
    fig.savefig(outfile)
    plt.close(fig)
    print(f'Saved: {outfile}')

print('_________________end__________________')
