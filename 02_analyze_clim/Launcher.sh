#!/bin/bash

#SBATCH --job-name=doxy2
#SBATCH -N1 
#SBATCH --ntasks-per-node=16
#SBATCH --time=0:50:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

#cd "$SLURM_SUBMIT_DIR"
#. ${BASEDIR:-/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01}/utils/profile.inc

echo "Job started at: $(date)"

BASEDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01
NAMEDIR=02_analyze_clim
WORKDIR=${BASEDIR}/${NAMEDIR}

# Activate the Python virtual environment
#source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=${BASEDIR}/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=${BASEDIR}/ONLINE

OUTDIR=${WORKDIR}/plots

mkdir -p "$OUTDIR"
#python -u timeseries_at_depth.py -o "$OUTDIR" -v O2o
#python timeseries_qc_pres_sal_rho.py -o "$WORKDIR/plots_qc_pres_sal_rho"
python timeseries_qc_pres_sal_rho_line_trend.py -o "$WORKDIR/plots_qc_pres_sal_rho_trend"


OUTDIR=${WORKDIR}/plots/Hov
source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
python Hovmoeller_temp_sal_rho_doxy.py -o "$OUTDIR" #--basin alb

python create_pdf_hovmoeller.py -i "$WORKDIR/plots/Hov/" -d superfloat -o "$WORKDIR/plots/Hov/all_basins_superfloat.pdf"

echo "Job end  at: $(date)"

