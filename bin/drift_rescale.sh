#! /bin/bash

usage()
{
echo "drift_rescale.sh [-p project] [-d dep] [-q queue] [-a account] [-t] [-r] [-e dec] -o list_of_observations.txt
  -p project  : project, (must be specified, no default)
  -d dep     : job number for dependency (afterok)
  -q queue    : job queue, default=workq
  -a account : computing account, default pawsey0272
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  -r read : read existing solutions instead of writing new ones
  -o obslist  : the list of obsids to process" 1>&2;
exit 1;
}

pipeuser=$(whoami)

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    computer="zeus"
    standardq="workq"
    ncpus=28
#    absmem=60
#    standardq="gpuq"
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    standardq="workq"
    ncpus=24
#    absmem=60
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    standardq="gpuq"
#    absmem=30 # Check this
fi

#initial variables

scratch="/astro"
group="/group"
base="$scratch/mwasci/$pipeuser/"
dbdir="$group/mwasci/$pipeuser/GLEAM-X-pipeline/"
dep=
queue="-p $standardq"
account=
tst=
readfile=

# parse args and set options
while getopts ':td:p:q:o:r' OPTION
do
    case "$OPTION" in
    d)
        dep=${OPTARG} ;;
    p)
        project=${OPTARG} ;;
	q)
	    queue="-p ${OPTARG}" ;;
	a)
	    account=${OPTARG} ;;
	o)
	    obslist=${OPTARG} ;;
    r)
        readfile=1 ;;
    t)
        tst=1 ;;
    g)
        gpubox=1 ;;
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

if [[ -z ${account} ]]
then
    account=pawsey0272
fi

base=$base/$project
cd $base

obss=($(sort $obslist))
listbase=`basename ${obslist}`
listbase=${listbase%%.*}
script="${dbdir}queue/rescale_${listbase}.sh"

cat ${dbdir}/bin/rescale.tmpl | sed -e "s:OBSLIST:${obslist}:g" \
                                 -e "s:ACCOUNT:${account}:g" \
                                 -e "s:READ:${readfile}:g" \
                                 -e "s:BASEDIR:${base}:g"  \
                                 -e "s:PIPEUSER:${pipeuser}:g" > ${script}

output="${dbdir}queue/logs/rescale_${listbase}.o%A_%a"
error="${dbdir}queue/logs/rescale_${listbase}.e%A_%a"

#sub="sbatch --begin=now+15 --output=${output} --error=${error} ${depend} ${queue} ${script}"
sub="sbatch --output=${output} --error=${error} ${depend} ${queue} ${script}"
if [[ ! -z ${tst} ]]
then
    echo "script is ${script}"
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
#n=1
#for obsnum in ${obss[@]}
#do
#    python ${dbdir}/bin/track_task.py queue --jobid=${jobid} --taskid=${n} --task='rescale' --submission_time=`date +%s` --batch_file=${script} \
#                     --obs_id=${obsnum} --stderr=${error} --stdout=${output}
#    ((n+=1))
#done

echo "Submitted ${script} as ${jobid}. Follow progress here:"
echo $output
echo $error
