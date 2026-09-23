#!/bin/bash

#SBATCH --job-name=03_calc_canyon
#SBATCH -N1 
#SBATCH --ntasks-per-node=16
#SBATCH --time=12:30:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

cd $SLURM_SUBMIT_DIR
BASEDIR=Tracing_deoxygenation_Med_ISSUE_01
WORKDIR=/g100_scratch/userexternal/camadio0/${BASEDIR}/

cd $SLURM_SUBMIT_DIR
. ${WORKDIR}/utils/profile.inc

echo "Job started at: $(date)"

source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
export ONLINE_REPO=${WORKDIR}/ONLINE/
export PYTHONPATH=${WORKDIR}/bit.sea/src:$PYTHONPATH

CORIOLIS=${WORKDIR}/ONLINE/CORIOLIS/
INPUTDIR=${WORKDIR}/ONLINE/SUPERFLOAT/
OUTDIR=${WORKDIR}/ONLINE/CANYON_MED_QC/

mkdir -p $OUTDIR

my_prex_or_die "python -u canyonmed.py -i $INPUTDIR -o $OUTDIR -c $CORIOLIS"

deactivate
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate

cp -r $INPUTDIR/Float_index.txt $OUTDIR/
my_prex_or_die "python dump_index_canyonmed.py -i $OUTDIR -o ${OUTDIR}/Float_Index.txt -t canyonmed_float"
echo "Job finished at: $(date)"

