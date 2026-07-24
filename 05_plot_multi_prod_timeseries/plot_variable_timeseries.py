import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.dates import AutoDateLocator, DateFormatter

from bitsea.basins import V2
from bitsea.basins.basin import Basin, ComposedBasin


ALIASES = {
    "ALK": {"bgc": "AT", "med": "ALK", "stat": "ALK"},
    "AT": {"bgc": "AT", "med": "ALK", "stat": "ALK"},
    "DIC": {"bgc": "DIC", "med": "DIC_merged", "stat": "DIC"},
    "PH_IN_SITU_TOTAL": {"bgc": "PH_IN_SITU_TOTAL", "med": "pH_ins_merged", "stat": "pH"},
    "PH": {"bgc": "PH_IN_SITU_TOTAL", "med": "pH_ins_merged", "stat": "pH"},
    "DOXY": {"bgc": "DOXY", "med": "O2o", "stat": "O2o"},
    "O2O": {"bgc": None, "med": "O2o", "stat": "O2o"},
    "PCO2": {"bgc": None, "med": "pCO2_rec", "stat": "pCO2"},
    "NITRATE": {"bgc": "NITRATE", "med": "N3n", "stat": "N3n"}
}

def get_elementary_basin_names():
    return [
        "alb",
        "swm1",
        "swm2",
        "nwm",
        "tyr1",
        "tyr2",
        "adr1",
        "adr2",
        "aeg",
        "ion1",
        "ion2",
        "ion3",
        "lev1",
        "lev2",
        "lev3",
        "lev4",
    ]


def get_elementary_basins():
    return [
        getattr(V2, name)
        for name in get_elementary_basin_names()
    ]


def load_bitsea_plot_units() -> dict[str, str]:
    xml_dir = Path(__file__).resolve().parents[1] / "bit.sea" / "src" / "bitsea" / "postproc"
    xml_files = [
        xml_dir / "Plotlist.xml",
        xml_dir / "Plotlist_bio_reduced.xml",
        xml_dir / "Plotlist_bio.xml",
    ]
    units = {}
    for xml_file in xml_files:
        if not xml_file.is_file():
            continue
        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            continue
        for elem in root.iter():
            key = None
            if elem.get("var"):
                key = elem.get("var").strip().lower()
            elif elem.get("name"):
                key = elem.get("name").strip().lower()
            if not key:
                continue
            unit = elem.get("units") or elem.get("plotunits")
            if unit:
                units.setdefault(key, unit.strip())
    return units


PLOT_UNITS = load_bitsea_plot_units()


def get_ylabel(var: str) -> str:
    unit = PLOT_UNITS.get(var.lower())
    if unit is None and var in ALIASES:
        alias_var = ALIASES[var].get("stat") or ALIASES[var].get("med") or ALIASES[var].get("bgc")
        if alias_var:
            unit = PLOT_UNITS.get(alias_var.lower())
    return f"{var} [{unit}]" if unit else var


def load_csv(path: Path, var: str, label: str, source_name: str, min_depth: float, max_depth: float) -> pd.DataFrame:
    df = pd.read_csv(path)
    if label == "BGC_ARGO":
        df = df.rename(columns={source_name: var})
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
    elif label == "MEDBGC_INS":
        df = df.rename(columns={source_name: var})
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
    else:
        mean_col = f"{source_name}_mean_{int(min_depth)}to{int(max_depth)}m"
        if mean_col not in df.columns:
            mean_col = f"{source_name}_mean_5m"
        df = df.rename(columns={mean_col: var})
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def find_csv(path: Path, pattern: str, recursive: bool = False) -> Path:
    if recursive:
        candidates = list(path.rglob(pattern))
    else:
        candidates = list(path.glob(pattern))
    if not candidates:
        return None
    if len(candidates) > 1:
        print(f"WARNING: multiple matches for {pattern} in {path}, using first: {candidates[0]}")
    return candidates[0]


