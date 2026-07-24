#!/usr/bin/env python3
"""Extracts a variable time series in a depth layer for each elementary V2 basin."""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from bitsea.basins import V2
from bitsea.basins.basin import Basin, ComposedBasin
from bitsea.commons.time_interval import TimeInterval
from bitsea.instruments import float_canyonmed as bio_float

VALID_VARS = ["AT", "PH_IN_SITU_TOTAL", "DIC", "DOXY", "NITRATE"]


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


def extract_variable_timeseries_for_basin(basin, time_interval, variable, min_depth=0.0, max_depth=5.0):
    """Extracts the requested variable data for a single basin and returns a DataFrame."""
    profiles = bio_float.FloatSelector(variable, time_interval, basin)
    rows = []

    for p in profiles:
        if variable == "DOXY":
            sourcedata = "insitu"
            source_type = "I"
        elif variable == "NITRATE":
            if p._my_float.has_insitu("NITRATE"):
                sourcedata = "insitu"
                source_type = "I"
            else:
                sourcedata = "canyon_med"
                source_type = "C"
        else:
            sourcedata = "canyon_med"
            source_type = None

        try:
            pres, values, _ = p.read(variable, sourcedata=sourcedata)
        except (AssertionError, KeyError, ValueError) as exc:
            print(f"Skipping profile {p.name()} due to read error: {exc}", flush=True)
            continue

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
                "wmo": p.name(),
                "cycle": p._my_float.cycle,
                "source_type": source_type,
            }
        )

    if len(rows) == 0:
        return pd.DataFrame(
            columns=[
                "basin",
                "time",
                "depth",
                variable,
                "lon",
                "lat",
                "profile_name",
                "wmo",
                "cycle",
                "source_type",
            ]
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
        help="Variable to analyze. Must be one of the allowed carbon variables.",
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
        default=5.0,
        help="Maximum depth for the layer selection in meters (default 5).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    TI = TimeInterval("19950101", "20280101", "%Y%m%d")
    SUB = get_elementary_basins()
    depth_tag = f"{int(args.min_depth)}-{int(args.max_depth)}m"
    output_dir = Path(__file__).resolve().parent / depth_tag
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(SUB)} elementary basins in V2.")
    all_dfs = []

    for isub in SUB:
        print(f"Extracting for elementary basin: {isub.name}")
        df = extract_variable_timeseries_for_basin(
            isub,
            TI,
            args.variable,
            min_depth=args.min_depth,
            max_depth=args.max_depth,
        )
        print(f"  points found: {len(df)}")
        if not df.empty:
            all_dfs.append(df)

    result = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame(
        columns=[
            "basin",
            "time",
            "depth",
            args.variable,
            "lon",
            "lat",
            "profile_name",
            "wmo",
            "cycle",
            "source_type",
        ]
    )
    output_file = output_dir / f"BGC_ARGO_{args.variable}_timeseries_all_basins_{depth_tag}.csv"
    result.to_csv(output_file, index=False)
    print(f"Time series saved to: {output_file}")


if __name__ == "__main__":
    main()
