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
from bitsea.instruments import superfloat 
from bitsea.instruments.var_conversions import FLOATVARS
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask
import sys
import xarray as xr
import seawater as sw
import gsw
import matplotlib.pyplot as plt
import os 
from bitsea.basins.region import Region, Rectangle
sys.path.append(os.path.abspath(".."))
from utils.basins_CA_new_bitsea import cross_Med_basins


OUTDIR     = "DOXY_FIGS/"
os.makedirs(OUTDIR, exist_ok=True)
varmod     = "O2o"#args.variable

# INIT
TheMask=Mask.from_file("/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc")
z_interp= TheMask.zlevels

if OGS.atl in OGS.Pred.basin_list:
  OGS.Pred.basin_list.remove(OGS.atl) # tolgo Atlantic buffer
else: pass

SUBS    = OGS.Pred.basin_list[:]
print('_________________start__________________')

SUB_COUNT = 0
TI=timerequestors.TimeInterval( starttime='19500101',endtime='20280101',dateformat='%Y%m%d',)
list_basin =[]
for ISUB in SUBS:
    list_basin.append(ISUB.name)

#COLUMNS=['wmo','Cycle','DRIFT_CODE','offset', 'filename','time','value_at600m','value_at_rho_sw','value_at_rho_gsw' , 'value_rho_gsw_ins', 'value_rho_levant']

COLUMNS=['wmo','Cycle','DRIFT_CODE','offset','time','value_at600m','value_at_rho_sw','value_at_rho_gsw' , 'value_rho_gsw_ins', 'value_rho_levant']

def get_density_600m(NAME_BASIN):
    df = pd.read_csv("/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/1_clim_analysis/density_600m.csv", index_col=0)
    dfstd = pd.read_csv("/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/1_clim_analysis/density_std_600m.csv", index_col=0)
    try:
        val  = df.loc[NAME_BASIN].values[0]
        std  = dfstd.loc[NAME_BASIN].values[0]
        return val,std
    except KeyError:
        print(f"Colonna '{NAME_BASIN}' non trovata")
        return None

def convert_oxygen(p,doxypres,doxyprofile):
    '''
    from micromol/Kg to  mmol/m3
    '''
    if doxypres.size == 0: return doxyprofile
    
    Pres  , temp, _ = p.read("TEMP")
    Pres_s, sali, _ = p.read("PSAL")

    if len(Pres) < 5 :
        Pres, temp, _   = p.read("TEMP", read_adjusted=False)
    if len(Pres_s) < 5 :
        Pres_s, sali, _ = p.read("PSAL", read_adjusted=False)

    if (len(temp) > 0 and len(sali) > 0 and len(Pres) >0 and len(Pres_s) > 0 ):
        if len(Pres) == len(Pres_s) and len(Pres) > 5 :
           density = sw.dens(sali,temp,Pres)
           density_on_zdoxy = np.interp(doxypres,Pres,density)
           return doxyprofile * density_on_zdoxy/1000.
        else:
           sali = np.interp(Pres,Pres_s,sali)
           density = sw.dens(sali,temp,Pres)
           density_on_zdoxy = np.interp(doxypres,Pres,density)
           return doxyprofile * density_on_zdoxy/1000.
    else:
        return
           

