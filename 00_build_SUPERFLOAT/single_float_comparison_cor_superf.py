from netCDF4 import Dataset, num2date
import gsw
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from utils.basins_CA_new_bitsea import cross_Med_basins
from bitsea.basins.region import Rectangle
from bitsea.commons.mask import Mask

# --- identifiers
#WMO       =  "6903090"
#FILENAME  =  "SD6903090_225.nc"
WMO       =  "6901865"
FILENAME  =  "SD6901865_125.nc"

max_depth =  1000
base_dir  =  "/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE"
#base_dir  = "/g100_scratch/usera07ogs/a07ogs00/V11C/ONLINE/"

# --- build file paths
file_c = os.path.join(base_dir, "CORIOLIS", WMO, FILENAME)
if not os.path.exists(file_c):
    FILENAME_alt = 'SR' + FILENAME[2:]
    file_c = os.path.join(base_dir, "CORIOLIS", WMO, FILENAME_alt)
    print(f'SD file not found, trying {FILENAME_alt}')
file_s = os.path.join(base_dir, "SUPERFLOAT", WMO, FILENAME)
if not os.path.exists(file_s):
    FILENAME_alt_s = 'SR' + FILENAME[2:]
    file_s = os.path.join(base_dir, "SUPERFLOAT", WMO, FILENAME_alt_s)
    print(f'SD file not found in SUPERFLOAT, trying {FILENAME_alt_s}')

# --- CORIOLIS (dark gray)
nc_c = Dataset(file_c)

# --- read profile time
juld         = nc_c.variables['JULD'][:].ravel()[0]
juld_units   = nc_c.variables['JULD'].units
profile_time = num2date(juld, juld_units).strftime('%Y-%m-%d')

vc    = nc_c.variables['DOXY_ADJUSTED'][:].ravel()   # µmol/kg
zc    = nc_c.variables['PRES'][:].ravel()
temp  = nc_c.variables['TEMP'][:].ravel()
sali  = nc_c.variables['PSAL'][:].ravel()
lon   = float(nc_c.variables['LONGITUDE'][:].ravel()[0])
lat   = float(nc_c.variables['LATITUDE'][:].ravel()[0])

# --- identify Mediterranean basin
point_rect   = Rectangle(lon, lon, lat, lat)
basin_result = cross_Med_basins(point_rect)
basin_name   = basin_result[0] if basin_result is not None else 'unknown'

# --- load monthly climatology (mean over all profiles at each depth level)
clim_month = int(profile_time.split('-')[1])
clim_dir   = os.path.join(os.path.dirname(os.path.abspath(__file__)),
             '..', '01_calc_clim', 'monthly_clim', 'plots', 'SUPERFLOAT')
csv_path   = os.path.join(clim_dir, f'{basin_name}_DOXY_{clim_month:02d}_superfloat.csv')

z_clim_plot   = None
oxy_clim_plot = None
if os.path.exists(csv_path):
    TheMask      = Mask.from_file('/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc')
    z_interp     = TheMask.zlevels
    df_clim      = pd.read_csv(csv_path, index_col=0)
    clim_mean    = df_clim.mean(axis=1).values      # shape (n_zlevels,)
    mask_clim    = z_interp <= max_depth
    z_clim_plot   = z_interp[mask_clim]
    oxy_clim_plot = clim_mean[mask_clim]
    print(f'Climatology loaded: {csv_path}')
else:
    print(f'Climatology file not found: {csv_path}')

# --- EMODNET climatology point + 2*stdev bar at 600m
emodnet_csv  = os.path.join(os.path.dirname(os.path.abspath(__file__)),
               'bit.sea', 'src', 'bitsea', 'Float', 'EMODNET_climatology.csv')
emodnet_std_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)),
               'bit.sea', 'src', 'bitsea', 'Float', 'EMODNET_stdev.csv')
df_emod      = pd.read_csv(emodnet_csv,     index_col=0)
df_emod_std  = pd.read_csv(emodnet_std_csv, index_col=0)
emodnet_val  = None
emodnet_xerr = None
if basin_name in df_emod.index:
    v    = df_emod.loc[basin_name,     'layer550-650']
    vstd = df_emod_std.loc[basin_name, 'layer550-650']
    if pd.notna(v) and pd.notna(vstd):
        emodnet_val  = float(v)
        emodnet_xerr = 2.0 * float(vstd)
    else:
        print(f'EMODNET value/stdev missing for basin {basin_name}')
