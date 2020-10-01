#! /bin/bash

usage()
{
echo "obs_cotter.sh [-p project] [-d dep] [-a account] [-t] obsnum
  -p project : project, no default
  -d dep      : job number for dependency (afterok)
  -a account : computing account, default pawsey0272
  -s timeres  : time resolution in sec. default = 2 s
  -k freqres  : freq resolution in KHz. default = 40 kHz
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  obsnum      : the obsid to process, or a text file of obsids (newline separated). 
               A job-array task will be submitted to process the collection of obsids. " 1>&2;
exit 1;
}

pipeuser="${GXUSER}"

#initial variables

dep=
timeres=
freqres=
tst=

# parse args and set options
while getopts ':ts:k:p:d:a:' OPTION
do
    case "$OPTION" in
    p)
        project=${OPTARG} ;;
    d)
        dep=${OPTARG} ;;
    a)
        account=${OPTARG} ;;
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

if [[ -z ${account} ]]
then
    account=pawsey0272
fi

# Establish job array options
if [[ -f ${obsnum} ]]
then
    # echo "${obsnum} is a file that exists, proceeding with job-array set up"
    numfiles=$(wc -l "${obsnum}" | awk '{print $1}')
    jobarray="#SBATCH --array=1-${numfiles}"
else
    numfiles=1
    jobarray=''
fi

queue="-p ${GXSTANDARDQ}"
codedir="${GXBASE}"
datadir="${GXSCRATCH}/$project"

if [[ -f ${obsnum} ]]
then
    testobs=$(sed -n -e 1p "${obsnum}")
else
    testobs=${obsnum}
fi

if [[ $testobs -lt 1151402936 ]] ; then
    # MWA128T, basescale 1.1
    if [[ -z $freqres ]] ; then freqres=40 ; fi
    if [[ -z $timeres ]] ; then timeres=4 ; fi
elif [[ $testobs -ge 1151402936 ]] && [[ $testobs -lt 1191580576 ]] ; then
    # MWAHEX, basescale 2.0
    if [[ -z $freqres ]] ; then freqres=40 ; fi
    if [[ -z $timeres ]] ; then timeres=8 ; fi
elif [[ $testobs -ge 1191580576 ]] ; then
    # MWALB, basescale 0.5
    if [[ -z $freqres ]] ; then freqres=40 ; fi
    if [[ -z $timeres ]] ; then timeres=4 ; fi
fi

script="${GXBASE}/queue/cotter_${obsnum}.sh"
cat "${GXBASE}/bin/cotter.tmpl" | sed -e "s:OBSNUM:${obsnum}:g" \
                                  -e "s:DATADIR:${datadir}:g" \
                                  -e "s:TASKLINE:${GXTASKLINE}:g" \
                                  -e "s:TRES:${timeres}:g" \
                                  -e "s:FRES:${freqres}:g" \
                                  -e "s:MEMORY:${GXMEMORY}:g" \
                                  -e "s:HOST:${GXCOMPUTER}:g" \
                                  -e "s:STANDARDQ:${GXSTANDARDQ}:g" \
                                  -e "s:ACCOUNT:${account}:g" \
                                  -e "s:PIPEUSER:${pipeuser}:g" \
                                  -e "s:ARRAYLINE:${jobarray}:g" > ${script}

output="${GXLOG}/cotter_${obsnum}.o%A"
error="${GXLOG}/cotter_${obsnum}.e%A"
if [[ -f ${obsnum} ]]
then
   output="${output}_%a"
   error="${error}_%a"
fi

sub="sbatch -M ${GXCOMPUTER} --begin=now+15 --output=${output} --error=${error} ${depend} ${queue} ${script}"
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

echo "Submitted ${script} as ${jobid} Follow progress here:"

for taskid in $(seq ${numfiles})
do
    # rename the err/output files as we now know the jobid
    obserror=$(echo "${error}" | sed -e "s/%A/${jobid}/" | sed -e "s/%a/${taskid}/")
    obsoutput=$(echo "${output}" | sed -e "s/%A/${jobid}/" | sed -e "s/%a/${taskid}/")
    
    if [[ -f ${obsnum} ]]
    then
        obs=$(sed -n -e "${taskid}"p "${obsnum}")
    else
        obs=$obsnum
    fi

    # record submission
    track_task.py queue --jobid="${jobid}" --taskid="${taskid}" --task='cotter' --submission_time="$(date +%s)" --batch_file="${script}" \
                        --obs_id="${obs}" --stderr="${obserror}" --stdout="${obsoutput}"

    echo "$obsoutput"
    echo "$obserror"
done
