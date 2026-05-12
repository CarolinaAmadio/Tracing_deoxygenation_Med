#!/usr/bin/env python3
"""
Estrai la media dei primi 5 metri del profilo ALK per ogni sottobacino.
Supporta file NetCDF (.nc) e pickle (.pkl) con struttura analoga.
"""

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from bitsea.commons.mask import Mask


TheMask=Mask.from_file("/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc")
z_lev= TheMask.zlevels
TheMask.get_depth_index(10)

sub_list = [
    "alb", "swm1", "swm2", "nwm", "tyr1", "tyr2",
    "adr1", "adr2", "aeg", "ion1", "ion2", "ion3",
    "lev1", "lev2", "lev3", "lev4", "med", "atl"]
coast_list = ["coast", "open_sea", "everywhere"]
stat_list = ["Mean", "Std", "min", "p05", "p25", "p50", "p75", "p95", "max"]


# Ensure bitsea modules are importable for legacy pickles.
bitsea_path = Path(__file__).resolve().parents[1] / "bit.sea" / "src"
if str(bitsea_path) not in sys.path:
    sys.path.insert(0, str(bitsea_path))

from bitsea.basins import V2
from bitsea.basins.basin import Basin, ComposedBasin


def parse_list(attr_value):
    if attr_value is None:
        return []
    items = [item.strip().strip('"').strip("'") for item in attr_value.split(",")]
    return [item for item in items if item]


def find_index(target, items):
    if target is None:
        return None
    target_lower = target.strip().lower()
    for idx, item in enumerate(items):
        if item.strip().lower() == target_lower:
            return idx
    return None


def normalize_time(ds):
    if "time" not in ds.coords:
        return ds

    time = ds["time"]
    if pd.api.types.is_integer_dtype(time.dtype):
        try:
            dt = pd.to_datetime(time.values, unit="s", origin="unix")
            ds = ds.assign_coords(time=dt)
        except Exception:
            pass
    return ds


def get_index_or_default(target, items, axis_name, default_target=None):
    if items:
        idx = find_index(target, items)
        if idx is not None:
            return idx
        raise ValueError(f"Categoria {axis_name} '{target}' non trovata in {axis_name}_list: {items}")

    if default_target is not None and target == default_target:
        if axis_name == "coast" and target == "everywhere":
            print(f"WARNING: {axis_name}_list mancante nel pickle; uso l'ultimo indice per '{target}'")
            return -1
        print(f"WARNING: {axis_name}_list mancante nel pickle; uso l'indice 0 per '{target}'")
        return 0

    raise ValueError(
        f"{axis_name}_list mancante nel pickle e '{target}' non può essere risolto"
    )


class LegacyUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "pathlib._local":
            module = "pathlib"
        if module.startswith("commons"):
            module = "bitsea." + module
        return super().find_class(module, name)


def list_to_dataset(obj, var_name):
    data = np.asarray(obj[0])
    time_obj = obj[1]
    if hasattr(time_obj, "get_datetime_array"):
        time = np.asarray(time_obj.get_datetime_array())
    elif hasattr(time_obj, "time"):
        time = np.asarray(time_obj.time)
    else:
        raise ValueError("TimeList object non ha get_datetime_array o time")

    if data.ndim == 5:
        dims = ("nFrames", "nSub", "nCoast", "depth", "nStat")
    elif data.ndim == 4:
        dims = ("nFrames", "nSub", "depth", "nStat")
    else:
        raise ValueError(f"Array '{var_name}' ha dimensione non supportata: {data.ndim}")

    coords = {"nFrames": time}
    if data.ndim == 5:
        coords.update({
            "nSub": np.arange(data.shape[1]),
            "nCoast": np.arange(data.shape[2]),
            "depth": np.arange(data.shape[3]),
            "nStat": np.arange(data.shape[4]),
        })
    else:
        coords.update({
            "nSub": np.arange(data.shape[1]),
            "depth": np.arange(data.shape[2]),
            "nStat": np.arange(data.shape[3]),
        })

    return xr.Dataset({var_name: (dims, data)}, coords=coords)


