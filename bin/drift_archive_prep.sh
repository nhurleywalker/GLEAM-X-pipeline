#! /bin/bash

usage()
{
echo "drift_archive_prep.sh [-d dep] [-p project] [-a account] [-u user] [-e endpoint] [-r remote_directory] [-t] obsnum

Prepares data products for eachobsid for archiving. This involves zipping and cropping certain data products, and moving them into place. This will NOT initiate the transfer to a remote endpoint. 

A SLURM job-array will be used to prepare separate obsids in parallel. 

  -d dep      : job number for dependency (afterok)
  -p project  : project, (must be specified, no default)
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  -o obsnum      : A text file of obsids (newline separated). 
               A job-array task will be submitted to process the collection of obsids. " 1>&2;
exit 1;
}

pipeuser="${GXUSER}"

#initial variables
dep=
tst=

# parse args and set options
while getopts ':td:a:p:o:' OPTION
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
	t)
	    tst=1
	    ;;
    o)
	    obslist=${OPTARG} 
        ;;
	? | : | h)
	    usage
	    ;;
  esac
done

# if obslist is not specified or an empty file then just print help

if [[ -z ${obslist} ]] || [[ ! -s ${obslist} ]] || [[ ! -e ${obslist} ]] || [[ -z $project ]]
then
    usage
fi

queue="-p ${GXSTANDARDQ}"
base="${GXSCRATCH}/${project}"

# Check that directory exists
if [[ ! -d ${base} ]]
then
    echo "ERROR: base directory ${base} does not exist"
    usage
fi

if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

if [[ ! -z ${GXACCOUNT} ]]
then
    account="--account=${GXACCOUNT}"
fi

# Establish job array options
numfiles=$(wc -l "${obslist}" | awk '{print $1}')
jobarray="--array=1-${numfiles}%1"

# start the real program
script="${GXSCRIPT}/darchive_${obsnum}.sh"
cat "${GXBASE}/templates/darchive.tmpl" | sed -e "s:OBSNUM:${obslist}:g" \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:PIPEUSER:${pipeuser}:g"  > "${script}"


# Will always be a job array
output="${GXLOG}/darchive_${obsnum}.o%A_%a"
error="${GXLOG}/darchive_${obsnum}.e%A_%a"

chmod 755 "${script}"

# sbatch submissions need to start with a shebang
echo '#!/bin/bash' > ${script}.sbatch
echo "singularity run ${GXCONTAINER} ${script}" >> ${script}.sbatch

if [ ! -z ${GXNCPULINE} ]
then
    # archive only needs a single CPU core
    GXNCPULINE="--ntasks-per-node=1"
fi

sub="sbatch  --export=ALL --time=02:00:00 --mem=24G -M ${GXCOMPUTER} --output=${output} --error=${error} "
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
    obserror=$(echo "${error}" | sed -e "s/%A/${jobid}/" -e "s/%a/${taskid}/")
    obsoutput=$(echo "${output}" | sed -e "s/%A/${jobid}/" -e "s/%a/${taskid}/")

    obs=$(sed -n -e "${taskid}p" "${obslist}")
    
    if [ "${GXTRACK}" = "track" ]
    then
    # record submission
    ${GXCONTAINER} track_task.py queue --jobid="${jobid}" --taskid="${taskid}" --task='archive' --submission_time="$(date +%s)" --batch_file="${script}" \
                        --obs_id="${obs}" --stderr="${obserror}" --stdout="${obsoutput}"
    fi

    echo "${obsoutput}"
    echo "${obserror}"
done
