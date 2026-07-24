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
    parser.add_argument(   '--maskfile', '-m',
                                type = str,
                                default = None,
                                required = True,
                                help = '''model mask''')    
    parser.add_argument(
        '--basin', '-b',
        type = str,
        default = None,
        help = 'Optional basin name to restrict the analysis.'
    )
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
import os 
from bitsea.basins.region import Region, Rectangle
sys.path.append(os.path.abspath(".."))
from utils.basins_CA_new_bitsea import cross_Med_basins

OUTDIR     = addsep(args.outdir)
os.makedirs(OUTDIR, exist_ok=True)
varmod     = "O2o"#args.variable


def build_wmo_birthdates(Profilelist):
    birthdates = {}
    for p in Profilelist:
        wmo = p._my_float.wmo
        if wmo not in birthdates or p.time < birthdates[wmo]:
            birthdates[wmo] = p.time
    return birthdates


# INIT
#TheMask=Mask.from_file("/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc")

MASKFILE=args.maskfile
TheMask=Mask.from_file(MASKFILE)

z_interp= TheMask.zlevels
bathy_map = TheMask.bathymetry()

if OGS.atl in OGS.Pred.basin_list:
  OGS.Pred.basin_list.remove(OGS.atl) # tolgo Atlantic buffer
else: pass

SUBS    = OGS.Pred.basin_list[:]
if args.basin is not None:
    SUBS = [sub for sub in SUBS if sub.name == args.basin]
    if not SUBS:
        raise ValueError(f"Basin '{args.basin}' not found.")
print('_________________start__________________')

SUB_COUNT = 0
TI=timerequestors.TimeInterval( starttime='19500101',endtime='20280101',dateformat='%Y%m%d',)
list_basin =[]
for ISUB in SUBS:
    list_basin.append(ISUB.name)

# Float birthdates computed once on the whole Mediterranean (OGS.med), so
# that float_age_days reflects the real float lifetime (days since its
# first ever profile), independently of the sub-basin a profile falls in.
print('_________________ computing global float birthdates (whole Med) __________________')
_super_Profilelist_ALL = superfloat.FloatSelector(FLOATVARS[varmod], TI, OGS.med)
_cor_Profilelist_ALL   = bio_float.FloatSelector(FLOATVARS[varmod], TI, OGS.med)

wmo_birth_super = build_wmo_birthdates(_super_Profilelist_ALL)
wmo_birth_cor   = build_wmo_birthdates(_cor_Profilelist_ALL)

COLUMNS=[
    'wmo','Cycle','DRIFT_CODE','offset','time',
    'lat','lon',
    'value_at600m','value_at_rho_gsw','depth_at_rho_gsw',
    'float_age_days','bathy_depth'
]

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


def collect_data_from_profiles(Profilelist, DOXY_convert=False, wmo_birth=None):
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

        float_age_days = np.nan
        if wmo_birth is not None:
            wmo = p._my_float.wmo
            if wmo in wmo_birth and p.time is not None:
                float_age_days = (p.time - wmo_birth[wmo]).days

        bathy_depth = np.nan
        if not np.isnan(p.lon) and not np.isnan(p.lat):
            ip, jp = TheMask.convert_lon_lat_to_indices(lon=p.lon, lat=p.lat)
            if TheMask[0, jp, ip]:
                bathy_depth = float(bathy_map[jp, ip])

        rows.append({
        'wmo': p._my_float.wmo,
        'Cycle': p._my_float.cycle,
        'DRIFT_CODE': drift_code,
        'offset': offset,
        #'filename': p._my_float.filename,
        'time': p.time.strftime('%Y%m%d'),
        'lat': p.lat,
        'lon': p.lon,
        'value_at600m': value,
        'value_at_rho_gsw': value_rho_gsw,
        'depth_at_rho_gsw': depth_at_rho_gsw,
        'float_age_days': float_age_days,
        'bathy_depth': bathy_depth})


    df_local = pd.DataFrame(rows, columns=COLUMNS)
    if not df_local.empty:
        df_local['time'] = pd.to_datetime(df_local['time'], format='%Y%m%d')
    return df_local

for ISUB in SUBS:
    #if ISUB.name != 'alb': continue
    print('_____________ '+ str(ISUB)  +' _____________')
    _super_Profilelist = superfloat.FloatSelector(FLOATVARS[varmod],TI, ISUB)
    _cor_Profilelist    = bio_float.FloatSelector(FLOATVARS[varmod],TI, ISUB)

    df_super = collect_data_from_profiles(_super_Profilelist, DOXY_convert=False, wmo_birth=wmo_birth_super)

    df_super = df_super.sort_values('time') 
    df_cor = collect_data_from_profiles(_cor_Profilelist, DOXY_convert=True, wmo_birth=wmo_birth_cor)
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

