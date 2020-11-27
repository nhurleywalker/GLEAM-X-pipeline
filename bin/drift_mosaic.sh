#! /bin/bash

usage()
{
echo "drift_mosaic.sh [-p project] [-d dep] [-q queue] [-a account] [-t] [-r ra] [-e dec] -o list_of_observations.txt
  -p project  : project, (must be specified, no default)
  -d dep     : job number for dependency (afterok)
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  -r RA       : Right Ascension (decimal hours; default = guess from observation list)
  -e dec      : Declination (decimal degrees; default = guess from observation list)
  -o obslist  : the list of obsids to process" 1>&2;
exit 1;
}

pipeuser=$(whoami)

#initial variables
dep=
queue="-p ${GXSTANDARDQ}"
tst=
ra=
dec=

# parse args and set options
while getopts ':td:p:o:r:e:' OPTION
do
    case "$OPTION" in
    d)
        dep=${OPTARG} ;;
    p)
        project=${OPTARG} ;;
	o)
	    obslist=${OPTARG} ;;
    r)
        ra=${OPTARG} ;;
    e)
        dec=${OPTARG} ;;
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
    numfiles=$(wc -l ${obslist} | awk '{print $1}')
fi

if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

if [[ ! -z ${GXACCOUNT} ]]
then
    account="--acount=${GXACCOUNT}"
fi

queue="-p ${GXSTANDARDQ}"
base="${GXSCRATCH}/${project}"
cd "${base}" || exit

obss=($(sort $obslist))
listbase=$(basename "${obslist}")
listbase=${listbase%%.*}
script="${GXSCRIPT}/mosaic_${listbase}.sh"

cat "${GXBASE}/bin/mosaic.tmpl" | sed -e "s:OBSLIST:${obslist}:g" \
                                      -e "s:RAPOINT:${ra}:g" \
                                      -e "s:DECPOINT:${dec}:g" \
                                      -e "s:BASEDIR:${base}:g" \
                                      -e "s:PIPEUSER:${pipeuser}:g" > "${script}"

output="${GXLOG}/mosaic_${listbase}.o%A_%a"
error="${GXLOG}/mosaic_${listbase}.e%A_%a"

chmod 755 "${script}"

# sbatch submissions need to start with a shebang
echo '#!/bin/bash' > "${script}.sbatch"
echo "singularity run ${GXCONTAINER} ${script}" >> "${script}.sbatch"

# Automatically runs a job array for each sub-band
sub="sbatch --array=0-4  --export=ALL  --time=12:00:00 --mem=${GXABSMEMORY}G -M ${GXCOMPUTER} --output=${output} --error=${error}"
sub="${sub} ${GXNCPULINE} ${account} ${GXTASKLINE} ${depend} ${queue} ${script}.sbatch"
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
error=$(${error//%A/"${jobid}"})
output=$(${output//%A/"${jobid}"})

# record submission
# if [ "${GXTRACK}" = "track" ]
# then
#     for taskid in $(seq 0 1 4)
#     do
#         for obsnum in "${obss[@]}"
#         do
#             track_task.py queue_mosaic --jobid="${jobid}" --taskid="${taskid}" --task='mosaic' --submission_time="$(date +%s)" --batch_file="${script}" \
#                                     --obs_id="${obsnum}" --stderr="${error}" --stdout="${output}"
#         done
#     done
# fi
echo "Submitted ${script} as ${jobid} . Follow progress here:"
echo "${output}"
echo "${error}"
