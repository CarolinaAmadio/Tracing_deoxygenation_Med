import argparse
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from pathlib import Path
from bitsea.basins import V2 as OGS


def parse_args():
    parser = argparse.ArgumentParser(
        description='Plot value_at600m and bathy_depth trends for all Bitsea sub-basins.'
    )
    
    parser.add_argument(
        '--indir', '-i',
        required=True,
        help='Directory for input CSV files.'
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

def fit_ols_trend(df, ycol):
    df2 = df[['time', ycol]].dropna()
    if len(df2) < 3:
        return None, None

    x = (df2['time'] - df2['time'].min()).dt.total_seconds() / 86400.0
    X = sm.add_constant(x)
    model = sm.OLS(df2[ycol].values, X).fit()
    fitted = pd.Series(model.predict(X), index=df2.index)
    stats = {
        'series': ycol,
        'n': len(df2),
        'date_start': df2['time'].min().date().isoformat(),
        'date_end': df2['time'].max().date().isoformat(),
        'duration_days': x.max(),
        'slope': model.params[1],
        'intercept': model.params[0],
        'slope_per_year': model.params[1] * 365.25,
        'slope_t': model.tvalues[1],
        'slope_p': model.pvalues[1],
        'intercept_t': model.tvalues[0],
        'intercept_p': model.pvalues[0],
        'r_squared': model.rsquared,
        'adj_r_squared': model.rsquared_adj,
        'std_err_slope': model.bse[1],
    }
    return stats, fitted

def main():
    args = parse_args()
    indir = Path(args.indir)    
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    subs = init_basins()
    if args.basin is not None:
        subs = [sub for sub in subs if sub.name == args.basin]
        if not subs:
            raise ValueError(f"Basin '{args.basin}' not found.")
    trend_rows = []

    for ISUB in subs:
        basin = ISUB.name
        basin_rows = []
        super_path = indir / f'{basin}_superfloat_oxy_at600m.csv'
        cor_path = indir / f'{basin}_coriolis_oxy_at600m.csv'

        if not super_path.exists() or not cor_path.exists():
            print(f'Skipping {basin}: missing CSV')
            continue

        df_super = pd.read_csv(super_path, parse_dates=['time'])
        df_cor = pd.read_csv(cor_path, parse_dates=['time'])

        fig, axs = plt.subplots(2, 2, figsize=(16, 12), sharex='col')

        for ax in axs.flatten():
            ax.grid(True)

        # top-left: superfloat O2 600m + high-bathy subset
        super_high = df_super[df_super['bathy_depth'] > 1000]
        stats, fitted = fit_ols_trend(df_super, 'value_at600m')
        if stats:
            row = {'basin': basin, 'dataset': 'superfloat', **stats}
            trend_rows.append(row)
            basin_rows.append(row)
            super_label = (
                f'trend O₂ 600m ({stats["slope_per_year"]:.2f}/yr, '
                f'p={stats["slope_p"]:.3g})'
            )
        else:
            super_label = 'trend O₂ 600m'
        fitted_super = fitted

        stats, fitted = fit_ols_trend(super_high, 'value_at600m')
        if stats:
            row = {'basin': basin, 'dataset': 'superfloat_high_bathy', **stats}
            trend_rows.append(row)
            basin_rows.append(row)
            super_high_label = (
                f'trend baty>1000 ({stats["slope_per_year"]:.2f}/yr, '
                f'p={stats["slope_p"]:.3g})'
            )
        else:
            super_high_label = 'trend baty>1000'
        fitted_super_high = fitted

        axs[0, 0].plot(
            df_super['time'], df_super['value_at600m'],
            linestyle='None', marker='o', markersize=8,
            markerfacecolor='dodgerblue', markeredgecolor='black',
            alpha=0.75, label='superfloat O₂ 600m'
        )
        if fitted_super is not None:
            axs[0, 0].plot(
                df_super.loc[fitted_super.index, 'time'],
                fitted_super,
                color='blue', lw=1.5, linestyle='-', label=super_label
            )
        axs[0, 0].plot(
            super_high['time'], super_high['value_at600m'],
            linestyle='None', marker='o', markersize=8,
            markerfacecolor='navy', markeredgecolor='black',
            alpha=0.85, label='superfloat O₂ 600m baty >1000'
        )
        if fitted_super_high is not None:
            axs[0, 0].plot(
                super_high.loc[fitted_super_high.index, 'time'],
                fitted_super_high,
                color='navy', lw=1.5, linestyle='--', label=super_high_label
            )
        axs[0, 0].set_title(f'{basin} superfloat — O₂ 600m')
        axs[0, 0].set_ylabel('Oxygen (mmol m$^{-3}$)')
        axs[0, 0].legend(loc='best')

        # top-right: coriolis O2 600m + high-bathy subset
        cor_high = df_cor[df_cor['bathy_depth'] > 1000]
        stats, fitted = fit_ols_trend(df_cor, 'value_at600m')
        if stats:
            row = {'basin': basin, 'dataset': 'coriolis', **stats}
            trend_rows.append(row)
            basin_rows.append(row)
            cor_label = (
                f'trend O₂ 600m ({stats["slope_per_year"]:.2f}/yr, '
                f'p={stats["slope_p"]:.3g})'
            )
        else:
            cor_label = 'trend O₂ 600m'
        fitted_cor = fitted

        stats, fitted = fit_ols_trend(cor_high, 'value_at600m')
        if stats:
            row = {'basin': basin, 'dataset': 'coriolis_high_bathy', **stats}
            trend_rows.append(row)
            basin_rows.append(row)
            cor_high_label = (
                f'trend baty>1000 ({stats["slope_per_year"]:.2f}/yr, '
                f'p={stats["slope_p"]:.3g})'
            )
        else:
            cor_high_label = 'trend baty>1000'
        fitted_cor_high = fitted

        axs[0, 1].plot(
            df_cor['time'], df_cor['value_at600m'],
            linestyle='None', marker='o', markersize=8,
            markerfacecolor='gray', markeredgecolor='black',
            alpha=0.75, label='coriolis O₂ 600m'
        )
        if fitted_cor is not None:
            axs[0, 1].plot(
                df_cor.loc[fitted_cor.index, 'time'],
                fitted_cor,
                color='dimgray', lw=1.5, linestyle='-', label=cor_label
            )
        axs[0, 1].plot(
            cor_high['time'], cor_high['value_at600m'],
            linestyle='None', marker='o', markersize=8,
            markerfacecolor='navy', markeredgecolor='black',
            alpha=0.85, label='coriolis O₂ 600m baty >1000'
        )
        if fitted_cor_high is not None:
            axs[0, 1].plot(
                cor_high.loc[fitted_cor_high.index, 'time'],
                fitted_cor_high,
                color='navy', lw=1.5, linestyle='--', label=cor_high_label
            )
        axs[0, 1].set_title(f'{basin} coriolis — O₂ 600m')
        axs[0, 1].legend(loc='best')

        # bottom-left: superfloat bathy_depth
        stats, fitted = fit_ols_trend(df_super, 'bathy_depth')
        if stats:
            row = {'basin': basin, 'dataset': 'superfloat_bathy', **stats}
            trend_rows.append(row)
            basin_rows.append(row)
        axs[1, 0].plot(
            df_super['time'], df_super['bathy_depth'],
            linestyle='None', marker='o', markersize=8,
            markerfacecolor='dodgerblue', markeredgecolor='black',
            alpha=0.75, label='superfloat bathy_depth'
        )
        axs[1, 0].set_title(f'{basin} superfloat — bathy vs time')
        axs[1, 0].set_ylabel('Bathymetry depth (m)')
        axs[1, 0].set_xlabel('Time')
        axs[1, 0].legend(loc='best')

        # bottom-right: coriolis bathy_depth
        stats, fitted = fit_ols_trend(df_cor, 'bathy_depth')
        if stats:
            row = {'basin': basin, 'dataset': 'coriolis_bathy', **stats}
            trend_rows.append(row)
            basin_rows.append(row)
        axs[1, 1].plot(
            df_cor['time'], df_cor['bathy_depth'],
            linestyle='None', marker='o', markersize=8,
            markerfacecolor='gray', markeredgecolor='black',
            alpha=0.75, label='coriolis bathy_depth'
        )
        axs[1, 1].set_title(f'{basin} coriolis — bathy vs time')
        axs[1, 1].set_xlabel('Time')
        axs[1, 1].legend(loc='best')

        for ax in axs.flatten():
            ax.tick_params(axis='x', rotation=45)

        plt.tight_layout()
        fig.savefig(outdir / f'{basin}_value_bathy_timeseries_with_trend.png', dpi=150)
        plt.close(fig)

        # nuova figura: O2 600m vs bathy ordinata in 2 subplot (superfloat / coriolis)
        fig2, axs2 = plt.subplots(1, 2, figsize=(16, 12), sharey=True)
        df_super_sorted = df_super.sort_values('bathy_depth')
        df_cor_sorted = df_cor.sort_values('bathy_depth')

        axs2[0].plot(
            df_super_sorted['bathy_depth'], df_super_sorted['value_at600m'],
            linestyle='None', marker='o', markersize=8,
            markerfacecolor='dodgerblue', markeredgecolor='black',
            alpha=0.75, label='superfloat'
        )
        axs2[0].set_title(f'{basin} superfloat — O₂ 600m vs baty')
        axs2[0].set_xlabel('Bathy depth (m)')
        axs2[0].set_ylabel('Oxygen (mmol m$^{-3}$)')
        axs2[0].legend(loc='best')
        axs2[0].grid(True)

        axs2[1].plot(
            df_cor_sorted['bathy_depth'], df_cor_sorted['value_at600m'],
            linestyle='None', marker='o', markersize=8,
            markerfacecolor='gray', markeredgecolor='black',
            alpha=0.75, label='coriolis'
        )
        axs2[1].set_title(f'{basin} coriolis — O₂ 600m vs baty')
        axs2[1].set_xlabel('Bathy depth (m)')
        axs2[1].legend(loc='best')
        axs2[1].grid(True)

        for ax2 in axs2:
            ax2.tick_params(axis='x', rotation=45)

        fig2.tight_layout()
        fig2.savefig(outdir / f'{basin}_value_vs_bathy_2x1.png', dpi=150)
        plt.close(fig2)

        if basin_rows:
            basin_df = pd.DataFrame(basin_rows)
            basin_csv = outdir / f'{basin}_stats_cor.csv'
            basin_df.to_csv(basin_csv, index=False)
            print('Saved', basin_csv)

    trend_df = pd.DataFrame(trend_rows)
    if not trend_df.empty:
        trend_df.to_csv(outdir / 'all_basins_trend_stats.csv', index=False)
        print('Saved', outdir / 'all_basins_trend_stats.csv')

        summary_df = build_basin_summary_table(trend_df)
        if not summary_df.empty:
            summary_csv = outdir / 'basins_summary_slope_table.csv'
            summary_df.to_csv(summary_csv)
            print('Saved', summary_csv)
    else:
        print('No trend stats available to save.')


def build_basin_summary_table(trend_df):
    """Build a table indexed by sub-basin with slope_per_year/slope_p
    columns for the superfloat and coriolis O2@600m trends (all bathy
    and bathy>1000 subset), taken from the per-basin {basin}_stats_cor.csv
    rows (dataset in ['superfloat', 'coriolis', 'superfloat_high_bathy',
    'coriolis_high_bathy'], series == 'value_at600m')."""
    datasets = [
        'superfloat', 'coriolis',
        'superfloat_high_bathy', 'coriolis_high_bathy',
    ]
    mask = (
        trend_df['series'].eq('value_at600m')
        & trend_df['dataset'].isin(datasets)
    )
    sub = trend_df.loc[mask, ['basin', 'dataset', 'slope_per_year', 'slope_p']]

    pivot = sub.pivot(index='basin', columns='dataset', values=['slope_per_year', 'slope_p'])
    pivot.columns = [f'{dataset}_{metric}' for metric, dataset in pivot.columns]

    col_order = [
        c for c in [
            'superfloat_slope_per_year', 'superfloat_slope_p',
            'coriolis_slope_per_year', 'coriolis_slope_p',
            'superfloat_high_bathy_slope_per_year', 'superfloat_high_bathy_slope_p',
            'coriolis_high_bathy_slope_per_year', 'coriolis_high_bathy_slope_p',
        ] if c in pivot.columns
    ]
    return pivot[col_order].sort_index().round(3)


if __name__ == '__main__':
    main()
