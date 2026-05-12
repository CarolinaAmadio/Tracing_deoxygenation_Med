#!/bin/bash

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
#source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/bit.sea/src:$PYTHONPATH

cd /g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/05_validation || exit 1

MIN_DEPTH=0
MAX_DEPTH=10
COAST_LIST=("everywhere" "open_sea" "coast")
VARIABLES=(ALK DIC PH_IN_SITU_TOTAL PCO2 DOXY)

for COAST in "${COAST_LIST[@]}"; do
    PLOT_DIR="plots/${MIN_DEPTH}-${MAX_DEPTH}m_${COAST}"

    for VAR in "${VARIABLES[@]}"; do
        echo "Running plot_variable_timeseries.py --var ${VAR} --min-depth ${MIN_DEPTH} --max-depth ${MAX_DEPTH} --coast ${COAST}"
        python plot_variable_timeseries.py --var "${VAR}" --min-depth "${MIN_DEPTH}" --max-depth "${MAX_DEPTH}" --coast "${COAST}"
        if [ $? -ne 0 ]; then
            echo "ERROR: plotting ${VAR} failed for coast=${COAST}"
            exit 1
        fi

        echo "Generating HTML and PDF for ${VAR} in ${COAST}"
        python clim_visualizer_html_pdf.py -v "${VAR}" -i "${PLOT_DIR}"
        if [ $? -ne 0 ]; then
            echo "ERROR: report generation for ${VAR} failed for coast=${COAST}"
            exit 1
        fi
    done

    DEST_DIR="/g100_work/OGS_test2528/internal-validation/pub/camadio/V13C/${MIN_DEPTH}-${MAX_DEPTH}m_${COAST}"
    mkdir -p "${DEST_DIR}"
    cp -v "${PLOT_DIR}"/*.pdf "${DEST_DIR}/"
done
