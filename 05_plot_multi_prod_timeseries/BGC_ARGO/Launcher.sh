#!/bin/bash

#SBATCH --job-name=argo_bgc
#SBATCH -N1
#SBATCH --ntasks-per-node=16
#SBATCH --time=00:30:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

# Activate the provided Python environment and run timeseries_at_surface_canyon.py
# for a list of allowed carbon variables.

NAMEDIR=Tracing_deoxygenation_Med_ISSUE_01

set -e
cd "$(dirname "$0")"
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate



export PYTHONPATH=/g100_scratch/userexternal/camadio0/${NAMEDIR}/05_plot_multi_prod_timeseries/bit.sea/src:$PYTHONPATH

export ONLINE_REPO=/g100_scratch/userexternal/camadio0/${NAMEDIR}/ONLINE/
#/g100_scratch/userexternal/camadio0/ARGOPY_TESTS/Climatologies_Argopy/ONLINE/

MIN_DEPTH=550
MAX_DEPTH=650
VARIABLES=(AT DIC PH_IN_SITU_TOTAL DOXY)
VARIABLES=(DOXY)

for VAR in "${VARIABLES[@]}"; do
    echo "Running timeseries_at_surface_canyon.py for variable: ${VAR}"
    #only canyonmed nitrate no insitu no ppcon
    python ./timeseries_at_surface_superfloat.py  \
        -v "${VAR}" \
        --min-depth "${MIN_DEPTH}" \
        --max-depth "${MAX_DEPTH}"
done

# a csv with all ins - ppcon and canyonmed saved 
#python timeseries_at_surface_canyon_ins_ppcon.py -v NITRATE --min-depth "${MIN_DEPTH}" --max-depth "${MAX_DEPTH}"

