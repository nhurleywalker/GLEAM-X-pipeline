#! /bin/bash

usage()
{
echo "obs_idg.sh [-p project] [-d dep] [-s] [-t] -o list_of_observations.txt
  -d dep      : job number for dependency (afterok)
  -p project  : project, (must be specified, no default)
  -s          : perform self-calibration after one round of IDG (default = False)
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  -o obslist  : the list of obsids to process.
                Job and output image names will be based on the name of this file." 1>&2;
exit 1;
}

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    prep_computer="zeus"
    prep_ncpus=28
    prep_memory=128
    prepq="workq"
    prep_account="pawsey0272"
    computer="zeus"
    account="pawsey0272"
    standardq="gpuq"
# 28 cores, 256GB RAM, and 4 GPUs on Zeus gpuq nodes; we should use a job-packing script to split in four
# But at the moment we cannot! So we just ask for the whole node
    ncpus=28
    memory=256
elif [[ "${HOST:0:4}" == "magn" ]] || [[ "${HOST:0:4}" == "topa" ]]
then
    prep_computer="magnus"
    prep_ncpus=20
    prep_memory=60
    prep_account="pawsey0272"
    prepq="workq"
    computer="topaz"
    account="pawsey0272"
    standardq="gpuq"
# 16 cores, 187GB useable RAM, and 2 GPUs on Topaz gpuq nodes; therefore we ask for 1/2 of a node
#    ncpus=8
#    memory=93
    ncpus=16
    memory=187
fi

# Regardless of where you're logged in to, Zeus is the machine to do the fits_warp TEC screen preparation

#initial variables

scratch="/astro"
group="/group"
base="$scratch/mwasci/$USER/"
dbdir="$group/mwasci/$USER/GLEAM-X-pipeline/"
dep=
queue="-p $standardq"
tst=false
selfcal=false

# parse args and set options
while getopts ':td:p:so:' OPTION
do
    case "$OPTION" in
    d)
        dep=${OPTARG} ;;
    p)
        project=${OPTARG} ;;
	q)
	    queue="-p ${OPTARG}" ;;
	o)
	    obslist=${OPTARG} ;;
	s)
	    selfcal=true ;;
    t)
        tst=true ;;
        ? | : | h)
            usage ;;
  esac
done

# if obslist is not specified or an empty file then just print help

if [[ -z ${obslist} ]] || [[ ! -s ${obslist} ]] || [[ ! -e ${obslist} ]] || [[ -z $project ]]
then
    usage
else
    numfiles=`wc -l ${obslist} | awk '{print $1}'`
fi

if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

base=$base$project
cd $base

list=`sort $obslist`
for obsnum in $list
do
    if [[ ! -d ${obsnum}/${obsnum}.ms ]]
    then
        echo "${obsnum}/${obsnum}.ms does not exist; cannot run IDG on this group of observations."
        exit 1
    fi
done

# Name of all the jobs based on this list of observations
obslistbase=`basename $obslist`
jobname=${obslistbase%.*}

