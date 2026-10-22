import argparse
import pathlib

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from basins_CA_new_bitsea import plot_map_subbasins

IMPORT_DATA = True
CSV_FILE = "Float_assimilated.csv"
OUTPUT_DIR = "PLOTS"
OUTPUT_FILE = "med_subbasins_map.png"
ALL_SUBS = True


def add_basin_polygons(ax, basin_names, basin_borders, all_subs=ALL_SUBS):
    highlight_colors = {
        "nwm": "#DEB2FF",
        "lev2": "#b2d235",
    }
    for name, borders in zip(basin_names, basin_borders):
        coords = np.asarray(borders)
        if coords.ndim != 2 or coords.shape[1] != 2:
            continue

        if all_subs:
            facecolor = "white"
            edgecolor = "#ff7f0e"  # arancione ad alto contrasto
            linewidth = 1.5
            alpha = 1.0
        else:
            facecolor = highlight_colors.get(name, "none")
            if facecolor == "none":
                continue
            edgecolor = "black"
            linewidth = 1.2
            alpha = 0.85

        poly = plt.Polygon(
            coords,
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=linewidth,
            alpha=alpha,
            transform=ccrs.PlateCarree(),
            zorder=0.5,
        )
        ax.add_patch(poly)


def load_positions(csv_path):
    df = pd.read_csv(csv_path, index_col=0)
    lon = np.array([])
    lat = np.array([])

    for col in df.columns:
        if col.endswith("_LON"):
            prefix = col[:-4]
            lat_col = f"{prefix}_LAT"
            if lat_col in df.columns:
                lon = np.concatenate([lon, df[col].dropna().to_numpy()])
                lat = np.concatenate([lat, df[lat_col].dropna().to_numpy()])

    return lon, lat


def plot_med_map(import_data=IMPORT_DATA, csv_file=CSV_FILE, output_dir=OUTPUT_DIR, output_file=OUTPUT_FILE, all_subs=True):
    basin_names, basin_borders = plot_map_subbasins()

    fig = plt.figure(figsize=(12, 10))
    ax = plt.axes(projection=ccrs.Mercator())
    ax.set_extent([-10, 40, 30, 48], crs=ccrs.PlateCarree())

    ax.add_feature(cfeature.OCEAN, facecolor="#f8f8f8", zorder=0)
    add_basin_polygons(ax, basin_names, basin_borders, all_subs=all_subs)
    ax.add_feature(cfeature.LAND, facecolor="black", zorder=2)
    ax.add_feature(cfeature.COASTLINE, linewidth=1, edgecolor="#999999", zorder=3)

    gl = ax.gridlines(
        crs=ccrs.PlateCarree(), draw_labels=True, linestyle="--", linewidth=0.6, color="gray"
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {"size": 10}
    gl.ylabel_style = {"size": 10}

    if all_subs:
        title = "Mediterranean subbasins - all 16 subbasins"
        output_file = output_file.replace(".png", "_all_subs.png")
    else:
        title = "Mediterranean subbasins - highlight nwm and lev2"
        output_file = output_file.replace(".png", "_highlight_nwm_lev2.png")

    if import_data:
        csv_path = pathlib.Path(csv_file)
        if csv_path.is_file():
            lon, lat = load_positions(csv_path)
            if lon.size and lat.size:
                ax.scatter(
                    lon,
                    lat,
                    color="red",
                    edgecolor="k",
                    s=20,
                    transform=ccrs.PlateCarree(),
                    zorder=5,
                    alpha=0.8,
                )
                title += f" + float positions ({len(lon)})"
            else:
                title += " + no valid positions found"

    # ax.set_title(title, fontsize=14)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_file

    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    print(f"Saved {output_path}")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot Mediterranean sub-basins map")
    parser.add_argument("--all-subs", action="store_true", help="Show all 16 subbasins (white fill + black edges)")
    parser.add_argument("--no-all-subs", dest="all_subs", action="store_false", help="Show only nwm and lev2 colored")
    parser.add_argument("--outdir", default=OUTPUT_DIR, help="Output directory for the map PNG")
    parser.add_argument("--csv-file", default=CSV_FILE, help="CSV file with float positions")
    args = parser.parse_args()

    plot_med_map(import_data=IMPORT_DATA, csv_file=args.csv_file, output_dir=args.outdir, output_file=OUTPUT_FILE, all_subs=args.all_subs)
