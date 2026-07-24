# ex script prova.tmp.py
import xarray as xr
import numpy as np
import pandas as pd
import glob
import os
import gsw
import argparse
import argopy

parser = argparse.ArgumentParser(description="Calculation of monthly climatologies per sub basin")
parser.add_argument("--indir", "-i", required=True,  help="Directory input")
parser.add_argument("--outdir", "-o", required=True,  help="Directory output")
parser.add_argument("--coriolis", "-c", required=True,  help="coriolis model")
args = parser.parse_args()

#dynamic inputs
INPUTDIR = args.indir
OUTDIR   = args.outdir
CORIOLIS = args.coriolis

FILELIST=sorted(glob.glob(INPUTDIR+'/*/*nc'))
VARLIST=['NO3', 'PO4','DIC','SiOH4','AT','pHT']

# -----------------------------
#  Interp su PRES_TEMP
# -----------------------------
def interp_to_pres(var_name, pres_name):
    var = ds[var_name].values
    pres_var = ds[pres_name].values
    interp = np.interp(pres, pres_var, var, left=np.nan, right=np.nan)
    return interp.reshape(1, -1)

# loop on each file in inputdir
for file in FILELIST:
    ds      =  xr.open_dataset(file)
    dsc     =  xr.open_dataset(CORIOLIS + os.path.relpath(file, INPUTDIR))
    outfile =  OUTDIR + os.path.relpath(file, INPUTDIR)
    if os.path.exists(outfile): 
        print( 'Skipping processing ' + outfile)
        continue
    print(file)
    os.makedirs(OUTDIR+ '/' + os.path.relpath(file, INPUTDIR).split('/')[0], exist_ok=True) 
    

    if 'DOXY' not in ds.data_vars:
        ds.to_netcdf(path= outfile,mode="w",format="NETCDF4")

    else:
        #  npres interpoator ndoxy and nTemp no same 
        pres     = ds["PRES_DOXY"].values
        n_levels = len(pres)
        new_ds   = xr.Dataset()

        new_ds = new_ds.assign_coords(
            N_PROF=[0],
            N_LEVELS=np.arange(n_levels))

        new_ds["PRES"] = (("N_PROF", "N_LEVELS"), pres.reshape(1, -1))

        #for var in ds.data_vars:
        for var in ['TEMP','PSAL','DOXY']:
             new_ds[var] = (
                    ("N_PROF", "N_LEVELS"),
                    interp_to_pres(var, f"PRES_{var}"))
        
        new_ds["LATITUDE"]  = ("N_PROF", ds["LATITUDE"].values)
        new_ds["LONGITUDE"] = ("N_PROF", ds["LONGITUDE"].values)

        #  SAVE TIME vars 
        ref_str  = ds["REFERENCE_DATE_TIME"].values.tobytes().decode("utf-8")
        ref_time = pd.to_datetime(ref_str, format="%Y%m%d%H%M%S")
        time     = ref_time + pd.to_timedelta(ds["JULD"].values, unit="D")
        new_ds["TIME"] = ("N_PROF", pd.to_datetime(time))

        # -----------------------------
        #  profile → point
        #  Canyon MED prediction
        # -----------------------------
        new_ds   = new_ds.argo.profile2point()
        # from mmol/m3 ---> ummol/kg using TEOS-10 via gsw
        SA = gsw.SA_from_SP(
            new_ds["PSAL"].values,
            new_ds["PRES"].values,
            new_ds["LONGITUDE"].values,
            new_ds["LATITUDE"].values,
        )
        CT = gsw.CT_from_t(
            SA,
            new_ds["TEMP"].values,
            new_ds["PRES"].values,
        )
        density = gsw.rho(SA, CT, new_ds["PRES"].values)
        new_ds["DOXY"] = new_ds["DOXY"] * 1000.0 / density
        NNvar    = new_ds.argo.canyon_med.predict()
        
        # convert DOXY back to mmol/m3
        new_ds["DOXY"] = new_ds["DOXY"] * density / 1000
        new_ds["DOXY"].attrs["units"] = "mmol/m3"

        #from ummol/kg to mmol/m3 
        vars_to_add = ["NO3", "PO4", "SiOH4"] # at and dic in umol/kg 
        for VAR in vars_to_add:
            NNvar[VAR] = NNvar[VAR] * density / 1000 # mmol/m3 -> µmol/kg
            NNvar[VAR].attrs["units"] = "mmol/m3"
        for VAR in ['DIC','AT','pHT'] :
            NNvar[VAR].attrs["units"] = "umol/kg"

        #  Copia variabili meta da dsc
        npoints   = NNvar.dims["N_POINTS"]
        meta_vars = ["PLATFORM_NUMBER", "CYCLE_NUMBER", "DIRECTION"]

        for v in meta_vars:
            if v in dsc:
                value = dsc[v].values.squeeze()
                NNvar[v] = ("N_POINTS", np.repeat(value, npoints))
                NNvar[v].attrs = dsc[v].attrs.copy()
                if hasattr(dsc[v], "encoding"):
                    NNvar[v].encoding = dsc[v].encoding.copy()

        #  Trasforma N_POINTS → (N_PROF, N_LEVELS)
        NN_profiles = xr.Dataset()
        NN_profiles = NN_profiles.assign_coords(
            N_PROF=[0],
            N_LEVELS=np.arange(n_levels)
        )

        for v in NNvar.data_vars:
            if NNvar[v].dims == ("N_POINTS",):
                NN_profiles[v] = (
                    ("N_PROF", "N_LEVELS"),
                    NNvar[v].values.reshape(1, n_levels)
                )
                NN_profiles[v].attrs = NNvar[v].attrs
                if hasattr(NNvar[v], "encoding"):
                    NN_profiles[v].encoding = NNvar[v].encoding

        ds_final = ds.copy()
        vars_to_add = ["NO3", "PO4", "DIC", "SiOH4", "AT", "pHT"]
        n_levels = ds.dims["nDOXY"]
        for VAR in vars_to_add:
            if VAR == "NO3":
                var_out = "NITRATE"
                dtype_out = np.float32
            elif VAR=="pHT":
                var_out="PH_IN_SITU_TOTAL"
                dtype_out = np.float32
            else:
                var_out = VAR
                dtype_out = np.float32
                
            dim_name = "n" + var_out + "_CANYONMED"


            # PRES
            ds_final["PRES_" + var_out + "_CANYONMED"] = (dim_name,ds["PRES_DOXY"].values)
            ds_final["PRES_" + var_out + "_CANYONMED"].attrs = (ds["PRES_DOXY"].attrs.copy())

            # DATA
            _data = NN_profiles[VAR].values[0, :]
            _data = np.float32(_data) 
            ds_final[var_out + "_CANYONMED"] = (dim_name, _data)
            ds_final[var_out + "_CANYONMED"].attrs = (NN_profiles[VAR].attrs.copy())

            # QC
            qc_array = np.full(n_levels, -1111, dtype=np.float32)
            ds_final[var_out + "_CANYONMED_QC"] = (dim_name, qc_array)
            ds_final[var_out + "_CANYONMED_QC"].attrs = {
                "long_name": "Quality flag for " + var_out,
                "conventions": "Argo reference table 2",
                "_FillValue": np.nan,}

        ds_final.to_netcdf(
            path= outfile,mode="w", format="NETCDF4", engine="netcdf4")


