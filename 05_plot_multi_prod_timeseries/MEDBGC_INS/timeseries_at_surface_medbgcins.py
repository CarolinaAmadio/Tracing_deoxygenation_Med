#!/usr/bin/env python3
"""Extracts a variable time series in a depth layer for each elementary V2 basin."""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from bitsea.basins import V2
from bitsea.basins.basin import Basin, ComposedBasin
from bitsea.commons.time_interval import TimeInterval
from bitsea.static.Carbon_reader import CarbonReader
from bitsea.static.Nutrients_reader import NutrientsReader
from bitsea.commons.mask import Mask

VALID_VARS = ["ALK", "pH_ins_merged", "DIC_merged", "pCO2_rec", "O2o", "N3n"]

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


def extract_variable_timeseries_for_basin(
    reader,
    basin,
    time_interval,
    variable,
    min_depth=0.0,
    max_depth=10.0,
    coastness_mask=None,
    TheMask=None,
):
    """Extracts the requested variable data for a single basin and returns a DataFrame."""
    if variable == "O2o":
        read_var = "oxygen"
    elif variable == "N3n":
        read_var = "nitrate"
    else:
        read_var = variable
    profiles = reader.Selector(read_var, time_interval, basin)
    rows = []

    for p in profiles:
        if coastness_mask is not None:
            ix, iy = TheMask.convert_lon_lat_to_indices(lon=p.lon, lat=p.lat)
            if not coastness_mask[iy, ix]:
                continue

        pres, values, _ = p.read(read_var)
        mask = (np.asarray(pres) >= min_depth) & (np.asarray(pres) <= max_depth)
        if not np.any(mask):
            continue

        selected_values = np.asarray(values)[mask]
        selected_values = selected_values[np.isfinite(selected_values)]
        if selected_values.size == 0:
            continue

        mean_value = np.nanmean(selected_values)
        rows.append(
            {
                "basin": basin.name,
                "time": p.time,
                "depth": max_depth,
                variable: mean_value,
                "lon": p.lon,
                "lat": p.lat,
                "profile_name": p.name(),
            }
        )

    if len(rows) == 0:
        return pd.DataFrame(
            columns=["basin", "time", "depth", variable, "lon", "lat", "profile_name"]
        )

    return pd.DataFrame(rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract a variable time series for a carbon variable in V2 elementary basins."
    )
    parser.add_argument(
        "-v",
        "--variable",
        required=True,
        choices=VALID_VARS,
        help="Variable to analyze. Must be one of the allowed variables. Use O2o for dissolved oxygen.",
    )
    parser.add_argument(
        "--min-depth",
        type=float,
        default=0.0,
        help="Minimum depth for the layer selection in meters (default 0).",
    )
    parser.add_argument(
        "--max-depth",
        type=float,
        default=10.0,
        help="Maximum depth for the layer selection in meters (default 10).",
    )
    parser.add_argument(
        "--maskfile",
        "-M",
        type=str,
        required=False,
        help="Path to the mesh mask file used for coastness filtering.",
    )
    parser.add_argument(
        "--coastness",
        type=str,
        choices=["coast", "open_sea", "everywhere"],
        default="everywhere",
        help="Area filter to select coast, open_sea, or everywhere.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    TheMask = None
    coastness_mask = None
    if args.coastness != "everywhere":
        if args.maskfile is None:
            raise ValueError(
                "--maskfile is required when --coastness is coast or open_sea"
            )
        TheMask = Mask.from_file(
            Path(args.maskfile),
            ylevels_var_name="gphit",
            xlevels_var_name="glamt",
        )
        mask200_2D = TheMask.mask_at_level(200.0)
        mask0_2D = TheMask.mask_at_level(0.0)
        coastmask = mask0_2D & (~mask200_2D)

        if args.coastness == "open_sea":
            coastness_mask = mask200_2D
        elif args.coastness == "coast":
            coastness_mask = coastmask

    TI = TimeInterval("19950101", "20240101", "%Y%m%d")
    C = CarbonReader()
    N = NutrientsReader()
    SUB = get_elementary_basins()
    depth_tag = f"{int(args.min_depth)}-{int(args.max_depth)}m"
    output_dir = Path(__file__).resolve().parent / f"{depth_tag}_{args.coastness}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(SUB)} elementary basins in V2.")
    all_dfs = []

    for isub in SUB:
        print(f"Extracting for elementary basin: {isub.name}")
        reader = N if args.variable in ["O2o", "N3n"] else C
        df = extract_variable_timeseries_for_basin(
            reader,
            isub,
            TI,
            args.variable,
            min_depth=args.min_depth,
            max_depth=args.max_depth,
            coastness_mask=coastness_mask,
            TheMask=TheMask,
        )
        print(f"  points found: {len(df)}")
        if not df.empty:
            all_dfs.append(df)

    result = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame(
        columns=["basin", "time", "depth", args.variable, "lon", "lat", "profile_name"]
    )
    output_file = output_dir / f"{args.variable}_timeseries_all_basins_{depth_tag}_{args.coastness}.csv"
    result.to_csv(output_file, index=False)
    print(f"Time series saved to: {output_file}")


if __name__ == "__main__":
    main()
