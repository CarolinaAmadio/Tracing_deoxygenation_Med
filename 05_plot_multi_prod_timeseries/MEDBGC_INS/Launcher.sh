
#!/bin/bash

# Activate the provided Python environment and run timeseries_at_surface.py
# for a list of allowed carbon variables.

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/bit.sea/src:$PYTHONPATH

MIN_DEPTH=0
MAX_DEPTH=10
VARIABLES=(ALK pH_ins_merged DIC_merged pCO2_rec O2o)

for VAR in "${VARIABLES[@]}"; do
    echo "Running timeseries_at_surface.py for variable: ${VAR}"
    python timeseries_at_surface_medbgcins.py \
        -v "${VAR}" \
        --min-depth "${MIN_DEPTH}" \
        --max-depth "${MAX_DEPTH}"

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

    #echo "Plotting variable: ${PLOT_VAR}"
    #python ../plot_variable_timeseries.py --var "${PLOT_VAR}"
    #echo
done
