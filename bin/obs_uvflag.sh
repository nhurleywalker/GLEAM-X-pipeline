#! /bin/bash

#set -x

usage()
{
echo "obs_uvflag.sh [-p project] [-d dep] [-a account] [-z] [-t] obsnum
  -p project : project, no default
  -d dep     : job number for dependency (afterok)
  -a account : computing account, default pawsey0272
  -z         : Debugging mode: flag the CORRECTED_DATA column
                instead of flagging the DATA column
  -t         : test. Don't submit job, just make the batch file
               and then return the submission command
  obsnum     : the obsid to process" 1>&2;
exit 1;
}

dep=
tst=
debug=

# parse args and set options
while getopts ':tza:d:p:' OPTION
do
    case "$OPTION" in
	d)
	    dep=${OPTARG}
	    ;;
    a)
        account=${OPTARG}
        ;;
	p)
	    project=${OPTARG}
	    ;;
	z)
	    debug=1
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

# if obsid or project are empty then just pring help
if [[ -z ${obsnum} || -z ${project} ]]
then
    usage
fi

if [[ -z ${account} ]]
then
    account=pawsey0272
fi

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    computer="zeus"
    standardq="workq"
    ncpus=28
    taskline="#SBATCH --ntasks=${ncpus}"
#    absmem=60
#    standardq="gpuq"
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    standardq="workq"
    ncpus=48
    taskline=""
#    absmem=60
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    standardq="gpuq"
    ncpus=40
    taskline=""
#    absmem=30 # Check this
fi

dbdir="/group/mwasci/$USER/GLEAM-X-pipeline/"
codedir="/group/mwasci/$USER/GLEAM-X-pipeline/"
queue="-p $standardq"
datadir=/astro/mwasci/$USER/$project

# set dependency
if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

script="${codedir}queue/uvflag_${obsnum}.sh"

#                                     -e "s:DBDIR:${dbdir}:g" \
cat ${codedir}bin/uvflag.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                     -e "s:DATADIR:${datadir}:g" \
                                     -e "s:HOST:${computer}:g" \
                                     -e "s:TASKLINE:${taskline}:g" \
                                     -e "s:STANDARDQ:${standardq}:g" \
                                     -e "s:DEBUG:${debug}:g" \
                                     -e "s:ACCOUNT:${account}:g" > ${script}

output="${codedir}queue/logs/uvflag_${obsnum}.o%A"
error="${codedir}queue/logs/uvflag_${obsnum}.e%A"

#sub="sbatch -M $computer --output=${output} --error=${error} --begin=now+3hours ${depend} ${queue} ${script}"
sub="sbatch -M $computer --output=${output} --error=${error} ${depend} ${queue} ${script}"

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
python ${dbdir}/bin/track_task.py queue --jobid=${jobid} --taskid=${taskid} --task='uvflag' --submission_time=`date +%s` --batch_file=${script} \
                     --obs_id=${obsnum} --stderr=${error} --stdout=${output}

echo "Submitted ${script} as ${jobid} . Follow progress here:"
echo $output
echo $error

