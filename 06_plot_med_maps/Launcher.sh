#!/bin/bash

NAMEDIR=Tracing_deoxygenation_Med_ISSUE_01

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
#source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/${NAMEDIR}/bit.sea/src

# mappa del med con 16 sottobacini
python plot_med_maps_subbasin.py --all-subs --outdir PLOTS

# mappa del med con alcuni sottobacini colorati no borders default hardcoded lev nwm
python plot_med_maps_subbasin.py --no-all-subs --outdir PLOTS