def collect_data_from_profiles(Profilelist, DOXY_convert=False):
    rows = []
    for p in Profilelist:
        #if (int(p._my_float.wmo)) ==6903065:
        #        if (int(p._my_float.cycle)) == int(17):
        #            sys.exit()
        pres, profile, qc = p.read(FLOATVARS[varmod])
        if DOXY_convert:
             profile  = convert_oxygen(p,pres, profile)
        if len (profile) <5: continue
        if len(pres)<5: continue
        if pres.max()< 600: continue
        with xr.open_dataset(p._my_float.filename) as ds:
            doxy_qc = ds.get("DOXY_QC")
            if doxy_qc is None:
                offset = np.nan
                drift_code = np.nan
            else:
                offset = doxy_qc.attrs.get("offset", np.nan)
                drift_code = doxy_qc.attrs.get("drift_code", np.nan)

        # media tra 550 e 650 m
        mask = (pres >= 550) & (pres <= 650)
        if np.any(mask):value = profile[mask].mean()
        else: value = np.nan 

        value_rho_sw = np.nan
        value_rho_gsw = np.nan
        value_rho_gsw_ins = np.nan
        value_rho_levant = np.nan

        pres_temp, temp, _ = p.read("TEMP")
        pres_sali, sali, _ = p.read("PSAL")

        if len(pres_temp) < 5 : 
            pres_temp, temp, _ = p.read("TEMP", read_adjusted=False)
            #print('car')
        if len(pres_sali) < 5 : 
            pres_sali, sali, _ = p.read("PSAL", read_adjusted=False)
            #print('olin')

        pos = Rectangle(np.float64(p.lon ) , np.float64( p.lon) , np.float64(p.lat) , np.float64(p.lat))
        NAME_BASIN , BORDER_BASIN = cross_Med_basins(pos)
        
        rho_600m_per_sub , stdev= get_density_600m(NAME_BASIN)
        stdev = stdev*2 

        #print( rho_600m_per_sub ,stdev) 
        #sys.exit()
        if (len(temp) > 0 and len(sali) > 0 and len(pres_temp) > 0 and len(pres_sali) >0
            and not np.isnan(p.lat) and not np.isnan(p.lon)):
            if len(pres_sali) != (len(pres_temp)):
                sali = np.interp(pres_temp,pres_sali , sali)
            # density with gsw TEOS10 : value_at_rho_gsw
            sa = gsw.SA_from_SP(sali, pres_temp, p.lon, p.lat)
            ct = gsw.CT_from_t(sa, temp, pres_temp)
            rho_gsw     =   gsw.rho(sa, ct, pres_temp) 
            density_interp = np.interp(pres, pres_temp, rho_gsw)
            mask_rho = (density_interp >=  rho_600m_per_sub- stdev) & (density_interp <= rho_600m_per_sub + stdev)
            if np.any(mask_rho): value_rho_gsw = profile[mask_rho].mean()
            
            # density gsw t insitu : value_rho_gsw_ins
            rho_gsw_ins =   gsw.rho_t_exact(sa, temp, pres_temp)
            density_interp_ins = np.interp(pres, pres_temp, rho_gsw_ins)
            mask_rho_ins= (density_interp_ins  >= rho_600m_per_sub- stdev) & (density_interp_ins <=rho_600m_per_sub + stdev)
            if np.any(mask_rho_ins): value_rho_gsw_ins = profile[mask_rho_ins].mean()

            # density with sw:  value_at_rho_sw
            rho_sw = sw.dens(sali,temp,pres_temp)
            rho_int_sw = np.interp(pres,pres_temp,rho_sw) 
            mask_rho = (rho_int_sw >= rho_600m_per_sub - stdev) & (rho_int_sw <= rho_600m_per_sub + stdev)
            if np.any(mask_rho): value_rho_sw = profile[mask_rho].mean()

            # --- densità a lat/lon fisso Levantino ---
            lon_levant, lat_levant = 34.0, 34.0  # esempio coordinate Levantino
            sa_levant = gsw.SA_from_SP(sali, pres_temp, lon_levant, lat_levant)
            ct_levant = gsw.CT_from_t(sa_levant, temp, pres_temp)
            rho_levant = gsw.rho(sa_levant, ct_levant, pres_temp)
            interp_rho_levant = np.interp(pres, pres_temp, rho_levant)  # densità a 600 m
            mask_rho = (interp_rho_levant >= rho_600m_per_sub - stdev) & ( interp_rho_levant <= rho_600m_per_sub + stdev)
            if np.any(mask_rho): value_rho_levant = profile[mask_rho].mean()

        rows.append({
        'wmo': p._my_float.wmo,
        'Cycle': p._my_float.cycle,
        'DRIFT_CODE': drift_code,
        'offset': offset,
        #'filename': p._my_float.filename,
        'time': p.time.strftime('%Y%m%d'),
        'value_at600m': value,
        'value_at_rho_sw': value_rho_sw,
        'value_at_rho_gsw': value_rho_gsw,
        'value_rho_gsw_ins': value_rho_gsw_ins,
        'value_rho_levant': value_rho_levant})


    df_local = pd.DataFrame(rows, columns=COLUMNS)
    if not df_local.empty:
        df_local['time'] = pd.to_datetime(df_local['time'], format='%Y%m%d')
    return df_local

