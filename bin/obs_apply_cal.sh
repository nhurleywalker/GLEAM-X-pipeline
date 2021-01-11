#! /bin/bash

usage()
{
echo "obs_apply_cal.sh [-p project] [-d dep] [-a account] [-c calid] [-z] [-t] obsnum
  -p project  : project, no default
  -d dep      : job number for dependency (afterok)
  -c calid    : obsid for calibrator.
                project/calid/calid_*_solutions.bin will be used
                to calibrate if it exists. A file can be supplied with the 
                obsids for the calibration fields that correspond to the 
                obsids specified in the obsid file, if it is provided. 
                Otherwise job will fail.
  -z          : Debugging mode: create a new CORRECTED_DATA column
                instead of applying to the DATA column
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  obsnum      : the obsid to process, or a text file of obsids (newline separated)" 1>&2;
exit 1;
}

pipeuser="${GXUSER}"

#initial variables
dep=
calid=
tst=
account=
debug=

# parse args and set options
while getopts ':tzd:a:c:p:' OPTION
do
    case "$OPTION" in
    d)
        dep=${OPTARG}
        ;;
	c)
	    calid=${OPTARG}
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

# if obsid or calid is empty then just print help
if [[ -z ${obsnum} ]] || [[ -z ${calid} ]]
then
    usage
fi

if [[ ! -z ${dep} ]]
then
    if [[ -f ${obsnum} ]]
    then
        depend="--dependency=aftercorr:${dep}"
    else
        depend="--dependency=afterok:${dep}"
    fi
fi

if [[ ! -z ${GXACCOUNT} ]]
then
    account="--account=${GXACCOUNT}"
fi

# Establish job array options
if [[ -f ${obsnum} ]]
then
    numfiles=$(wc -l ${obsnum} | awk '{print $1}')
    jobarray="--array=1-${numfiles}"
else
    numfiles=1
    jobarray=''
fi

# Set directories
queue="-p ${GXSTANDARDQ}"
base="${GXSCRATCH}/${project}"

if [[ $? != 0 ]]
then
    echo "Could not find calibrator file"
    echo "looked for latest of: ${base}/${calid}/${calid}*solutions*.bin"
    exit 1
fi


script="${GXSCRIPT}/apply_cal_${obsnum}.sh"

cat "${GXBASE}/templates/apply_cal.tmpl" | sed -e "s:OBSNUM:${obsnum}:g" \
                                       -e "s:BASEDIR:${base}:g" \
                                       -e "s:DEBUG:${debug}:g" \
                                       -e "s:CALID:${calid}:g" \
                                       -e "s:PIPEUSER:${pipeuser}:g"  > ${script}

chmod 755 "${script}"

output="${GXLOG}/apply_cal_${obsnum}.o%A"
error="${GXLOG}/apply_cal_${obsnum}.e%A"

if [[ -f ${obsnum} ]]
then
    output="${output}_%a"
    error="${error}_%a"
fi

# sbatch submissions need to start with a shebang
echo '#!/bin/bash' > ${script}.sbatch
echo "singularity run ${GXCONTAINER} ${script}" >> ${script}.sbatch

if [ ! -z ${GXNCPULINE} ]
then
    # autoflag only needs a single CPU core
    GXNCPULINE="--ntasks-per-node=1"
fi

sub="sbatch --begin=now+5minutes  --export=ALL ${account} --time=01:00:00 --mem=24G -M ${GXCOMPUTER} --output=${output} --error=${error} "
sub="${sub}  ${GXNCPULINE} ${account} ${GXTASKLINE} ${jobarray} ${depend} ${queue} ${script}.sbatch"

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

echo "Submitted ${script} as ${jobid} . Follow progress here:"

for taskid in $(seq ${numfiles})
    do
    # rename the err/output files as we now know the jobid
    obserror=`echo ${error} | sed -e "s/%A/${jobid}/" -e "s/%a/${taskid}/"`
    obsoutput=`echo ${output} | sed -e "s/%A/${jobid}/" -e "s/%a/${taskid}/"`

    if [[ -f ${obsnum} ]]
    then
        obs=$(sed -n -e ${taskid}p ${obsnum})
    else
        obs=$obsnum
    fi

    if [ "${GXTRACK}" = "track" ]
    then
        # record submission
        ${GXCONTAINER} track_task.py queue --jobid=${jobid} --taskid=${taskid} --task='apply_cal' --submission_time=`date +%s` --batch_file=${script} \
                            --obs_id=${obs} --stderr=${obserror} --stdout=${obsoutput}
    fi

    echo $obsoutput
    echo $obserror
done
