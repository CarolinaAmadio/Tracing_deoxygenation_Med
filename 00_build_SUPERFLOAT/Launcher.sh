#!/bin/bash

#SBATCH --job-name=fix_qc
#SBATCH -N1
#SBATCH --ntasks-per-node=48
#SBATCH --time=04:30:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

cd "$SLURM_SUBMIT_DIR"
. /g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01/utils/profile.inc

BASEDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01
NAMEDIR=00_build_SUPERFLOAT

echo "Job started at: $(date)"

WORKDIR=${BASEDIR}/${NAMEDIR}

VARNAME='O2o'   # O2o:DOX
DATE_start=19990101
DATE_end=20261231

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export ONLINE_REPO=${BASEDIR}/ONLINE

# preparo il dataset
export PYTHONPATH=${WORKDIR}/bit.sea/src
OUTDIR=${BASEDIR}/ONLINE/SUPERFLOAT
DOXY_DIAG_DIR=${WORKDIR}/oxy_diag
mkdir -p "$OUTDIR" "$DOXY_DIAG_DIR"


cd "${WORKDIR}/bit.sea/src/bitsea/Float/" || exit 1

my_prex "python superfloat_chla.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
# to plot the oxy diagn : -f --make_plots to ingore rempve args 
my_prex "python superfloat_oxygen.py -s $DATE_start -e $DATE_end -o $OUTDIR -O $DOXY_DIAG_DIR -f --make_plots -w 48"
my_prex "python superfloat_nitrate.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
my_prex "python superfloat_par.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
my_prex "python superfloat_ph.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
my_prex "python superfloat_bbp700.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
my_prex "python superfloat_kd490.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
my_prex "python dump_index.py -i $OUTDIR -o ${OUTDIR}/Float_Index.txt -t superfloat"


cd "$WORKDIR"


# QC REPORT FOR DOXY

OUTDIR_rej=${DOXY_DIAG_DIR}/float_stat_rejection.csv
OUTDIR_acc=${DOXY_DIAG_DIR}/float_stat_accepted.csv

# create a pdf with all figs created in superloat_oxygen.py
# All oxygen diagnostics are kept under oxy_diag.
python drift_plots_to_pdf.py -i "${DOXY_DIAG_DIR}/PLOTS_DRIFT/" -o "${DOXY_DIAG_DIR}/PLOTS_DRIFT/PLOTS_DRIFT.pdf"
python rejection_summary_by_basin.py -i "${DOXY_DIAG_DIR}/" -o "$OUTDIR_rej"
python accepted_summary_by_basin.py -i "${DOXY_DIAG_DIR}/Floats_accepted.csv" -o "$OUTDIR_acc"


# if needed we compare CORIOLIS and SUPERFLOAT profile.
# hardcoded wmo e n profile
#python single_float_comparison_cor_superf.py