parser = argparse.ArgumentParser(
    description="Plot one variable series from CANYON_MED, MEDBGC_INS and STAT_PROFILES."
)
parser.add_argument("--var", required=True, help="Variable to plot, e.g. ALK")
parser.add_argument("--min-depth", type=float, default=0.0, help="Minimum depth for the plotted layer in meters")
parser.add_argument("--max-depth", type=float, default=5.0, help="Maximum depth for the plotted layer in meters")
parser.add_argument("--coast", default="everywhere", help="Coastness filter for STAT_PROFILES, e.g. everywhere or open_sea")
args = parser.parse_args()
user_var = args.var.upper()
min_depth = args.min_depth
max_depth = args.max_depth
coast = args.coast
depth_tag = f"{int(min_depth)}-{int(max_depth)}m"

if user_var not in ALIASES:
    raise ValueError(
        f"Variable '{user_var}' not supported. Supported values: {', '.join(sorted(ALIASES.keys()))}"
    )

mapping = ALIASES[user_var]
var = user_var
base = Path(__file__).resolve().parent

paths = {}
if mapping["bgc"] is not None:
    paths["BGC_ARGO"] = find_csv(
        base / "CANYON_MED",
        f"*_{mapping['bgc']}_*timeseries_all_basins*{depth_tag}*_ppcon_ins_cmed.csv",
        recursive=True,
    ) or find_csv(
        base / "CANYON_MED",
        f"*_{mapping['bgc']}_*timeseries_all_basins*{depth_tag}*.csv",
        recursive=True,
    )
else:
    paths["BGC_ARGO"] = None

if mapping["med"] is not None:
    paths["MEDBGC_INS"] = find_csv(
        base / "MEDBGC_INS",
        f"*{mapping['med']}*timeseries_all_basins*{depth_tag}*.csv",
        recursive=True,
    )
else:
    paths["MEDBGC_INS"] = None

if mapping["stat"] is not None:
    stat_dir = base.joinpath("STAT_PROFILES", f"{depth_tag}_{coast}")
    if stat_dir.is_dir():
        stat_paths = list(
            stat_dir.rglob(
                f"*{mapping['stat']}*layer_{int(min_depth)}_{int(max_depth)}m*.csv"
            )
        )
    else:
        stat_paths = list(
            base.joinpath("STAT_PROFILES").rglob(
                f"*{mapping['stat']}*layer_{int(min_depth)}_{int(max_depth)}m*.csv"
            )
        )
    for path in stat_paths:
        paths[path.parent.name] = path

if not any(path is not None for path in paths.values()):
    raise FileNotFoundError(
        f"No dataset files found for variable '{user_var}' in {base}"
    )


data = {}
for label, source_path in paths.items():
    if source_path is None:
        print(f"WARNING: no file available for {label} and variable {user_var}")
        continue

    if label == "BGC_ARGO":
        source_name = mapping["bgc"]
    elif label == "MEDBGC_INS":
        source_name = mapping["med"]
    else:
        source_name = mapping["stat"]

    data[label] = load_csv(source_path, var, label, source_name, min_depth, max_depth)

if not data:
    raise RuntimeError(f"No datasets available for variable '{user_var}'")

basins = [basin.name for basin in get_elementary_basins()]

plt.style.use("default")
default_palette =['cyan'] #["#5B8CC9", "#D47C4F", "#7CA982", "#9B6FBF", "#8C8C8C"]
color_by_label = {
    "V12C": "deeppink",
    "QUID_V13C_DA_SAT": "yellow",
    "V13C": "green",
    "RA": "k",
    "INTERIM": "k",
    "MEDBGC_INS": "goldenrod",
}
source_type_colors = {
    "I": "red",  # "#1F1F1F",  # insitu
    "C": "#7F7F7F",  # canyon_med
    "P": "#B0B0B0",  # ppcon
    None: color_by_label.get("BGC_ARGO", default_palette[0]),
}

outdir = base / "plots" / f"{depth_tag}_{coast}"
outdir.mkdir(parents=True, exist_ok=True)

