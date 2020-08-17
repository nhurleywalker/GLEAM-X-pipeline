#! /bin/bash

# Script to drive the peeling process. Originally based on the obs_calibrate.sh script. 
usage()
{
echo "obs_peel.sh [-d dep] [-q queue] [-n calname] [-t] obsnum

    Script to drive the peeling process across a set of observation IDs.

  -d dep     : job number for dependency (afterok)
  -q queue   : job queue, default=workq
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process" 1>&2;
exit 1;
}

# Supercomputer options
if [[ "${HOST:0:4}" == "gala" ]]
then
    computer="galaxy"
    account="pawsey0272"
    standardq="workq"
    absmem=60
#    standardq="gpuq"
#    absmem=30
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    account="pawsey0272"
    standardq="workq"
    absmem=60
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    account="pawsey0272"
    standardq="gpuq"
    absmem=30 # Check this
fi

#initialize as empty
scratch=/astro
base="$scratch/mwasci/$USER/GLEAMX/"
dep=
queue='-p workq'
calname=
tst=

# parse args and set options
while getopts ':td:q:' OPTION
do
    case "$OPTION" in
	d)
	    dep=${OPTARG}
	    ;;

	q)
	    queue="-p ${OPTARG}"
	    ;;
	t)
	    tst=1
	    ;;
	? | : | h)
	    usage
	    ;;
  esac
done
# set the obsid to be the first non option
shift  "$(($OPTIND -1))"
obsnum=$1

# if obsid is empty then just pring help
if [[ -z ${obsnum} ]]
then
    usage
fi

# set dependency
if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

script="${base}queue/peel_${obsnum}.sh"

cat ${base}/bin/peel.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                -e "s:BASEDIR:${base}:g" \
                                -e "s:HOST:${computer}:g" \
                                -e "s:STANDARDQ:${standardq}:g" \
                                -e "s:ACCOUNT:${account}:g" > ${script}

output="${base}queue/logs/peel_${obsnum}.o%A"
error="${base}queue/logs/peel_${obsnum}.e%A"

sub="sbatch --begin=now+15 --output=${output} --error=${error} ${depend} ${queue} ${script}"

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

echo "Submitted ${script} as ${jobid}"
