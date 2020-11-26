#! /bin/bash

usage()
{
echo "obs_manta.sh [-p project] [-d dep] [-q queue] [-s timeave] [-k freqav] [-t] -o list_of_observations.txt
  -d dep      : job number for dependency (afterok)
  -p project  : project, (must be specified, no default)
  -s timeres  : time resolution in sec. default = 2 s
  -k freqres  : freq resolution in KHz. default = 40 kHz
  -f edgeflag : number of edge band channels flagged. default = 80
  -e expiry   : number of days datafile will be available for download for. default = 7
  -g          : download gpubox fits files instead of measurement sets
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  -o obslist  : the list of obsids to process" 1>&2;
exit 1;
}

# Supercomputer options
# Hardcode for downloading
if [ -z $GXCOPYA ] 
then
    account="--account ${GXCOPYA}"
fi
standardq="${GXCOPYQ}"

pipeuser=$(whoami)

#initial variables
dep=
queue="-p $standardq"
tst=
gpubox=
timeres=
freqres=
edgeflag=80
expiry=7

# parse args and set options
while getopts ':tgd:p:s:k:o:f:e:' OPTION
do
    case "$OPTION" in
    d)
        dep=${OPTARG} ;;
    p)
        project=${OPTARG} ;;
	s)
	    timeres=${OPTARG} ;;
	k)
	    freqres=${OPTARG} ;;
	o)
	    obslist=${OPTARG} ;;
    t)
        tst=1 ;;
    g)
        gpubox=1 ;;
    f)
        edgeflag=${OPTARG} ;;
    e)
        expiry=${OPTARG} ;;
    ? | : | h)
            usage ;;
  esac
done

# if obslist is not specified or an empty file then just print help

if [[ -z ${obslist} ]] || [[ ! -s ${obslist} ]] || [[ ! -e ${obslist} ]] || [[ -z $project ]]
then
    usage
fi

if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

# Add the metadata to the observations table in the database
# import_observations_from_db.py --obsid "${obslist}"

base="${GXSCRATCH}/${project}"
cd "${base}" || exit 1

dllist=""
list=$(cat "${obslist}")
if [[ -e "${obslist}_manta.tmp" ]] ; then rm "${obslist}_manta.tmp" ; fi

# Set up telescope-configuration-dependent options
# Might use these later to get different metafits files etc
for obsnum in $list
do
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

    if [[ -d "${obsnum}/${obsnum}.ms" ]]
    then
        echo "${obsnum}/${obsnum}.ms already exists. I will not download it again."
    else
        if [[ -z ${gpubox} ]]
        then
            echo "obs_id=${obsnum}, job_type=c, timeres=${timeres}, freqres=${freqres}, edgewidth=${edgeflag}, expiry_days=${expiry}, conversion=ms, allowmissing=true, flagdcchannels=true" >>  "${obslist}_manta.tmp"
            stem="ms"
        else
            echo "obs_id=${obsnum}, job_type=d, download_type=vis, expiry_days=${expiry}" >>  "${obslist}_manta.tmp"
            stem="vis"
        fi
        dllist=$dllist"$obsnum "
    fi
done

listbase=$(basename ${obslist})
listbase=${listbase%%.*}
script="${GXSCRIPT}/manta_${listbase}.sh"

echo "obslist is $obslist"

cat "${GXBASE}/templates/manta.tmpl" | sed -e "s:OBSLIST:${obslist}:g" \
                                 -e "s:STEM:${stem}:g"  \
                                 -e "s:BASEDIR:${base}:g" \
                                 -e "s:PIPEUSER:${pipeuser}:g" > "${script}"

output="${GXLOG}/manta_${listbase}.o%A"
error="${GXLOG}/manta_${listbase}.e%A"

chmod 755 "${script}"

# sbatch submissions need to start with a shebang
echo '#!/bin/bash' > "${script}.sbatch"
echo 'module load singularity' >> "${script}.sbatch"
echo "singularity run -B '${GXHOME}:${HOME}' ${GXCONTAINER} ${script}" >> "${script}.sbatch"

# This is the only task that should reasonably be expected to run on another cluster. 
# Export all GLEAM-X pipeline configurable variables and the MWA_ASVO_API_KEY to ensure 
# obs_mantra completes as expected
sub="sbatch --export=$(echo ${!GX*} | tr ' ' ','),MWA_ASVO_API_KEY  --time=12:00:00 -M ${GXCOPYM} --output=${output} --error=${error}"
sub="${sub} ${account} ${queue} ${script}.sbatch"

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
error="${error//%A/${jobid[0]}}"
output="${output//%A/${jobid[0]}}"

# record submission
n=1
for obsnum in $dllist
do
    if [ "${GXTRACK}" = "track" ]
    then
        track_task.py queue --jobid="${jobid[0]}" --taskid="${n}" --task='download' --submission_time="$(date +%s)" \
                        --batch_file="${script}" --obs_id="${obsnum}" --stderr="${error}" --stdout="${output}"
    fi
    ((n+=1))
done

echo "Submitted ${script} as ${jobid}. Follow progress here:"
echo "${output}"
echo "${error}"
