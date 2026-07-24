import argparse

def argument():
    parser = argparse.ArgumentParser(description = '''
    Compute tseries of oxy in Superfloat and Coriolis profiles 
    Mediterranean sub-basin. For every profile, extracts the oxygen
concentration around 600 m and at the isopycnal corresponding to the mean
basin density at 600 m.
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
import gsw
import matplotlib.pyplot as plt
import os 
from bitsea.basins.region import Region, Rectangle
sys.path.append(os.path.abspath(".."))
from utils.basins_CA_new_bitsea import cross_Med_basins

OUTDIR     = "plots/"
os.makedirs(OUTDIR, exist_ok=True)
varmod     = "O2o"#args.variable
plot_cols  = ['value_at600m', 'value_at_rho_gsw']


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

COLUMNS=['wmo','Cycle','DRIFT_CODE','offset','time','value_at600m','value_at_rho_gsw','depth_at_rho_gsw']

def get_density_600m(NAME_BASIN):
    df = pd.read_csv("/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/02_analyze_clim//density_600m.csv", index_col=0)
    dfstd = pd.read_csv("/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/02_analyze_clim//density_std_600m.csv", index_col=0)
    try:
        val  = df.loc[NAME_BASIN].values[0]
        std  = dfstd.loc[NAME_BASIN].values[0]
        return val,std
    except KeyError:
        print(f"Colonna '{NAME_BASIN}' non trovata")
        return None

def read_temp_psal(p):
    PresT, Temp, QcT = p.read('TEMP')
    Pres, Sali, QcS = p.read('PSAL')
    if (Pres is None or PresT is None or Temp is None or Sali is None or len(Pres) < 5 or len(PresT) < 5):
        PresT, Temp, QcT = p.read('TEMP', read_adjusted=False)
        Pres, Sali, QcS = p.read('PSAL', read_adjusted=False)
    return PresT, Temp, QcT, Pres, Sali, QcS


def convert_oxygen(p, doxypres, doxyprofile):
    ''' from micromol/Kg to  mmol/m3'''
    if doxypres.size == 0: return doxyprofile
    PresT, temp, Qc, Pres, sali, QcS = read_temp_psal(p)
    if len(temp) != len(sali):
        temp = np.interp(Pres, PresT, temp)
    SA = gsw.SA_from_SP(sali, Pres, p.lon, p.lat)
    density = gsw.rho(SA, gsw.CT_from_t(SA, temp, Pres), Pres)
    density_on_zdoxy = np.interp(doxypres, Pres, density)
    return doxyprofile * density_on_zdoxy / 1000.
           

def get_rho_layer(mask_rho, profile, pres, density_interp, rho_600m_per_sub, lat): 
    '''calculate value and depth at density'''
    
    if np.any(mask_rho): 
       value_rho = profile[mask_rho].mean()
       pres_rho = pres[mask_rho].mean()
    else: 
       idx = np.argmin(np.abs(density_interp - rho_600m_per_sub))
       if np.abs(density_interp[idx] - rho_600m_per_sub) <= 0.1:
            idx_sort = np.argsort(density_interp)
            rho_sorted = density_interp[idx_sort]
            pres_sorted = pres[idx_sort]
            prof_sorted = profile[idx_sort]
            value_rho = np.interp(rho_600m_per_sub, rho_sorted, prof_sorted)
            pres_rho = np.interp(rho_600m_per_sub, rho_sorted, pres_sorted)
       else:
            return np.nan, np.nan

    depth_rho = -gsw.z_from_p(pres_rho, lat)
    return value_rho, depth_rho


def collect_data_from_profiles(Profilelist, DOXY_convert=False):
    rows = []
    for p in Profilelist:
        #if (int(p._my_float.wmo)) ==6903065:
        #        if (int(p._my_float.cycle)) == int(17):
        #            sys.exit()
        
        # convert doxy in coriolis with sw
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

        value_rho_gsw = np.nan
        depth_at_rho_gsw = np.nan

        pres_temp, temp, _, pres_sali, sali, _ = read_temp_psal(p)

        pos = Rectangle(np.float64(p.lon ) , np.float64( p.lon) , np.float64(p.lat) , np.float64(p.lat))
        NAME_BASIN , BORDER_BASIN = cross_Med_basins(pos)
        
        rho_600m_per_sub , stdev= get_density_600m(NAME_BASIN)
        stdev = stdev*2 

        if (len(temp) > 0 and len(sali) > 0 and len(pres_temp) > 0 and len(pres_sali) >0
            and not np.isnan(p.lat) and not np.isnan(p.lon)):
            if len(pres_sali) != (len(pres_temp)):
                sali = np.interp(pres_temp,pres_sali , sali)
            
            # density with gsw TEOS10 : value_at_rho_gsw
            sa = gsw.SA_from_SP(sali, pres_temp, p.lon, p.lat)
            ct = gsw.CT_from_t(sa, temp, pres_temp)
            rho_gsw = gsw.rho(sa, ct, pres_temp)
            density_interp = np.interp(pres, pres_temp, rho_gsw)
            mask_rho = (density_interp >= rho_600m_per_sub - stdev) & (density_interp <= rho_600m_per_sub + stdev)
            value_rho_gsw, depth_at_rho_gsw = get_rho_layer(
                mask_rho,
                profile,
                pres,
                density_interp,
                rho_600m_per_sub,
                p.lat
            )

        rows.append({
        'wmo': p._my_float.wmo,
        'Cycle': p._my_float.cycle,
        'DRIFT_CODE': drift_code,
        'offset': offset,
        #'filename': p._my_float.filename,
        'time': p.time.strftime('%Y%m%d'),
        'value_at600m': value,
        'value_at_rho_gsw': value_rho_gsw,
        'depth_at_rho_gsw': depth_at_rho_gsw})


    df_local = pd.DataFrame(rows, columns=COLUMNS)
    if not df_local.empty:
        df_local['time'] = pd.to_datetime(df_local['time'], format='%Y%m%d')
    return df_local

for ISUB in SUBS:
    #if ISUB.name != 'alb': continue
    print('_____________ '+ str(ISUB)  +' _____________')
    _super_Profilelist = superfloat.FloatSelector(FLOATVARS[varmod],TI, ISUB)
    _cor_Profilelist    = bio_float.FloatSelector(FLOATVARS[varmod],TI, ISUB)

    df_super = collect_data_from_profiles(_super_Profilelist, DOXY_convert=False)

    df_super = df_super.sort_values('time') 
    df_cor = collect_data_from_profiles(_cor_Profilelist, DOXY_convert=True)
    df_cor = df_cor.sort_values('time')

    if df_super.empty or df_cor.empty:
        print(f"Skipping {ISUB.name}: df_super.empty={df_super.empty}, df_cor.empty={df_cor.empty}")
        continue

    df_super['time'] = pd.to_datetime(df_super['time'])
    df_super['year'] = df_super['time'].dt.year
    df_super['month'] = df_super['time'].dt.month
    df_cor['time'] = pd.to_datetime(df_cor['time'])
    df_cor['year'] = df_cor['time'].dt.year
    df_cor['month'] = df_cor['time'].dt.month

    df_cor.to_csv(OUTDIR +'/'+ ISUB.name+ '_coriolis_oxy_at600m.csv')
    df_super.to_csv(OUTDIR +'/'+ ISUB.name+ '_superfloat_oxy_at600m.csv')

    df_intersect = pd.merge(df_super[['wmo','Cycle']],
        df_cor[['wmo','Cycle']],on=['wmo','Cycle'],
        how='inner').drop_duplicates().reset_index(drop=True)
    df_intersect = df_intersect.rename(columns={'Cycle': 'cycle'})[['wmo','cycle']]
    df_intersect.to_csv(OUTDIR +'/'+ ISUB.name+ '_intersect_wmo_cycle.csv', index=False)

    # plot dnesity at ca 600m

    fig, ax = plt.subplots(figsize=(10,6))
    ax.plot(
        df_super['time'],
        df_super['value_at600m'],
        linestyle='None',
        marker='o',
        markersize=12,
        markerfacecolor='red',
        markeredgecolor='black',
        alpha=1,
        label='value_at600m'
    )
    ax.plot(
        df_super['time'],
        df_super['value_at_rho_gsw'],
        linestyle='None',
        marker='o',
        markersize=6,
        markerfacecolor='gray',
        markeredgecolor='black',
        alpha=1.0,
        label='value_at_rho_gsw'
    )
    ax.set_title(f'{ISUB.name} Superfloat')
    ax.set_xlabel('Time')
    ax.set_ylabel('Oxygen at 600 m')
    ax.grid(True)
    ax.tick_params(axis='x', rotation=45)
    ax.set_ylim(155, 230)

    # Converti il tempo in numerico
    x = df_super['time']
    x_num = np.arange(len(x))  # semplice indice numerico

    # Loop sulle colonne che stai plottando
    for col in plot_cols:
        y = df_super[col].values

        # Fit lineare
        coeffs = np.polyfit(x_num, y, 1)
        trend = np.polyval(coeffs, x_num)

        ax.plot(x, trend, color='k')

    ax2 = ax.twinx()
    ax2.plot(
        df_super['time'],
        df_super['depth_at_rho_gsw'],
        #color='k',
        #linewidth=1,
        #linestyle=':',
        color='goldenrod',
        linewidth=0.8,
        linestyle=':',
        label='Depth at rho gsw'
    )
    ax2.set_ylabel('Depth at rho gsw (m)')
    ax2.invert_yaxis()
    ax2.grid(False)

    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc='best')

    fig.tight_layout()
    fig.savefig(OUTDIR +'/'+ ISUB.name + "_superfloat.png", bbox_inches='tight')

    fig, ax = plt.subplots(figsize=(10,6))
    ax.plot(
        df_cor['time'],
        df_cor['value_at600m'],
        linestyle='None',
        marker='o',
        markersize=12,
        markerfacecolor='red',
        markeredgecolor='black',
        alpha=1,
        label='value_at600m'
    )
    ax.plot(
        df_cor['time'],
        df_cor['value_at_rho_gsw'],
        linestyle='None',
        marker='o',
        markersize=6,
        markerfacecolor='gray',
        markeredgecolor='black',
        alpha=1.0,
        label='value_at_rho_gsw'
    )
    ax.set_title(f'{ISUB.name} Coriolis')
    ax.set_xlabel('Time')
    ax.set_ylabel('Oxygen at 600 m')
    ax.grid(True)
    ax.tick_params(axis='x', rotation=45)
    ax.set_ylim(155, 230)
 
    lines, labels = ax.get_legend_handles_labels()
    ax.legend(lines , labels ,loc='best')

    fig.tight_layout()
    fig.savefig(OUTDIR +'/'+  ISUB.name + "_coriolis.png", bbox_inches='tight')

    #plt.show()
    #sys.exit()
    #cutoff = pd.Timestamp('2022-10-31')
    #df_super = df_super[df_super['time'] > cutoff]
    #df_cor  = df_cor[df_cor['time'] > cutoff]
    
    if (not df_super.empty) and (not df_cor.empty):
        # media globale (per titolo)
        mean_super = df_super['value_at600m'].mean()
        mean_cor   = df_cor['value_at600m'].mean()

        plt.figure(figsize=(10,6))

        # superfloat → verde scuro, bordo nero
        plt.plot(
            df_super['time'],
            df_super['value_at600m'],
            linestyle='None',
            marker='o',
            markersize=12,
            markerfacecolor='red',
            markeredgecolor='black',
            markeredgewidth=1.5,
            label=f'Superfloat (mean={mean_super:.2f})')

        # coriolis → verde chiaro, bordo bianco
        plt.plot(
            df_cor['time'],
            df_cor['value_at600m'],
            linestyle='None',
            marker='o',
            markersize=6,
            markerfacecolor='black',
            markeredgecolor='gray',
            markeredgewidth=1.2,
            label=f'Coriolis (mean={mean_cor:.2f})')

        plt.xlabel('Time')
        plt.ylabel('Oxygen at 600 m')
        plt.xticks(rotation=45)

        plt.title(
            ISUB.name +
            f' Mean Oxygen at 600 m\nSuperfloat={mean_super:.2f} | Coriolis={mean_cor:.2f}')

        plt.legend()
        plt.grid()
        plt.tight_layout()
        plt.savefig(OUTDIR + '/' + ISUB.name + '_comparison_oxy_at600m.png')
        plt.close()