else:
    print(f'Basin {basin_name} not found in EMODNET climatology')

_zc   = nc_c.variables['PRES_ADJUSTED'][:].ravel()
_temp = nc_c.variables['TEMP_ADJUSTED'][:].ravel()
_sali = nc_c.variables['PSAL_ADJUSTED'][:].ravel()

# --- compute density (TEOS-10)
SA        = gsw.SA_from_SP(sali,  zc,  lon, lat)
density   = gsw.rho(SA,  gsw.CT_from_t(SA,  temp,  zc),  zc)
SA_adj    = gsw.SA_from_SP(_sali, _zc, lon, lat)
_density  = gsw.rho(SA_adj, gsw.CT_from_t(SA_adj, _temp, _zc), _zc)

# --- convert oxygen to mmol/m3
vc_mmol     = vc *  density / 1000.0
_vc_adj  = vc * _density / 1000.0   # mmol/m3 

# --- SUPERFLOAT (red)
nc_s     = Dataset(file_s)
vs       = nc_s.variables['DOXY'][:].ravel()   # assumed mmol/m3
#print(vs[:])
zs       = nc_s.variables['PRES_DOXY'][:].ravel()

# remove mask 
vc_mmol, zc     = vc_mmol[~vc_mmol.mask], zc[~vc_mmol.mask]
_vc_adj, _zc = _vc_adj[~_vc_adj.mask], _zc[~_vc_adj.mask]

# --- depth limit
mask_depth_adj = _zc <= max_depth
mask_depth_c = zc <= max_depth
mask_depth_s = zs <= max_depth
mask_depth_s = mask_depth_s.ravel()

#import sys
#sys.exit()
vc_mmol, zc = vc_mmol[mask_depth_c], zc[mask_depth_c]
vs, zs = vs[mask_depth_s], zs[mask_depth_s]
_vc_adj, _zc = _vc_adj[mask_depth_adj] , _zc[ mask_depth_adj]

# --- plot
plt.figure(figsize=(5, 7))

plt.plot(vc_mmol, zc, color='k',  linewidth=3.4)
plt.plot(vc_mmol, zc, color='seashell',  linewidth=3 , label='CORIOLIS (mmol/m3)')
if len(vs>5):
    plt.plot(vs, zs, color='k', linewidth=3.4)
    plt.plot(vs, zs, color='darkorange',  linewidth=3, label='SUPERFLOAT (mmol/m3)')

if len(_vc_adj>5):
    plt.plot(_vc_adj, _zc, color='k', linewidth=1)
    plt.plot(_vc_adj, _zc, color='maroon', linewidth=0.7, label='CORIOLIS adjusted (mmol/m3)')
if z_clim_plot is not None:
    plt.plot(oxy_clim_plot, z_clim_plot, color='k', linewidth=1.9, linestyle='--')
    plt.plot(oxy_clim_plot, z_clim_plot, color='peru', linewidth=1.5,
             linestyle='--', label=f'clim month {clim_month:02d} ({basin_name})')
if emodnet_val is not None:
    plt.errorbar(emodnet_val, 595, xerr=emodnet_xerr, fmt='o',
                 color='darkslategrey', capsize=5, linewidth=1.5, zorder=5,
                 label='Emod_clim')
# invert y-axis for depth
plt.gca().invert_yaxis()

plt.xlabel('Oxygen (mmol/m³)')
plt.ylabel('Pressure (dbar)')
plt.title(f'Float {FILENAME}  —  {profile_time}  —  {basin_name}')


plt.ylim(600, 0)   # instead of invert_yaxis()
plt.legend()
plt.grid()

plt.tight_layout()

plots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
os.makedirs(plots_dir, exist_ok=True)
outfile = os.path.join(plots_dir, FILENAME.replace('.nc', '.png'))
plt.savefig(outfile, bbox_inches='tight')
plt.close()
print(f'Saved {outfile}')
