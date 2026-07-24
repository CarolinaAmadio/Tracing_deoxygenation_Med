#!/bin/bash

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
#source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/bit.sea/src
#export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/bit.sea/src:$PYTHONPATH

cd /g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/05_plot_multi_prod_timeseries || exit 1

MIN_DEPTH=80
MAX_DEPTH=120
#COAST_LIST=("everywhere" "open_sea" "coast")

COAST_LIST=("open_sea")


#VARIABLES=(ALK DIC PH_IN_SITU_TOTAL PCO2 DOXY NITRATE)
VARIABLES=(NITRATE)

for COAST in "${COAST_LIST[@]}"; do
    PLOT_DIR="plots/${MIN_DEPTH}-${MAX_DEPTH}m_${COAST}"
    SUBPLOT_DIR="plots/${MIN_DEPTH}-${MAX_DEPTH}m_${COAST}_subplot"

    for VAR in "${VARIABLES[@]}"; do
        echo "Running plot_variable_timeseries.py --var ${VAR} --min-depth ${MIN_DEPTH} --max-depth ${MAX_DEPTH} --coast ${COAST}"
        python plot_variable_timeseries.py --var "${VAR}" --min-depth "${MIN_DEPTH}" --max-depth "${MAX_DEPTH}" --coast "${COAST}"
        if [ $? -ne 0 ]; then
            echo "ERROR: plotting ${VAR} failed for coast=${COAST}"
            exit 1
        fi

        echo "Running plot_variable_timeseries_subplot.py --var ${VAR} --min-depth ${MIN_DEPTH} --max-depth ${MAX_DEPTH} --coast ${COAST}"
        python plot_variable_timeseries_subplot.py --var "${VAR}" --min-depth "${MIN_DEPTH}" --max-depth "${MAX_DEPTH}" --coast "${COAST}"
        if [ $? -ne 0 ]; then
            echo "ERROR: subplot plotting ${VAR} failed for coast=${COAST}"
            exit 1
        fi

        echo "Generating HTML and PDF for ${VAR} in ${COAST}"
        python clim_visualizer_html_pdf.py -v "${VAR}" -i "${PLOT_DIR}"
        if [ $? -ne 0 ]; then
            echo "ERROR: report generation for ${VAR} failed for coast=${COAST}"
            exit 1
        fi

        if [ -d "${SUBPLOT_DIR}" ]; then
            echo "Generating HTML and PDF for subplot ${VAR} in ${COAST}"
            python clim_visualizer_html_pdf.py -v "${VAR}" -i "${SUBPLOT_DIR}"
            if [ $? -ne 0 ]; then
                echo "ERROR: subplot report generation for ${VAR} failed for coast=${COAST}"
                exit 1
            fi
        fi
    done

    DEST_DIR="/g100_work/OGS_test2528/internal-validation/pub/camadio/V13C/${MIN_DEPTH}-${MAX_DEPTH}m_${COAST}"
    SUBPLOT_DEST_DIR="/g100_work/OGS_test2528/internal-validation/pub/camadio/V13C/${MIN_DEPTH}-${MAX_DEPTH}m_${COAST}_subplot"
    mkdir -p "${DEST_DIR}"
    mkdir -p "${SUBPLOT_DEST_DIR}"
    cp -v "${PLOT_DIR}"/*.pdf "${DEST_DIR}/"
    if [ -d "${SUBPLOT_DIR}" ]; then
        cp -v "${SUBPLOT_DIR}"/*.pdf "${SUBPLOT_DEST_DIR}/"
    fi

done