def dataset_from_pickle(path, var_name):
    with open(path, "rb") as handle:
        try:
            obj = LegacyUnpickler(handle, encoding="latin1").load()
        except TypeError:
            handle.seek(0)
            obj = LegacyUnpickler(handle).load()
        except Exception:
            handle.seek(0)
            obj = pickle.load(handle, fix_imports=True, encoding="latin1")

    if isinstance(obj, xr.Dataset):
        return obj

    if isinstance(obj, xr.DataArray):
        return obj.to_dataset(name=var_name)

    if isinstance(obj, list):
        return list_to_dataset(obj, var_name)

    if isinstance(obj, pd.DataFrame):
        return obj.to_xarray()

    if isinstance(obj, dict):
        if var_name in obj:
            return dict_to_dataset(obj, var_name)

        try:
            ds = xr.Dataset.from_dict(obj)
            if var_name in ds or len(ds.data_vars) == 1:
                return ds
        except Exception:
            pass

    raise ValueError(f"Impossibile caricare un Dataset da file pickle: {path}")


def dict_to_dataset(obj, var_name):
    data = obj[var_name]
    data = np.asarray(data)
    data = xr.DataArray(data).values

    if data.ndim == 5:
        dims = ("nFrames", "nSub", "nCoast", "depth", "nStat")
    elif data.ndim == 4:
        dims = ("nFrames", "nSub", "depth", "nStat")
    else:
        raise ValueError(f"Array '{var_name}' ha dimensione non supportata: {data.ndim}")

    coords = {}
    if "time" in obj:
        coords["nFrames"] = obj["time"]
    if "depth" in obj:
        coords["depth"] = obj["depth"]
    if "nSub" in obj:
        coords["nSub"] = obj["nSub"]
    if "nCoast" in obj:
        coords["nCoast"] = obj["nCoast"]
    if "nStat" in obj:
        coords["nStat"] = obj["nStat"]

    data_array = xr.DataArray(data, dims=dims, coords=coords, name=var_name)
    ds = data_array.to_dataset()

    attrs = {}
    for key in ("sub___list", "coast_list", "stat__list", "frame_list"):
        if key in obj:
            attrs[key] = obj[key]
    if attrs:
        ds.attrs.update(attrs)

    return ds


def load_dataset(input_file, var_name):
    input_path = Path(input_file)
    suffix = input_path.suffix.lower()

    if suffix == ".nc":
        return xr.open_dataset(input_path)
    if suffix == ".pkl":
        return dataset_from_pickle(input_path, var_name)

    raise ValueError(f"Formato file non supportato: {suffix}")


def find_pkl_file(base_dir, case, var_name):
    path = Path(base_dir) / case / f"{var_name}.pkl"
    return path if path.is_file() else None


def process_batch(
    input_base,
    case_names,
    var_names,
    coast_name="everywhere",
    stat_name="Mean",
    min_depth=0.0,
    max_depth=10.0,
    output_base=None,
):
    input_base = Path(input_base)
    if output_base is not None:
        output_base = Path(output_base)

    depth_tag = f"{int(min_depth)}-{int(max_depth)}m"
    for case in case_names:
        for var_name in var_names:
            input_file = find_pkl_file(input_base, case, var_name)
            if input_file is None:
                print(f"WARNING: file mancante {input_base / case / f'{var_name}.pkl'}, skip")
                continue

            if output_base is not None:
                output_dir = output_base / depth_tag / case
            else:
                output_dir = input_base / depth_tag / case
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{case}_{var_name}.layer_{int(min_depth)}_{int(max_depth)}m.{stat_name}.csv"

            print(f"Processing {input_file} var={var_name} coast={coast_name} stat={stat_name}")
            process_file(
                input_file,
                output_file=output_file,
                var_name=var_name,
                coast_name=coast_name,
                stat_name=stat_name,
                min_depth=min_depth,
                max_depth=max_depth,
            )


