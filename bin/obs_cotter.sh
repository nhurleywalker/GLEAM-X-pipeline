#! /bin/bash

usage()
{
echo "obs_cotter.sh [-p project] [-d dep] [-q queue] [-t] obsnum
  -p project : project, no default
  -d dep      : job number for dependency (afterok)
  -q queue    : job queue, default=workq
  -s timeres  : time resolution in sec. default = 2 s
  -k freqres  : freq resolution in KHz. default = 40 kHz
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  obsnum      : the obsid to process" 1>&2;
exit 1;
}

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    computer="zeus"
    account="pawsey0272"
    standardq="workq"
    absmem=120
    memory=110
    ncpus=28
    taskline="#SBATCH --ntasks=${ncpus}"
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    account="pawsey0272"
    standardq="workq"
    absmem=60
    memory=55
    ncpus=48
    taskline=""
fi

#initial variables

dep=
queue=
timeres=
freqres=
tst=

# parse args and set options
while getopts ':tp:d:q:' OPTION
do
    case "$OPTION" in
    p)
        project=${OPTARG} ;;
    d)
        dep=${OPTARG} ;;
	q)
	    queue="${OPTARG}" ;;
    s)
        timeres=${OPTARG} ;;
    k)
        freqres=${OPTARG} ;;
    t)
        tst=1 ;;
    ? | : | h)
        usage ;;
  esac
done

# set the obsid to be the first non option
shift  "$(($OPTIND -1))"
obsnum=$1

# if obsid is empty then just print help

if [[ -z ${obsnum} ]] 
then
    usage
fi

if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

if [[ -z ${queue} ]]
then
    queue="-p $standardq"
else
    queue="-p $queue"
fi

dbdir="/group/mwasci/$USER/GLEAM-X-pipeline/"
codedir="/group/mwasci/$USER/GLEAM-X-pipeline/"
datadir=/astro/mwasci/$USER/$project

if [[ $obsnum -lt 1151402936 ]] ; then
    telescope="MWA128T"
    basescale=1.1
    if [[ -z $freqres ]] ; then freqres=40 ; fi
    if [[ -z $timeres ]] ; then timeres=4 ; fi
elif [[ $obsnum -ge 1151402936 ]] && [[ $obsnum -lt 1191580576 ]] ; then
    telescope="MWAHEX"
    basescale=2.0
    if [[ -z $freqres ]] ; then freqres=40 ; fi
    if [[ -z $timeres ]] ; then timeres=8 ; fi
elif [[ $obsnum -ge 1191580576 ]] ; then
    telescope="MWALB"
    basescale=0.5
    if [[ -z $freqres ]] ; then freqres=40 ; fi
    if [[ -z $timeres ]] ; then timeres=4 ; fi
fi

script="${codedir}queue/cotter_${obsnum}.sh"
cat ${codedir}bin/cotter.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                  -e "s:DATADIR:${datadir}:g" \
                                  -e "s:TASKLINE:${taskline}:g" \
                                  -e "s:TRES:${timeres}:g" \
                                  -e "s:FRES:${freqres}:g" \
                                  -e "s:MEMORY:${memory}:g" \
                                  -e "s:HOST:${computer}:g" \
                                  -e "s:STANDARDQ:${standardq}:g" \
                                  -e "s:ACCOUNT:${account}:g" > ${script}

output="${codedir}queue/logs/cotter_${obsnum}.o%A"
error="${codedir}queue/logs/cotter_${obsnum}.e%A"

sub="sbatch -M $computer --begin=now+15 --output=${output} --error=${error} ${depend} ${queue} ${script}"
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
taskid=1

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid}/"`
output=`echo ${output} | sed "s/%A/${jobid}/"`

# record submission
python ${dbdir}/bin/track_task.py queue --jobid=${jobid} --taskid=${taskid} --task='cotter' --submission_time=`date +%s` --batch_file=${script} \
                     --obs_id=${obsnum} --stderr=${error} --stdout=${output}

echo "Submitted ${script} as ${jobid} Follow progress here:"
echo $output
echo $error
