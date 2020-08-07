#! /bin/bash

usage()
{
echo "obs_manta.sh [-p project] [-d dep] [-q queue] [-s timeave] [-k freqav] [-t] -o list_of_observations.txt
  -d dep      : job number for dependency (afterok)
  -q queue    : job queue, default=copyq
  -p project  : project, (must be specified, no default)
  -s timeres  : time resolution in sec. default = 2 s
  -k freqres  : freq resolution in KHz. default = 40 kHz
  -g          : download gpubox fits files instead of measurement sets
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  -o obslist  : the list of obsids to process" 1>&2;
exit 1;
}

# Supercomputer options
# Hardcode for downloading
computer="zeus"
account="mwasci"
standardq="copyq"

#initial variables

scratch="/astro"
group="/group"
base="$scratch/mwasci/$USER/"
dbdir="$group/mwasci/$USER/GLEAM-X-pipeline/"
dep=
queue="-p $standardq"
tst=
gpubox=
timeres=
freqres=

source "$dbdir/GLEAM-X-pipeline.profile"

# parse args and set options
while getopts ':tgd:p:s:k:o:' OPTION
do
    case "$OPTION" in
    d)
        dep=${OPTARG} ;;
    p)
        project=${OPTARG} ;;
	q)
	    queue="-p ${OPTARG}" ;;
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

# Add the metadata to the observations table in the database
python ${dbdir}db/import_observations_from_db.py --obsid $obslist

# And now record the apparent brightness of sources in the obs
# this takes a considerable time and shouldn't be done on the 
# login node. 
# python ${dbdir}db/check_sources_vs_obsids.py $obslist


base=$base/$project
cd $base

dllist=""
list=`cat $obslist`
if [[ -e ${obslist}_manta.tmp ]] ; then rm ${obslist}_manta.tmp ; fi
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
    if [[ -d ${obsnum}/${obsnum}.ms ]]
    then
        echo "${obsnum}/${obsnum}.ms already exists. I will not download it again."
    else
        if [[ -z ${gpubox} ]]
        then
            echo "obs_id=${obsnum}, job_type=c, timeres=${timeres}, freqres=${freqres}, edgewidth=80, conversion=ms, allowmissing=true, flagdcchannels=true" >>  ${obslist}_manta.tmp
            stem="ms"
        else
            echo "obs_id=${obsnum}, job_type=d, download_type=vis" >>  ${obslist}_manta.tmp
            stem="vis"
        fi
        dllist=$dllist"$obsnum "
    fi
done

listbase=`basename ${obslist}`
listbase=${listbase%%.*}
script="${dbdir}queue/manta_${listbase}.sh"

echo "obslist is $obslist"

cat ${dbdir}/bin/manta.tmpl | sed -e "s:OBSLIST:${obslist}:g" \
                                 -e "s:STEM:${stem}:g"  \
                                 -e "s:BASEDIR:${base}:g"  > ${script}
#                                 -e "s:ACCOUNT:${account}:g"

output="${dbdir}queue/logs/manta_${listbase}.o%A"
error="${dbdir}queue/logs/manta_${listbase}.e%A"

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
n=1
for obsnum in $dllist
do
    python ${dbdir}/bin/track_task.py queue --jobid=${jobid} --taskid=${n} --task='download' --submission_time=`date +%s` --batch_file=${script} \
                     --obs_id=${obsnum} --stderr=${error} --stdout=${output}
    ((n+=1))
done

echo "Submitted ${script} as ${jobid}. Follow progress here:"
echo $output
echo $error
