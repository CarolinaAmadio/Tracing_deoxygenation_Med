#!/bin/bash

#SBATCH --job-name=03_calc_NN
#SBATCH -N1 -n 1
#SBATCH --time=01:30:00
##SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
##SBATCH --partition=g100_meteo_prod
#SBATCH --partition=g100_usr_prod
##SBATCH --qos=qos_meteo

###
### 1. calculate ppcon ./opa_downloader.src_ksh lines 154
###    from git@gitlab.hpc.cineca.it:OGS/v5c.git
### training statig data /g100_work/OGS_prod2528/OPA/V12C-prod/etc/static-data/FLOAT/PPCON_TRAIN/

###
BASEDIR=Tracing_deoxygenation_Med_ISSUE_01
WORKDIR=/g100_scratch/userexternal/camadio0/${BASEDIR}/

cd $SLURM_SUBMIT_DIR
. ${WORKDIR}/utils/profile.inc

echo "Job started at: $(date)"

# iMport bitsea and ONLINE
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export ONLINE_REPO=${WORKDIR}/ONLINE/
export PYTHONPATH=${WORKDIR}/bit.sea/src:$PYTHONPATH

# I/O 
INPUTDIR=${WORKDIR}/ONLINE/SUPERFLOAT/
OUTDIR=${WORKDIR}/ONLINE/PPCON/

# creo dir PPCON e copio il contenuto di SUPERFLOAT in PPCON 
mkdir -p $OUTDIR
NPROC=8
find "$INPUTDIR" -mindepth 1 -maxdepth 1 -type d -print0 |
    xargs -0 -n 1 -P "$NPROC" -I {} \
    rsync -a "{}" "$OUTDIR/"

echo "Copy finished at: $(date)"

TRAIN_DIR=${WORKDIR}/03_calculate_NN_datasets/PPCON/static-data/PPCON_TRAIN/
ONLINE_REPO_CLUSTERING=${ONLINE_REPO}/PPCON/clustering/


mkdir -p $ONLINE_REPO_CLUSTERING

cd  ${WORKDIR}/bit.sea/src/bitsea/Float/ppcon/

my_prex_or_die "python -u clustering/clustering.py -i $ONLINE_REPO -u $ONLINE_REPO/SUPERFLOAT/Float_Index.txt -o $ONLINE_REPO_CLUSTERING"
#cd $SLURM_SUBMIT_DIR 
my_prex_or_die "python -u make_generated_ds/generate_netcdf_netcdf4.py -t $ONLINE_REPO_CLUSTERING -m $TRAIN_DIR -p $ONLINE_REPO/PPCON"
my_prex_or_die "python dump_index.py -i $ONLINE_REPO/PPCON -o $ONLINE_REPO/PPCON/Float_Index.txt -t ppcon_float"


cd $SLURM_SUBMIT_DIR
echo "Job finished at: $(date)"