for ISUB in SUBS:
    if ISUB.name != 'alb': continue
    print('_____________ '+ str(ISUB)  +' _____________')
    _super_Profilelist = superfloat.FloatSelector(FLOATVARS[varmod],TI, ISUB)
    _cor_Profilelist    = bio_float.FloatSelector(FLOATVARS[varmod],TI, ISUB)

    df_super = collect_data_from_profiles(_super_Profilelist, DOXY_convert=False)

    df_super = df_super.sort_values('time') 
    df_cor = collect_data_from_profiles(_cor_Profilelist, DOXY_convert=True)
    df_cor = df_cor.sort_values('time')

    df_super['time'] = pd.to_datetime(df_super['time'])
    df_super['year'] = df_super['time'].dt.year
    df_super['month'] = df_super['time'].dt.month
    df_cor['time'] = pd.to_datetime(df_cor['time'])
    df_cor['year'] = df_cor['time'].dt.year
    df_cor['month'] = df_cor['time'].dt.month

    df_cor.to_csv(OUTDIR +'/'+ ISUB.name+ '_coriolis_oxy_at600m.csv')
    df_super.to_csv(OUTDIR +'/'+ ISUB.name+ '_superfloat_oxy_at600m.csv')
    
    # plot dnesity at ca 600m 
    ax = df_super.plot(x='time',y=df_super.columns[-7:-2],style='o',markersize=10,alpha=0.5,title='Superfloat')
    fig = ax.get_figure()
    fig.savefig(OUTDIR +'/'+ ISUB.name + "_superfloat.png", bbox_inches='tight')

    ax = df_cor.plot(x='time',y=df_cor.columns[-7:-2],style='o', markersize=10,alpha=0.3, title='Coriolis')
    fig = ax.get_figure()
    fig.savefig(OUTDIR +'/'+  ISUB.name + "_coriolis.png", bbox_inches='tight')

    #plt.show()
    #sys.exit()
    #cutoff = pd.Timestamp('2025-10-31')

    #df_super_recent = df_super[df_super['time'] > cutoff]
    #df_cor_recent   = df_cor[df_cor['time'] > cutoff]
    
    sys.exit()
    if (not df_super.empty) and (not df_cor.empty):

        df_mean_super = df_super.groupby('time')['value_at600m'].mean().reset_index()
        df_mean_cor   = df_cor.groupby('time')['value_at600m'].mean().reset_index()

        # media globale (per titolo)
        mean_super = df_mean_super['value_at600m'].mean()
        mean_cor   = df_mean_cor['value_at600m'].mean()

        plt.figure(figsize=(10,6))

        # superfloat → verde scuro, bordo nero
        plt.plot(
            df_mean_super['time'],
            df_mean_super['value_at600m'],
            linestyle='None',
            marker='o',
            markersize=12,
            markerfacecolor='red',
            markeredgecolor='black',
            markeredgewidth=1.5,
            label=f'Superfloat (mean={mean_super:.2f})'
        )

        # coriolis → verde chiaro, bordo bianco
        plt.plot(
            df_mean_cor['time'],
            df_mean_cor['value_at600m'],
            linestyle='None',
            marker='o',
            markersize=6,
            markerfacecolor='black',
            markeredgecolor='gray',
            markeredgewidth=1.2,
            label=f'Coriolis (mean={mean_cor:.2f})'
        )

        plt.xlabel('Time')
        plt.ylabel('Oxygen at 600 m')
        plt.xticks(rotation=45)

        plt.title(
            ISUB.name +
            f' Mean Oxygen at 600 m\nSuperfloat={mean_super:.2f} | Coriolis={mean_cor:.2f}'
        )

        plt.legend()
        plt.grid()
        plt.tight_layout()

        plt.savefig(OUTDIR + '/' + ISUB.name + '_comparison_oxy_at600m.png')
        plt.close()
        
    
"""    
    if not df_super.empty:
        df_mean_super = df_super.groupby('time')['value_at600m'].mean().reset_index()
        plt.figure()
        plt.plot(df_mean_super['time'], df_mean_super['value_at600m'])
        plt.xlabel('Time')
        plt.xticks(rotation=45)
        plt.ylabel('Oxygen at 600 m')
        plt.title(ISUB.name + ' Mean Oxygen at 600 m (superfloat) profiles with drift: ' + str(len(df_super[df_super.DRIFT_CODE==1])) + ' over ' + str(len(df_super)))
        plt.grid()
        plt.savefig(OUTDIR + '/' + ISUB.name + '_superfloat_oxy_at600m.png')

    # save and plot coriolis
    df_cor.to_csv(OUTDIR + '/' + ISUB.name + '_coriolis_oxy_at600m.csv', index=False)
    if not df_cor.empty:
        df_mean_cor = df_cor.groupby('time')['value_at600m'].mean().reset_index()
        plt.figure()
        plt.plot(df_mean_cor['time'], df_mean_cor['value_at600m'])
        plt.xticks(rotation=45) 
        plt.xlabel('Time')
        plt.ylabel('Oxygen at 600 m')
        plt.title(ISUB.name + ' Mean Oxygen at 600 m (coriolis) profiles with drift: ' + str(len(df_cor[df_cor.DRIFT_CODE==1])) + ' over ' + str(len(df_cor)))
        plt.grid()
        plt.savefig(OUTDIR + '/' + ISUB.name + '_coriolis_oxy_at600m.png')
"""

