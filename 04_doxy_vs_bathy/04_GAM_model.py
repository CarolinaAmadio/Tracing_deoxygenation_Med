import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
import pandas as pd
import statsmodels.api as sm
from bitsea.basins import V2 as OGS
from pygam import LinearGAM, s, te
import sys
import numpy as np

MARKERS = ['o','s','^','D','P','X','v','*']
# Qualitative palette for per-WMO styling, avoiding pink/magenta tones
# (default matplotlib tab10 cycle includes a pink at index 6).
WMO_COLORS = [
    '#1f77b4',  # blue
    '#ff7f0e',  # orange
    '#2ca02c',  # green
    '#d62728',  # red
    '#9467bd',  # purple
    '#8c564b',  # brown
    '#17becf',  # cyan
    '#7f7f7f',  # gray
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=' gam analysnn'
    )
    parser.add_argument('--plotdir', '-p',default='plots',
        help='Directory containing the _oxy_at600m.csv files.'
    )
    parser.add_argument('--outdir', '-o', required=True,
        help='Directory for output PNG and CSV files.'
    )
    parser.add_argument('--basin', '-b',type=str,default=None,
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
    df['value_at600m'] = pd.to_numeric(df['value_at600m'], errors='coerce')
    df= df.dropna(subset=["time","lat","lon","value_at600m","bathy_depth"])
    df["time_years"] = (df["time"] - df["time"].min()).dt.days / 365.25
    y  = df["value_at600m"].values
    X1 = df[["time_years", "lat", "lon"]].values
    X2 = df[["time_years", "lat", "lon", "bathy_depth"]].values
    return df,y, X1, X2


def build_wmo_style(wmo_list):
    """
    Build a shared marker/color mapping for each WMO, so the same
    float is drawn identically (marker + color) across the
    superfloat and coriolis figures.
    """
    style = {}
    for i, wmo in enumerate(sorted(wmo_list)):
        style[wmo] = {
            'marker': MARKERS[i % len(MARKERS)],
            'color': WMO_COLORS[i % len(WMO_COLORS)],
        }
    return style


def make_residual_diagnostics_figure(df_plot, basin, source, wmo_style):
    fig, axes = plt.subplots(2, 2, figsize=(10, 6),
        constrained_layout=True)

    levels = [-8, -6, -4, -2, 0, 2, 4, 6, 8]
    cmap = plt.cm.RdBu_r
    norm = BoundaryNorm(levels, cmap.N)


    # ==========================================
    # 1) Spatial residual map
    # lon-lat colored by residual
    # marker = WMO
    # ==========================================

    ax = axes[0,0]

    for wmo in sorted(df_plot.wmo.unique()):

        ii = df_plot["wmo"] == wmo

        sc = ax.scatter(
            df_plot.loc[ii,"lon"],
            df_plot.loc[ii,"lat"],
            c=df_plot.loc[ii,"residual"],
            cmap=cmap,
            norm=norm,
            s=60,
            marker=wmo_style[wmo]['marker'],
            edgecolor="k",
            label=str(wmo)
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Spatial distribution of GAM residuals")

    ax.legend(
        title="WMO",
        fontsize=8
    )


    # ==========================================
    # 2) Residual vs time
    # marker = WMO
    # ==========================================

    ax = axes[0,1]

    for wmo in sorted(df_plot.wmo.unique()):

        ii = df_plot["wmo"] == wmo

        ax.scatter(
            df_plot.loc[ii,"time"],
            df_plot.loc[ii,"residual"],
            s=50,
            marker=wmo_style[wmo]['marker'],
            color=wmo_style[wmo]['color'],
            label=str(wmo)
        )

    ax.axhline(
        0,
        color="k",
        linestyle="--"
    )

    ax.set_xlabel("Time")
    ax.set_ylabel("Residual (O$_2$ obs - GAM, mmol m$^{-3}$)")
    ax.set_title("Residuals vs time")


    # ==========================================
    # 3) Residual vs bathymetry
    # marker = WMO
    # ==========================================

    ax = axes[1,0]

    for wmo in sorted(df_plot.wmo.unique()):

        ii = df_plot["wmo"] == wmo

        ax.scatter(
            df_plot.loc[ii,"bathy_depth"],
            df_plot.loc[ii,"residual"],
            s=50,
            marker=wmo_style[wmo]['marker'],
            color=wmo_style[wmo]['color'],
            label=str(wmo)
        )


    ax.axhline(
        0,
        color="k",
        linestyle="--"
    )

    ax.set_xlabel("Bathymetry (m)")
    ax.set_ylabel("Residual")
    ax.set_title("Residuals vs bathymetry")


    # ==========================================
    # 4) Residual vs WMO
    # marker/color = WMO (same style as panels 2-3)
    # ==========================================

    ax = axes[1,1]

    for wmo in sorted(df_plot.wmo.unique()):

        ii = df_plot["wmo"] == wmo

        ax.scatter(
            df_plot.loc[ii,"residual"],
            df_plot.loc[ii,"wmo"],
            s=50,
            marker=wmo_style[wmo]['marker'],
            color=wmo_style[wmo]['color'],
            edgecolor="k",
            label=str(wmo)
        )

    ax.axvline(
        0,
        color="k",
        linestyle="--"
    )

    ax.set_xlabel("Residual (O$_2$ obs - GAM, mmol m$^{-3}$)")
    ax.set_ylabel("WMO")
    ax.set_title("Residual-wmo relationship")

    plt.suptitle(
        f"{basin} ({source}) - GAM residual diagnostics",
        fontsize=14
    )

    return fig


def make_residual_lineplot_figure(df_plot_super, df_plot_cor, basin, colors):
    """
    1x2 figure: observed value_at600m vs GAM prediction over time,
    with the gap between the two lines shaded (= residual).
    Left panel  -> superfloat (dodgerblue)
    Right panel -> coriolis (gray)
    """
    fig, axes = plt.subplots(
        1, 2, figsize=(12, 5), sharey=True, squeeze=False,
        constrained_layout=True
    )

    panels = [
        (df_plot_super, "superfloat", colors["superfloat"]),
        (df_plot_cor,   "coriolis",   colors["coriolis"]),
    ]

    for col, (df_plot, source, color) in enumerate(panels):
        ax = axes[0, col]
        d = df_plot.sort_values("time")

        ax.plot(
            d["time"], d["value_at600m"],
            color=color, lw=1.5, marker="o", markersize=3,
            label=f"{source} obs"
        )
        ax.plot(
            d["time"], d["predicted"],
            color="k", lw=1.5, linestyle="--",
            label="GAM prediction"
        )

        ax.fill_between(
            d["time"], d["value_at600m"], d["predicted"],
            color=color, alpha=0.3, label="residual"
        )

        ax.set_xlabel("Time")
        ax.set_title(f"{basin} - {source}")
        ax.legend(fontsize=8)

    axes[0, 0].set_ylabel("O$_2$ at 600 m (mmol m$^{-3}$)")
    plt.suptitle(f"{basin} - observed vs GAM prediction", fontsize=14)

    return fig


def make_predicted_vs_observed_figure(df_plot_super, df_plot_cor, basin, colors):
    """
    1x2 scatter figure: GAM predicted O2 vs observed O2.
    Left panel  -> superfloat (dodgerblue)
    Right panel -> coriolis (gray)
    """
    fig, axes = plt.subplots(
        1, 2, figsize=(10, 5), sharex=True, sharey=True, squeeze=False,
        constrained_layout=True
    )

    panels = [
        (df_plot_super, "superfloat", colors["superfloat"]),
        (df_plot_cor,   "coriolis",   colors["coriolis"]),
    ]

    for col, (df_plot, source, color) in enumerate(panels):
        ax = axes[0, col]

        ax.scatter(
            df_plot["value_at600m"], df_plot["predicted"],
            s=40, color=color, edgecolor="k", alpha=0.8,
            label=f"{source}"
        )

        lo = min(df_plot["value_at600m"].min(), df_plot["predicted"].min())
        hi = max(df_plot["value_at600m"].max(), df_plot["predicted"].max())
        ax.plot([lo, hi], [lo, hi], color="k", linestyle="--", lw=1, label="1:1")

        ax.set_xlabel("Observed O$_2$ at 600 m (mmol m$^{-3}$)")
        ax.set_title(f"{basin} - {source}")
        ax.legend(fontsize=8)

    axes[0, 0].set_ylabel("Predicted O$_2$ (GAM, mmol m$^{-3}$)")
    plt.suptitle(f"{basin} - predicted vs observed", fontsize=14)

    return fig


def make_residual_summary_figure(df_plot_super, df_plot_cor, basin, colors):
    """
    1x2 figure summarizing residuals for both datasets together:
    (0,0) residuals vs time (lineplot)
    (0,1) histogram of residuals
    superfloat -> dodgerblue, coriolis -> gray
    """
    fig, axes = plt.subplots(
        1, 2, figsize=(11, 5), squeeze=False,
        constrained_layout=True
    )

    panels = [
        (df_plot_super, "superfloat", colors["superfloat"]),
        (df_plot_cor,   "coriolis",   colors["coriolis"]),
    ]

    # (0,0) residuals vs time
    ax = axes[0, 0]
    for df_plot, source, color in panels:
        ax.scatter(
            df_plot["time"], df_plot["residual"],
            s=25, color=color, edgecolor="none", alpha=0.8,
            label=source
        )

    ax.axhline(0, color="k", linestyle="--", lw=1)
    ax.set_xlabel("Time")
    ax.set_ylabel("Residual (O$_2$ obs - GAM, mmol m$^{-3}$)")
    ax.set_title("Residuals vs time")
    ax.legend(fontsize=8)

    # (0,1) histogram of residuals
    ax = axes[0, 1]
    for df_plot, source, color in panels:
        ax.hist(
            df_plot["residual"],
            bins=20, color=color, alpha=0.5,
            edgecolor="k", label=source
        )

    ax.axvline(0, color="k", linestyle="--", lw=1)
    ax.set_xlabel("Residual (O$_2$ obs - GAM, mmol m$^{-3}$)")
    ax.set_ylabel("Count")
    ax.set_title("Residual distribution")
    ax.legend(fontsize=8)

    plt.suptitle(f"{basin} - residual summary", fontsize=14)

    return fig


def make_annual_residual_trend_figure(annual_super, annual_cor, basin, colors):
    """
    Mean residual per year (with standard error bars), for both
    datasets. Used to check whether the GAM leaves a temporal trend
    in the residuals (mean_residual should be ~0 with no structure).
    """
    fig, ax = plt.subplots(figsize=(7, 5), constrained_layout=True)

    panels = [
        (annual_super, "superfloat", colors["superfloat"]),
        (annual_cor,   "coriolis",   colors["coriolis"]),
    ]

    for df_annual, source, color in panels:
        se = df_annual["std_residual"] / df_annual["n"].clip(lower=1) ** 0.5
        ax.errorbar(
            df_annual["year"], df_annual["mean_residual"],
            yerr=se,
            marker="o", color=color, label=source, capsize=3
        )

    ax.axhline(0, color="k", linestyle="--", lw=1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Mean residual (O$_2$ obs - GAM, mmol m$^{-3}$)")
    ax.set_title(f"{basin} - annual mean residual")
    ax.legend(fontsize=8)

    return fig


def fit_ols_trend(df, ycol):
    """
    OLS linear trend of `ycol` vs time (days since the series start).
    Same convention as fit_ols_trend() in 02_plot_basins_value_bathy_trend.py.
    """
    df2 = df[["time", ycol]].dropna()
    if len(df2) < 3:
        return None

    x = (df2["time"] - df2["time"].min()).dt.total_seconds() / 86400.0
    X = sm.add_constant(x)
    model = sm.OLS(df2[ycol].values, X).fit()
    return {
        "series": ycol,
        "n": len(df2),
        "intercept": model.params[0],
        "slope": model.params[1],
        "slope_per_year": model.params[1] * 365.25,
        "slope_p": model.pvalues[1],
        "r_squared": model.rsquared,
        "std_err_slope": model.bse[1],
    }


def make_trend_comparison_figure(df_plot_super, df_plot_cor, basin, colors, trend_rows):
    """
    1x2 figure comparing the OLS trend fitted on the raw value_at600m
    series vs the lat/lon/bathy bias-corrected series (o2_corrected).
    Left panel  -> superfloat (dodgerblue)
    Right panel -> coriolis (gray)
    """
    fig, axes = plt.subplots(
        1, 2, figsize=(12, 5), sharey=True, squeeze=False,
        constrained_layout=True
    )

    trends = {(r["source"], r["series"]): r for r in trend_rows}

    panels = [
        (df_plot_super, "superfloat", colors["superfloat"]),
        (df_plot_cor,   "coriolis",   colors["coriolis"]),
    ]

    for col, (df_plot, source, color) in enumerate(panels):
        ax = axes[0, col]
        d = df_plot.sort_values("time")

        for ycol, style, alpha in [
            ("value_at600m", "--", 0.4),
            ("o2_corrected", "-", 0.9),
        ]:
            ax.scatter(d["time"], d[ycol], s=15, color=color, alpha=alpha)

            key = (source, ycol)
            if key in trends:
                x = (d["time"] - d["time"].min()).dt.total_seconds() / 86400.0
                fitted = trends[key]["intercept"] + trends[key]["slope"] * x
                slope_yr = trends[key]["slope_per_year"]
                ax.plot(
                    d["time"], fitted,
                    color="k" if ycol == "value_at600m" else color,
                    linestyle=style, lw=1.8,
                    label=f"{ycol} ({slope_yr:+.3f}/yr)"
                )

        ax.set_xlabel("Time")
        ax.set_title(f"{basin} - {source}")
        ax.legend(fontsize=8)

    axes[0, 0].set_ylabel("O$_2$ (mmol m$^{-3}$)")
    plt.suptitle(f"{basin} - OLS trend: raw vs bias-corrected", fontsize=14)

    return fig


def make_bias_corrected_timeseries_figure(df_plot_super, df_plot_cor, basin, colors, trend_rows):
    """
    1x2 figure: O2 corrected for the lat/lon (and bathymetry, when
    present in the GAM formula) bias, i.e. o2_corrected vs time,
    where o2_corrected = value_at600m + o2_bias_corrected.
    Left panel  -> superfloat (dodgerblue)
    Right panel -> coriolis (gray)
    """
    fig, axes = plt.subplots(
        1, 2, figsize=(12, 5), sharey=True, squeeze=False,
        constrained_layout=True
    )

    trends = {(r["source"], r["series"]): r for r in trend_rows}

    panels = [
        (df_plot_super, "superfloat", colors["superfloat"]),
        (df_plot_cor,   "coriolis",   colors["coriolis"]),
    ]

    for col, (df_plot, source, color) in enumerate(panels):
        ax = axes[0, col]
        d = df_plot.sort_values("time")

        ax.plot(
            d["time"], d["o2_corrected"],
            color=color, lw=1.2, marker="o", markersize=3,
            label=f"{source} (bias-corrected)"
        )

        key = (source, "o2_corrected")
        if key in trends:
            x = (d["time"] - d["time"].min()).dt.total_seconds() / 86400.0
            fitted = trends[key]["intercept"] + trends[key]["slope"] * x
            ax.plot(
                d["time"], fitted,
                color="k", lw=1.5, linestyle="--",
                label=f"OLS trend ({trends[key]['slope_per_year']:+.3f}/yr)"
            )

        ax.set_xlabel("Time")
        ax.set_title(f"{basin} - {source}")
        ax.legend(fontsize=8)

    axes[0, 0].set_ylabel("O$_2$ bias-corrected (mmol m$^{-3}$)")
    plt.suptitle(f"{basin} - O2 corrected for lat/lon/bathy bias", fontsize=14)

    return fig


def gam_summary_to_dataframe(gam):
    """
    Turn the structured statistics_ dict of a fitted pygam model into
    a single-row DataFrame (global fit stats + one p-value column
    per term), since gam.summary() only prints and returns None.
    """
    stats = gam.statistics_
    row = {
        "n_samples": stats["n_samples"],
        "m_features": stats["m_features"],
        "edof": float(stats["edof"]),
        "scale": float(stats["scale"]),
        "AIC": float(stats["AIC"]),
        "AICc": float(stats["AICc"]),
        "GCV": float(stats["GCV"]),
        "UBRE": stats["UBRE"],
        "loglikelihood": float(stats["loglikelihood"]),
        "deviance": float(stats["deviance"]),
        "pseudo_r2_explained_deviance": stats["pseudo_r2"]["explained_deviance"],
        "pseudo_r2_McFadden": stats["pseudo_r2"]["McFadden"],
        "pseudo_r2_McFadden_adj": stats["pseudo_r2"]["McFadden_adj"],
    }
    for i, (term, p_value) in enumerate(zip(gam.terms, stats["p_values"])):
        term_label = f"{i}_{type(term).__name__}_feat{getattr(term, 'feature', None)}"
        row[f"p_value__{term_label}"] = p_value
    return pd.DataFrame([row])


def fit_and_plot_gam(df_super, Ys, Xs, df_cor, Yc, Xc, formula, gam_name,
                      basin, ISUB, wmo_style, colors, outdir):
    """
    Fit a GAM (given by `formula`) separately on the superfloat and
    coriolis datasets, then produce and save the full set of
    diagnostic figures under outdir/<gam_name>/, plus the residuals
    and the statistical summary as CSV files.
    """
    gam_outdir = outdir / gam_name
    gam_outdir.mkdir(parents=True, exist_ok=True)

    gam_super = LinearGAM(formula).fit(Xs, Ys)
    print("\n====================")
    print(f"{gam_name.upper()} (superfloat)")
    print("====================")
    print(gam_super.summary())

    gam_cor = LinearGAM(formula).fit(Xc, Yc)
    print("\n====================")
    print(f"{gam_name.upper()} (coriolis)")
    print("====================")
    print(gam_cor.summary())

    gam_summary_to_dataframe(gam_super).to_csv(
        gam_outdir / f"{ISUB.name}_superfloat_gam_summary.csv", index=False
    )
    gam_summary_to_dataframe(gam_cor).to_csv(
        gam_outdir / f"{ISUB.name}_coriolis_gam_summary.csv", index=False
    )

    pred_s = gam_super.predict(Xs)
    res_s = Ys - pred_s
    pdep_time_s = gam_super.partial_dependence(term=0, X=Xs)
    df_plot_super = df_super.copy()
    df_plot_super["residual"] = res_s
    df_plot_super["predicted"] = pred_s
    df_plot_super["o2_bias_corrected"] = res_s + pdep_time_s
    df_plot_super["o2_corrected"] = df_plot_super["value_at600m"] + df_plot_super["o2_bias_corrected"]

    pred_c = gam_cor.predict(Xc)
    res_c = Yc - pred_c
    pdep_time_c = gam_cor.partial_dependence(term=0, X=Xc)
    df_plot_cor = df_cor.copy()
    df_plot_cor["residual"] = res_c
    df_plot_cor["predicted"] = pred_c
    df_plot_cor["o2_bias_corrected"] = res_c + pdep_time_c
    df_plot_cor["o2_corrected"] = df_plot_cor["value_at600m"] + df_plot_cor["o2_bias_corrected"]

    df_plot_super.to_csv(
        gam_outdir / f"{ISUB.name}_superfloat_residuals.csv", index=False
    )
    df_plot_cor.to_csv(
        gam_outdir / f"{ISUB.name}_coriolis_residuals.csv", index=False
    )

    trend_rows = []
    for df_plot, source in [(df_plot_super, "superfloat"), (df_plot_cor, "coriolis")]:
        for ycol in ["value_at600m", "o2_corrected"]:
            trend_stats = fit_ols_trend(df_plot, ycol)
            if trend_stats is not None:
                trend_stats["source"] = source
                trend_rows.append(trend_stats)

    pd.DataFrame(trend_rows).to_csv(
        gam_outdir / f"{ISUB.name}_ols_trend_raw_vs_corrected.csv", index=False
    )

    fig_trend = make_trend_comparison_figure(df_plot_super, df_plot_cor, basin, colors, trend_rows)
    fig_trend.savefig(
        gam_outdir / f"{ISUB.name}_trend_raw_vs_corrected.png",
        bbox_inches="tight"
    )
    plt.close(fig_trend)

    fig_corrected = make_bias_corrected_timeseries_figure(df_plot_super, df_plot_cor, basin, colors, trend_rows)
    fig_corrected.savefig(
        gam_outdir / f"{ISUB.name}_o2_bias_corrected_vs_time.png",
        bbox_inches="tight"
    )
    plt.close(fig_corrected)

    annual_super = (
        df_plot_super.groupby("year")["residual"]
        .agg(mean_residual="mean", std_residual="std", n="count")
        .reset_index()
    )
    annual_cor = (
        df_plot_cor.groupby("year")["residual"]
        .agg(mean_residual="mean", std_residual="std", n="count")
        .reset_index()
    )
    annual_super.to_csv(
        gam_outdir / f"{ISUB.name}_superfloat_residual_by_year.csv", index=False
    )
    annual_cor.to_csv(
        gam_outdir / f"{ISUB.name}_coriolis_residual_by_year.csv", index=False
    )

    fig_annual = make_annual_residual_trend_figure(annual_super, annual_cor, basin, colors)
    fig_annual.savefig(
        gam_outdir / f"{ISUB.name}_residual_by_year.png",
        bbox_inches="tight"
    )
    plt.close(fig_annual)

    fig_super = make_residual_diagnostics_figure(df_plot_super, basin, "superfloat", wmo_style)
    fig_super.savefig(
        gam_outdir / f"{ISUB.name}_superfloat_residual.png",
        bbox_inches="tight"
    )
    plt.close(fig_super)

    fig_cor = make_residual_diagnostics_figure(df_plot_cor, basin, "coriolis", wmo_style)
    fig_cor.savefig(
        gam_outdir / f"{ISUB.name}_coriolis_residual.png",
        bbox_inches="tight"
    )
    plt.close(fig_cor)

    fig_line = make_residual_lineplot_figure(df_plot_super, df_plot_cor, basin, colors)
    fig_line.savefig(
        gam_outdir / f"{ISUB.name}_residual_lineplot.png",
        bbox_inches="tight"
    )
    plt.close(fig_line)

    fig_scatter = make_predicted_vs_observed_figure(df_plot_super, df_plot_cor, basin, colors)
    fig_scatter.savefig(
        gam_outdir / f"{ISUB.name}_predicted_vs_observed.png",
        bbox_inches="tight"
    )
    plt.close(fig_scatter)

    fig_summary = make_residual_summary_figure(df_plot_super, df_plot_cor, basin, colors)
    fig_summary.savefig(
        gam_outdir / f"{ISUB.name}_residual_summary.png",
        bbox_inches="tight"
    )
    plt.close(fig_summary)

    return gam_super, gam_cor


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

colors = {'superfloat': 'dodgerblue', 'coriolis': 'gray'}

#sys.exit()

for ISUB in subs:
    basin = ISUB.name
    super_path = plotdir / f'{basin}_superfloat_oxy_at600m.csv'
    cor_path = plotdir / f'{basin}_coriolis_oxy_at600m.csv'
    if not super_path.exists() or not cor_path.exists():
        print(f'Skipping {basin}: missing CSV file(s)')
        continue

    df_super, Ys, X1s, X2s = read_oxy_csv(super_path)
    df_cor,   Yc, X1c, X2c = read_oxy_csv(cor_path)

    wmo_style = build_wmo_style(set(df_super.wmo.unique()) | set(df_cor.wmo.unique()))

    # GAM 1
    # O2 = time + spatial(lat,lon)
    fit_and_plot_gam(
        df_super, Ys, X1s, df_cor, Yc, X1c,
        formula=s(0) + te(1, 2), gam_name="gam1",
        basin=basin, ISUB=ISUB, wmo_style=wmo_style, colors=colors, outdir=outdir
    )

    # GAM 2
    # O2 = time + spatial(lat,lon) + bathymetry
    fit_and_plot_gam(
        df_super, Ys, X2s, df_cor, Yc, X2c,
        formula=s(0) + te(1, 2) + s(3), gam_name="gam2",
        basin=basin, ISUB=ISUB, wmo_style=wmo_style, colors=colors, outdir=outdir
    )