ylabel = get_ylabel(var)
for basin in basins:
    fig, ax = plt.subplots(figsize=(10, 5))

    has_date = False
    for index, (label, df) in enumerate(data.items()):
        color = color_by_label.get(label, default_palette[index % len(default_palette)])
        legend_label = label  
        if label in ["BGC_ARGO", "MEDBGC_INS"]:
            if "basin" not in df.columns:
                continue
            dfb = df[df["basin"] == basin].copy()
            if dfb.empty:
                continue
            if "time" in dfb.columns:
                dfb = dfb.sort_values("time")
                if var == "NITRATE" and "source_type" in dfb.columns:
                    for source_type in ["P", "C", "I"]:
                        dfg = dfb[dfb["source_type"] == source_type]
                        if dfg.empty:
                            continue
                        if source_type == "I":
                            marker = "."
                            size = 15
                            facecolor = "coral"
                            #edgecolor = "k"
                            zorder = 6
                        elif source_type == "P":
                            marker = "."
                            size = 15
                            facecolor = "b"
                            edgecolor = None #"silver"
                            zorder = 4
                        else:  # canyon_med
                            marker = "."
                            size = 15
                            facecolor = "dodgerblue"
                            edgecolor = None
                            zorder = 3
                        scatter_kwargs = {
                            "marker": marker,
                            "s": size,
                            "facecolors": facecolor,
                            "linewidths": 0.5,
                            "alpha": 0.88,
                            "zorder": zorder,
                            "label": f"{legend_label} ({source_type})",
                        }
                        if edgecolor is not None:
                            scatter_kwargs["edgecolors"] = edgecolor
                        ax.scatter(
                            dfg["time"],
                            dfg[var],
                            **scatter_kwargs,
                        )
                else:
                    ax.scatter(
                        dfb["time"],
                        dfb[var],
                        marker="+",
                        s=15,
                        #edgecolors="k",
                        linewidths=0.7,
                        color=color,
                        alpha=0.6,
                        zorder=3,
                        label=legend_label,
                    )
                has_date = True
        else:
            if df.empty:
                continue
            if "coast" in df.columns and "stat" in df.columns:
                dff = df[(df["coast"] == coast) & (df["stat"] == "Mean")].copy()
            else:
                dff = df.copy()
            if "sub" in dff.columns:
                dff = dff[dff["sub"] == basin]
            if dff.empty:
                continue

            edge_plot_kwargs = {
                "color": "black",
                "alpha": 1,
                "linestyle": "-",
                "linewidth": 3.,
                "zorder": 4,
            }
            if "quid" in label.lower() and "v13c" in label.lower():
                plot_kwargs = {
                    "color": color,
                    "alpha": 1.0,
                    "linestyle": ":",
                    "linewidth": 3.,
                    "zorder": 7,
                    "label": legend_label,
                }

            elif label in ["RA", "INTERIM"]:
                plot_kwargs = {
                    "color": color,
                    "alpha": 1.0,
                    "linestyle": "-",
                    "linewidth": 3.,
                    "zorder": 5,
                    "label": legend_label,
                }

            elif "V12C" in label:
                plot_kwargs = {
                    "color": color,
                    "alpha": 0.8,
                    "linestyle": "-",
                    "linewidth": 3.,
                    "zorder": 5,
                    "label": legend_label,
                }
            else:
                plot_kwargs = {
                    "color": color,
                    "alpha": 0.8,
                    "linestyle": "-",
                    #"marker": "o",
                    #"markersize": 4,
                    "linewidth": 3.,
                    "zorder": 6,
                    "label": legend_label,
                }

            if "date" in dff.columns:
                dff = dff.sort_values("date")
                ax.plot(dff["date"], dff[var], **edge_plot_kwargs)
                ax.plot(dff["date"], dff[var], **plot_kwargs)
                has_date = True
            else:
                ax.plot(dff["sub"], dff[var], **edge_plot_kwargs)
                ax.plot(dff["sub"], dff[var], **plot_kwargs)

    ax.set_title(f"{var} series for basin {basin}")
    ax.set_xlabel("time")
    ax.set_ylabel(ylabel)
    ax.legend(frameon=True, fontsize="small", ncol=2)
    ax.grid(True, linestyle=":", alpha=0.5)

    if has_date:
        locator = AutoDateLocator()
        formatter = DateFormatter("%Y-%m-%d")
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        fig.autofmt_xdate(rotation=45, ha="right")

    fig.tight_layout()

    out_path = outdir / f"{var}_timeseries_{basin}.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Saved {out_path}")
