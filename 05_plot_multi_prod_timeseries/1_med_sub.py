import sys
sys.path.append("/g100/home/userexternal/camadio0/CA_functions/")

import numpy as np
import pandas as pd
from funzioni_CA import parsing_path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as colors
from matplotlib import cm as color_map
from basins_CA import plot_map_subbasins
from funzioni_CA import new_directory
from utils import cmp_for_maps

# ✅ CARTOPY IMPORTS
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# === BASINS ===
name_basins, basin_borders = plot_map_subbasins()
cmap, colors = cmp_for_maps(name_basins)
colors = colors[::-1]

PLOT_POSITION = True
VARLIST = ['N3n', 'P_l', 'O2o']

# ======================================================================================
# ✅ FUNZIONE DI SUPPORTO: AGGIUNGE POLIGONI (ex-Basemap)
# ======================================================================================
def add_basin_polygons(ax, basin_borders, colors):
    for III in range(len(basin_borders)):
        corners = np.array(basin_borders[III])
        lon = corners[:,0]
        lat = corners[:,1]
        poly = plt.Polygon(
            np.vstack([lon, lat]).T,
            facecolor=colors[III],
            edgecolor='black',
            linewidth=0.3,
            transform=ccrs.PlateCarree(),
            zorder=2
        )
        ax.add_patch(poly)

# ======================================================================================
# ✅ LOOP PRINCIPALE VARIABILI
# ======================================================================================

for NAMEVAR in VARLIST:

    # === CARTOPY FIGURE ===
    fig = plt.figure(figsize=(16, 8))
    ax = plt.axes(projection=ccrs.Mercator())
    
    # === LIMITI COME IN BASEMAP ===
    ax.set_extent([-10, 40, 30, 48], crs=ccrs.PlateCarree())

    # === COSTE, CONTINENTI, BOUNDARY ===
    ax.coastlines(resolution='10m', linewidth=1)
    ax.add_feature(cfeature.LAND, facecolor="khaki", zorder=1)
    ax.add_feature(cfeature.OCEAN, facecolor="aliceblue")
    ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5)

    # === GRIDLINES ===
    gl = ax.gridlines(
        crs=ccrs.PlateCarree(),
        draw_labels=True,
        linestyle='--',
        linewidth=0.6,
        color='gray'
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 10}
    gl.ylabel_style = {"size": 10}

    # === CARICAMENTO CSV ===
    df = pd.read_csv('Float_assimilated.csv', index_col=0)
    colLON = NAMEVAR + "_LON"
    colLAT = NAMEVAR + "_LAT"

    lon = df[colLON].dropna().to_numpy()
    lat = df[colLAT].dropna().to_numpy()

    # === POLIGONI SUB-BASINS (ex Basemap Polygons) ===
    add_basin_polygons(ax, basin_borders, colors)

    # === SCATTER FLOAT POSITIONS ===
    if PLOT_POSITION:
        ax.scatter(
            lon, lat,
            color='grey',
            edgecolor='k',
            s=10,
            transform=ccrs.PlateCarree(),
            zorder=5
        )

    # === TITLE & SAVE ===
    plt.title(f'Assimilated Float Positions for {NAMEVAR} '
              f'(tot profiles={len(lon)})',
              fontsize=14)

    plt.savefig(f"{NAMEVAR}_Float_position.png", dpi=150, bbox_inches='tight')
    plt.close(fig)

