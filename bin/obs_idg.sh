#! /bin/bash

usage()
{
echo "obs_idg.sh [-p project] [-d dep] [-q queue] [-s] [-t] -o list_of_observations.txt
  -d dep      : job number for dependency (afterok)
  -q queue    : job queue, default=gpuq
  -p project  : project, (must be specified, no default)
  -s          : perform self-calibration after one round of IDG (default = False)
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  -o obslist  : the list of obsids to process.
                Job and output image names will be based on the name of this file." 1>&2;
exit 1;
}

pipeuser=$(whoami)

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    computer="zeus"
    account="mwasci"
    standardq="gpuq"
# 28 cores, 256GB RAM, and 4 GPUs on Zeus gpuq nodes; we should use a job-packing script to split in four
# But at the moment we cannot! So we just ask for the whole node
    ncpus=28
    memory=256
elif [[ "${HOST:0:4}" == "magn" ]] || [[ "${HOST:0:4}" == "topa" ]]
then
    computer="topaz"
    account="pawsey0272"
    standardq="gpuq"
# 16 cores, 192GB RAM, and 2 GPUs on Topaz gpuq nodes; therefore we ask for 1/2 of a node
    ncpus=8
    memory=96
fi

#initial variables

scratch="/astro"
group="/group"
base="$scratch/mwasci/$pipeuser/"
dbdir="$group/mwasci/$pipeuser/GLEAM-X-pipeline/"
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

list=`cat $obslist`
for obsnum in $list
do
    if [[ ! -d ${obsnum}/${obsnum}.ms ]]
    then
        echo "${obsnum}/${obsnum}.ms does not exist; cannot run IDG on this group of observations."
        exit 1
    fi
done

obslistbase=`basename $obslist`
jobname=${obslistbase%.*}
srun_script=${dbdir}queue/srun_${jobname}.sh

cat ${dbdir}bin/srun_IDG.tmpl | sed -e "s:JOBNAME:${jobname}:g" \
                                 -e "s:HOST:${computer}:g"  \
                                 -e "s:NCPUS:${ncpus}:g"  \
                                 -e "s:MEMORY:${memory}:g"  \
                                 -e "s:ACCOUNT:${account}:g" \
                                 -e "s:STANDARDQ:${standardq}:g" \
                                 -e "s:DBDIR:${dbdir}:g" \
                                 -e "s:BASEDIR:${base}:g"  > ${srun_script}

main_script=${dbdir}queue/idg_${jobname}.sh
cat ${dbdir}bin/IDG.tmpl | sed -e "s:OBSLIST:${obslist}:g" \
                                -e "s:BASEDIR:${base}:g" \
                                -e "s:NCPUS:${ncpus}:g"  \
                                -e "s:MEMORY:${memory}:g"  \
                                -e "s:DBDIR:${dbdir}:g" \
                                -e "s:SELFCAL:${selfcal}:g" > ${main_script}

chmod +x $main_script

output="${dbdir}queue/logs/idg_${jobname}.o%A"
error="${dbdir}queue/logs/idg_${jobname}.e%A"

sub="sbatch --output=${output} --error=${error} ${depend} ${queue} ${srun_script}"
if ${tst}
then
    echo "srun script is ${srun_script}"
    echo "main script is ${main_script}"
    echo "submit via:"
    echo "${sub}"
    exit 0
fi

# submit job
jobid=($(${sub}))
jobid=${jobid[3]}

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid}/"`
output=`echo ${output} | sed "s/%A/${jobid}/"`

# record submission
n=1
for obsnum in $list
do
    python ${dbdir}/bin/track_task.py queue --jobid=${jobid} --taskid=${n} --task='idg' --submission_time=`date +%s` --batch_file=${main_script} \
                     --obs_id=${obsnum} --stderr=${error} --stdout=${output}
    ((n+=1))
done

echo "Submitted ${srun_script} and ${main_script} as ${jobid}. Follow progress here:"
echo $output
echo $error