# How many observations
obss=($(sort $obslist))
num=${#obss[@]}

screens=""
for obsnum in ${obss[@]} ; do screens="$screens $obsnum/${obsnum}_screen-image_dldm.fits" ; done

# The script that prepares each observation ready for IDG:
# Must run on Zeus due to fits_warp
# Runs chgcentre to put them all at the same phase centre
# Makes an initial image with a shallow clean
# Does some source-finding, runs fits_warp, and determines the TEC screens
prep_script=${dbdir}queue/prep_${jobname}.sh
array_line="#SBATCH --array=1-${num}"
task_line="#SBATCH --ntasks=${prep_ncpus}"
cat ${dbdir}bin/prep_IDG.tmpl | sed -e "s:OBSLIST:${obslist}:g" \
                                -e "s:BASEDIR:${base}:g" \
                                -e "s:HOST:${prep_computer}:g"  \
                                -e "s:NCPUS:${prep_ncpus}:g"  \
                                -e "s:MEMORY:${prep_memory}:g"  \
                                -e "s:ACCOUNT:${prep_account}:g" \
                                -e "s:STANDARDQ:${prepq}:g" \
                                -e "s:ARRAYLINE:${array_line}:g" \
                                -e "s:TASKLINE:${task_line}:g" \
                                -e "s:DBDIR:${dbdir}:g" > ${prep_script}
output_prep="${dbdir}queue/logs/idg_prep_${jobname}.o%A"
error_prep="${dbdir}queue/logs/idg_prep_${jobname}.e%A"
chmod +x $prep_script

# An srun script that runs on Zeus or Topaz
# Will be submitted by the wrap script
# Needs to be defined here because it needs to go in the wrap script
srun_script=${dbdir}queue/srun_${jobname}.sh
cat ${dbdir}bin/srun_IDG.tmpl | sed -e "s:JOBNAME:${jobname}:g" \
                                 -e "s:HOST:${computer}:g"  \
                                 -e "s:NCPUS:${ncpus}:g"  \
                                 -e "s:MEMORY:${memory}:g"  \
                                 -e "s:ACCOUNT:${account}:g" \
                                 -e "s:STANDARDQ:${standardq}:g" \
                                 -e "s:DBDIR:${dbdir}:g" \
                                 -e "s:BASEDIR:${base}:g"  > ${srun_script}
chmod +x $srun_script

# A very simple wrapper script that depends on the array job being finished
# Runs on Zeus due to lack of cross-cluster dependencies
# Will submit the IDG run when it has finished
wrap_script=${dbdir}queue/wrap_${jobname}.sh
wrap_output="${dbdir}queue/logs/wrap_idg_${jobname}.o%A"
wrap_error="${dbdir}queue/logs/wrap_idg_${jobname}.e%A"
idg_output="${dbdir}queue/logs/idg_${jobname}.o%A"
idg_error="${dbdir}queue/logs/idg_${jobname}.e%A"
cat ${dbdir}bin/wrap_prep_IDG.tmpl | sed -e "s:JOBNAME:${jobname}:g" \
                                 -e "s:OBSLIST:${obslist}:g" \
                                 -e "s:HOST:${prep_computer}:g"  \
                                 -e "s:COMPUTER:${computer}:g"  \
                                 -e "s:ACCOUNT:${prep_account}:g" \
                                 -e "s:STANDARDQ:${prepq}:g" \
                                 -e "s:WRAP_OUTPUT:${wrap_output}:g" \
                                 -e "s:WRAP_ERROR:${wrap_error}:g" \
                                 -e "s:IDG_OUTPUT:${idg_output}:g" \
                                 -e "s:IDG_ERROR:${idg_error}:g" \
                                 -e "s:SRUN_SCRIPT:${srun_script}:g" \
                                 -e "s:DBDIR:${dbdir}:g" \
                                 -e "s:BASEDIR:${base}:g"  > ${wrap_script}
chmod +x $wrap_script

# The main script that runs IDG on the prepared observation, running on Zeus or Topaz in a container
main_script=${dbdir}queue/idg_${jobname}.sh
cat ${dbdir}bin/IDG.tmpl | sed -e "s:OBSLIST:${obslist}:g" \
                                -e "s:BASEDIR:${base}:g" \
                                -e "s:NCPUS:${ncpus}:g"  \
                                -e "s:JOBNAME:${jobname}:g"  \
                                -e "s:MEMORY:${memory}:g"  \
                                -e "s:DBDIR:${dbdir}:g" \
                                -e "s:SELFCAL:${selfcal}:g" > ${main_script}
chmod +x $main_script

aterm_dest=${datadir}/${jobname}_aterm.config
# The aterm.config file to allow primary-beam and ionospheric correction
cat ${dbdir}bin/aterm.tmpl | sed -e "s:SCREENS:${screens}:g" > ${aterm_dest}

prep_output="${dbdir}queue/logs/prep_idg_${jobname}.o%A_%a"
prep_error="${dbdir}queue/logs/prep_idg_${jobname}.e%A_%a"

if ${tst}
then
    echo "prep script is ${prep_script}"
    echo "wrap script is ${wrap_script}"
    echo "srun script is ${srun_script}"
    echo "main script is ${main_script}"
    exit 0
fi

# submit the preparation job
sub_prep="sbatch -M ${prep_computer} --output=${prep_output} --error=${prep_error} ${depend} ${prep_script}"
jobid=($(${sub_prep}))
jobid=${jobid[3]}
# 
# rename the err/output files as we now know the jobid
prep_error=`echo ${prep_error} | sed "s/%A/${jobid}/"`
prep_output=`echo ${prep_output} | sed "s/%A/${jobid}/"`

# record submission
n=1
for obsnum in $list
do
    python ${dbdir}/bin/track_task.py queue --jobid=${jobid} --taskid=${n} --task='prep_idg' --submission_time=`date +%s` --batch_file=${main_script} \
                     --obs_id=${obsnum} --stderr=${prep_error} --stdout=${prep_output}
    ((n+=1))
done

sub_wrap="sbatch -M ${prep_computer} --depend=afterok:${jobid} ${wrap_script}"
wrapid=($(${sub_wrap}))
wrapid=${wrapid[3]}

echo "Submitted: ${prep_script} as ${jobid}"
echo "Submitted: ${wrap_script} as ${wrapid}"
echo "${srun_script} and ${main_script} will follow on ${computer}. Follow prep progress here:"
echo $prep_output | sed "s/%a/\*/"
echo $prep_error | sed "s/%a/\*/"
