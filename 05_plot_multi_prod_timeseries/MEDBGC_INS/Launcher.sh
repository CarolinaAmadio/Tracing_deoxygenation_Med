
#!/bin/bash

# Activate the provided Python environment and run timeseries_at_surface.py
# for a list of allowed carbon variables.

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/bit.sea/src:$PYTHONPATH
export MASKFILE="/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc"


COAST_LIST=("open_sea")
#COAST_LIST=("everywhere" "open_sea" "coast")

MIN_DEPTH=0
MAX_DEPTH=10
VARIABLES=(ALK pH_ins_merged DIC_merged pCO2_rec O2o N3n)

for VAR in "${VARIABLES[@]}"; do
    for coastness in "${COAST_LIST[@]}"; do
        echo "Running timeseries_at_surface.py for variable: ${VAR} coastness: ${coastness}"
        python timeseries_at_surface_medbgcins.py \
            -v "${VAR}" \
            --min-depth "${MIN_DEPTH}" \
            --max-depth "${MAX_DEPTH}" \
            --maskfile "${MASKFILE}" \
            --coastness "${coastness}"

    case "${VAR}" in
        pCO2_rec)
            PLOT_VAR="PCO2"
            ;;
        pH_ins_merged)
            PLOT_VAR="PH"
            ;;
        DIC_merged)
            PLOT_VAR="DIC"
            ;;
        O2o)
            PLOT_VAR="O2O"
            ;;
        *)
            PLOT_VAR="${VAR}"
            ;;
    esac

done
