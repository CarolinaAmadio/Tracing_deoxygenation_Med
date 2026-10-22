#!/bin/bash

#SBATCH --job-name=03_canyon
#SBATCH -N1 -n 1
#SBATCH --time=06:30:00
##SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
##SBATCH --partition=g100_meteo_prod
#SBATCH --partition=g100_usr_prod
##SBATCH --qos=qos_meteo

#cd $SLURM_SUBMIT_DIR
BASEDIR=Tracing_deoxygenation_Med_ISSUE_01
WORKDIR=/g100_scratch/userexternal/camadio0/${BASEDIR}/

#cd $SLURM_SUBMIT_DIR
. ${WORKDIR}/utils/profile.inc
echo "Job started at: $(date)"

source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
export ONLINE_REPO=${WORKDIR}/ONLINE/
export PYTHONPATH=${WORKDIR}/bit.sea/src:$PYTHONPATH

CORIOLIS=${WORKDIR}/ONLINE/CORIOLIS/
INPUTDIR=${WORKDIR}/ONLINE/SUPERFLOAT/
OUTDIR=${WORKDIR}/ONLINE/CANYONMED/

#CORIOLIS=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01/03_calculate_NN_datasets/CANYONMED/ONLINE/CORIOLIS/
#INPUTDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01/03_calculate_NN_datasets/CANYONMED/ONLINE/SUPERFLOAT/

#OUTDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01/03_calculate_NN_datasets/CANYONMED/ONLINE/CANYONMED/

mkdir -p $OUTDIR

my_prex_or_die "python -u canyonmed.py -i $INPUTDIR -o $OUTDIR -c $CORIOLIS"

deactivate
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate

cp -r $INPUTDIR/Float_Index.txt $OUTDIR/

my_prex_or_die "python -u dump_index_canyonmed.py -i $OUTDIR -o ${OUTDIR}/Float_Index.txt -t canyonmed_float"
echo "Job finished at: $(date)"

