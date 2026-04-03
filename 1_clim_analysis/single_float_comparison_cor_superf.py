from netCDF4 import Dataset
import matplotlib.pyplot as plt
import numpy as np
import seawater as sw   # or use gsw if preferred
import os

# --- identifiers
WMO       =  "6902876"
FILENAME  =  "SD6902876_253.nc"
max_depth =  610
base_dir  =  "/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE"

# --- build file paths
file_c = os.path.join(base_dir, "CORIOLIS", WMO, FILENAME)
file_s = os.path.join(base_dir, "SUPERFLOAT", WMO, FILENAME)

# --- CORIOLIS (dark gray)
nc_c = Dataset(file_c)

vc    = nc_c.variables['DOXY_ADJUSTED'][:].ravel()   # µmol/kg
zc    = nc_c.variables['PRES'][:].ravel()
temp  = nc_c.variables['TEMP'][:].ravel()
sali  = nc_c.variables['PSAL'][:].ravel()

_zc   = nc_c.variables['PRES_ADJUSTED'][:].ravel()
_temp = nc_c.variables['TEMP_ADJUSTED'][:].ravel()
_sali = nc_c.variables['PSAL_ADJUSTED'][:].ravel()

# --- compute density
density  = sw.dens(sali, temp, zc)
_density = sw.dens(_sali, _temp, _zc)

# --- convert oxygen to mmol/m3
vc       = vc *  density / 1000.0
_vc_adj  = vc * _density / 1000.0   # mmol/m3 

# --- SUPERFLOAT (red)
nc_s     = Dataset(file_s)
vs       = nc_s.variables['DOXY'][:].ravel()   # assumed mmol/m3
zs       = nc_s.variables['PRES_DOXY'][:].ravel()

# remove mask 
vc, zc       = vc[~vc.mask], zc[~vc.mask] 
_vc_adj, _zc = _vc_adj[~_vc_adj.mask], _zc[~_vc_adj.mask]

# --- depth limit
mask_depth_adj = _zc <= max_depth
mask_depth_c = zc <= max_depth
mask_depth_s = zs <= max_depth
mask_depth_s = mask_depth_s.ravel()

#import sys
#sys.exit()
vc, zc = vc[mask_depth_c], zc[mask_depth_c]
vs, zs = vs[mask_depth_s], zs[mask_depth_s]
_vc_adj, _zc = _vc_adj[mask_depth_adj] , _zc[ mask_depth_adj]

# --- plot
plt.figure(figsize=(5, 7))

plt.plot(vc, zc, color='0.2',  linewidth=4 , label='CORIOLIS (mmol/m3)')
plt.plot(vs, zs, color='red',  linewidth=1.5, label='SUPERFLOAT')
plt.plot(_vc_adj, _zc, color='limegreen', linewidth=1.5, label='CORIOLIS adjusted (mmol/m3)')
# invert y-axis for depth
plt.gca().invert_yaxis()

plt.xlabel('Oxygen (mmol/m³)')
plt.ylabel('Pressure (dbar)')
plt.title(f'Float {FILENAME} profile comparison')


plt.ylim(600, 0)   # instead of invert_yaxis()
plt.legend()
plt.grid()

plt.tight_layout()
plt.show()
