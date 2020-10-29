#! /bin/bash

endpoint='146.118.69.100' #HOST is already used as a keyword in other script
user='ubuntu'
remote='/mnt/dav/GLEAM-X/Archived_Obsids'

usage()
{
echo "obs_archive.sh [-d dep] [-p project] [-a account] [-u user] [-e endpoint] [-r remote_directory] [-t] obsnum

Archives the processed data products onto the data central archive system. By default traffic is routed through a nimbus instance, requiring a public ssh key to first be added to list of authorized keys. Data Central runs ownCloud, and at the moment easiest way through is a davfs2 mount. Consult Natasha or Tim. 

  -d dep      : job number for dependency (afterok)
  -a account  : computing account, default pawsey0272
  -p project  : project, (must be specified, no default)
  -u user     : user name of system to archive to (default: '$user')
  -e endpoint : hostname to copy the archive data to (default: '$endpoint')
  -r remote   : remote directory to copy files to (default: '$remote')
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  obsnum      : the obsid to process, or a text file of obsids (newline separated). 
               A job-array task will be submitted to process the collection of obsids. " 1>&2;
exit 1;
}

pipeuser="${GXUSER}"

#initial variables
dep=
tst=

# parse args and set options
while getopts ':td:a:p:u:h:r:' OPTION
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
	u)
        user=${OPTARG}
        ;;
    h)
        endpoint=${OPTARG}
        ;;
    r)
        remote=${OPTARG}
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

queue="-p ${GXSTANDARDQ}"
base="${GXSCRATCH}/${project}"

# if obsid is empty then just print help

if [[ -z ${obsnum} ]] || [[ -z $project ]] || [[ ! -d ${base} ]]
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

if [[ -z ${account} ]]
then
    account=pawsey0272
fi

# Establish job array options
if [[ -f ${obsnum} ]]
then
    numfiles=$(wc -l "${obsnum}" | awk '{print $1}')
    jobarray="--array=1-${numfiles}%1"
else
    numfiles=1
    jobarray=''
fi

# start the real program
script="${GXSCRIPT}/archive_${obsnum}.sh"
cat "${GXBASE}/bin/archive.tmpl" | sed -e "s:OBSNUM:${obsnum}:g" \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:ENDUSER:${user}:g" \
                                 -e "s:ENDPOINT:${endpoint}:g" \
                                 -e "s:REMOTE:${remote}:g" \
                                 -e "s:PIPEUSER:${pipeuser}:g"  > "${script}"

output="${GXLOG}/archive_${obsnum}.o%A"
error="${GXLOG}/archive_${obsnum}.e%A"

if [[ -f ${obsnum} ]]
then
   output="${output}_%a"
   error="${error}_%a"
fi


chmod 755 "${script}"

# sbatch submissions need to start with a shebang
echo '#!/bin/bash' > ${script}.sbatch
echo "singularity run -B '${HOME}:${HOME}' ${GXCONTAINER} ${script}" >> ${script}.sbatch

if [ ! -z ${GXNCPULINE} ]
then
    # archive only needs a single CPU core
    GXNCPULINE="--ntasks-per-node=1"
fi

sub="sbatch  --export=ALL --account=${account} --time=02:00:00 --mem=24G -M ${GXCOMPUTER} --output=${output} --error=${error} "
sub="${sub}  ${GXNCPULINE} ${GXTASKLINE} ${jobarray} ${depend} ${queue} ${script}.sbatch"

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

    if [[ -f ${obsnum} ]]
    then
        obs=$(sed -n -e "${taskid}p" "${obsnum}")
    else
        obs="${obsnum}"
    fi

    if [ "${GXTRACK}" = "track" ]
    then
    # record submission
    track_task.py queue --jobid="${jobid}" --taskid="${taskid}" --task='archive' --submission_time="$(date +%s)" --batch_file="${script}" \
                        --obs_id="${obs}" --stderr="${obserror}" --stdout="${obsoutput}"
    fi

    echo "${obsoutput}"
    echo "${obserror}"
done
