from netCDF4 import Dataset
import matplotlib.pyplot as plt
import numpy as np
import seawater as sw   # or use gsw if preferred
import os

# --- identifiers
WMO = "6903266"
FILENAME = "SD6903266_152.nc"
max_depth = 600
base_dir = "/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE"

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
density = sw.dens(sali, temp, zc)
_density = sw.dens(_sali, _temp, _zc)

# --- convert oxygen to mmol/m3
vc = vc * density / 1000.0
_vc_adj = vc * _density / 1000.0   # mmol/m3 

# --- SUPERFLOAT (red)
nc_s = Dataset(file_s)

vs = nc_s.variables['DOXY'][:].ravel()   # assumed mmol/m3
zs = nc_s.variables['PRES_DOXY'][:].ravel()

# --- remove NaNs
mask_c = np.isfinite(vc) & np.isfinite(zc)
mask_s = np.isfinite(vs) & np.isfinite(zs)

vc, zc = vc[mask_c], zc[mask_c]
vs, zs = vs[mask_s], zs[mask_s]

# --- remove NaNs for adjusted profile
mask_adj = np.isfinite(_vc_adj) & np.isfinite(_zc)
_vc_adj, _zc = _vc_adj[mask_adj], _zc[mask_adj]

# --- depth limit
mask_depth_adj = _zc <= max_depth
_vc_adj, _zc = _vc_adj[mask_depth_adj], _zc[mask_depth_adj]

max_depth = 600

mask_depth_c = zc <= max_depth
mask_depth_s = zs <= max_depth

vc, zc = vc[mask_depth_c], zc[mask_depth_c]
vs, zs = vs[mask_depth_s], zs[mask_depth_s]


# --- plot
plt.figure(figsize=(5, 7))

plt.plot(vc, zc, color='0.2',  linewidth=4 , label='CORIOLIS (mmol/m3)')
plt.plot(vs, zs, color='red',  linewidth=1.5, label='SUPERFLOAT')
plt.plot(_vc_adj, _zc, color='limegreen', linewidth=1.5, label='CORIOLIS adjusted (mmol/m3)')
# invert y-axis for depth
plt.gca().invert_yaxis()

plt.xlabel('Oxygen (mmol/m³)')
plt.ylabel('Pressure (dbar)')
plt.title(f'Float {WMO} profile comparison')


plt.ylim(600, 0)   # instead of invert_yaxis()
plt.legend()
plt.grid()

plt.tight_layout()
plt.show()
