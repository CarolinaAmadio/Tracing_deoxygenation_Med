"""Plot oxygen at 600m time series for each basin by duration subset.

Input:
- CSV files named <basin>_superfloat_oxy_at600m.csv and <basin>_coriolis_oxy_at600m.csv
  located in the plot directory.
- optional basin name to restrict the analysis.

Output:
- one PNG per basin with 3 rows and 2 columns of subset time series.
- a CSV file per basin with trend statistics.
- an overall CSV file with trend statistics for all basins.

This script reads oxygen at 600m data, groups it by duration subset, fits
linear trends, plots each subset with trend lines, and saves statistics.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.api as sm
from bitsea.basins import V2 as OGS


def parse_args():
    parser = argparse.ArgumentParser(
        description='Plot oxygen at 600m time series for each basin by duration subset.'
    )
    parser.add_argument(
        '--plotdir', '-p',
        default='plots',
        help='Directory containing the _oxy_at600m.csv files.'
    )
    parser.add_argument(
        '--outdir', '-o',
        required=True,
        help='Directory for output PNG and CSV files.'
    )
    parser.add_argument(
        '--basin', '-b',
        type=str,
        default=None,
        help='Optional basin name to restrict the analysis.'
    )
    return parser.parse_args()


def init_basins():
    if OGS.atl in OGS.Pred.basin_list:
        OGS.Pred.basin_list.remove(OGS.atl)
    if hasattr(OGS, 'med') and OGS.med in OGS.Pred.basin_list:
        OGS.Pred.basin_list.remove(OGS.med)
    return OGS.Pred.basin_list[:]


def read_oxy_csv(path):
    df = pd.read_csv(path, parse_dates=['time'],index_col=0)
    if 'float_age_days' in df.columns:
        df['duration_days'] = pd.to_numeric(df['float_age_days'], errors='coerce')
    #else:
    #    df = df.sort_values('time')
    #    if 'time' in df.columns:
    #        df['duration_days'] = (
    #            df['time'] - df['time'].min()
    #        ).dt.total_seconds() / 86400.0
    #    else:
    #        df['duration_days'] = pd.NA

    df['value_at600m'] = pd.to_numeric(df['value_at600m'], errors='coerce')
    return df


def fit_ols_trend(df, ycol):
    df2 = df[['time', ycol]].dropna()
    if len(df2) < 3:
        return None, None

    x = (df2['time'] - df2['time'].min()).dt.total_seconds() / 86400.0
    X = sm.add_constant(x)
    model = sm.OLS(df2[ycol].values, X).fit()
    fitted = pd.Series(model.predict(X), index=df2.index)
    conf_int = model.conf_int(alpha=0.05)
    slope_ci_lower, slope_ci_upper = conf_int.iloc[1].values
    stats = {
        'series': ycol,
        'n': len(df2),
        'date_start': df2['time'].min().date().isoformat(),
        'date_end': df2['time'].max().date().isoformat(),
        'duration_days': x.max(),
        'slope': model.params[1],
        'intercept': model.params[0],
        'slope_per_year': model.params[1] * 365.25,
        'slope_per_year_ci_lower': slope_ci_lower * 365.25,
        'slope_per_year_ci_upper': slope_ci_upper * 365.25,
        'slope_ci_lower': slope_ci_lower,
        'slope_ci_upper': slope_ci_upper,
        'slope_t': model.tvalues[1],
        'slope_p': model.pvalues[1],
        'intercept_t': model.tvalues[0],
        'intercept_p': model.pvalues[0],
        'r_squared': model.rsquared,
        'adj_r_squared': model.rsquared_adj,
        'std_err_slope': model.bse[1],
    }
    return stats, fitted


def plot_duration_vs_trend(ax, rows, colors):
    if not rows:
        ax.text(
            0.5, 0.5, 'No trend stats available',
            ha='center', va='center', transform=ax.transAxes,
            fontsize=10, color='gray'
        )
        return

    df = pd.DataFrame(rows)
    order = ['duration <= 1 year', 'duration <= 2 years', 'all data']
    x = list(range(len(order)))
    xlabels = ['≤1 year', '≤2 years', 'all']

    for dataset in ['superfloat', 'coriolis']:
        subset = df[df['dataset'] == dataset]
        y = []
        yerr_lower = []
        yerr_upper = []
        for label in order:
            row = subset[subset['subset'] == label]
            if row.empty:
                y.append(float('nan'))
                yerr_lower.append(0.0)
                yerr_upper.append(0.0)
            else:
                row = row.iloc[0]
                y.append(row['slope_per_year'])
                yerr_lower.append(row['slope_per_year'] - row['slope_per_year_ci_lower'])
                yerr_upper.append(row['slope_per_year_ci_upper'] - row['slope_per_year'])

        ax.errorbar(
            x, y,
            yerr=[yerr_lower, yerr_upper],
            fmt='o-',
            label=dataset,
            color=colors[dataset],
            capsize=5,
            markersize=8,
            linewidth=1.5,
            alpha=0.9
        )

    ax.set_xticks(x)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel('Duration subset')
    ax.set_ylabel('Oxygen trend (mmol m$^{-3}$ yr$^{-1}$)')
    ax.set_title('Trend vs duration subset')
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    ax.legend(loc='best', fontsize='small')


def plot_oxy_by_duration(ax, df, threshold, title, color):
    if threshold is None:
        subset = df.copy()
    else:
        subset = df[df['duration_days'] <= threshold]

    if subset.empty:
        ax.text(
            0.5, 0.5, 'No data available',
            ha='center', va='center', transform=ax.transAxes,
            fontsize=10, color='gray'
        )
        return None

    ax.plot(
        subset['time'], subset['value_at600m'],
        linestyle='none', marker='o', markersize=6,
        markerfacecolor=color, markeredgecolor='black', alpha=0.75,
        label='value_at600m'
    )

    stats, fitted = fit_ols_trend(subset, 'value_at600m')
    if fitted is not None:
        ax.plot(
            subset.loc[fitted.index, 'time'], fitted,
            color='black', lw=1.5, label='trend'
        )
        slope_year = stats['slope'] * 365.25
        trend_label = f' trend={slope_year:.2f}/yr p={stats["slope_p"]:.3g}'
    else:
        trend_label = ''

    ax.set_title(f'{title}{trend_label}')
    ax.grid(True)
    ax.legend(loc='best', fontsize='small')
    return stats


args = parse_args()
plotdir = Path(args.plotdir)
outdir = Path(args.outdir)
outdir.mkdir(parents=True, exist_ok=True)

subs = init_basins()
Basin=args.basin
if Basin is not None:
    subs = [sub for sub in subs if sub.name == Basin]
    if not subs:
        raise ValueError(f"Basin '{args.basin}' not found.")

thresholds = [365, 730, None]
titles = ['duration <= 1 year', 'duration <= 2 years', 'all data']
colors = {'superfloat': 'dodgerblue', 'coriolis': 'gray'}

all_trends = []

for ISUB in subs:
    basin = ISUB.name
    super_path = plotdir / f'{basin}_superfloat_oxy_at600m.csv'
    cor_path = plotdir / f'{basin}_coriolis_oxy_at600m.csv'

    if not super_path.exists() or not cor_path.exists():
        print(f'Skipping {basin}: missing CSV file(s)')
        continue

    df_super = read_oxy_csv(super_path)
    df_cor = read_oxy_csv(cor_path)

    fig, axs = plt.subplots(3, 2, figsize=(14, 15), sharex='col', sharey='row')

    basin_rows = []
    for row_idx, threshold in enumerate(thresholds):
        for col_idx, dataset in enumerate(['superfloat', 'coriolis']):
            df = df_super if dataset == 'superfloat' else df_cor
            stats = plot_oxy_by_duration(
                axs[row_idx, col_idx], df, threshold,
                f'{dataset} — {titles[row_idx]}',
                colors[dataset]
            )
            if stats is not None:
                stats_row = {
                    'basin': basin,
                    'dataset': dataset,
                    'subset': titles[row_idx],
                    **stats,
                }
                all_trends.append(stats_row)
                basin_rows.append(stats_row)

    for ax in axs[:, 0]:
        ax.set_ylabel('Oxygen (mmol m$^{-3}$)')
    for ax in axs[-1, :]:
        ax.set_xlabel('Time')

    for ax in axs.flatten():
        ax.tick_params(axis='x', rotation=45)

    plt.suptitle(f'{basin} — oxygen at 600m by duration subset', y=0.97)
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    out_path = outdir / f'{basin}_oxy600m_duration_subsets.png'
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print('Saved', out_path)

    if basin_rows:
        basin_df = pd.DataFrame(basin_rows)
        basin_csv = outdir / f'{basin}_stats_cor.csv'
        basin_df.to_csv(basin_csv, index=False)
        print('Saved', basin_csv)

        trend_fig, trend_ax = plt.subplots(figsize=(8, 6))
        plot_duration_vs_trend(trend_ax, basin_rows, colors)
        trend_ax.set_title(f'{basin} — O₂ trend vs duration subset')
        trend_fig.tight_layout()
        trend_out_path = outdir / f'{basin}_oxy600m_duration_trend_scatter.png'
        trend_fig.savefig(trend_out_path, dpi=150)
        plt.close(trend_fig)
        print('Saved', trend_out_path)

if all_trends:
    trend_df = pd.DataFrame(all_trends)
    trend_df.to_csv(outdir / 'all_basins_trend_stats.csv', index=False)
    print('Saved', outdir / 'all_basins_trend_stats.csv')

    summary_mask = trend_df['subset'].eq('all data')
    summary_sub = trend_df.loc[summary_mask, ['basin', 'dataset', 'slope_per_year', 'slope_p']]
    summary_pivot = summary_sub.pivot(index='basin', columns='dataset', values=['slope_per_year', 'slope_p'])
    summary_pivot.columns = [f'{dataset}_{metric}' for metric, dataset in summary_pivot.columns]
    col_order = [
        c for c in [
            'superfloat_slope_per_year', 'superfloat_slope_p',
            'coriolis_slope_per_year', 'coriolis_slope_p',
        ] if c in summary_pivot.columns
    ]
    summary_df = summary_pivot[col_order].sort_index()
    if not summary_df.empty:
        summary_csv = outdir / 'basins_summary_slope_table.csv'
        summary_df.to_csv(summary_csv)
        print('Saved', summary_csv)
else:
    print('No trend statistics available to save.')


