from netCDF4 import Dataset
import gsw
import numpy as np
import pandas as pd
from bitsea.commons.mask import Mask
from bitsea.basins import V2 as OGS
import pandas as pd 
import seawater as sw   # EOS-80
import matplotlib.pyplot as plt
import os

outdir = "plots_density"
os.makedirs(outdir, exist_ok=True)

TheMask=Mask.from_file("/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc")
m600_idx=TheMask.get_depth_index(600)
z_interp= TheMask.zlevels

ds_s = Dataset("../PTEM_PSAL/vosaline.nc")
ds_t = Dataset("../PTEM_PSAL/votemper.nc")

temp    = ds_t.variables['votemper'][:,:,1,:,0]
sal     = ds_s.variables['vosaline'][:,:,1,:,0]

#In [36]: temp.shape
#Out[36]: (52, 18) # week subbasin at 600m 

if OGS.atl in OGS.Pred.basin_list:
  OGS.Pred.basin_list.remove(OGS.atl) # tolgo Atlantic buffer
else: pass

SUBS    = OGS.Pred.basin_list[:]

def get_center_lat_lon(ISUB):
    lons = [p[0] for p in ISUB.borders]
    lats = [p[1] for p in ISUB.borders]
    return np.mean(lons), np.mean(lats)

fig, axes = plt.subplots(4, 4, figsize=(16, 12), sharex=True, sharey=True)
vmin = 1026
vmax = 1036
axes = axes.flatten()

df=pd.DataFrame(index=np.arange(0,1), columns=np.arange(0,len(SUBS)))
df_std= pd.DataFrame(index=np.arange(0,1), columns=np.arange(0,len(SUBS)))
sub_list=[]
for isub , ISUB  in enumerate(SUBS):
    print('_____________')
    print(ISUB)
    sub_list.append(ISUB.name)
    ax = axes[isub]

    tmp_temp = temp[:,isub,:]
    tmp_sal  =  sal[:,isub,:]

    tmp_temp = np.where(tmp_temp > 1e19, np.nan, tmp_temp)
    tmp_sal  = np.where(tmp_sal  > 1e19, np.nan, tmp_sal)

    lon, lat = get_center_lat_lon(ISUB)
    p = gsw.p_from_z(-z_interp, lat)
    p_2d = np.tile(p, (tmp_temp.shape[0], 1))

    # ---------------------------
    # GSW density
    # ---------------------------
    SA = gsw.SA_from_SP(tmp_sal, p_2d, lon, lat)
    CT = gsw.CT_from_pt(SA, tmp_temp)
    rho_gsw = gsw.rho(SA, CT, p_2d)
    # ---------------------------
    # EOS-80 density
    # ---------------------------
    rho_sw = sw.dens(tmp_sal, tmp_temp, p_2d)
    # Compare densities
    diff = np.abs(rho_gsw - rho_sw)

    if np.nanmax(diff) > 0.1:
        print(f"Density mismatch in basin {ISUB.name}: max diff = {np.nanmax(diff):.3f}")

    df_rho = pd.DataFrame(rho_gsw , columns=z_interp)
    df_rho = df_rho.T

    df_rho.index.name = "depth"

    if df_rho.index.max() < 555:
        ax.set_title(f"{ISUB.name}\n(no 600m)")
        ax.axis('off')
        continue
    rho_ref = df_rho.mean(axis=1).iloc[m600_idx]
    rho_std = df_rho.std(axis=1).iloc[m600_idx]
    print(rho_ref)
    df.iloc[:,isub] = rho_ref
    df_std.iloc[:,isub] = rho_std
    mask = df_rho.index <= 1000
    z_plot = z_interp[mask]
    rho_plot = df_rho.values[mask, :]  # mantieni righe corrispondenti alle profondità
 
    cf = ax.contourf(
    np.arange(df_rho.shape[1]),  # asse X
    z_plot*-1,                      # asse Y
    rho_plot,                    # righe ordinate come in df_rho
    levels=20,
    cmap='cividis_r',
    vmin=vmin,
    vmax=vmax
    )

    ax.set_title(f"{ISUB.name}\nρ(600m)={rho_ref:.3f}")
    #ax.invert_yaxis()


df.columns=sub_list
df_out = df.T
df_out.to_csv("density_600m.csv")

df_std.columns=sub_list
df_outs = df_std.T
df_outs.to_csv("density_std_600m.csv")



cbar = fig.colorbar(
    cf,
    ax=axes,
    orientation='horizontal',
    fraction=0.02,
    pad=0.02
)

cbar.set_label("Density (kg/m³)")

# ---------------------------
# Axis labels (only outer)
# ---------------------------
for ax in axes[12:]:  # bottom row
    ax.set_xlabel("Time")

for i in range(0, 16, 4):  # first column
    axes[i].set_ylabel("Depth (m)")

# ---------------------------
# Layout
# ---------------------------
fig.subplots_adjust(bottom=0.15,hspace=0.3 , top=0.95)
# ---------------------------
# Save
# ---------------------------
plt.savefig( outdir+ "/density_subplots_4x4.png")
plt.close()

print("Saved: density_subplots_4x4.png")
