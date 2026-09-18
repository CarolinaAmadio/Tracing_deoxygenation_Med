import argparse
import glob
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

parser = argparse.ArgumentParser(
    description='Plot Hovmöller difference between two mean-profile CSV sets',
    formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument(
    '--dir1',
    type=str,
    required=True,
    help='First directory containing mean profile CSV files, e.g. PLOTS/HOVMOELLER/2012_2016')

parser.add_argument(
    '--dir2',
    type=str,
    required=True,
    help='Second directory containing mean profile CSV files, e.g. PLOTS/HOVMOELLER/2022_2026')

parser.add_argument(
    '--outdir',
    type=str,
    required=True,
    help='Output directory where diff CSV and Hovmöller plots will be written')

parser.add_argument(
    '--sub',
    type=str,
    default=None,
    help='Optional sub-basin name to process only one basin')

args = parser.parse_args()

input_dir1 = os.path.abspath(args.dir1)
input_dir2 = os.path.abspath(args.dir2)
outdir = os.path.abspath(args.outdir)
os.makedirs(outdir, exist_ok=True)

files1 = sorted(glob.glob(os.path.join(input_dir1, '*_mean_profiles_*.csv')))
files2 = sorted(glob.glob(os.path.join(input_dir2, '*_mean_profiles_*.csv')))
if not files1:
    raise RuntimeError(f'No mean profile CSVs found in {input_dir1}')
if not files2:
    raise RuntimeError(f'No mean profile CSVs found in {input_dir2}')

subs1 = {os.path.basename(p).split('_mean_profiles_')[0] for p in files1}
subs2 = {os.path.basename(p).split('_mean_profiles_')[0] for p in files2}
common_subs = sorted(subs1 & subs2)
if args.sub:
    if args.sub not in common_subs:
        raise RuntimeError(f'Sub-basin {args.sub} not found in both directories')
    common_subs = [args.sub]

if not common_subs:
    raise RuntimeError('No common sub-basins found between the two directories')

print(f'Common sub-basins: {common_subs}', flush=True)

for sub in common_subs:
    file1_candidates = sorted(glob.glob(os.path.join(input_dir1, f'{sub}_mean_profiles_*.csv')))
    file2_candidates = sorted(glob.glob(os.path.join(input_dir2, f'{sub}_mean_profiles_*.csv')))
    if not file1_candidates or not file2_candidates:
        print(f'Skipping {sub}: missing file in one directory', flush=True)
        continue
    if len(file1_candidates) > 1 or len(file2_candidates) > 1:
        raise RuntimeError(f'More than one candidate file found for {sub} in one of the directories')

    file1 = file1_candidates[0]
    file2 = file2_candidates[0]

    print(f'Processing {sub}:\n  {file1}\n  {file2}', flush=True)

    df1 = pd.read_csv(file1, index_col=0)
    df2 = pd.read_csv(file2, index_col=0)
    all_months = [f'{m:02d}' for m in range(1, 13)]
    df1 = df1.reindex(columns=all_months)
    df2 = df2.reindex(columns=all_months)

    df_diff = df2.astype(float) - df1.astype(float)
    df_diff.index.name = 'depth_m'

    out_csv = os.path.join(outdir, f'{sub}_mean_profiles_diff.csv')
    df_diff.to_csv(out_csv)
    print(f'Wrote diff CSV: {out_csv}', flush=True)

    depths = pd.to_numeric(df_diff.index, errors='coerce')
    if depths.notna().any():
        df_plot = df_diff.loc[depths <= 1000]
        if df_plot.empty:
            df_plot = df_diff
    else:
        df_plot = df_diff

    fig, ax = plt.subplots(figsize=(max(10, len(all_months) * 0.5), 8))
    cmap = plt.cm.RdBu_r
    if sub in ['nwm', 'lev2']:
        vmin, vmax = -20.0, 20.0
        levels = np.arange(vmin, vmax + 2, 2)
    else:
        vmin = np.nanmin(df_plot.values)
        vmax = np.nanmax(df_plot.values)
        if np.isnan(vmin) or np.isnan(vmax) or vmin == vmax:
            vmin, vmax = -1.0, 1.0
        else:
            bound = max(abs(vmin), abs(vmax))
            vmin, vmax = -bound, bound
        levels = np.linspace(vmin, vmax, 21)

    depth_vals = pd.to_numeric(df_plot.index, errors='coerce')
    if depth_vals.notna().any():
        y_values = depth_vals.values
    else:
        y_values = np.arange(df_plot.shape[0])

    x_values = np.arange(len(all_months))
    X, Y = np.meshgrid(x_values, y_values)

    norm = plt.matplotlib.colors.BoundaryNorm(levels, cmap.N, clip=True)
    cf = ax.contourf(X, Y, df_plot.values, levels=levels, cmap=cmap, norm=norm, extend='both')

    cs = ax.contour(X, Y, df_plot.values, levels=[0.0], colors='k', linewidths=1.2)
    ax.clabel(cs, fmt='%1.2f', fontsize=22)

    ax.set_xticks(np.arange(len(all_months)))
    ax.set_xticklabels(all_months, rotation=45, ha='right', fontsize=22)
    ax.set_ylabel('depth (m)', fontsize=22)
    ax.set_xlabel('month', fontsize=22)
    ax.set_title(f'{sub} diff {os.path.basename(input_dir2)} - {os.path.basename(input_dir1)}', fontsize=22)

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
    cbar.set_label('difference', fontsize=22)
    cbar.ax.tick_params(labelsize=22)

    fig.subplots_adjust(right=0.8)
    out_png = os.path.join(outdir, f'{sub}_mean_profiles_diff.png')
    fig.savefig(out_png)
    plt.close(fig)
    print(f'Wrote diff PNG: {out_png}', flush=True)