def process_file(
    input_file,
    output_file=None,
    var_name="ALK",
    coast_name="everywhere",
    stat_name="Mean",
    min_depth=0.0,
    max_depth=5.0,
):
    input_path = Path(input_file)
    ds = load_dataset(input_path, var_name)
    ds = normalize_time(ds)

    if "nFrames" in ds.coords and "time" not in ds.coords:
        ds = ds.assign_coords(time=("nFrames", ds["nFrames"].values))

    ds = ds.assign_coords(
        nSub=sub_list,
        nCoast=coast_list,
        nStat=stat_list,
    )

    if var_name not in ds:
        raise KeyError(f"Variabile '{var_name}' non trovata in {input_file}")
    
    #data = ds[var_name].isel(nCoast=2, nStat=0)
    data = ds[var_name].sel(
    nStat=stat_name,
    nCoast=coast_name)

    data = data.sel(
    nSub=~data.nSub.isin(["med", "atl"]))


    if "depth" not in data.coords:
        raise KeyError("La variabile non ha la coordinata 'depth' richiesta.")

    depth = z_lev
    z_index_min = TheMask.get_depth_index(min_depth)
    z_index_max = TheMask.get_depth_index(max_depth)

    if depth.size == 0:
        raise ValueError("La coordinata depth è vuota.")

    if depth[0] > depth[-1]:
        data = data.sortby("depth")
     
    layer_data = data.isel(depth=slice(z_index_min, z_index_max))
    mean_layer = layer_data.mean(dim="depth")

    value_name = f"{var_name}_mean_{int(min_depth)}to{int(max_depth)}m"
    df = mean_layer.to_dataframe(name=value_name).reset_index()

    if "nSub" in df.columns:
        df["sub"] = df["nSub"].astype(str)

    if "nCoast" in df.columns:
        df["coast"] = coast_name
        

    if "nFrames" in df.columns:
        df["time"] = pd.to_datetime(df["nFrames"], errors="coerce")
        df["date"] = df["time"].dt.strftime("%Y-%m-%d")
    elif "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df["date"] = df["time"].dt.strftime("%Y-%m-%d")
    elif "frame_list" in ds.attrs:
        dates = pd.to_datetime(ds.attrs["frame_list"], errors="coerce")
        if len(dates) == len(df):
            df["date"] = dates.strftime("%Y-%m-%d")
        else:
            df["date"] = pd.NA

    df["stat"] = stat_name

    if "sub" in df.columns:
        basin_order = sub_list 
        cat_type = pd.CategoricalDtype(categories=basin_order, ordered=True)
        df["sub"] = df["sub"].astype(str)
        df["_sub_order"] = df["sub"].astype(cat_type)

    if "date" in df.columns:
        df["_date_order"] = pd.to_datetime(df["date"], errors="coerce")

    sort_keys = []
    if "_sub_order" in df.columns:
        sort_keys.append("_sub_order")
    if "_date_order" in df.columns:
        sort_keys.append("_date_order")
    if sort_keys:
        df = df.sort_values(sort_keys, na_position="last")

    columns = []
    if "sub" in df.columns:
        columns.append("sub")
    if "coast" in df.columns:
        columns.append("coast")
    columns.extend(["stat", value_name])
    if "date" in df.columns:
        columns.append("date")

    df = df[[col for col in columns if col in df.columns]]
    df = df.drop(columns=[col for col in ["_sub_order", "_date_order"] if col in df.columns])

    if output_file is None:
        depth_tag = f"{int(min_depth)}-{int(max_depth)}m"
        output_file = input_path.with_suffix(
            f".{var_name}.layer_{int(min_depth)}_{int(max_depth)}m.{stat_name}.csv"
        )
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Calcola la media di uno strato di profondità dei profili per ogni sottobacino "
            "a partire da file pickle (.pkl)."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input-file", "-i", help="File in input singolo (.nc o .pkl)")
    group.add_argument("--input-base", "-b", help="Directory base contenente le cartelle dei case")
    parser.add_argument("--output-file", "-o", help="File CSV di output per il singolo input")
    parser.add_argument("--output-base", "-B", help="Directory base per gli output batch. Se omesso, usa la stessa cartella del case")
    parser.add_argument("--cases", default="V12C,V13C,RA,QUID_V13C_dasatfloat", help="Nomi dei case separati da virgola")
    parser.add_argument("--vars", default="ALK,DIC,pH,pCO2,O2o", help="Variabili da processare, separate da virgola")
    parser.add_argument("--var", default="ALK", help="Variabile da processare nel caso singolo (default ALK)")
    parser.add_argument("--coast", default="everywhere", help="Categoria coast da usare (default everywhere)")
    parser.add_argument("--stat", default="Mean", help="Statistica da elaborare (default Mean)")
    parser.add_argument("--min-depth", type=float, default=0.0, help="Profondità minima per la media in metri (default 0)")
    parser.add_argument("--max-depth", type=float, default=5.0, help="Profondità massima per la media in metri (default 5)")
    args = parser.parse_args()

    if args.input_file:
        output_path = process_file(
            args.input_file,
            output_file=args.output_file,
            var_name=args.var,
            coast_name=args.coast,
            stat_name=args.stat,
            min_depth=args.min_depth,
            max_depth=args.max_depth,
        )
        print(f"CSV scritto in: {output_path}")
        return

    case_names = [case.strip() for case in args.cases.split(",") if case.strip()]
    var_names = [var.strip() for var in args.vars.split(",") if var.strip()]

    process_batch(
        args.input_base,
        case_names,
        var_names,
        coast_name=args.coast,
        stat_name=args.stat,
        min_depth=args.min_depth,
        max_depth=args.max_depth,
        output_base=args.output_base,
    )


if __name__ == "__main__":
    main()
