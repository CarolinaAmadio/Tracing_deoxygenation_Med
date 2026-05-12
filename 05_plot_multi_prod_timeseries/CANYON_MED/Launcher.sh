
#!/bin/bash

# Activate the provided Python environment and run timeseries_at_surface_canyon.py
# for a list of allowed carbon variables.

set -e
cd "$(dirname "$0")"
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=/g100_scratch/userexternal/camadio0/ARGOPY_TESTS/Climatologies_Argopy/ONLINE/

MIN_DEPTH=0
MAX_DEPTH=10
VARIABLES=(AT DIC PH_IN_SITU_TOTAL DOXY)

for VAR in "${VARIABLES[@]}"; do
    echo "Running timeseries_at_surface_canyon.py for variable: ${VAR}"
    python ./timeseries_at_surface_canyon.py \
        -v "${VAR}" \
        --min-depth "${MIN_DEPTH}" \
        --max-depth "${MAX_DEPTH}"
done


