#!/usr/bin/env python3
import argparse
import re
from pathlib import Path
from collections import defaultdict
from bitsea.commons.mask import Mask
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

parser = argparse.ArgumentParser(
    description="Plot all monthly average profiles per sub-basin from CORIOLIS and SUPERFLOAT netCDF files.")
parser.add_argument("--coriolis-dir",required=True,help="Directory containing CORIOLIS monthly avg netCDF files.",)
parser.add_argument("--superfloat-dir",required=True,help="Directory containing SUPERFLOAT monthly avg netCDF files.",)
parser.add_argument("--outdir",required=True,help="Output directory for generated plots.",)
parser.add_argument("--var",default=None,help="Optional variable to plot (if omitted, all detected variables are plotted).",)
args = parser.parse_args()

BASE_CORIOLIS = Path(args.coriolis_dir).expanduser().resolve()
BASE_SUPERFLOAT = Path(args.superfloat_dir).expanduser().resolve()
OUTDIR = Path(args.outdir).expanduser().resolve()
OUTDIR.mkdir(parents=True, exist_ok=True)
TheMask = Mask.from_file(
        '/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc')
z_lev = TheMask.zlevels

BASINS = [
    "alb", "swm1", "swm2", "nwm", "tyr1", "tyr2",
    "adr1", "adr2", "aeg", "ion1", "ion2", "ion3",
    "lev1", "lev2", "lev3", "lev4",
]
MONTHS = [f"{m:02d}" for m in range(1, 13)]
MONTH_LABELS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

pattern_coriolis = re.compile(r"^(?P<month>\d{2})_Avg_(?P<var>.+)_coriolis_ogs$", re.IGNORECASE)
pattern_superfloat = re.compile(r"^(?P<month>\d{2})_Avg_superfloat_dataset_(?P<var>.+)$", re.IGNORECASE)

coriolis_files = defaultdict(dict)
superfloat_files = defaultdict(dict)

for path in sorted(BASE_CORIOLIS.glob("*.nc")):
    m = pattern_coriolis.match(path.stem)
    if not m:
        continue
    month = m.group("month")
    var = m.group("var")
    coriolis_files[var][month] = path

for path in sorted(BASE_SUPERFLOAT.glob("*.nc")):
    m = pattern_superfloat.match(path.stem)
    if not m:
        continue
    month = m.group("month")
    var = m.group("var")
    superfloat_files[var][month] = path

variables = set(coriolis_files.keys()) | set(superfloat_files.keys())
if args.var:
    variables = {args.var}

for var in sorted(variables):
    if args.var and var.lower() != args.var.lower():
        continue
    print(f"Processing variable: {var}")
    for basin_index, basin in enumerate(BASINS):
        fig, axes = plt.subplots(3, 4, figsize=(18, 12), sharey=True)
        plotted_any = False
        for month_index, month in enumerate(MONTHS):
            ax = axes.flat[month_index]
            ax.set_title(f"{MONTH_LABELS[month_index]} {basin}")
            ax.grid(True, linestyle=":", alpha=0.4)
            ax.set_xlabel(var)
            if month_index % 4 == 0:
                ax.set_ylabel("depth")

            cor_path = coriolis_files.get(var, {}).get(month)
            sup_path = superfloat_files.get(var, {}).get(month)

            if cor_path is not None:
                with Dataset(cor_path) as nc:
                    varname = var if var in nc.variables else None
                    if varname is None:
                        for candidate in nc.variables:
                            if candidate.lower() == var.lower():
                                varname = candidate
                                break
                    if varname is None:
                        raise KeyError(f"Variable {var} not found in {cor_path}")
                    profile = np.array(nc.variables[varname][basin_index, :]).squeeze()
                if profile.ndim > 1:
                    profile = profile.ravel()
                ax.plot(profile, z_lev, color="k", linestyle="-", linewidth=1.5, label="Coriolis")
                plotted_any = True
            if sup_path is not None:
                with Dataset(sup_path) as nc:
                    varname = var if var in nc.variables else None
                    if varname is None:
                        for candidate in nc.variables:
                            if candidate.lower() == var.lower():
                                varname = candidate
                                break
                    if varname is None:
                        raise KeyError(f"Variable {var} not found in {sup_path}")
                    profile = np.array(nc.variables[varname][basin_index, :]).squeeze()
                if profile.ndim > 1:
                    profile = profile.ravel()
                ax.plot(profile, z_lev, color="red", linestyle="--", linewidth=1.5, label="Superfloat")
                plotted_any = True
            if cor_path is None and sup_path is None:
                ax.text(0.5, 0.5, "no data", ha="center", va="center", color="0.5")

        if not plotted_any:
            plt.close(fig)
            continue
        for ax in axes.flat:
            ax.set_ylim(2000,0)
            ax.set_xlim(160,260)
        handles = [
            plt.Line2D([0], [0], color="k", lw=1.5, label="Coriolis"),
            plt.Line2D([0], [0], color="red", lw=1.5, ls="--", label="Superfloat"),
        ]
        fig.legend(handles=handles, loc="lower center", ncol=2, fontsize="small")
        fig.suptitle(f"{basin} - {var} monthly averages")
        fig.tight_layout(rect=[0, 0.03, 1, 0.96])
        out_path = OUTDIR / f"{basin}_{var}_all_months.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        print(f"Saved {out_path}")
