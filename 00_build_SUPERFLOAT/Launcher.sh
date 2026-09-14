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
mkdir -p "$OUTDIR"

cd "${WORKDIR}/bit.sea/src/bitsea/Float/" || exit 1
#my_prex "python superfloat_chla.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
#my_prex "python superfloat_oxygen.py -s $DATE_start -e $DATE_end -o $OUTDIR -O $OUTDIR -f --make_plots -w 48"
#exit 0
#my_prex "python superfloat_oxygen.py -s $DATE_start -e $DATE_end -o $OUTDIR -O $OUTDIR -f -w 48"
#my_prex "python superfloat_nitrate.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
#my_prex "python superfloat_par.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
#my_prex "python superfloat_ph.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
#my_prex "python superfloat_bbp700.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
#my_prex "python superfloat_kd490.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
#my_prex "python dump_index.py -i $OUTDIR -o ${OUTDIR}/Float_Index.txt -t superfloat"



cd "$WORKDIR"

OUTDIR_rej=${WORKDIR}/float_stat_rejection.csv
OUTDIR_acc=${WORKDIR}/float_stat_accepted.csv

#exit 0
#python drift_plots_to_pdf.py -i "${OUTDIR}/PLOTS_DRIFT/" -o /g100_work/OGS_test2528/internal-validation/pub/camadio/Tracing_deoxygenation_Med/PLOTS_DRIFT/PLOTS_DRIFT.pdf

python rejection_summary_by_basin.py -i "${OUTDIR}/" -o "$OUTDIR_rej"
python accepted_summary_by_basin.py -i "${OUTDIR}/Floats_accepted.csv" -o "$OUTDIR_acc"




exit 0
## plot figs 
cd "$SLURM_SUBMIT_DIR"
for NAME_TEST in fix_qc; do
#for NAME_TEST in master fix_qc to_test; do
	OUTDIR_fig=DOXY_FIGS_$NAME_TEST/
	mkdir -p "$OUTDIR_fig"
	
	OUTDIR=${BASEDIR}/ONLINE/SUPERFLOAT_$NAME_TEST
	ln -s "$OUTDIR" "${BASEDIR}/ONLINE/SUPERFLOAT"
	my_prex "python -u timeseries_at_depth.py -o $OUTDIR_fig -v $VARNAME"
	rm -f "${BASEDIR}/ONLINE/SUPERFLOAT"
done


echo "Job end at: $(date)"	
#python single_float_comparison_cor_superf.py
