import argparse
import glob
import os
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser(
    description='Create mean depth profiles from CSV files for all sub-basins in a directory',
    formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument(
    '--inputdir', '-i',
    type=str,
    required=True,
    help='Directory containing CSV files with sub-basin data')

parser.add_argument(
    '--outputdir', '-o',
    type=str,
    required=True,
    help='Directory where output CSV files and plots will be written')

parser.add_argument(
    '--year-min',
    type=int,
    required=True,
    help='Start year for column selection')

parser.add_argument(
    '--year-max',
    type=int,
    required=True,
    help='End year for column selection')

parser.add_argument(
    '--climfile',
    type=str,
    default=None,
    help='Optional path to EMODNET_climatology.csv for sub-basin isoline values')

args = parser.parse_args()

inputdir = os.path.abspath(args.inputdir)
outputdir = os.path.abspath(args.outputdir)
outputdir = os.path.join(outputdir, f'{args.year_min}_{args.year_max}')
os.makedirs(outputdir, exist_ok=True)

csv_files = sorted(glob.glob(os.path.join(inputdir, '*_superfloat.csv')))
if not csv_files:
    raise RuntimeError(f'No CSV files found in {inputdir} matching *_superfloat.csv')

subbasins = sorted({os.path.basename(path).split('_', 1)[0] for path in csv_files})
print(f'Found {len(subbasins)} sub-basins: {subbasins}', flush=True)

climfile = None
if args.climfile:
    if os.path.exists(args.climfile):
        climfile = args.climfile
    else:
        raise RuntimeError(f'Climatology file not found: {args.climfile}')
else:
    for search_dir in [inputdir, os.getcwd(), os.path.abspath(os.path.join(inputdir, '..'))]:
        candidate = os.path.join(search_dir, 'EMODNET_climatology.csv')
        if os.path.exists(candidate):
            climfile = candidate
            break

clim_map = {}
if climfile:
    clim_df = pd.read_csv(climfile)
    if clim_df.shape[1] == 1:
        clim_map = clim_df.iloc[:, 0].to_dict()
    elif clim_df.shape[1] >= 2:
        first = clim_df.columns[0]
        second = clim_df.columns[1]
        clim_map = pd.Series(clim_df.iloc[:, 1].values, index=clim_df.iloc[:, 0].astype(str)).to_dict()
    else:
        raise RuntimeError(f'Unexpected EMODNET climate file format: {climfile}')
    print(f'Loaded climatology file: {climfile}', flush=True)
else:
    print('No EMODNET climatology file found; isoline will be skipped if not provided.', flush=True)

for sub in subbasins:
    sub_files = [path for path in csv_files if os.path.basename(path).startswith(sub + '_')]
    if not sub_files:
        continue

    def month_from_filename(path):
        basename = os.path.basename(path)
        match = re.search(r'_(\d{2})_superfloat\.csv$', basename)
        if not match:
            raise ValueError(f'Unable to parse month from filename: {basename}')
        return int(match.group(1))

    sub_files = sorted(sub_files, key=month_from_filename)
    profiles = []
    file_labels = []
    month_counts = {f'{m:02d}': 0 for m in range(1, 13)}

    for file_path in sub_files:
        df = pd.read_csv(file_path, index_col=0)
        if df.empty:
            print(f'Skipping empty file {file_path}', flush=True)
            continue

        dates = pd.to_datetime(df.columns, dayfirst=True, errors='coerce')
        if dates.isna().all():
            raise ValueError(f'Cannot parse date columns in {file_path}')

        mask = (dates.year >= args.year_min) & (dates.year <= args.year_max)
        month_str = f'{month_from_filename(file_path):02d}'
        month_counts[month_str] = int(mask.sum())
        if not mask.any():
            print(f'No columns in year range {args.year_min}-{args.year_max} for {file_path}', flush=True)
            continue

        mean_profile = df.loc[:, mask].mean(axis=1, skipna=True)
        profiles.append(mean_profile)
        file_labels.append(month_str)

    if not profiles:
        print(f'No valid profiles for sub-basin {sub}', flush=True)
        continue

    df_mean = pd.concat(profiles, axis=1)
    df_mean.columns = file_labels
    df_mean.index.name = 'depth_m'
    all_months = [f'{m:02d}' for m in range(1, 13)]
    df_mean = df_mean.reindex(columns=all_months)

    out_csv = os.path.join(outputdir, f'{sub}_mean_profiles_{args.year_min}-{args.year_max}.csv')
    #df_mean.to_csv(out_csv)
    #print(f'Wrote mean profiles CSV: {out_csv}', flush=True)

    depths = pd.to_numeric(df_mean.index, errors='coerce')
    if depths.notna().any():
        df_plot = df_mean.loc[depths <= 1000]
        if df_plot.empty:
            df_plot = df_mean
    else:
        df_plot = df_mean

    fig, ax = plt.subplots(figsize=(max(10, len(all_months) * 0.5), 8))
    cmap = plt.cm.viridis
    if sub == 'nwm':
        vmin, vmax = 170, 260
        levels = np.linspace(vmin, vmax, 19)
    else:
        vmin = np.nanmin(df_plot.values)
        vmax = np.nanmax(df_plot.values)
        if np.isnan(vmin) or np.isnan(vmax) or vmin == vmax:
            vmin, vmax = 0.0, 1.0
        levels = np.linspace(vmin, vmax, 12)

    depth_vals = pd.to_numeric(df_plot.index, errors='coerce')
    if depth_vals.notna().any():
        y_values = depth_vals.values
    else:
        y_values = np.arange(df_plot.shape[0])

    x_values = np.arange(len(all_months))
    X, Y = np.meshgrid(x_values, y_values)

    norm = plt.matplotlib.colors.BoundaryNorm(levels, cmap.N, clip=True)
    cf = ax.contourf(X, Y, df_plot.values, levels=levels, cmap=cmap, norm=norm, extend='both')

    clim_value = None
    if climfile and sub in clim_map:
        try:
            clim_value = float(clim_map[sub])
        except Exception:
            clim_value = None

    if clim_value is not None:
        clim_value = round(clim_value, 2)
        clim_value = 187.5
        #cs = ax.contour(X, Y, df_plot.values, levels=[clim_value], colors='w', linewidths=2, linestyle=":")
        cs = ax.contour(X, Y, df_plot.values, levels=[clim_value], colors='w',linewidths=2, linestyles=':')
        ax.clabel(cs, fmt='%1.2f', fontsize=12)
        #ax.text(0.98, 0.95, f'clim {sub}: {clim_value}', transform=ax.transAxes,
        #        ha='right', va='top', fontsize=8, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
    #else:
    #    ax.text(0.98, 0.95, 'clim: n/a', transform=ax.transAxes,
    #            ha='right', va='top', fontsize=8, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

    ax.set_xticks(np.arange(len(all_months)))
    ax.set_xticklabels(all_months, rotation=45, ha='right', fontsize=22)
    ax.set_ylabel('depth (m)', fontsize=22)
    ax.set_xlabel('month', fontsize=22)
    ax.set_title(f'{sub} {args.year_min}-{args.year_max} mean profiles', fontsize=22)

    if depth_vals.notna().any():
        tick_idx = np.linspace(0, len(y_values) - 1, min(10, len(y_values)), dtype=int)
        y_positions = y_values[tick_idx]
        y_labels = [f'{val:.2f}' for val in y_positions]
    else:
        tick_idx = np.linspace(0, df_plot.shape[0] - 1, min(10, df_plot.shape[0]), dtype=int)
        y_positions = tick_idx
        y_labels = df_plot.index[tick_idx]

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=22)
    ax.invert_yaxis()

    cbar = fig.colorbar(cf, ax=ax, boundaries=levels, ticks=levels)
    cbar.set_label(sub, fontsize=22)
    cbar.ax.tick_params(labelsize=22)

    obs_lines = [f'{m}: {month_counts[m]} ' for m in all_months]
    obs_text = 'mesi: #profili\n' + '\n'.join(obs_lines)
    fig.subplots_adjust(right=0.78)
    fig.text(0.82, 0.5, obs_text, ha='left', va='center', fontsize=8, family='monospace', bbox=dict(facecolor='white', alpha=0.8, edgecolor='black'))

    out_png = os.path.join(outputdir, f'{sub}_{args.year_min}-{args.year_max}_mean_profiles.png')
    fig.savefig(out_png)
    plt.close(fig)
    print(f'Wrote heatmap PNG: {out_png}', flush=True)
